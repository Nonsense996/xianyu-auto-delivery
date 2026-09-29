"""账号连接生命周期管理：进程内单例，随 FastAPI 启动恢复所有启用账号的连接"""
import asyncio

from ..database import AsyncSessionLocal
from .. import models
from .xianyu_client import XianyuClient


class WsManager:
    def __init__(self):
        self._clients: dict[int, XianyuClient] = {}
        self._lock = asyncio.Lock()

    async def _load_cookie(self, account_id: int) -> tuple[str, str, bool] | None:
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            acc = (await db.execute(
                select(models.XianyuAccount).where(models.XianyuAccount.id == account_id)
            )).scalar_one_or_none()
            if acc is None:
                return None
            return acc.cookie, acc.user_id, acc.enabled

    async def start_account(self, account_id: int):
        async with self._lock:
            await self.stop_account(account_id, update_status=False)
            info = await self._load_cookie(account_id)
            if info is None:
                return
            cookie, user_id, enabled = info
            if not enabled or not cookie:
                return
            client = XianyuClient(account_id)
            await client.start(cookie, user_id)
            self._clients[account_id] = client

    async def stop_account(self, account_id: int, update_status: bool = True):
        client = self._clients.pop(account_id, None)
        if client:
            await client.stop()
        elif update_status:
            pass

    async def restart_account(self, account_id: int):
        await self.start_account(account_id)

    async def start_all(self):
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            ids = (await db.execute(
                select(models.XianyuAccount.id)
                .where(models.XianyuAccount.enabled == True)  # noqa: E712
            )).scalars().all()
        for aid in ids:
            await self.start_account(aid)

    def get_client(self, account_id: int) -> XianyuClient | None:
        return self._clients.get(account_id)


manager = WsManager()
