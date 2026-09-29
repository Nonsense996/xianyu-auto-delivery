from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from . import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


def hash_password(p: str) -> str:
    return pwd_context.hash(p)


def verify_password(p: str, h: str) -> bool:
    try:
        return pwd_context.verify(p, h)
    except Exception:
        return False


def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, settings.SECRET_KEY, algorithm="HS256")


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> models.Admin:
    exc = HTTPException(status_code=401, detail="未登录或登录已过期")
    if credentials is None:
        raise exc
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise exc
    username = payload.get("sub")
    if not username:
        raise exc
    res = await db.execute(select(models.Admin).where(models.Admin.username == username))
    admin = res.scalar_one_or_none()
    if admin is None:
        raise exc
    return admin


async def ensure_admin(db: AsyncSession):
    """首次启动时创建默认管理员"""
    res = await db.execute(select(models.Admin).limit(1))
    if res.scalar_one_or_none() is None:
        db.add(models.Admin(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
        ))
        await db.commit()
