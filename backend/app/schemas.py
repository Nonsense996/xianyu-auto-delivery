from datetime import datetime
from pydantic import BaseModel, Field


# ---------- 通用 ----------
class PageResult(BaseModel):
    total: int
    items: list


class Msg(BaseModel):
    ok: bool = True
    msg: str = "ok"


# ---------- 认证 ----------
class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- 账号 ----------
class AccountIn(BaseModel):
    name: str
    cookie: str
    enabled: bool = True


class AccountOut(BaseModel):
    id: int
    name: str
    user_id: str
    enabled: bool
    status: str
    status_msg: str
    last_heartbeat: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- 商品 ----------
class ProductIn(BaseModel):
    account_id: int
    name: str
    xianyu_item_id: str
    price: float = 0
    auto_delivery: bool = True
    delivery_template: str = "感谢购买！您的卡密：{card}\n如有问题请随时联系我~"
    enabled: bool = True
    remark: str = ""


class ProductOut(ProductIn):
    id: int
    stock: int = 0
    sold_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- 卡密 ----------
class CardImportIn(BaseModel):
    product_id: int
    contents: str = Field(description="卡密文本，每行一个")


class CardBatchIn(BaseModel):
    ids: list[int]


# ---------- 订单 ----------
class OrderOut(BaseModel):
    id: int
    order_id: str
    account_id: int
    product_id: int | None
    buyer_id: str
    buyer_message: str
    amount: float
    status: str
    delivered_content: str
    error_msg: str
    created_at: datetime
    delivered_at: datetime | None

    class Config:
        from_attributes = True


# ---------- 规则 ----------
class RuleIn(BaseModel):
    account_id: int | None = None
    keyword: str
    reply_text: str
    enabled: bool = True
    priority: int = 0


class RuleOut(RuleIn):
    id: int
    hit_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DefaultReplyIn(BaseModel):
    enabled: bool
    reply_text: str
