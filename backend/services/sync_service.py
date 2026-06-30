"""
Service de synchronisation : orchestre le scraping woob → persistance SQLite.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Union

from sqlalchemy.orm import Session

from auth.security import decrypt
from models.models import AppSetting, BankAccount, Transaction
from scraper.ca_scraper import CreditAgricoleScraper, ScrapedAccount, ScrapedTransaction
from scraper.csv_import import ImportedTransaction
from scraper.ca_regions import CA_REGIONS

logger = logging.getLogger(__name__)


def _get_setting(db: Session, key: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not row:
        return ""
    if row.is_encrypted and row.value:
        try:
            return decrypt(row.value)
        except Exception:
            return ""
    return row.value


async def sync_all_accounts(db: Session) -> dict:
    """Point d'entrée principal : récupère les paramètres CA et synchronise tout."""
    region_id = _get_setting(db, "ca.region")
    login = _get_setting(db, "ca.login")
    password = _get_setting(db, "ca.password")

    if not all([region_id, login, password]):
        raise ValueError("Paramètres CA non configurés (région, login, password)")

    if region_id not in CA_REGIONS:
        raise ValueError(f"Région CA inconnue : {region_id}")

    _, region_url = CA_REGIONS[region_id]

    scraper = CreditAgricoleScraper(
        region_id=region_id,
        region_url=region_url,
        login=login,
        password=password,
    )

    logger.info("[sync] Récupération des comptes CA (%s)", region_id)
    scraped_accounts = await scraper.fetch_accounts()

    stats = {"accounts": 0, "transactions_new": 0, "transactions_updated": 0}

    for scraped in scraped_accounts:
        account = _upsert_account(db, scraped, region_id, region_url)
        stats["accounts"] += 1

        logger.info("[sync] Récupération transactions pour %s", account.name)
        transactions = await scraper.fetch_transactions(scraped)
        new_count = persist_transactions(db, account, transactions)
        stats["transactions_new"] += new_count

        account.last_synced = datetime.now(timezone.utc)
        db.commit()

    logger.info("[sync] Synchronisation terminée : %s", stats)
    return stats


def _upsert_account(
    db: Session,
    scraped: ScrapedAccount,
    region_id: str,
    region_url: str,
) -> BankAccount:
    account = db.query(BankAccount).filter(BankAccount.external_id == scraped.external_id).first()

    if account:
        account.balance = scraped.balance
        account.name = scraped.name
        db.commit()
        return account

    number = scraped.number
    masked = f"****{number[-4:]}" if len(number) >= 4 else number

    account = BankAccount(
        external_id=scraped.external_id,
        name=scraped.name,
        number_masked=masked,
        account_type=scraped.account_type,
        balance=scraped.balance,
        currency=scraped.currency,
        ca_region=region_id,
        ca_region_url=region_url,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    logger.info("[sync] Nouveau compte créé : %s", account.name)
    return account


def persist_transactions(
    db: Session,
    account: BankAccount,
    transactions: list[Union[ScrapedTransaction, ImportedTransaction]],
) -> int:
    """Persiste les transactions en ignorant les doublons (external_id unique)."""
    new_count = 0

    for tx in transactions:
        external_id = tx.external_id
        existing = db.query(Transaction).filter(
            Transaction.external_id == external_id,
            Transaction.account_id == account.id,
        ).first()

        if existing:
            continue

        new_tx = Transaction(
            external_id=external_id,
            account_id=account.id,
            date=tx.date,
            value_date=tx.value_date if hasattr(tx, "value_date") else None,
            amount=tx.amount if isinstance(tx.amount, Decimal) else Decimal(str(tx.amount)),
            label=tx.label,
            raw_label=tx.raw_label,
            transaction_type=tx.transaction_type,
        )
        db.add(new_tx)
        new_count += 1

    if new_count > 0:
        db.commit()
        logger.info("[sync] %d nouvelles transactions persistées pour %s", new_count, account.name)

    return new_count
