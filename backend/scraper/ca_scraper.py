"""
Scraper Crédit Agricole via woob (module cragr).

woob est un framework Python qui simule la navigation sur l'espace client CA.
Le module `cragr` supporte les ~37 caisses régionales.

Ref: https://gitlab.com/woob/woob (release 3.7, oct 2024)
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapedAccount:
    external_id: str
    name: str
    number: str  # numéro brut
    account_type: str
    balance: Decimal
    currency: str = "EUR"


@dataclass
class ScrapedTransaction:
    external_id: str
    account_external_id: str
    date: date
    value_date: Optional[date]
    amount: Decimal
    label: str
    raw_label: str
    transaction_type: str


class CreditAgricoleScraper:
    """
    Interface vers woob/cragr pour la récupération des données CA.

    Setup woob (exécuté une seule fois au démarrage ou depuis l'IHM) :
      1. `woob update`  — télécharge/met à jour le module cragr
      2. Configure le backend via _write_backend_config()
    """

    def __init__(self, region_id: str, region_url: str, login: str, password: str):
        self.region_id = region_id
        self.region_url = region_url
        self.login = login
        self.password = password
        self.woob_dir = Path(settings.woob_data_dir)
        self.backend_name = "bankassistant_ca"

    # ------------------------------------------------------------------
    # Config woob
    # ------------------------------------------------------------------

    def _write_backend_config(self) -> None:
        """Écrit le fichier de configuration du backend woob."""
        backends_dir = self.woob_dir / "backends"
        backends_dir.mkdir(parents=True, exist_ok=True)

        config_content = (
            f"[{self.backend_name}]\n"
            f"_module = cragr\n"
            f"website = {self.region_url}\n"
            f"login = {self.login}\n"
            f"password = {self.password}\n"
        )
        config_path = backends_dir / self.backend_name
        config_path.write_text(config_content)
        config_path.chmod(0o600)  # lisible uniquement par le processus

    def _cleanup_backend_config(self) -> None:
        """Supprime le fichier de config après utilisation (sécurité)."""
        config_path = self.woob_dir / "backends" / self.backend_name
        if config_path.exists():
            config_path.unlink()

    # ------------------------------------------------------------------
    # API publique (async pour ne pas bloquer FastAPI)
    # ------------------------------------------------------------------

    async def fetch_accounts(self) -> list[ScrapedAccount]:
        return await asyncio.to_thread(self._fetch_accounts_sync)

    async def fetch_transactions(
        self,
        account: ScrapedAccount,
        since: Optional[date] = None,
    ) -> list[ScrapedTransaction]:
        return await asyncio.to_thread(self._fetch_transactions_sync, account, since)

    async def test_connection(self) -> bool:
        """Teste les credentials CA. Retourne True si OK."""
        try:
            accounts = await self.fetch_accounts()
            return len(accounts) >= 0
        except Exception as e:
            logger.warning("Connexion CA échouée : %s", e)
            return False

    # ------------------------------------------------------------------
    # Implémentation synchrone (appelée via to_thread)
    # ------------------------------------------------------------------

    def _fetch_accounts_sync(self) -> list[ScrapedAccount]:
        self._write_backend_config()
        try:
            return self._run_woob_fetch_accounts()
        finally:
            self._cleanup_backend_config()

    def _fetch_transactions_sync(
        self,
        account: ScrapedAccount,
        since: Optional[date],
    ) -> list[ScrapedTransaction]:
        self._write_backend_config()
        try:
            return self._run_woob_fetch_transactions(account, since)
        finally:
            self._cleanup_backend_config()

    def _run_woob_fetch_accounts(self) -> list[ScrapedAccount]:
        """Appel woob Python API pour récupérer les comptes."""
        try:
            from woob.core import Woob
            from woob.capabilities.bank import CapBank
        except ImportError as e:
            raise RuntimeError(
                "woob n'est pas installé ou non compatible avec cet OS. "
                "Utilisez l'import CSV/OFX depuis l'interface (Transactions → Import)."
            ) from e

        w = Woob(workdir=str(self.woob_dir))
        accounts = []

        for backend in w.iter_backends(backend_name=self.backend_name, caps=CapBank):
            for acc in backend.iter_accounts():
                accounts.append(
                    ScrapedAccount(
                        external_id=str(acc.id),
                        name=str(acc.label),
                        number=str(acc.id),
                        account_type=self._map_account_type(str(acc.type)),
                        balance=Decimal(str(acc.balance)) if acc.balance is not None else Decimal("0"),
                        currency=str(acc.currency) if acc.currency else "EUR",
                    )
                )

        w.deinit()
        return accounts

    def _run_woob_fetch_transactions(
        self,
        account: ScrapedAccount,
        since: Optional[date],
    ) -> list[ScrapedTransaction]:
        """Appel woob Python API pour récupérer les transactions."""
        try:
            from woob.core import Woob
            from woob.capabilities.bank import CapBank
        except ImportError as e:
            raise RuntimeError("woob n'est pas installé.") from e

        w = Woob(workdir=str(self.woob_dir))
        transactions = []

        for backend in w.iter_backends(backend_name=self.backend_name, caps=CapBank):
            # Reconstituer l'objet account woob depuis l'external_id
            woob_account = None
            for acc in backend.iter_accounts():
                if str(acc.id) == account.external_id:
                    woob_account = acc
                    break

            if woob_account is None:
                logger.warning("Compte %s introuvable dans woob", account.external_id)
                continue

            for tr in backend.iter_history(woob_account):
                tr_date = tr.date.date() if isinstance(tr.date, datetime) else tr.date
                if since and tr_date < since:
                    continue

                value_date = None
                if tr.vdate:
                    value_date = tr.vdate.date() if isinstance(tr.vdate, datetime) else tr.vdate

                transactions.append(
                    ScrapedTransaction(
                        external_id=str(tr.id) if tr.id else self._generate_tx_id(tr),
                        account_external_id=account.external_id,
                        date=tr_date,
                        value_date=value_date,
                        amount=Decimal(str(tr.amount)),
                        label=self._clean_label(str(tr.label)),
                        raw_label=str(tr.raw),
                        transaction_type=self._map_transaction_type(str(tr.type)),
                    )
                )

        w.deinit()
        return transactions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_account_type(woob_type: str) -> str:
        mapping = {
            "TYPE_CHECKING": "checking",
            "TYPE_SAVINGS": "savings",
            "TYPE_LOAN": "loan",
            "TYPE_MARKET": "market",
            "TYPE_LIFE_INSURANCE": "life_insurance",
            "TYPE_PEE": "pee",
            "TYPE_PERCO": "perco",
            "TYPE_DEPOSIT": "deposit",
        }
        return mapping.get(woob_type, "other")

    @staticmethod
    def _map_transaction_type(woob_type: str) -> str:
        mapping = {
            "TYPE_TRANSFER": "transfer",
            "TYPE_ORDER": "order",
            "TYPE_CHECK": "check",
            "TYPE_CARD": "card",
            "TYPE_WITHDRAWAL": "withdrawal",
            "TYPE_PAYBACK": "payback",
            "TYPE_BANK": "bank_fee",
            "TYPE_DEFERRED_CARD": "card_deferred",
            "TYPE_DIRECT_DEBIT": "direct_debit",
        }
        return mapping.get(woob_type, "unknown")

    @staticmethod
    def _clean_label(label: str) -> str:
        """Nettoie le libellé de transaction (supprime les espaces multiples)."""
        return " ".join(label.split())

    @staticmethod
    def _generate_tx_id(tr) -> str:
        """Génère un ID de transaction si woob n'en fournit pas."""
        import hashlib
        raw = f"{tr.date}{tr.amount}{tr.label}{tr.raw}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
