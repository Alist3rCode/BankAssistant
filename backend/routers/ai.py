"""Routes IA — chat, prévisions et suggestions budgétaires via LiteLLM."""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth.security import decrypt
from dependencies import CurrentUser, DB
from models.models import AppSetting, BankAccount, Budget, BudgetEntry, Category, Transaction

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────

def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not row:
        return default
    if row.is_encrypted and row.value:
        try:
            return decrypt(row.value)
        except Exception:
            return default
    return row.value or default


def _build_litellm(db: Session):
    """Retourne (full_model_string, litellm_kwargs) configurés depuis la DB."""
    import litellm
    import os

    provider = _get_setting(db, "ai.provider", "groq")
    model = _get_setting(db, "ai.model", "")
    groq_key = _get_setting(db, "ai.groq_api_key", "")
    mistral_key = _get_setting(db, "ai.mistral_api_key", "")
    ollama_url = _get_setting(db, "ollama_base_url", "")

    if groq_key:
        litellm.api_key = groq_key
    if mistral_key:
        os.environ["MISTRAL_API_KEY"] = mistral_key

    if provider == "groq":
        full_model = f"groq/{model or 'llama-3.3-70b-versatile'}"
        litellm.api_key = groq_key
    elif provider == "mistral":
        full_model = f"mistral/{model or 'mistral-large-latest'}"
    elif provider == "ollama":
        full_model = f"ollama/{model or 'mistral-nemo'}"
        if ollama_url:
            litellm.api_base = ollama_url
    else:
        full_model = model or "groq/llama-3.3-70b-versatile"

    return full_model, provider


def _monthly_stats(db: Session, months: int = 3) -> dict:
    """Calcule les stats de dépenses des N derniers mois par catégorie."""
    today = date.today()
    start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    for _ in range(months - 1):
        start = (start - timedelta(days=1)).replace(day=1)

    rows = (
        db.query(
            Category.name,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(Transaction.date >= start, Transaction.amount < 0)
        .group_by(Category.id)
        .all()
    )

    return {r.name: float(r.total) for r in rows}


def _current_month_spending(db: Session) -> dict:
    """Dépenses du mois en cours par catégorie."""
    today = date.today()
    start_of_month = today.replace(day=1)

    rows = (
        db.query(
            Category.name,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(Transaction.date >= start_of_month, Transaction.amount < 0)
        .group_by(Category.id)
        .all()
    )
    return {r.name: float(r.total) for r in rows}


# ─── Schemas ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: str = ""


class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str


class ForecastResponse(BaseModel):
    analysis: str
    provider: str
    model: str
    current_month_total: float
    projected_month_total: float
    days_elapsed: int
    days_in_month: int


class SuggestionsResponse(BaseModel):
    suggestions: str
    provider: str
    model: str


# ─── Routes ────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, current_user: CurrentUser, db: DB):
    import litellm

    full_model, provider = _build_litellm(db)

    system_prompt = (
        "Tu es un assistant bancaire personnel francophone. "
        "Tu analyses les données financières fournies et réponds de manière claire, concise et utile. "
        "Tu ne partages jamais de données sensibles hors du contexte fourni. "
        "Toujours répondre en français."
    )

    messages = [
        {"role": "system", "content": system_prompt + ("\n\n" + body.context if body.context else "")},
        {"role": "user", "content": body.message},
    ]

    try:
        response = await litellm.acompletion(model=full_model, messages=messages, max_tokens=1024, temperature=0.3)
        answer = response.choices[0].message.content or "Je n'ai pas pu générer une réponse."
    except Exception as e:
        logger.error("LiteLLM chat error : %s", e)
        raise HTTPException(status_code=502, detail=f"Erreur IA : {e}")

    return ChatResponse(response=answer, provider=provider, model=full_model)


@router.post("/forecast", response_model=ForecastResponse)
async def forecast(current_user: CurrentUser, db: DB):
    """Projette les dépenses de fin de mois basé sur la tendance actuelle et l'historique."""
    import litellm

    today = date.today()
    import calendar
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_elapsed = today.day

    current = _current_month_spending(db)
    historical = _monthly_stats(db, months=3)

    current_total = sum(current.values())
    avg_daily = current_total / days_elapsed if days_elapsed > 0 else 0
    projected_total = avg_daily * days_in_month

    accounts = db.query(BankAccount).filter(BankAccount.is_active == True).all()
    total_balance = sum(float(a.balance) for a in accounts)

    context = f"""Données financières — {today.strftime('%B %Y')}

Solde total des comptes : {total_balance:+.2f} €
Jour dans le mois : {days_elapsed}/{days_in_month}

Dépenses ce mois (par catégorie) :
{chr(10).join(f"  - {cat}: {amt:.2f} €" for cat, amt in sorted(current.items(), key=lambda x: x[1]))}
Total mois en cours : {current_total:.2f} €

Moyenne des 3 derniers mois (par catégorie) :
{chr(10).join(f"  - {cat}: {amt/3:.2f} €/mois" for cat, amt in sorted(historical.items(), key=lambda x: x[1]))}

Projection fin de mois (rythme actuel) : {projected_total:.2f} €"""

    prompt = (
        f"Analyse mes dépenses du mois de {today.strftime('%B %Y')} et génère :\n"
        "1. Une analyse de la tendance vs les mois précédents\n"
        "2. Une projection précise de fin de mois par catégorie\n"
        "3. Les catégories qui dépassent la moyenne historique\n"
        "4. 2-3 conseils concrets pour optimiser d'ici la fin du mois\n\n"
        "Sois concis et pratique. Réponds en français."
    )

    full_model, provider = _build_litellm(db)

    system = "Tu es un conseiller financier personnel francophone, expert en analyse de budgets."
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": context + "\n\n" + prompt},
    ]

    try:
        response = await litellm.acompletion(model=full_model, messages=messages, max_tokens=1500, temperature=0.2)
        analysis = response.choices[0].message.content or "Analyse indisponible."
    except Exception as e:
        logger.error("LiteLLM forecast error : %s", e)
        raise HTTPException(status_code=502, detail=f"Erreur IA : {e}")

    return ForecastResponse(
        analysis=analysis,
        provider=provider,
        model=full_model,
        current_month_total=current_total,
        projected_month_total=projected_total,
        days_elapsed=days_elapsed,
        days_in_month=days_in_month,
    )


@router.post("/suggestions", response_model=SuggestionsResponse)
async def budget_suggestions(current_user: CurrentUser, db: DB):
    """Génère des suggestions d'optimisation budgétaire basées sur l'historique."""
    import litellm

    today = date.today()
    historical = _monthly_stats(db, months=6)
    budgets = db.query(Budget).filter(Budget.is_active == True).all()

    budgets_info = []
    for b in budgets:
        entries_total = (
            db.query(func.sum(BudgetEntry.amount)).filter(BudgetEntry.budget_id == b.id).scalar() or 0
        )
        budgets_info.append(
            f"  - {b.name} : {float(entries_total):.2f} € alloués"
            + (f" / {float(b.target_amount):.2f} € cible" if b.target_amount else "")
        )

    accounts = db.query(BankAccount).filter(BankAccount.is_active == True).all()
    total_balance = sum(float(a.balance) for a in accounts)

    income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.amount > 0,
        Transaction.date >= today.replace(day=1),
    ).scalar() or 0

    context = f"""Profil financier au {today.strftime('%d/%m/%Y')}

Solde total : {total_balance:.2f} €
Revenus mois en cours : {float(income):.2f} €

Dépenses moyennes sur 6 mois (par catégorie) :
{chr(10).join(f"  - {cat}: {abs(amt)/6:.2f} €/mois" for cat, amt in sorted(historical.items(), key=lambda x: x[1]))}

Budgets actuels :
{chr(10).join(budgets_info) or "  (aucun budget configuré)"}"""

    prompt = (
        "En te basant sur ces données financières :\n"
        "1. Identifie les 3 postes de dépenses les plus optimisables\n"
        "2. Propose des montants cibles réalistes pour chaque poste\n"
        "3. Suggère une répartition idéale du budget mensuel (règle 50/30/20 adaptée)\n"
        "4. Donne 3 actions concrètes à mettre en place ce mois-ci\n\n"
        "Sois précis avec des chiffres. Réponds en français."
    )

    full_model, provider = _build_litellm(db)
    messages = [
        {"role": "system", "content": "Tu es un conseiller financier personnel francophone expert en optimisation budgétaire."},
        {"role": "user", "content": context + "\n\n" + prompt},
    ]

    try:
        response = await litellm.acompletion(model=full_model, messages=messages, max_tokens=1500, temperature=0.2)
        suggestions = response.choices[0].message.content or "Suggestions indisponibles."
    except Exception as e:
        logger.error("LiteLLM suggestions error : %s", e)
        raise HTTPException(status_code=502, detail=f"Erreur IA : {e}")

    return SuggestionsResponse(suggestions=suggestions, provider=provider, model=full_model)
