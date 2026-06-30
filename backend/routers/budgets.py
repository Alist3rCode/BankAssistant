from decimal import Decimal
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from dependencies import CurrentUser, DB
from models.models import Budget, BudgetEntry, Transaction

router = APIRouter(prefix="/budgets", tags=["budgets"])


class BudgetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_amount: Optional[float] = None
    currency: str = "EUR"
    period_type: str = "monthly"
    color: Optional[str] = None
    is_default: bool = False


class BudgetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    target_amount: Optional[float]
    currency: str
    period_type: str
    color: Optional[str]
    is_active: bool
    is_default: bool
    spent: float = 0.0
    income: float = 0.0
    entry_count: int = 0

    model_config = {"from_attributes": True}


class BudgetEntryCreate(BaseModel):
    transaction_id: str
    amount: float
    notes: Optional[str] = None


class EntryDetail(BaseModel):
    id: str
    transaction_id: str
    amount: float
    notes: Optional[str]
    transaction_label: str
    transaction_date: str
    transaction_amount: float


def _compute_stats(db, budget_id: str) -> tuple[float, float, int]:
    """Retourne (spent, income, entry_count) pour un budget."""
    rows = (
        db.query(BudgetEntry.amount)
        .filter(BudgetEntry.budget_id == budget_id)
        .all()
    )
    spent = sum(float(r.amount) for r in rows if float(r.amount) < 0)
    income = sum(float(r.amount) for r in rows if float(r.amount) > 0)
    return abs(spent), income, len(rows)


@router.get("/", response_model=list[BudgetResponse])
async def list_budgets(current_user: CurrentUser, db: DB):
    budgets = db.query(Budget).filter(Budget.is_active == True).all()
    result = []
    for b in budgets:
        spent, income, entry_count = _compute_stats(db, b.id)
        result.append(BudgetResponse(
            id=b.id, name=b.name, description=b.description,
            target_amount=float(b.target_amount) if b.target_amount else None,
            currency=b.currency, period_type=b.period_type, color=b.color,
            is_active=b.is_active, is_default=b.is_default,
            spent=spent, income=income, entry_count=entry_count,
        ))
    return result


@router.post("/", response_model=BudgetResponse, status_code=201)
async def create_budget(body: BudgetCreate, current_user: CurrentUser, db: DB):
    budget = Budget(
        name=body.name,
        description=body.description,
        target_amount=Decimal(str(body.target_amount)) if body.target_amount else None,
        currency=body.currency,
        period_type=body.period_type,
        color=body.color,
        is_default=body.is_default,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return BudgetResponse(
        id=budget.id, name=budget.name, description=budget.description,
        target_amount=float(budget.target_amount) if budget.target_amount else None,
        currency=budget.currency, period_type=budget.period_type, color=budget.color,
        is_active=budget.is_active, is_default=budget.is_default,
        spent=0.0, income=0.0, entry_count=0,
    )


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(budget_id: str, body: BudgetCreate, current_user: CurrentUser, db: DB):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget introuvable")

    budget.name = body.name
    budget.description = body.description
    budget.target_amount = Decimal(str(body.target_amount)) if body.target_amount else None
    budget.period_type = body.period_type
    budget.color = body.color
    budget.is_default = body.is_default
    db.commit()
    db.refresh(budget)
    spent, income, entry_count = _compute_stats(db, budget.id)
    return BudgetResponse(
        id=budget.id, name=budget.name, description=budget.description,
        target_amount=float(budget.target_amount) if budget.target_amount else None,
        currency=budget.currency, period_type=budget.period_type, color=budget.color,
        is_active=budget.is_active, is_default=budget.is_default,
        spent=spent, income=income, entry_count=entry_count,
    )


@router.delete("/{budget_id}", status_code=204)
async def delete_budget(budget_id: str, current_user: CurrentUser, db: DB):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget introuvable")
    if budget.is_default:
        raise HTTPException(status_code=400, detail="Le budget principal ne peut pas être supprimé")
    budget.is_active = False
    db.commit()


@router.get("/{budget_id}/entries", response_model=list[EntryDetail])
async def list_entries(budget_id: str, current_user: CurrentUser, db: DB):
    """Liste les transactions assignées à un budget avec leurs détails."""
    entries = (
        db.query(BudgetEntry)
        .filter(BudgetEntry.budget_id == budget_id)
        .order_by(BudgetEntry.assigned_at.desc())
        .all()
    )
    result = []
    for e in entries:
        tx = db.query(Transaction).filter(Transaction.id == e.transaction_id).first()
        if tx:
            result.append(EntryDetail(
                id=e.id,
                transaction_id=tx.id,
                amount=float(e.amount),
                notes=e.notes,
                transaction_label=tx.label or tx.raw_label,
                transaction_date=tx.date.isoformat(),
                transaction_amount=float(tx.amount),
            ))
    return result


@router.post("/{budget_id}/entries", status_code=201)
async def assign_transaction(budget_id: str, body: BudgetEntryCreate, current_user: CurrentUser, db: DB):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget introuvable")
    tx = db.query(Transaction).filter(Transaction.id == body.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")

    # Utilise le montant de la transaction si non précisé
    amount = body.amount if body.amount != 0 else float(tx.amount)

    entry = BudgetEntry(
        budget_id=budget_id,
        transaction_id=body.transaction_id,
        amount=Decimal(str(amount)),
        notes=body.notes,
    )
    db.add(entry)
    db.commit()
    return {"id": entry.id, "message": "Transaction assignée au budget"}


@router.delete("/{budget_id}/entries/{entry_id}", status_code=204)
async def remove_entry(budget_id: str, entry_id: str, current_user: CurrentUser, db: DB):
    entry = db.query(BudgetEntry).filter(
        BudgetEntry.id == entry_id,
        BudgetEntry.budget_id == budget_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrée introuvable")
    db.delete(entry)
    db.commit()
