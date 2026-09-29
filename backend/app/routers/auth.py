from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import models, schemas
from ..auth import get_current_admin, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenOut)
async def login(body: schemas.LoginIn, db: AsyncSession = Depends(get_db)):
    admin = (await db.execute(
        select(models.Admin).where(models.Admin.username == body.username)
    )).scalar_one_or_none()
    if admin is None or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    return schemas.TokenOut(access_token=create_access_token(admin.username))


@router.get("/me")
async def me(admin: models.Admin = Depends(get_current_admin)):
    return {"username": admin.username}


@router.post("/password")
async def change_password(old_password: str, new_password: str,
                          admin: models.Admin = Depends(get_current_admin),
                          db: AsyncSession = Depends(get_db)):
    from ..auth import hash_password
    if not verify_password(old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    admin.password_hash = hash_password(new_password)
    await db.commit()
    return schemas.Msg(msg="密码已修改")
