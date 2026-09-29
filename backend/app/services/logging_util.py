from ..database import AsyncSessionLocal
from .. import models


async def add_log(db=None, level: str = "info", module: str = "", account_id: int | None = None,
                  message: str = ""):
    """写一条运行日志；db 为空时自建会话"""
    if db is not None:
        db.add(models.AppLog(level=level, module=module, account_id=account_id,
                             message=message[:2000]))
        await db.commit()
        return
    async with AsyncSessionLocal() as session:
        session.add(models.AppLog(level=level, module=module, account_id=account_id,
                                  message=message[:2000]))
        await session.commit()
