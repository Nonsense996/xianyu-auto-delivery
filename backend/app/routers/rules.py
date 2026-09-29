from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import models, schemas
from ..auth import get_current_admin

router = APIRouter(prefix="/api/rules", tags=["rules"], dependencies=[Depends(get_current_admin)])


@router.get("")
async def list_rules(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(
        select(models.ReplyRule).order_by(models.ReplyRule.priority.desc(), models.ReplyRule.id)
    )).scalars().all()
    return [schemas.RuleOut.model_validate(r).model_dump() for r in items]


@router.post("")
async def create_rule(body: schemas.RuleIn, db: AsyncSession = Depends(get_db)):
    r = models.ReplyRule(**body.model_dump())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return schemas.RuleOut.model_validate(r).model_dump()


@router.put("/{rule_id}")
async def update_rule(rule_id: int, body: schemas.RuleIn, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(
        select(models.ReplyRule).where(models.ReplyRule.id == rule_id)
    )).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    await db.commit()
    return schemas.RuleOut.model_validate(r).model_dump()


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(
        select(models.ReplyRule).where(models.ReplyRule.id == rule_id)
    )).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    await db.delete(r)
    await db.commit()
    return schemas.Msg(msg="已删除")


@router.get("/default-reply")
async def get_default_reply(db: AsyncSession = Depends(get_db)):
    dr = (await db.execute(select(models.DefaultReply).limit(1))).scalar_one_or_none()
    if dr is None:
        return {"enabled": False, "reply_text": ""}
    return {"enabled": dr.enabled, "reply_text": dr.reply_text}


@router.put("/default-reply")
async def set_default_reply(body: schemas.DefaultReplyIn, db: AsyncSession = Depends(get_db)):
    dr = (await db.execute(select(models.DefaultReply).limit(1))).scalar_one_or_none()
    if dr is None:
        dr = models.DefaultReply()
        db.add(dr)
    dr.enabled, dr.reply_text = body.enabled, body.reply_text
    await db.commit()
    return schemas.Msg(msg="已保存")
