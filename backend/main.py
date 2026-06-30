import logging
import subprocess
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
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

# CORS — restreint à l'URL de l'application (PWA sur même domaine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url, "http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Routers
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

app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(scraper_router)
app.include_router(settings_router)
app.include_router(budgets_router)
app.include_router(categories_router)
app.include_router(ai_router)
app.include_router(audit_router)
app.include_router(notifications_router)
app.include_router(category_rules_router)
app.include_router(export_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
