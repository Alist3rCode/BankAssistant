from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from auth.jwt import create_access_token, create_refresh_token, decode_token, REFRESH_TOKEN_TYPE
from auth.security import (
    compute_lockout_until,
    encrypt,
    hash_password,
    is_account_locked,
    verify_password,
)
from auth.totp import (
    generate_qr_code_base64,
    generate_totp_secret,
    get_totp_uri,
    verify_totp_code,
)
from dependencies import CurrentUser, DB
from models.models import AuditLog, User

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Schemas ----------

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    requires_totp: bool = False
    user_id: str = ""


class TOTPVerifyRequest(BaseModel):
    user_id: str
    code: str
    temp_token: str  # token temporaire émis après login réussi mais avant 2FA


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code_base64: str
    uri: str


class TOTPConfirmRequest(BaseModel):
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- Helpers ----------

def _log_audit(db: Session, action: str, user_id: Optional[str], request: Request, details: str = "") -> None:
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        details=details or None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    ))
    db.commit()


# ---------- Routes ----------

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DB, request: Request):
    """Crée le premier utilisateur (une seule fois — app mono-utilisateur)."""
    if db.query(User).count() > 0:
        raise HTTPException(status_code=400, detail="Un compte existe déjà")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _log_audit(db, "REGISTER", user.id, request)
    return {"message": "Compte créé avec succès"}


@router.post("/login", response_model=LoginResponse)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, ],
    db: DB,
    request: Request,
):
    """Login avec email + mot de passe. Retourne un token (ou demande le 2FA)."""
    user: Optional[User] = db.query(User).filter(User.email == form.username).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    if is_account_locked(user.locked_until):
        raise HTTPException(
            status_code=423,
            detail=f"Compte verrouillé jusqu'à {user.locked_until.isoformat()}",
        )

    if not verify_password(form.password, user.hashed_password):
        user.failed_login_attempts += 1
        user.locked_until = compute_lockout_until(user.failed_login_attempts)
        db.commit()
        _log_audit(db, "LOGIN_FAILED", user.id, request)
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    # Réinitialiser les tentatives en cas de succès
    user.failed_login_attempts = 0
    user.locked_until = None

    if user.totp_enabled:
        # Émettre un token temporaire court (5 min) qui n'autorise que /auth/totp/verify
        temp_token = create_access_token(user.id)  # TODO: type dédié "pre_auth"
        db.commit()
        return LoginResponse(
            access_token="",
            refresh_token="",
            requires_totp=True,
            user_id=user.id,
        )

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    _log_audit(db, "LOGIN", user.id, request)

    return LoginResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/totp/verify", response_model=LoginResponse)
async def totp_verify(body: TOTPVerifyRequest, db: DB, request: Request):
    """Valide le code TOTP après le premier login."""
    user = db.query(User).filter(User.id == body.user_id, User.is_active == True).first()
    if not user or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA non configuré")

    if not verify_totp_code(user.totp_secret, body.code):
        _log_audit(db, "TOTP_FAILED", user.id, request)
        raise HTTPException(status_code=401, detail="Code TOTP invalide")

    user.last_login = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    db.commit()
    _log_audit(db, "LOGIN_TOTP", user.id, request)

    return LoginResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(body: RefreshRequest, db: DB):
    """Échange un refresh token contre un nouveau access token."""
    user_id = decode_token(body.refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    if not user_id:
        raise HTTPException(status_code=401, detail="Refresh token invalide ou expiré")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")

    return LoginResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/totp/setup", response_model=TOTPSetupResponse)
async def totp_setup(current_user: CurrentUser, db: DB):
    """Génère un secret TOTP et retourne le QR code pour la configuration initiale."""
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, current_user.email)
    qr = generate_qr_code_base64(uri)

    # Stocker temporairement le secret (non encore activé)
    current_user.totp_secret = encrypt(secret)
    current_user.totp_enabled = False
    db.commit()

    return TOTPSetupResponse(secret=secret, qr_code_base64=qr, uri=uri)


@router.post("/totp/confirm")
async def totp_confirm(body: TOTPConfirmRequest, current_user: CurrentUser, db: DB, request: Request):
    """Confirme l'activation du 2FA en vérifiant un premier code."""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Lance d'abord GET /auth/totp/setup")

    if not verify_totp_code(current_user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Code TOTP invalide")

    current_user.totp_enabled = True
    db.commit()
    _log_audit(db, "TOTP_ENABLED", current_user.id, request)
    return {"message": "2FA activé avec succès"}


@router.delete("/totp")
async def totp_disable(current_user: CurrentUser, db: DB, request: Request):
    """Désactive le 2FA (confirmation via mot de passe requise côté IHM)."""
    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.commit()
    _log_audit(db, "TOTP_DISABLED", current_user.id, request)
    return {"message": "2FA désactivé"}


@router.get("/me")
async def me(current_user: CurrentUser):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "totp_enabled": current_user.totp_enabled,
        "last_login": current_user.last_login,
    }
