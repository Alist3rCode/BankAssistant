from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de données
    db_path: str = "/app/data/bankassistant.db"
    encryption_key: str = Field(..., description="Clé Fernet base64 pour le chiffrement des champs sensibles")

    # JWT
    secret_key: str = Field(..., description="Clé secrète JWT")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Sécurité
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    # Woob
    woob_data_dir: str = "/app/woob-data"

    # IA
    default_llm_provider: str = "groq"
    default_llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str = ""
    mistral_api_key: str = ""
    ollama_base_url: str = ""

    # Notifications
    ntfy_url: str = "http://ntfy:80"
    ntfy_topic: str = "bankassistant"
    ntfy_token: str = ""

    # Application
    app_url: str = "https://localhost"
    log_level: str = "INFO"
    debug: bool = False


settings = Settings()
