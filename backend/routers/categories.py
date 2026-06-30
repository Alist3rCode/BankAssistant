from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from dependencies import CurrentUser, DB
from models.models import Category

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryResponse(BaseModel):
    id: str
    name: str
    icon: Optional[str]
    color: Optional[str]
    is_income: bool
    is_system: bool

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    is_income: bool = False


@router.get("/", response_model=list[CategoryResponse])
async def list_categories(current_user: CurrentUser, db: DB):
    cats = db.query(Category).all()
    return [CategoryResponse(
        id=c.id, name=c.name, icon=c.icon, color=c.color,
        is_income=c.is_income, is_system=c.is_system,
    ) for c in cats]


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(body: CategoryCreate, current_user: CurrentUser, db: DB):
    cat = Category(name=body.name, icon=body.icon, color=body.color, is_income=body.is_income)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoryResponse(id=cat.id, name=cat.name, icon=cat.icon, color=cat.color,
                            is_income=cat.is_income, is_system=cat.is_system)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: str, body: CategoryCreate, current_user: CurrentUser, db: DB):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    if cat.is_system:
        raise HTTPException(status_code=400, detail="Les catégories système ne peuvent pas être modifiées")
    cat.name = body.name
    cat.icon = body.icon
    cat.color = body.color
    cat.is_income = body.is_income
    db.commit()
    db.refresh(cat)
    return CategoryResponse(id=cat.id, name=cat.name, icon=cat.icon, color=cat.color,
                            is_income=cat.is_income, is_system=cat.is_system)


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: str, current_user: CurrentUser, db: DB):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    if cat.is_system:
        raise HTTPException(status_code=400, detail="Les catégories système ne peuvent pas être supprimées")
    db.delete(cat)
    db.commit()
