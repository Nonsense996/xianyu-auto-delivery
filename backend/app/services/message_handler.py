"""
收到买家消息后的业务处理：
1. 订单/付款事件 或 买家发言命中商品 -> 自动发货（发卡密）
2. 普通消息 -> 关键词规则回复 -> 兜底回复
"""
import json
from datetime import datetime

from sqlalchemy import select, update

from ..database import AsyncSessionLocal
from .. import models
from . import xianyu_api
from .logging_util import add_log


async def _log(db, level: str, module: str, account_id: int | None, message: str):
    db.add(models.AppLog(level=level, module=module, account_id=account_id, message=message))
    await db.commit()


async def handle_chat(account_id: int, chat: dict, client):
    """client 需提供 send_text(text) 协程用于回复"""
    async with AsyncSessionLocal() as db:
        # 当前会话对应账号，用于发消息取 Cookie
        acc = (await db.execute(
            select(models.XianyuAccount).where(models.XianyuAccount.id == account_id)
        )).scalar_one_or_none()
        if acc is None or not acc.enabled:
            return

        content = chat["content"]
        conv_id = chat["conversation_id"]

        # 1) 尝试自动发货
        delivered = await try_deliver(db, account_id, chat, client)
        if delivered:
            return

        # 2) 自动回复（关键词规则 -> 兜底）
        await try_reply(db, acc, conv_id, content, client)


async def try_deliver(db, account_id: int, chat: dict, client) -> bool:
    """匹配商品并发货；返回是否发生了发货"""
    item_id, order_id, buyer_msg = chat["item_id"], chat["order_id"], chat["content"]

    # 商品匹配：优先消息里带的商品ID，其次买家消息里直接包含卡密关键词
    product = None
    if item_id:
        product = (await db.execute(
            select(models.Product).where(
                models.Product.account_id == account_id,
                models.Product.xianyu_item_id == item_id,
                models.Product.enabled == True,  # noqa: E712
                models.Product.auto_delivery == True,  # noqa: E712
            )
        )).scalar_one_or_none()

    # 已发货过的订单不重复发
    if order_id:
        existed = (await db.execute(
            select(models.Order).where(models.Order.order_id == order_id)
        )).scalar_one_or_none()
        if existed and existed.status == "delivered":
            return True  # 视为已处理

    # 无商品匹配时，付款事件也可能没有 itemId：尝试用"买家消息包含商品关键词"兜底匹配
    if product is None and buyer_msg:
        candidates = (await db.execute(
            select(models.Product).where(
                models.Product.account_id == account_id,
                models.Product.enabled == True,  # noqa: E712
                models.Product.auto_delivery == True,  # noqa: E712
            )
        )).scalars().all()
        for p in candidates:
            if p.name and p.name in buyer_msg:
                product = p
                break
        # 仅当消息像"拍下/付款/已购"类事件时才允许无精确商品匹配发货
        if product is None and not order_id:
            return False

    if product is None:
        return False

    # 取一张未售卡密（行级锁定用 update...returning 保证并发安全）
    card = (await db.execute(
        select(models.CardKey)
        .where(models.CardKey.product_id == product.id, models.CardKey.status == "unused")
        .order_by(models.CardKey.id)
        .limit(1)
    )).scalars().first()

    order = models.Order(
        order_id=order_id or f"conv-{chat['conversation_id'][:24]}-{int(datetime.now().timestamp())}",
        account_id=account_id, product_id=product.id,
        buyer_id=chat["sender_id"], buyer_message=buyer_msg or "", amount=product.price,
    )
    db.add(order)
    await db.flush()

    if card is None:
        order.status = "failed"
        order.error_msg = "卡密库存不足"
        await db.commit()
        await add_log(db, "error", "delivery", account_id,
                      f"商品「{product.name}」卡密库存不足，订单 {order.order_id} 待人工处理")
        return True

    text = product.delivery_template.replace("{card}", card.content)
    order.card_id = card.id
    order.delivered_content = text
    order.status = "delivered"
    order.delivered_at = datetime.now()

    try:
        res = await xianyu_api.send_text_message(dict(client.cookies), chat["conversation_id"], text, client._client)
        ret = res.get("ret") or []
        if res.get("content") and "SUCCESS" not in json.dumps(res.get("content", {})) and \
                any("FAIL" in str(r) for r in ret):
            raise RuntimeError(str(ret))
        card.status = "sold"
        card.order_id = order.order_id
        card.sold_at = datetime.now()
    except Exception as e:
        order.status = "failed"
        order.error_msg = f"发送失败: {e}"
        await add_log(db, "error", "delivery", account_id,
                      f"订单 {order.order_id} 发送消息失败: {e}（卡密未扣减）")
    await db.commit()
    return True


async def try_reply(db, acc, conv_id: str, content: str, client):
    if not content:
        return
    rules = (await db.execute(
        select(models.ReplyRule)
        .where(models.ReplyRule.enabled == True)  # noqa: E712
        .where((models.ReplyRule.account_id == None) | (models.ReplyRule.account_id == acc.id))  # noqa: E711
        .order_by(models.ReplyRule.priority.desc(), models.ReplyRule.id)
    )).scalars().all()

    for rule in rules:
        keywords = [k.strip() for k in rule.keyword.replace("，", ",").split(",") if k.strip()]
        if any(kw in content for kw in keywords):
            await _send_reply(acc, conv_id, rule.reply_text, client)
            await db.execute(
                update(models.ReplyRule).where(models.ReplyRule.id == rule.id)
                .values(hit_count=rule.hit_count + 1)
            )
            await db.commit()
            return

    dr = (await db.execute(select(models.DefaultReply).limit(1))).scalar_one_or_none()
    if dr and dr.enabled and dr.reply_text:
        await _send_reply(acc, conv_id, dr.reply_text, client)


async def _send_reply(acc, conv_id: str, text: str, client):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            await xianyu_api.send_text_message(dict(client.cookies), conv_id, text, c)
    except Exception as e:
        async with AsyncSessionLocal() as db:
            await add_log(db, "error", "reply", acc.id, f"自动回复发送失败: {e}")
