import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from limiter import limiter
from scheduler.jobs import start_scheduler, stop_scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _create_default_admin() -> None:
    """Crée le compte admin depuis .env si aucun utilisateur n'existe encore."""
    if not settings.admin_password:
        return
    from database import SessionLocal
    from models.models import User
    from auth.security import hash_password
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            user = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
            )
            db.add(user)
            db.commit()
            logger.info("Compte admin cree : %s", settings.admin_email)
    finally:
        db.close()


def run_migrations() -> None:
    """Applique les migrations Alembic au démarrage."""
    logger.info("Vérification et application des migrations Alembic...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Erreur migration Alembic : %s", result.stderr)
        raise RuntimeError("Migration de base de données échouée")
    logger.info("Migrations OK")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage
    run_migrations()
    _create_default_admin()
    start_scheduler()
    logger.info("BankAssistant démarré — %s", settings.app_url)
    yield
    # Arrêt
    stop_scheduler()
    logger.info("BankAssistant arrêté")


app = FastAPI(
    title="BankAssistant API",
    description="Assistant bancaire IA self-hosted pour Crédit Agricole",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.app_url,
        "http://localhost:8000",
        "http://localhost:5173",  # Vite dev server
        "https://localhost",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Routers
from fastapi import APIRouter as _APIRouter
from routers.auth import router as auth_router
from routers.accounts import router as accounts_router
from routers.transactions import router as transactions_router
from routers.scraper import router as scraper_router
from routers.settings import router as settings_router
from routers.budgets import router as budgets_router
from routers.categories import router as categories_router
from routers.ai import router as ai_router
from routers.audit import router as audit_router
from routers.notifications import router as notifications_router
from routers.category_rules import router as category_rules_router
from routers.export import router as export_router

_api = _APIRouter(prefix="/api")
_api.include_router(auth_router)
_api.include_router(accounts_router)
_api.include_router(transactions_router)
_api.include_router(scraper_router)
_api.include_router(settings_router)
_api.include_router(budgets_router)
_api.include_router(categories_router)
_api.include_router(ai_router)
_api.include_router(audit_router)
_api.include_router(notifications_router)
_api.include_router(category_rules_router)
_api.include_router(export_router)
app.include_router(_api)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Servir le frontend Vue.js buildé (mode local sans Docker/Caddy) ────────
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    logger.info("Frontend dist trouvé — service des fichiers statiques activé")

    # /assets/* — JS, CSS, fonts hashés (cache long)
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """Sert index.html pour toutes les routes non-API (SPA routing Vue Router)."""
        candidate = _FRONTEND_DIST / full_path
        # Fichiers statiques à la racine (favicon, manifest, sw.js…)
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
