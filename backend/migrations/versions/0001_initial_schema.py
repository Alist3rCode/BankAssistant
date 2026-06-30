"""Schéma initial complet

Revision ID: 0001
Revises:
Create Date: 2026-06-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Catégories par défaut (seront insérées dans upgrade)
DEFAULT_CATEGORIES = [
    ("Alimentation & Courses", "🛒", "#4CAF50", False, True),
    ("Restaurants & Bars", "🍽️", "#FF9800", False, True),
    ("Transport", "🚗", "#2196F3", False, True),
    ("Logement", "🏠", "#9C27B0", False, True),
    ("Santé", "💊", "#F44336", False, True),
    ("Loisirs & Divertissement", "🎮", "#00BCD4", False, True),
    ("Vêtements & Mode", "👔", "#E91E63", False, True),
    ("Abonnements", "📱", "#607D8B", False, True),
    ("Banque & Assurance", "🏦", "#795548", False, True),
    ("Éducation", "📚", "#FF5722", False, True),
    ("Voyage", "✈️", "#03A9F4", False, True),
    ("Cadeaux & Dons", "🎁", "#8BC34A", False, True),
    ("Salaire", "💰", "#4CAF50", True, True),
    ("Remboursements", "↩️", "#8BC34A", True, True),
    ("Aides & Allocations", "🏛️", "#CDDC39", True, True),
    ("Autres revenus", "💸", "#FFEB3B", True, True),
    ("Non catégorisé", "❓", "#9E9E9E", False, True),
]

# Paramètres par défaut
DEFAULT_SETTINGS = [
    ("scraping.enabled", "true", False),
    ("scraping.schedule_hour", "6", False),
    ("scraping.schedule_minute", "0", False),
    ("notifications.enabled", "false", False),
    ("notifications.budget_alert", "true", False),
    ("notifications.large_transaction_threshold", "500", False),
    ("notifications.daily_report", "false", False),
    ("notifications.daily_report_hour", "8", False),
    ("ai.provider", "groq", False),
    ("ai.model", "llama-3.3-70b-versatile", False),
    ("ai.auto_categorize", "true", False),
    ("ai.language", "fr", False),
    ("ca.region", "", False),
    ("ca.region_url", "", False),
    ("ca.login", "", True),
    ("ca.password", "", True),
    ("ai.groq_api_key", "", True),
    ("ai.mistral_api_key", "", True),
]


def upgrade() -> None:
    # --- Table users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("totp_secret", sa.String(255), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- Table bank_accounts ---
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("number_masked", sa.String(50), nullable=False),
        sa.Column("iban_encrypted", sa.Text(), nullable=True),
        sa.Column("account_type", sa.String(50), nullable=False, server_default="checking"),
        sa.Column("balance", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("ca_region", sa.String(100), nullable=False),
        sa.Column("ca_region_url", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bank_accounts_external_id", "bank_accounts", ["external_id"], unique=True)

    # --- Table categories ---
    op.create_table(
        "categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("is_income", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- Table transactions ---
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("bank_accounts.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("raw_label", sa.String(500), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("is_categorized", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("external_id", "account_id", name="uq_transaction_external"),
    )
    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_index("ix_transactions_external_id", "transactions", ["external_id"])

    # --- Table budgets ---
    op.create_table(
        "budgets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("period_type", sa.String(20), nullable=False, server_default="monthly"),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- Table budget_entries ---
    op.create_table(
        "budget_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("budget_id", sa.String(36), sa.ForeignKey("budgets.id"), nullable=False),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- Table category_rules ---
    op.create_table(
        "category_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pattern", sa.String(255), nullable=False),
        sa.Column("match_type", sa.String(20), nullable=False, server_default="contains"),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- Table app_settings ---
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- Table audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # --- Table notification_logs ---
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- Données initiales : catégories ---
    import uuid
    from datetime import datetime
    categories_table = sa.table(
        "categories",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("icon", sa.String),
        sa.column("color", sa.String),
        sa.column("is_income", sa.Boolean),
        sa.column("is_system", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(
        categories_table,
        [
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "icon": icon,
                "color": color,
                "is_income": is_income,
                "is_system": is_system,
                "created_at": datetime.utcnow(),
            }
            for name, icon, color, is_income, is_system in DEFAULT_CATEGORIES
        ],
    )

    # --- Données initiales : settings ---
    settings_table = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.String),
        sa.column("is_encrypted", sa.Boolean),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        settings_table,
        [
            {
                "key": key,
                "value": value,
                "is_encrypted": is_encrypted,
                "updated_at": datetime.utcnow(),
            }
            for key, value, is_encrypted in DEFAULT_SETTINGS
        ],
    )

    # --- Budget par défaut : Vie courante ---
    budgets_table = sa.table(
        "budgets",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("currency", sa.String),
        sa.column("period_type", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("is_default", sa.Boolean),
        sa.column("color", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        budgets_table,
        [
            {
                "id": str(uuid.uuid4()),
                "name": "Vie courante",
                "description": "Budget principal — salaire et dépenses habituelles",
                "currency": "EUR",
                "period_type": "monthly",
                "is_active": True,
                "is_default": True,
                "color": "#4CAF50",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("notification_logs")
    op.drop_table("audit_logs")
    op.drop_table("app_settings")
    op.drop_table("category_rules")
    op.drop_table("budget_entries")
    op.drop_table("budgets")
    op.drop_table("transactions")
    op.drop_table("categories")
    op.drop_table("bank_accounts")
    op.drop_table("users")
