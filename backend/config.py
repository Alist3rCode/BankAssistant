from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# .env est à la racine du projet (un niveau au-dessus de backend/)
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # Base de données (chemin relatif au dossier courant en local, absolu en Docker)
    db_path: str = "./data/bankassistant.db"
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
    woob_data_dir: str = "./woob-data"

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
    app_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    debug: bool = False


settings = Settings()
