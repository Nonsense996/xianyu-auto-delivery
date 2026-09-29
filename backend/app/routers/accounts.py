from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import models, schemas
from ..auth import get_current_admin
from ..services import xianyu_api
from ..services.ws_manager import manager

import httpx

router = APIRouter(prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(get_current_admin)])


async def _check_cookie(cookie_str: str) -> tuple[str, str]:
    """验证 Cookie 有效性，返回 (user_id, 错误信息)"""
    cookies = xianyu_api.parse_cookie(cookie_str)
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            await xianyu_api.get_access_token(cookies, client)
            user_id = await xianyu_api.get_user_id(cookies, client)
            return user_id, ""
        except Exception as e:
            return "", f"Cookie 校验失败: {e}"


@router.get("")
async def list_accounts(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(
        select(models.XianyuAccount).order_by(models.XianyuAccount.id)
    )).scalars().all()
    # 附带每个账号的商品数
    counts = dict((await db.execute(
        select(models.Product.account_id, func.count()).group_by(models.Product.account_id)
    )).all())
    out = []
    for a in items:
        d = schemas.AccountOut.model_validate(a).model_dump()
        d["product_count"] = counts.get(a.id, 0)
        out.append(d)
    return out


@router.post("")
async def create_account(body: schemas.AccountIn, db: AsyncSession = Depends(get_db)):
    user_id, err = await _check_cookie(body.cookie)
    if err:
        raise HTTPException(status_code=400, detail=err)
    acc = models.XianyuAccount(name=body.name, cookie=body.cookie, enabled=body.enabled,
                               user_id=user_id)
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    await manager.start_account(acc.id)
    return schemas.AccountOut.model_validate(acc)


@router.put("/{account_id}")
async def update_account(account_id: int, body: schemas.AccountIn,
                         db: AsyncSession = Depends(get_db)):
    acc = (await db.execute(
        select(models.XianyuAccount).where(models.XianyuAccount.id == account_id)
    )).scalar_one_or_none()
    if acc is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    cookie_changed = acc.cookie != body.cookie
    acc.name, acc.enabled = body.name, body.enabled
    if cookie_changed:
        user_id, err = await _check_cookie(body.cookie)
        if err:
            raise HTTPException(status_code=400, detail=err)
        acc.cookie, acc.user_id = body.cookie, user_id
    await db.commit()
    if cookie_changed:
        await manager.restart_account(account_id)
    elif acc.enabled:
        await manager.start_account(account_id)
    else:
        await manager.stop_account(account_id)
    return schemas.Msg(msg="已保存")


@router.delete("/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    await manager.stop_account(account_id)
    acc = (await db.execute(
        select(models.XianyuAccount).where(models.XianyuAccount.id == account_id)
    )).scalar_one_or_none()
    if acc:
        await db.delete(acc)
        await db.commit()
    return schemas.Msg(msg="已删除")


@router.post("/{account_id}/toggle")
async def toggle_account(account_id: int, db: AsyncSession = Depends(get_db)):
    acc = (await db.execute(
        select(models.XianyuAccount).where(models.XianyuAccount.id == account_id)
    )).scalar_one_or_none()
    if acc is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    acc.enabled = not acc.enabled
    await db.commit()
    if acc.enabled:
        await manager.start_account(account_id)
    else:
        await manager.stop_account(account_id)
    return {"enabled": acc.enabled}


@router.post("/{account_id}/reconnect")
async def reconnect(account_id: int):
    await manager.restart_account(account_id)
    return schemas.Msg(msg="已发起重连")
