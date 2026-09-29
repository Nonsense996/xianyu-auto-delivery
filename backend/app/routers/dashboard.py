from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import models
from ..auth import get_current_admin

router = APIRouter(prefix="/api", tags=["dashboard"], dependencies=[Depends(get_current_admin)])


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    async def count(model, *conds):
        q = select(func.count()).select_from(model)
        for c in conds:
            q = q.where(c)
        return (await db.execute(q)).scalar() or 0

    total_delivered = await count(models.Order, models.Order.status == "delivered")
    today_delivered = await count(models.Order, models.Order.status == "delivered",
                                  models.Order.created_at >= today)
    failed = await count(models.Order, models.Order.status.in_(("failed", "pending")))
    total_amount = (await db.execute(
        select(func.coalesce(func.sum(models.Order.amount), 0))
        .where(models.Order.status == "delivered")
    )).scalar()

    stock = await count(models.CardKey, models.CardKey.status == "unused")
    online = await count(models.XianyuAccount, models.XianyuAccount.enabled == True)  # noqa: E712
    accounts_total = await count(models.XianyuAccount)

    # 近 7 日发货趋势
    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        nxt = day + timedelta(days=1)
        c = (await db.execute(
            select(func.count()).select_from(models.Order)
            .where(models.Order.status == "delivered",
                   models.Order.created_at >= day, models.Order.created_at < nxt)
        )).scalar() or 0
        trend.append({"date": day.strftime("%m-%d"), "count": c})

    # 低库存商品（<5 张）
    low_stock = (await db.execute(
        select(models.Product.id, models.Product.name, func.count())
        .join(models.CardKey, models.CardKey.product_id == models.Product.id)
        .where(models.CardKey.status == "unused", models.Product.enabled == True)  # noqa: E712
        .group_by(models.Product.id, models.Product.name)
        .having(func.count() < 5)
    )).all()

    # 最近日志
    logs = (await db.execute(
        select(models.AppLog).order_by(models.AppLog.id.desc()).limit(10)
    )).scalars().all()

    return {
        "cards": {
            "total_delivered": total_delivered, "today_delivered": today_delivered,
            "failed": failed, "total_amount": float(total_amount), "stock": stock,
        },
        "accounts": {"online": online, "total": accounts_total},
        "trend": trend,
        "low_stock": [{"id": r[0], "name": r[1], "stock": r[2]} for r in low_stock],
        "logs": [{"level": l.level, "module": l.module, "message": l.message,
                  "created_at": str(l.created_at)} for l in logs],
    }


@router.get("/logs")
async def list_logs(level: str = "", page: int = 1, size: int = 50,
                    db: AsyncSession = Depends(get_db)):
    q = select(models.AppLog)
    cnt_q = select(func.count()).select_from(models.AppLog)
    if level:
        q, cnt_q = q.where(models.AppLog.level == level), cnt_q.where(models.AppLog.level == level)
    total = (await db.execute(cnt_q)).scalar()
    items = (await db.execute(
        q.order_by(models.AppLog.id.desc()).offset((page - 1) * size).limit(size)
    )).scalars().all()
    return {"total": total, "items": [
        {"id": l.id, "level": l.level, "module": l.module, "account_id": l.account_id,
         "message": l.message, "created_at": str(l.created_at)} for l in items]}
