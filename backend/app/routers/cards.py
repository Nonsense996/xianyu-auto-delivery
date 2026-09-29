from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import models, schemas
from ..auth import get_current_admin

router = APIRouter(prefix="/api/cards", tags=["cards"], dependencies=[Depends(get_current_admin)])


@router.get("")
async def list_cards(product_id: int, status: str = "", page: int = 1, size: int = 50,
                     db: AsyncSession = Depends(get_db)):
    q = select(models.CardKey).where(models.CardKey.product_id == product_id)
    cnt_q = select(func.count()).select_from(models.CardKey).where(
        models.CardKey.product_id == product_id)
    if status:
        q = q.where(models.CardKey.status == status)
        cnt_q = cnt_q.where(models.CardKey.status == status)
    total = (await db.execute(cnt_q)).scalar()
    items = (await db.execute(
        q.order_by(models.CardKey.id.desc()).offset((page - 1) * size).limit(size)
    )).scalars().all()
    return {"total": total, "items": [
        {"id": c.id, "content": c.content, "status": c.status, "order_id": c.order_id,
         "sold_at": c.sold_at, "created_at": c.created_at} for c in items]}


@router.post("/import")
async def import_cards(body: schemas.CardImportIn, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(
        select(models.Product).where(models.Product.id == body.product_id)
    )).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    contents = [line.strip() for line in body.contents.replace("\r\n", "\n").split("\n")
                if line.strip()]
    if not contents:
        raise HTTPException(status_code=400, detail="没有可导入的卡密")
    db.add_all([models.CardKey(product_id=body.product_id, content=c) for c in contents])
    await db.commit()
    return schemas.Msg(msg=f"成功导入 {len(contents)} 张卡密")


@router.post("/delete")
async def delete_cards(body: schemas.CardBatchIn, db: AsyncSession = Depends(get_db)):
    """仅允许删除未售出的卡密（已售的作为发货凭证保留）"""
    items = (await db.execute(
        select(models.CardKey).where(models.CardKey.id.in_(body.ids))
    )).scalars().all()
    deleted = 0
    for c in items:
        if c.status == "sold":
            continue
        await db.delete(c)
        deleted += 1
    await db.commit()
    return schemas.Msg(msg=f"删除 {deleted} 张（已售 {len(items) - deleted} 张不可删除）")
