"""
闲鱼网页版协议封装（独立模块，闲鱼协议变动时只需改这里）。

协议思路参考开源项目 XianyuAutoAgent 的逆向成果：
- mtop H5 接口签名：sign = md5(token & t & appKey & data)，token 取 Cookie 中 _m_h5_tk 前段
- token 获取：mtop.goofish.token.get，返回 accessToken 用于 WebSocket 注册
- 长连接：wss://wss-goofish.dingtalk.com/ ，注册后每 15s 心跳
"""
import base64
import hashlib
import json
import re
import time
import uuid
from urllib.parse import unquote

import httpx


APP_KEY = "34839810"
H5_API = "https://h5api.m.goofish.com/h5"
WS_URL = "wss://wss-goofish.dingtalk.com/"
WS_APP_ID = "444e9908-a51b-4b57-850b-687f5cb49b3c"

DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Referer": "https://www.goofish.com/",
    "Origin": "https://www.goofish.com",
}


def parse_cookie(cookie_str: str) -> dict:
    """把浏览器复制的 Cookie 字符串解析为 dict（注意 unquote value）"""
    cookies = {}
    for item in cookie_str.replace("\n", "").split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        k, v = item.split("=", 1)
        cookies[k.strip()] = unquote(v.strip())
    return cookies


def get_m_h5_tk(cookies: dict) -> str:
    """取 _m_h5_tk 的 token 部分（下划线前 32 位），没有则为空串"""
    tk = cookies.get("_m_h5_tk", "")
    return tk.split("_")[0] if tk else ""


def make_sign(token: str, t: str, data: str) -> str:
    raw = f"{token}&{t}&{APP_KEY}&{data}"
    return hashlib.md5(raw.encode()).hexdigest()


async def mtop_request(api: str, data: str, cookies: dict, client: httpx.AsyncClient,
                       version: str = "1.0") -> dict:
    """通用 mtop H5 请求：自动签名，并把响应 Set-Cookie 里的 _m_h5_tk 合并回 cookies"""
    t = str(int(time.time() * 1000))
    sign = make_sign(get_m_h5_tk(cookies), t, data)
    params = {
        "jsv": "2.7.4", "appKey": APP_KEY, "t": t, "sign": sign,
        "api": api, "v": version, "type": "originaljson",
        "dataType": "json", "valueType": "string", "timeout": "20000",
    }
    headers = dict(DEFAULT_HEADERS)
    headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    resp = await client.post(H5_API + f"/{api}/{version}/", params=params, data={"data": data},
                             headers=headers)
    # 响应可能下发新的 _m_h5_tk，合并回 cookies 供下次签名
    for k, v in resp.cookies.items():
        if k.startswith("_m_h5_tk"):
            cookies[k] = v
    return resp.json()


async def get_access_token(cookies: dict, client: httpx.AsyncClient) -> dict:
    """获取 WebSocket 用的 accessToken；成功后 cookies 里会带上新的 _m_h5_tk"""
    res = await mtop_request("mtop.goofish.token.get", "{}", cookies, client)
    data = res.get("data") or {}
    token = data.get("accessToken") or data.get("access_token")
    if not token:
        raise RuntimeError(f"获取 token 失败: {res.get('ret')} （Cookie 大概率已失效）")
    return {"access_token": token, "device_id": data.get("deviceId") or str(uuid.uuid4())}


async def send_text_message(cookies: dict, conversation_id: str, text: str,
                            client: httpx.AsyncClient) -> dict:
    """向指定会话发送文本消息（自动发货的出口动作）"""
    msg_id = str(uuid.uuid4())
    payload = {
        "conversationId": conversation_id,
        "conversationType": "1",
        "contentType": "text",
        "msgId": msg_id,
        "content": json.dumps({"text": text}, ensure_ascii=False),
        "bizScene": "",
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return await mtop_request("mtop.taobao.idle.message.send", data, cookies, client)


async def get_user_id(cookies: dict, client: httpx.AsyncClient) -> str:
    """从 Cookie 里提取当前登录用户ID，取不到再调接口"""
    for key in ("unb", "uid", "tracknick"):
        if cookies.get(key) and re.fullmatch(r"\d+", str(cookies[key])):
            return str(cookies[key])
    try:
        res = await mtop_request("mtop.idle.user.page.head", "{}", cookies, client)
        data = res.get("data") or {}
        uid = data.get("userId") or data.get("userIdLong") or ""
        return str(uid) if uid else ""
    except Exception:
        return ""


def find_first(obj, keys: list):
    """在任意嵌套 JSON 里递归查找第一个命中 key 的值（应对消息结构变化）"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and v not in (None, "", []):
                return v
        for v in obj.values():
            r = find_first(v, keys)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_first(v, keys)
            if r is not None:
                return r
    return None


def try_json_loads(s) -> object | None:
    """尽量把字符串还原成 JSON，失败返回 None"""
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not (s.startswith("{") or s.startswith("[")):
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def decode_sync_data(raw) -> object | None:
    """同步推送包里的 data 可能是 JSON 字符串、二次 JSON 或 base64+zlib 压缩，逐层尝试"""
    if raw is None:
        return None
    obj = try_json_loads(raw) if isinstance(raw, str) else raw
    for _ in range(3):
        if obj is None:
            # 尝试 base64 + zlib 解压
            if isinstance(raw, str):
                try:
                    import zlib
                    obj = json.loads(zlib.decompress(base64.b64decode(raw)).decode("utf-8", "ignore"))
                    break
                except Exception:
                    return None
            else:
                return None
        else:
            # 若字段值本身还是 JSON 字符串，继续展开一层
            if isinstance(obj, dict):
                expanded = False
                for k, v in list(obj.items()):
                    inner = try_json_loads(v) if isinstance(v, str) else None
                    if isinstance(inner, (dict, list)):
                        obj[k] = inner
                        expanded = True
                if not expanded:
                    break
                continue
            break
    return obj


def extract_chat_info(data: dict) -> dict | None:
    """
    从 WebSocket 同步推送中提取会话信息。
    返回 {conversation_id, sender_id, content, item_id, order_id, msg_type} 或 None。
    结构通过递归查找关键字段获取，对闲鱼消息结构调整有较好兼容性。
    """
    big = decode_sync_data(data)
    if not isinstance(big, dict):
        return None

    # 只处理聊天类消息（topic 形如 chattype:message:send / sync）
    topic = str(data.get("headers", {}).get("topic", ""))
    if topic and not (topic.startswith("chattype") or "/sync" in topic):
        return None

    def to_str(v):
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        return str(v)

    conv_id = find_first(big, ["conversationId", "conversationShortId", "cid", "convId"])
    sender = find_first(big, ["senderUserId", "senderUserIdStr", "senderUId", "userId"])
    # 消息正文：优先 text 字段
    content_obj = find_first(big, ["content", "text"])
    if isinstance(content_obj, dict):
        content_obj = content_obj.get("text") or json.dumps(content_obj, ensure_ascii=False)
    content = to_str(content_obj)
    item_id = find_first(big, ["itemId", "itemTagId", "itemTagIdStr"])
    order_id = find_first(big, ["orderId", "bizOrderId", "buyOrderId"])

    if not conv_id or (not content and not order_id):
        return None

    msg_type = "chat"
    # 订单支付成功等系统通知里通常带订单号，标记为 order 事件供发货逻辑判断
    if order_id and (not content or any(kw in content for kw in ("付款", "已拍下", "订单"))):
        msg_type = "order"

    return {
        "conversation_id": to_str(conv_id),
        "sender_id": to_str(sender),
        "content": content,
        "item_id": to_str(item_id),
        "order_id": to_str(order_id),
        "msg_type": msg_type,
    }
