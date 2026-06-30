"""Service de notifications push via ntfy (self-hosted)."""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from config import settings
from models.models import NotificationLog

logger = logging.getLogger(__name__)


async def send_notification(
    db: Session,
    title: str,
    message: str,
    notification_type: str,
    priority: str = "default",
    tags: list[str] | None = None,
) -> bool:
    """Envoie une notification via ntfy et log le résultat."""
    log = NotificationLog(
        notification_type=notification_type,
        title=title,
        message=message,
        is_sent=False,
    )
    db.add(log)
    db.commit()

    if not settings.ntfy_url or not settings.ntfy_topic:
        log.error = "ntfy non configuré"
        db.commit()
        return False

    headers = {
        "Title": title,
        "Priority": priority,
        "Content-Type": "text/plain; charset=utf-8",
    }
    if tags:
        headers["Tags"] = ",".join(tags)
    if settings.ntfy_token:
        headers["Authorization"] = f"Bearer {settings.ntfy_token}"

    url = f"{settings.ntfy_url.rstrip('/')}/{settings.ntfy_topic}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, content=message.encode(), headers=headers)
            resp.raise_for_status()

        log.is_sent = True
        log.sent_at = datetime.now(timezone.utc)
        db.commit()
        return True

    except Exception as e:
        log.error = str(e)
        db.commit()
        logger.warning("[ntfy] Envoi échoué : %s", e)
        return False


async def send_daily_report(db: Session) -> None:
    from sqlalchemy import func
    from models.models import Transaction, BankAccount
    from datetime import date, timedelta

    today = date.today()
    start_of_month = today.replace(day=1)

    total_expenses = (
        db.query(func.sum(Transaction.amount))
        .filter(Transaction.amount < 0, Transaction.date >= start_of_month)
        .scalar()
        or 0
    )
    total_income = (
        db.query(func.sum(Transaction.amount))
        .filter(Transaction.amount > 0, Transaction.date >= start_of_month)
        .scalar()
        or 0
    )

    accounts = db.query(BankAccount).filter(BankAccount.is_active == True).all()
    balance_total = sum(float(a.balance) for a in accounts)

    message = (
        f"📊 Rapport du {today.strftime('%d/%m/%Y')}\n"
        f"Solde total : {balance_total:+.2f} €\n"
        f"Dépenses ce mois : {float(total_expenses):.2f} €\n"
        f"Revenus ce mois : {float(total_income):.2f} €"
    )

    await send_notification(
        db=db,
        title="BankAssistant — Rapport journalier",
        message=message,
        notification_type="DAILY_REPORT",
        tags=["bank", "chart_with_upwards_trend"],
    )
