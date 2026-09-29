"""
每个闲鱼账号一条 WebSocket 长连接：注册 -> 心跳 -> 收消息 -> 交给 message_handler 处理。
由 ws_manager 统一管理生命周期（启动/停止/重连）。
"""
import asyncio
import json
import random
import time
from datetime import datetime

import websockets

from ..database import AsyncSessionLocal
from .. import models
from . import xianyu_api
from .message_handler import handle_chat

HEARTBEAT_INTERVAL = 15
RECONNECT_MIN = 5
RECONNECT_MAX = 300


def _build_register(token: str, device_id: str) -> str:
    return json.dumps({
        "lwp": "/reg",
        "headers": {
            "app_id": xianyu_api.WS_APP_ID,
            "device_id": device_id,
            "os": "web",
        },
        "ext": {
            "type": "app",
            "app_id": xianyu_api.WS_APP_ID,
            "device_id": device_id,
            "os": "web",
            "token": token,
        },
    }, ensure_ascii=False)


HEARTBEAT_MSG = json.dumps({"lwp": "/!", "headers": {"host": "wss-goofish.dingtalk.com"}})


class XianyuClient:
    def __init__(self, account_id: int):
        self.account_id = account_id
        self.cookies: dict = {}
        self.device_id: str = ""
        self.sender_blacklist: set[str] = set()  # 自己的 userId，过滤自己发出的消息
        self._task: asyncio.Task | None = None
        self._stop = False
        self._last_ack = 0.0
        self._client = None  # httpx.AsyncClient，start() 里创建

    # ---------- 状态落库 ----------
    async def _set_status(self, status: str, msg: str = ""):
        async with AsyncSessionLocal() as db:
            from sqlalchemy import update
            await db.execute(
                update(models.XianyuAccount)
                .where(models.XianyuAccount.id == self.account_id)
                .values(status=status, status_msg=msg[:250],
                        last_heartbeat=datetime.now() if status == "online" else None)
            )
            await db.commit()

    # ---------- 生命周期 ----------
    async def start(self, cookie_str: str, self_user_id: str = ""):
        import httpx
        self._stop = False
        self.cookies = xianyu_api.parse_cookie(cookie_str)
        self.self_user_id = self_user_id
        self._client = httpx.AsyncClient(timeout=15)
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stop = True
        if self._task:
            self._task.cancel()
        if self._client:
            await self._client.aclose()
        await self._set_status("offline", "手动停止")

    async def update_cookie(self, cookie_str: str, self_user_id: str = ""):
        """热更新 Cookie：断开旧连接并重连"""
        await self.stop()
        await self.start(cookie_str, self_user_id)

    # ---------- 主循环 ----------
    async def _run(self):
        import httpx
        delay = RECONNECT_MIN
        while not self._stop:
            try:
                await self._set_status("connecting", "正在获取 token…")
                token_info = await xianyu_api.get_access_token(self.cookies, self._client)
                self.device_id = token_info["device_id"]

                await self._set_status("connecting", "正在建立长连接…")
                async with websockets.connect(xianyu_api.WS_URL, ping_interval=None) as ws:
                    await ws.send(_build_register(token_info["access_token"], self.device_id))
                    await self._set_status("online", "连接成功，正在监听消息")
                    delay = RECONNECT_MIN

                    hb_task = asyncio.create_task(self._heartbeat_loop(ws))
                    try:
                        async for raw in ws:
                            self._last_ack = time.time()
                            await self._on_ws_message(ws, raw)
                            if self._stop:
                                break
                    finally:
                        hb_task.cancel()
            except asyncio.CancelledError:
                return
            except Exception as e:
                await self._set_status("error", f"{type(e).__name__}: {e}")
            if self._stop:
                return
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX)

    async def _heartbeat_loop(self, ws):
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            # 两个心跳周期内没收到任何下行视为假死，触发重连
            if time.time() - self._last_ack > HEARTBEAT_INTERVAL * 2.5:
                await ws.close()
                return
            await ws.send(HEARTBEAT_MSG)
            await self._set_status("online", "在线")

    # ---------- 消息处理 ----------
    async def _on_ws_message(self, ws, raw: str):
        try:
            data = json.loads(raw)
        except Exception:
            return
        lwp = data.get("lwp", "")
        if lwp in ("/!", "/ack", "/reg"):  # 心跳与应答
            return

        body = data.get("body", {})
        sync_list = body.get("syncPushPackage", {}).get("data") or []
        for item in sync_list:
            chat = xianyu_api.extract_chat_info(item)
            if chat:
                await self._dispatch(ws, chat)
        # ack 消息确认
        if "ackId" in json.dumps(data)[:200] or "code" in body:
            pass

    async def _dispatch(self, ws, chat: dict):
        if self.self_user_id and chat["sender_id"] == self.self_user_id:
            return  # 过滤自己发的消息，避免自问自答死循环
        await handle_chat(self.account_id, chat, self)
