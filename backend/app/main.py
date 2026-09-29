from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import init_db
from .auth import ensure_admin
from .database import AsyncSessionLocal
from .routers import auth as auth_router
from .routers import accounts, products, cards, orders, rules, dashboard
from .services.ws_manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await ensure_admin(db)
    await manager.start_all()  # 恢复所有启用账号的长连接
    yield
    # 停机时关闭所有连接
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        ids = (await db.execute(select(models.XianyuAccount.id))).scalars().all()
    for aid in ids:
        await manager.stop_account(aid, update_status=False)


app = FastAPI(title="闲鱼自动发货管理系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(accounts.router)
app.include_router(products.router)
app.include_router(cards.router)
app.include_router(orders.router)
app.include_router(rules.router)
app.include_router(dashboard.router)


@app.get("/api/health")
async def health():
    return {"ok": True}
