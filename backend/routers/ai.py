"""
Route /ai/chat — Assistant bancaire IA via LiteLLM (Groq, Mistral, Ollama).
"""

import logging
from pydantic import BaseModel
from fastapi import APIRouter
from sqlalchemy.orm import Session
from dependencies import CurrentUser, DB
from models.models import AppSetting
from auth.security import decrypt

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    context: str = ""


class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not row:
        return default
    if row.is_encrypted and row.value:
        try:
            return decrypt(row.value)
        except Exception:
            return default
    return row.value or default


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, current_user: CurrentUser, db: DB):
    provider = _get_setting(db, "ai.provider", "groq")
    model = _get_setting(db, "ai.model", "")

    # Configurer les clés API via litellm
    import litellm

    groq_key = _get_setting(db, "ai.groq_api_key", "")
    mistral_key = _get_setting(db, "ai.mistral_api_key", "")
    ollama_url = _get_setting(db, "ollama_base_url", "")

    if groq_key:
        litellm.api_key = groq_key
    if mistral_key:
        import os
        os.environ["MISTRAL_API_KEY"] = mistral_key

    # Déterminer le modèle complet selon le provider
    if provider == "groq":
        full_model = f"groq/{model or 'llama-3.3-70b-versatile'}"
        litellm.api_key = groq_key
    elif provider == "mistral":
        full_model = f"mistral/{model or 'mistral-large-latest'}"
    elif provider == "ollama":
        full_model = f"ollama/{model or 'mistral-nemo'}"
        if ollama_url:
            litellm.api_base = ollama_url
    else:
        full_model = model or "groq/llama-3.3-70b-versatile"

    system_prompt = (
        "Tu es un assistant bancaire personnel francophone. "
        "Tu analyses les données financières fournies et réponds de manière claire, concise et utile. "
        "Tu ne partages jamais de données sensibles hors du contexte fourni. "
        "Toujours répondre en français."
    )

    messages = []
    if body.context:
        messages.append({"role": "system", "content": system_prompt + "\n\n" + body.context})
    else:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": body.message})

    try:
        response = await litellm.acompletion(
            model=full_model,
            messages=messages,
            max_tokens=1024,
            temperature=0.3,
        )
        answer = response.choices[0].message.content or "Je n'ai pas pu générer une réponse."
    except Exception as e:
        logger.error("LiteLLM error : %s", e)
        raise

    return ChatResponse(response=answer, provider=provider, model=full_model)
