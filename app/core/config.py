from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "DSO 大客户月结订单系统"
    DATABASE_URL: str = "sqlite:///./dso_orders.db"
    API_V1_PREFIX: str = "/api/v1"

    model_config = {"env_file": ".env"}


settings = Settings()
