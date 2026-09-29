import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "闲鱼自动发货管理系统"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-9f8e7d6c5b4a")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

    # 管理后台登录账号（首次启动自动创建）
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

    # 数据库：默认 SQLite，Docker 里用 MySQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/xianyu.db")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
