"""Export des transactions en CSV."""

import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc

from dependencies import CurrentUser, DB
from models.models import Transaction, BankAccount, Category, BudgetEntry, Budget

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/csv")
async def export_csv(
    current_user: CurrentUser,
    db: DB,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    account_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
):
    """Exporte les transactions filtrées au format CSV (UTF-8 BOM pour Excel)."""
    query = db.query(Transaction).order_by(desc(Transaction.date))

    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)

    transactions = query.all()

    # Pré-charger les données liées pour éviter les N+1
    account_map = {a.id: a.name for a in db.query(BankAccount).all()}
    category_map = {c.id: c.name for c in db.query(Category).all()}

    budget_map: dict[str, list[str]] = {}
    entries = db.query(BudgetEntry).all()
    budget_names = {b.id: b.name for b in db.query(Budget).all()}
    for entry in entries:
        budget_map.setdefault(entry.transaction_id, []).append(budget_names.get(entry.budget_id, ""))

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    writer.writerow(["Date", "Libellé", "Montant (€)", "Catégorie", "Compte", "Budgets", "Notes"])
    for tx in transactions:
        writer.writerow([
            tx.date.strftime("%d/%m/%Y"),
            tx.label or tx.raw_label or "",
            str(float(tx.amount)).replace(".", ","),
            category_map.get(tx.category_id, "") if tx.category_id else "",
            account_map.get(tx.account_id, ""),
            " | ".join(budget_map.get(tx.id, [])),
            tx.notes or "",
        ])

    csv_content = "﻿" + output.getvalue()  # BOM UTF-8 pour Excel

    filename_parts = ["transactions"]
    if date_from:
        filename_parts.append(date_from.strftime("%Y%m%d"))
    if date_to:
        filename_parts.append(date_to.strftime("%Y%m%d"))
    filename = "_".join(filename_parts) + ".csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
