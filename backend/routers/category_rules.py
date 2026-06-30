from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from dependencies import CurrentUser, DB
from models.models import CategoryRule, Category
from services.categorization_service import apply_rules

router = APIRouter(prefix="/category-rules", tags=["category-rules"])

VALID_MATCH_TYPES = {"contains", "starts_with", "ends_with", "regex"}


class RuleCreate(BaseModel):
    pattern: str
    match_type: str = "contains"
    category_id: str
    priority: int = 0
    is_active: bool = True


class RuleResponse(BaseModel):
    id: str
    pattern: str
    match_type: str
    category_id: str
    category_name: str
    priority: int
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[RuleResponse])
async def list_rules(current_user: CurrentUser, db: DB):
    rules = (
        db.query(CategoryRule)
        .join(CategoryRule.category)
        .order_by(CategoryRule.priority.desc(), CategoryRule.created_at)
        .all()
    )
    return [RuleResponse(
        id=r.id, pattern=r.pattern, match_type=r.match_type,
        category_id=r.category_id, category_name=r.category.name,
        priority=r.priority, is_active=r.is_active,
    ) for r in rules]


@router.post("/", response_model=RuleResponse, status_code=201)
async def create_rule(body: RuleCreate, current_user: CurrentUser, db: DB):
    if body.match_type not in VALID_MATCH_TYPES:
        raise HTTPException(status_code=400, detail=f"match_type doit être parmi {VALID_MATCH_TYPES}")
    cat = db.query(Category).filter(Category.id == body.category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    rule = CategoryRule(
        pattern=body.pattern,
        match_type=body.match_type,
        category_id=body.category_id,
        priority=body.priority,
        is_active=body.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return RuleResponse(
        id=rule.id, pattern=rule.pattern, match_type=rule.match_type,
        category_id=rule.category_id, category_name=cat.name,
        priority=rule.priority, is_active=rule.is_active,
    )


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: str, body: RuleCreate, current_user: CurrentUser, db: DB):
    rule = db.query(CategoryRule).filter(CategoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    if body.match_type not in VALID_MATCH_TYPES:
        raise HTTPException(status_code=400, detail=f"match_type doit être parmi {VALID_MATCH_TYPES}")
    cat = db.query(Category).filter(Category.id == body.category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    rule.pattern = body.pattern
    rule.match_type = body.match_type
    rule.category_id = body.category_id
    rule.priority = body.priority
    rule.is_active = body.is_active
    db.commit()
    db.refresh(rule)
    return RuleResponse(
        id=rule.id, pattern=rule.pattern, match_type=rule.match_type,
        category_id=rule.category_id, category_name=cat.name,
        priority=rule.priority, is_active=rule.is_active,
    )


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, current_user: CurrentUser, db: DB):
    rule = db.query(CategoryRule).filter(CategoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    db.delete(rule)
    db.commit()


@router.post("/apply")
async def apply_rules_to_transactions(
    current_user: CurrentUser,
    db: DB,
    all_transactions: bool = False,
):
    """Applique toutes les règles actives sur les transactions (non catégorisées par défaut)."""
    count = apply_rules(db, only_uncategorized=not all_transactions)
    return {"updated": count, "message": f"{count} transaction(s) catégorisée(s)"}
