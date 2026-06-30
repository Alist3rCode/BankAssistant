import logging
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.security import decrypt, encrypt
from dependencies import CurrentUser, DB
from models.models import AppSetting, BankAccount, Transaction
from scraper.ca_regions import CA_REGIONS
from scraper.csv_import import CSVImporter, OFXImporter
from services.sync_service import sync_all_accounts, persist_transactions

router = APIRouter(prefix="/scraper", tags=["scraper"])
logger = logging.getLogger(__name__)


class ConnectionTestRequest(BaseModel):
    region_id: str
    login: str
    password: str


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    accounts_found: int = 0


class ScrapeStatusResponse(BaseModel):
    status: Literal["idle", "running", "error"]
    last_run: Optional[str]
    last_error: Optional[str]


_scrape_status: dict = {"status": "idle", "last_run": None, "last_error": None}


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_connection(body: ConnectionTestRequest, current_user: CurrentUser):
    """Teste les credentials CA avant de les sauvegarder."""
    if body.region_id not in CA_REGIONS:
        raise HTTPException(status_code=400, detail="Région CA inconnue")

    _, region_url = CA_REGIONS[body.region_id]

    from scraper.ca_scraper import CreditAgricoleScraper
    scraper = CreditAgricoleScraper(
        region_id=body.region_id,
        region_url=region_url,
        login=body.login,
        password=body.password,
    )

    try:
        accounts = await scraper.fetch_accounts()
        return ConnectionTestResponse(
            success=True,
            message=f"Connexion réussie — {len(accounts)} compte(s) trouvé(s)",
            accounts_found=len(accounts),
        )
    except Exception as e:
        logger.warning("Test connexion CA échoué : %s", e)
        return ConnectionTestResponse(success=False, message=str(e))


@router.post("/trigger")
async def trigger_scraping(
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    db: DB,
):
    """Déclenche un scraping immédiat (non-bloquant)."""
    if _scrape_status["status"] == "running":
        raise HTTPException(status_code=409, detail="Un scraping est déjà en cours")

    background_tasks.add_task(_run_scraping_background, db)
    return {"message": "Scraping démarré en arrière-plan"}


@router.get("/status", response_model=ScrapeStatusResponse)
async def get_scraping_status(current_user: CurrentUser):
    return ScrapeStatusResponse(**_scrape_status)


@router.post("/import/csv")
async def import_csv(
    current_user: CurrentUser,
    db: DB,
    file: UploadFile = File(...),
    account_id: Optional[str] = None,
):
    """Importe un fichier CSV exporté depuis le site Crédit Agricole."""
    content = await file.read()

    # Choisir le compte cible (premier compte actif si non précisé)
    account = _get_target_account(db, account_id)

    importer = CSVImporter()
    imported = importer.parse(content, account.external_id)

    count = persist_transactions(db, account, imported)
    return {"message": f"{count} transaction(s) importée(s)", "total_parsed": len(imported)}


@router.post("/import/ofx")
async def import_ofx(
    current_user: CurrentUser,
    db: DB,
    file: UploadFile = File(...),
    account_id: Optional[str] = None,
):
    """Importe un fichier OFX/QFX exporté depuis le site Crédit Agricole."""
    content = await file.read()
    account = _get_target_account(db, account_id)

    importer = OFXImporter()
    imported = importer.parse(content, account.external_id)

    count = persist_transactions(db, account, imported)
    return {"message": f"{count} transaction(s) importée(s)", "total_parsed": len(imported)}


# ---------- Helpers ----------

def _get_target_account(db: Session, account_id: Optional[str]) -> BankAccount:
    if account_id:
        account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Compte introuvable")
        return account

    account = db.query(BankAccount).filter(BankAccount.is_active == True).first()
    if not account:
        raise HTTPException(
            status_code=400,
            detail="Aucun compte trouvé. Configurez d'abord votre connexion CA.",
        )
    return account


async def _run_scraping_background(db: Session) -> None:
    _scrape_status["status"] = "running"
    _scrape_status["last_error"] = None
    try:
        await sync_all_accounts(db)
        from datetime import datetime, timezone
        _scrape_status["last_run"] = datetime.now(timezone.utc).isoformat()
        _scrape_status["status"] = "idle"
    except Exception as e:
        _scrape_status["status"] = "error"
        _scrape_status["last_error"] = str(e)
        logger.error("Scraping background error : %s", e)
