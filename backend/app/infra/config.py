from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # MongoDB
    mongo_user: str
    mongo_password: str
    mongo_db: str
    mongo_host: str = "mongodb"
    mongo_port: int = 27017

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15

    # API
    allowed_origins: list[str] = ["http://localhost"]
    api_prefix: str = "/api/v1"
    debug: bool = False

    @property
    def mongo_uri(self) -> str:
        return (
            f"mongodb://{self.mongo_user}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}/{self.mongo_db}"
            f"?authSource=admin"
        )


settings = Settings()
