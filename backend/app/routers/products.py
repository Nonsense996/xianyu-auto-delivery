from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import models, schemas
from ..auth import get_current_admin

router = APIRouter(prefix="/api/products", tags=["products"], dependencies=[Depends(get_current_admin)])


async def _with_stats(db: AsyncSession, items: list[models.Product]) -> list[dict]:
    out = []
    for p in items:
        d = schemas.ProductOut.model_validate(p).model_dump()
        row = (await db.execute(
            select(func.count()).select_from(models.CardKey)
            .where(models.CardKey.product_id == p.id, models.CardKey.status == "unused")
        )).scalar()
        sold = (await db.execute(
            select(func.count()).select_from(models.CardKey)
            .where(models.CardKey.product_id == p.id, models.CardKey.status == "sold")
        )).scalar()
        d["stock"], d["sold_count"] = row, sold
        out.append(d)
    return out


@router.get("")
async def list_products(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(
        select(models.Product).order_by(models.Product.id.desc())
    )).scalars().all()
    return await _with_stats(db, list(items))


@router.post("")
async def create_product(body: schemas.ProductIn, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(
        select(models.Product).where(models.Product.xianyu_item_id == body.xianyu_item_id)
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="该闲鱼商品ID已绑定过商品")
    p = models.Product(**body.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return (await _with_stats(db, [p]))[0]


@router.put("/{product_id}")
async def update_product(product_id: int, body: schemas.ProductIn,
                         db: AsyncSession = Depends(get_db)):
    p = (await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    dup = (await db.execute(
        select(models.Product).where(models.Product.xianyu_item_id == body.xianyu_item_id,
                                     models.Product.id != product_id)
    )).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail="该闲鱼商品ID已绑定其他商品")
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    await db.commit()
    return (await _with_stats(db, [p]))[0]


@router.delete("/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    unused = (await db.execute(
        select(func.count()).select_from(models.CardKey)
        .where(models.CardKey.product_id == product_id, models.CardKey.status == "unused")
    )).scalar()
    if unused:
        raise HTTPException(status_code=400, detail=f"还有 {unused} 张未售卡密，请先清空卡密再删除")
    await db.delete(p)
    await db.commit()
    return schemas.Msg(msg="已删除")
