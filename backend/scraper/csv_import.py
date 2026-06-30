"""
Import de transactions depuis des fichiers CSV ou OFX exportés depuis le site CA.
Fallback si woob se casse après une MAJ du site CA.
"""

import csv
import hashlib
import io
import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ImportedTransaction:
    external_id: str
    date: date
    value_date: Optional[date]
    amount: Decimal
    label: str
    raw_label: str
    transaction_type: str = "unknown"


class CSVImporter:
    """
    Importe le CSV Crédit Agricole.
    Format CA : Date;Date valeur;Libellé;Débit;Crédit
    (Le séparateur peut être ; ou ,)
    """

    KNOWN_HEADERS = {
        "date": ["date", "date opération", "date operation"],
        "value_date": ["date valeur", "valeur"],
        "label": ["libellé", "libelle", "description", "motif"],
        "debit": ["débit", "debit", "montant débit", "montant debit"],
        "credit": ["crédit", "credit", "montant crédit", "montant credit"],
        "amount": ["montant", "amount"],
    }

    def parse(self, content: bytes, account_external_id: str) -> list[ImportedTransaction]:
        text = content.decode("utf-8-sig", errors="replace")  # gère le BOM UTF-8 du CA
        dialect = self._detect_dialect(text)
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)

        # Normaliser les noms de colonnes
        if reader.fieldnames is None:
            raise ValueError("Fichier CSV vide ou sans en-tête")

        col_map = self._map_columns(reader.fieldnames)
        transactions = []

        for row_num, row in enumerate(reader, start=2):
            try:
                tx = self._parse_row(row, col_map, account_external_id)
                if tx:
                    transactions.append(tx)
            except Exception as e:
                logger.warning("Ligne %d ignorée : %s", row_num, e)

        logger.info("Import CSV : %d transactions importées", len(transactions))
        return transactions

    def _detect_dialect(self, text: str) -> str:
        sample = text[:2048]
        if sample.count(";") > sample.count(","):
            return "excel-tab"  # On surcharge le séparateur ci-dessous
        return "excel"

    def _map_columns(self, fieldnames: list[str]) -> dict[str, str]:
        """Mappe les colonnes du CSV vers les noms internes."""
        result = {}
        normalized = {f.strip().lower(): f for f in fieldnames}

        for internal, candidates in self.KNOWN_HEADERS.items():
            for candidate in candidates:
                if candidate in normalized:
                    result[internal] = normalized[candidate]
                    break

        if "date" not in result:
            raise ValueError("Colonne 'Date' introuvable dans le CSV")
        if "label" not in result:
            raise ValueError("Colonne 'Libellé' introuvable dans le CSV")

        return result

    def _parse_row(
        self, row: dict, col_map: dict, account_external_id: str
    ) -> Optional[ImportedTransaction]:
        raw_date = row.get(col_map.get("date", ""), "").strip()
        if not raw_date:
            return None

        tx_date = self._parse_date(raw_date)
        value_date = None
        if "value_date" in col_map:
            raw_vdate = row.get(col_map["value_date"], "").strip()
            if raw_vdate:
                value_date = self._parse_date(raw_vdate)

        raw_label = row.get(col_map.get("label", ""), "").strip()
        label = " ".join(raw_label.split())

        amount = self._parse_amount(row, col_map)
        if amount is None:
            return None

        # Génération d'un ID stable basé sur les données
        external_id = self._generate_id(account_external_id, tx_date, amount, raw_label)

        return ImportedTransaction(
            external_id=external_id,
            date=tx_date,
            value_date=value_date,
            amount=amount,
            label=label,
            raw_label=raw_label,
        )

    def _parse_amount(self, row: dict, col_map: dict) -> Optional[Decimal]:
        if "amount" in col_map:
            raw = row.get(col_map["amount"], "").strip()
            return self._to_decimal(raw)

        # Format CA : colonnes séparées Débit / Crédit
        debit_raw = row.get(col_map.get("debit", ""), "").strip() if "debit" in col_map else ""
        credit_raw = row.get(col_map.get("credit", ""), "").strip() if "credit" in col_map else ""

        if credit_raw:
            val = self._to_decimal(credit_raw)
            if val and val != Decimal("0"):
                return abs(val)

        if debit_raw:
            val = self._to_decimal(debit_raw)
            if val and val != Decimal("0"):
                return -abs(val)  # débit = montant négatif

        return None

    @staticmethod
    def _to_decimal(value: str) -> Optional[Decimal]:
        if not value:
            return None
        # Gérer les formats français : 1.234,56 ou 1234,56 ou 1234.56
        cleaned = value.replace("\xa0", "").replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        cleaned = cleaned.replace("+", "")
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    @staticmethod
    def _parse_date(raw: str) -> date:
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Format de date non reconnu : {raw!r}")

    @staticmethod
    def _generate_id(account_id: str, tx_date: date, amount: Decimal, label: str) -> str:
        raw = f"{account_id}|{tx_date}|{amount}|{label}"
        return "csv_" + hashlib.sha256(raw.encode()).hexdigest()[:24]


class OFXImporter:
    """
    Importe le format OFX/QFX exporté par le Crédit Agricole.
    """

    def parse(self, content: bytes, account_external_id: str) -> list[ImportedTransaction]:
        try:
            from ofxparse import OfxParser  # type: ignore[import]
        except ImportError as e:
            raise RuntimeError("ofxparse non installé. Ajoutez `ofxparse` aux requirements.") from e

        ofx = OfxParser.parse(io.BytesIO(content))
        transactions = []

        for account in ofx.accounts:
            for tx in account.statement.transactions:
                tx_date = tx.date.date() if isinstance(tx.date, datetime) else tx.date
                label = " ".join(str(tx.memo or tx.payee or "").split())
                raw_label = str(tx.memo or "")
                amount = Decimal(str(tx.amount))
                external_id = str(tx.id) if tx.id else CSVImporter._generate_id(
                    account_external_id, tx_date, amount, raw_label
                )
                transactions.append(
                    ImportedTransaction(
                        external_id=f"ofx_{external_id}",
                        date=tx_date,
                        value_date=None,
                        amount=amount,
                        label=label,
                        raw_label=raw_label,
                        transaction_type=str(tx.type).lower() if tx.type else "unknown",
                    )
                )

        logger.info("Import OFX : %d transactions importées", len(transactions))
        return transactions
