import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.security import encrypt, decrypt
from dependencies import CurrentUser, DB
from models.models import AppSetting
from scheduler.jobs import load_schedule_from_db

router = APIRouter(prefix="/settings", tags=["settings"])

# Clés nécessitant un chiffrement (sensibles)
ENCRYPTED_KEYS = {"ca.login", "ca.password", "ai.groq_api_key", "ai.mistral_api_key"}


class SettingResponse(BaseModel):
    key: str
    value: Any
    is_encrypted: bool


class UpdateSettingRequest(BaseModel):
    value: Any


@router.get("/", response_model=list[SettingResponse])
async def get_all_settings(current_user: CurrentUser, db: DB):
    rows = db.query(AppSetting).all()
    result = []
    for row in rows:
        value = row.value
        if row.is_encrypted and value:
            value = "***"  # ne pas renvoyer les secrets
        else:
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(SettingResponse(key=row.key, value=value, is_encrypted=row.is_encrypted))
    return result


@router.get("/{key}")
async def get_setting(key: str, current_user: CurrentUser, db: DB):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Paramètre '{key}' introuvable")

    value = row.value
    if row.is_encrypted:
        return {"key": key, "value": "***", "is_encrypted": True}

    try:
        value = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        pass
    return {"key": key, "value": value, "is_encrypted": False}


@router.put("/batch")
async def update_settings_batch(
    body: dict[str, Any],
    current_user: CurrentUser,
    db: DB,
):
    """Met à jour plusieurs paramètres en une seule requête."""
    for key, value in body.items():
        is_encrypted = key in ENCRYPTED_KEYS
        raw_value = json.dumps(value) if isinstance(value, (dict, list, bool)) else str(value)

        if is_encrypted and raw_value and raw_value != "***":
            raw_value = encrypt(raw_value)

        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = raw_value
            row.is_encrypted = is_encrypted
        else:
            db.add(AppSetting(key=key, value=raw_value, is_encrypted=is_encrypted))

    db.commit()
    load_schedule_from_db()
    return {"message": f"{len(body)} paramètre(s) mis à jour"}


@router.put("/{key}")
async def update_setting(key: str, body: UpdateSettingRequest, current_user: CurrentUser, db: DB):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()

    is_encrypted = key in ENCRYPTED_KEYS
    raw_value = body.value

    # Sérialiser en JSON si nécessaire
    if isinstance(raw_value, (dict, list, bool)):
        raw_value = json.dumps(raw_value)
    else:
        raw_value = str(raw_value)

    if is_encrypted and raw_value and raw_value != "***":
        raw_value = encrypt(raw_value)

    if row:
        row.value = raw_value
        row.is_encrypted = is_encrypted
    else:
        db.add(AppSetting(key=key, value=raw_value, is_encrypted=is_encrypted))

    db.commit()

    # Si c'est un paramètre de scheduling, recharger les jobs
    if key.startswith("scraping.") or key.startswith("notifications.daily_report"):
        load_schedule_from_db()

    return {"message": f"Paramètre '{key}' mis à jour"}
