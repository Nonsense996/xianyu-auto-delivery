from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Admin(Base):
    """管理后台登录账号"""
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class XianyuAccount(Base):
    """闲鱼账号（鱼店）：一个账号一条 Cookie，对应一条 WebSocket 长连接"""
    __tablename__ = "xianyu_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), comment="备注名")
    user_id: Mapped[str] = mapped_column(String(64), default="", comment="闲鱼用户ID（解析Cookie得到）")
    cookie: Mapped[str] = mapped_column(Text, comment="完整 Cookie 字符串")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用监听")
    status: Mapped[str] = mapped_column(String(16), default="offline", comment="offline/connecting/online/error")
    status_msg: Mapped[str] = mapped_column(String(256), default="", comment="最近状态说明")
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    products: Mapped[list["Product"]] = relationship(back_populates="account")


class Product(Base):
    """商品：绑定闲鱼商品ID，配置自动发货"""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("xianyu_accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    xianyu_item_id: Mapped[str] = mapped_column(String(64), index=True, comment="闲鱼商品ID")
    price: Mapped[float] = mapped_column(Float, default=0)
    auto_delivery: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否自动发货")
    delivery_template: Mapped[str] = mapped_column(
        Text, default="感谢购买！您的卡密：{card}\n如有问题请随时联系我~",
        comment="发货内容模板，{card} 会被替换为卡密",
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    account: Mapped["XianyuAccount"] = relationship(back_populates="products")
    cards: Mapped[list["CardKey"]] = relationship(back_populates="product")


class CardKey(Base):
    """卡密库存"""
    __tablename__ = "card_keys"
    __table_args__ = (Index("ix_card_product_status", "product_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    content: Mapped[str] = mapped_column(Text, comment="卡密内容")
    status: Mapped[str] = mapped_column(String(16), default="unused", comment="unused/sold/invalid")
    order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="售出关联订单号")
    sold_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    product: Mapped["Product"] = relationship(back_populates="cards")


class Order(Base):
    """订单/发货记录"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="闲鱼订单号/会话订单标识")
    account_id: Mapped[int] = mapped_column(ForeignKey("xianyu_accounts.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    card_id: Mapped[int | None] = mapped_column(ForeignKey("card_keys.id"), nullable=True)
    buyer_id: Mapped[str] = mapped_column(String(64), default="", comment="买家ID")
    buyer_message: Mapped[str] = mapped_column(Text, default="", comment="买家原始消息")
    amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True,
                                        comment="pending/delivered/failed/manual")
    delivered_content: Mapped[str] = mapped_column(Text, default="", comment="实际发送内容")
    error_msg: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReplyRule(Base):
    """自动回复规则：关键词触发"""
    __tablename__ = "reply_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("xianyu_accounts.id"), nullable=True,
                                                   comment="为空表示对所有账号生效")
    keyword: Mapped[str] = mapped_column(String(128), index=True, comment="触发关键词，多个用逗号分隔")
    reply_text: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="数字越大优先级越高")
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DefaultReply(Base):
    """兜底自动回复（未命中任何规则时）"""
    __tablename__ = "default_reply"

    id: Mapped[int] = mapped_column(primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_text: Mapped[str] = mapped_column(Text, default="亲，在的！请问有什么可以帮您~")


class AppLog(Base):
    """系统运行日志"""
    __tablename__ = "app_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(8), default="info", index=True, comment="info/warn/error")
    module: Mapped[str] = mapped_column(String(32), default="", comment="来源模块")
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
