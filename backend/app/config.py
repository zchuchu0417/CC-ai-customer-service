"""集中管理所有配置，从 .env 读取"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 应用
    app_name: str = "cc-ai-customer-service"
    app_version: str = "0.1.0"
    app_env: str = "local"

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 13306
    mysql_user: str = "cc_user"
    mysql_password: str = "cc_pass_2026"
    mysql_db: str = "cc_ai_cs"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # LLM
    deepseek_api_key: str = ""
    siliconflow_api_key: str = ""

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# 全局唯一实例
settings = Settings()