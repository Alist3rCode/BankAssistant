from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from dependencies import CurrentUser, DB
from models.models import BankAccount
from scraper.ca_regions import CA_REGIONS

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountResponse(BaseModel):
    id: str
    name: str
    number_masked: str
    account_type: str
    balance: float
    currency: str
    ca_region: str
    is_active: bool
    last_synced: Optional[str]

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[AccountResponse])
async def list_accounts(current_user: CurrentUser, db: DB):
    accounts = db.query(BankAccount).filter(BankAccount.is_active == True).all()
    return [
        AccountResponse(
            id=a.id,
            name=a.name,
            number_masked=a.number_masked,
            account_type=a.account_type,
            balance=float(a.balance),
            currency=a.currency,
            ca_region=a.ca_region,
            is_active=a.is_active,
            last_synced=a.last_synced.isoformat() if a.last_synced else None,
        )
        for a in accounts
    ]


@router.get("/regions")
async def list_ca_regions(_: CurrentUser):
    """Retourne la liste de toutes les caisses régionales CA."""
    return [
        {"id": region_id, "name": name, "url": url}
        for region_id, (name, url) in CA_REGIONS.items()
    ]


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: str, current_user: CurrentUser, db: DB):
    account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    return AccountResponse(
        id=account.id,
        name=account.name,
        number_masked=account.number_masked,
        account_type=account.account_type,
        balance=float(account.balance),
        currency=account.currency,
        ca_region=account.ca_region,
        is_active=account.is_active,
        last_synced=account.last_synced.isoformat() if account.last_synced else None,
    )
