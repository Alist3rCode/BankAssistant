"""
Jobs APScheduler — scraping journalier automatique et alertes.
L'heure de déclenchement est configurable depuis l'IHM (app_settings).
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from database import SessionLocal
from models.models import AppSetting, BankAccount, NotificationLog

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Europe/Paris")

JOB_ID_SCRAPE = "daily_scrape"
JOB_ID_REPORT = "daily_report"


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row else default


async def run_scraping_job() -> None:
    """Job principal : récupère les transactions depuis CA et les persiste."""
    logger.info("[scheduler] Démarrage du scraping journalier")
    db = SessionLocal()
    try:
        from services.sync_service import sync_all_accounts
        await sync_all_accounts(db)
    except Exception as e:
        logger.error("[scheduler] Erreur scraping : %s", e)
    finally:
        db.close()


async def run_daily_report_job() -> None:
    """Job de rapport : envoie un résumé quotidien via ntfy."""
    logger.info("[scheduler] Envoi du rapport journalier")
    db = SessionLocal()
    try:
        from services.notification_service import send_daily_report
        await send_daily_report(db)
    except Exception as e:
        logger.error("[scheduler] Erreur rapport : %s", e)
    finally:
        db.close()


def load_schedule_from_db() -> None:
    """Lit les settings de la BDD et (re)configure les jobs."""
    db = SessionLocal()
    try:
        scraping_enabled = _get_setting(db, "scraping.enabled", "true").lower() == "true"
        hour = int(_get_setting(db, "scraping.schedule_hour", "6"))
        minute = int(_get_setting(db, "scraping.schedule_minute", "0"))

        if scheduler.get_job(JOB_ID_SCRAPE):
            scheduler.remove_job(JOB_ID_SCRAPE)

        if scraping_enabled:
            scheduler.add_job(
                run_scraping_job,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=JOB_ID_SCRAPE,
                name="Scraping CA journalier",
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info("[scheduler] Job scraping planifié à %02d:%02d", hour, minute)
        else:
            logger.info("[scheduler] Scraping automatique désactivé")

        # Rapport journalier
        report_enabled = _get_setting(db, "notifications.daily_report", "false").lower() == "true"
        report_hour = int(_get_setting(db, "notifications.daily_report_hour", "8"))

        if scheduler.get_job(JOB_ID_REPORT):
            scheduler.remove_job(JOB_ID_REPORT)

        if report_enabled:
            scheduler.add_job(
                run_daily_report_job,
                trigger=CronTrigger(hour=report_hour, minute=0),
                id=JOB_ID_REPORT,
                name="Rapport journalier",
                replace_existing=True,
            )
    finally:
        db.close()


def start_scheduler() -> None:
    load_schedule_from_db()
    scheduler.start()
    logger.info("[scheduler] APScheduler démarré")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def trigger_scraping_now() -> None:
    """Déclenche un scraping immédiat (depuis l'IHM)."""
    scheduler.add_job(
        run_scraping_job,
        id="manual_scrape",
        name="Scraping manuel",
        replace_existing=True,
    )
