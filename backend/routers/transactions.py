from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc
from dependencies import CurrentUser, DB
from models.models import Transaction, Category

router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransactionResponse(BaseModel):
    id: str
    account_id: str
    date: str
    amount: float
    label: str
    transaction_type: str
    category_id: Optional[str]
    category_name: Optional[str]
    is_categorized: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class UpdateTransactionRequest(BaseModel):
    category_id: Optional[str] = None
    notes: Optional[str] = None
    label: Optional[str] = None


@router.get("/", response_model=list[TransactionResponse])
async def list_transactions(
    current_user: CurrentUser,
    db: DB,
    account_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
):
    q = db.query(Transaction)

    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    if min_amount is not None:
        q = q.filter(Transaction.amount >= Decimal(str(min_amount)))
    if max_amount is not None:
        q = q.filter(Transaction.amount <= Decimal(str(max_amount)))
    if search:
        q = q.filter(Transaction.label.ilike(f"%{search}%"))

    q = q.order_by(desc(Transaction.date)).offset(offset).limit(limit)
    transactions = q.all()

    return [_to_response(t, db) for t in transactions]


@router.get("/{tx_id}", response_model=TransactionResponse)
async def get_transaction(tx_id: str, current_user: CurrentUser, db: DB):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    return _to_response(tx, db)


@router.patch("/{tx_id}", response_model=TransactionResponse)
async def update_transaction(tx_id: str, body: UpdateTransactionRequest, current_user: CurrentUser, db: DB):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")

    if body.category_id is not None:
        if body.category_id and not db.query(Category).filter(Category.id == body.category_id).first():
            raise HTTPException(status_code=400, detail="Catégorie introuvable")
        tx.category_id = body.category_id or None
        tx.is_categorized = bool(body.category_id)

    if body.notes is not None:
        tx.notes = body.notes or None

    if body.label is not None:
        tx.label = body.label

    db.commit()
    db.refresh(tx)
    return _to_response(tx, db)


def _to_response(tx: Transaction, db: DB) -> TransactionResponse:
    category_name = None
    if tx.category_id:
        cat = db.query(Category).filter(Category.id == tx.category_id).first()
        category_name = cat.name if cat else None

    return TransactionResponse(
        id=tx.id,
        account_id=tx.account_id,
        date=tx.date.isoformat(),
        amount=float(tx.amount),
        label=tx.label,
        transaction_type=tx.transaction_type,
        category_id=tx.category_id,
        category_name=category_name,
        is_categorized=tx.is_categorized,
        notes=tx.notes,
    )
