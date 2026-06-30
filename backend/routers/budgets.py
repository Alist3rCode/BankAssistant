from decimal import Decimal
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
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

    model_config = {"from_attributes": True}


class BudgetEntryCreate(BaseModel):
    transaction_id: str
    amount: float
    notes: Optional[str] = None


@router.get("/", response_model=list[BudgetResponse])
async def list_budgets(current_user: CurrentUser, db: DB):
    budgets = db.query(Budget).filter(Budget.is_active == True).all()
    return [BudgetResponse(
        id=b.id, name=b.name, description=b.description,
        target_amount=float(b.target_amount) if b.target_amount else None,
        currency=b.currency, period_type=b.period_type, color=b.color,
        is_active=b.is_active, is_default=b.is_default,
    ) for b in budgets]


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
    return BudgetResponse(
        id=budget.id, name=budget.name, description=budget.description,
        target_amount=float(budget.target_amount) if budget.target_amount else None,
        currency=budget.currency, period_type=budget.period_type, color=budget.color,
        is_active=budget.is_active, is_default=budget.is_default,
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


@router.post("/{budget_id}/entries", status_code=201)
async def assign_transaction(budget_id: str, body: BudgetEntryCreate, current_user: CurrentUser, db: DB):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget introuvable")
    tx = db.query(Transaction).filter(Transaction.id == body.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")

    entry = BudgetEntry(
        budget_id=budget_id,
        transaction_id=body.transaction_id,
        amount=Decimal(str(body.amount)),
        notes=body.notes,
    )
    db.add(entry)
    db.commit()
    return {"id": entry.id, "message": "Transaction assignée au budget"}
