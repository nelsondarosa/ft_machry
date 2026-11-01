from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    # DATABASE_URL tem prioridade. Sem ela, os campos abaixo montam a conexão.
    DATABASE_URL: str | None = None
    DB_CONNECTION: str = "sqlite"

    DATABASE_PATH: str = "data/app.db"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_DATABASE: str = "ft_machry"
    DB_USERNAME: str = "postgres"
    DB_PASSWORD: str = ""

    SECRET_KEY: str = "machry-desenvolvimento-troque-em-producao"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = False

    OWNER_USERNAME: str = "dona"
    OWNER_INITIAL_PASSWORD: str = "Dona@123"
    MANAGER_USERNAME: str = "gestor"
    MANAGER_INITIAL_PASSWORD: str = "Gestor@123"
    COOK_USERNAME: str = "cozinha"
    COOK_INITIAL_PASSWORD: str = "Cozinha@123"

config = Config()
