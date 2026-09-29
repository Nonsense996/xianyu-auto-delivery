from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import models, schemas
from ..auth import get_current_admin
from ..services.logging_util import add_log
from ..services import xianyu_api

router = APIRouter(prefix="/api/orders", tags=["orders"], dependencies=[Depends(get_current_admin)])

import httpx


async def _resend(db: AsyncSession, order: models.Order, text_override: str = ""):
    """给失败/待处理订单手动补发"""
    acc = (await db.execute(
        select(models.XianyuAccount).where(models.XianyuAccount.id == order.account_id)
    )).scalar_one_or_none()
    if acc is None:
        raise HTTPException(status_code=400, detail="关联账号已删除，无法补发")
    # 找一张卡密（补发时优先用原来那单绑定的卡密）
    card = None
    if order.card_id:
        card = (await db.execute(
            select(models.CardKey).where(models.CardKey.id == order.card_id)
        )).scalar_one_or_none()
    if card is None and order.product_id:
        card = (await db.execute(
            select(models.CardKey).where(
                models.CardKey.product_id == order.product_id,
                models.CardKey.status == "unused")
            .order_by(models.CardKey.id).limit(1)
        )).scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=400, detail="没有可用卡密")

    text = text_override or order.delivered_content
    if not text:
        p = (await db.execute(
            select(models.Product).where(models.Product.id == order.product_id)
        )).scalar_one_or_none()
        text = p.delivery_template.replace("{card}", card.content) if p else card.content

    conv_id = order.buyer_id  # 由前端在补发时传 conversationId，或按订单号回查
    conv_id = _conv_header.get(order.order_id, conv_id)
    if not conv_id:
        raise HTTPException(status_code=400, detail="缺少会话ID，请通过对话页补发")

    cookies = xianyu_api.parse_cookie(acc.cookie)
    async with httpx.AsyncClient(timeout=15) as client:
        res = await xianyu_api.send_text_message(cookies, conv_id, text, client)
    ret = str(res.get("ret") or res)
    if "FAIL" in ret.upper():
        raise HTTPException(status_code=400, detail=f"闲鱼接口返回失败: {ret[:200]}")

    if order.status != "delivered":
        order.status, order.delivered_content = "delivered", text
        order.delivered_at, order.error_msg = datetime.now(), ""
        order.card_id = card.id
        if card.status == "unused":
            card.status, card.order_id, card.sold_at = "sold", order.order_id, datetime.now()
        await db.commit()
        await add_log(db, "info", "delivery", order.account_id, f"订单 {order.order_id} 手动补发成功")


# 会话ID 由前端临时传入（同一请求内存字典，简化实现）
_conv_header: dict[str, str] = {}


@router.get("")
async def list_orders(status: str = "", account_id: int = 0, page: int = 1, size: int = 20,
                      db: AsyncSession = Depends(get_db)):
    q = select(models.Order)
    cnt_q = select(func.count()).select_from(models.Order)
    if status:
        q, cnt_q = q.where(models.Order.status == status), cnt_q.where(models.Order.status == status)
    if account_id:
        q, cnt_q = (q.where(models.Order.account_id == account_id),
                    cnt_q.where(models.Order.account_id == account_id))
    total = (await db.execute(cnt_q)).scalar()
    items = (await db.execute(
        q.order_by(models.Order.id.desc()).offset((page - 1) * size).limit(size)
    )).scalars().all()
    return {"total": total, "items": [schemas.OrderOut.model_validate(o).model_dump() for o in items]}


@router.post("/{order_id}/resend")
async def resend(order_id: str, conversation_id: str = "", text: str = "",
                 db: AsyncSession = Depends(get_db)):
    """conversation_id：如果之前未记录，需要从闲鱼会话页获取后传入"""
    order = (await db.execute(
        select(models.Order).where(models.Order.order_id == order_id)
    )).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if conversation_id:
        _conv_header[order_id] = conversation_id
    await _resend(db, order, text)
    return schemas.Msg(msg="补发成功")


@router.post("/{order_id}/status")
async def set_status(order_id: str, status: str, db: AsyncSession = Depends(get_db)):
    order = (await db.execute(
        select(models.Order).where(models.Order.order_id == order_id)
    )).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if status not in ("pending", "delivered", "failed", "manual"):
        raise HTTPException(status_code=400, detail="非法状态")
    order.status = status
    await db.commit()
    return schemas.Msg(msg="已更新")
