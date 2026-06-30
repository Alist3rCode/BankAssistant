"""Service d'application des règles de catégorisation sur les transactions."""

import re
import logging
from sqlalchemy.orm import Session
from models.models import CategoryRule, Transaction

logger = logging.getLogger(__name__)


def _matches(label: str, pattern: str, match_type: str) -> bool:
    label_lower = label.lower()
    pattern_lower = pattern.lower()
    try:
        if match_type == "contains":
            return pattern_lower in label_lower
        if match_type == "starts_with":
            return label_lower.startswith(pattern_lower)
        if match_type == "ends_with":
            return label_lower.endswith(pattern_lower)
        if match_type == "regex":
            return bool(re.search(pattern, label, re.IGNORECASE))
    except re.error:
        logger.warning("Regex invalide ignorée : %s", pattern)
    return False


def apply_rules(db: Session, only_uncategorized: bool = True) -> int:
    """Applique toutes les règles actives par ordre de priorité décroissante.

    Retourne le nombre de transactions mises à jour.
    """
    rules = (
        db.query(CategoryRule)
        .filter(CategoryRule.is_active == True)
        .order_by(CategoryRule.priority.desc())
        .all()
    )
    if not rules:
        return 0

    query = db.query(Transaction)
    if only_uncategorized:
        query = query.filter(Transaction.is_categorized == False)

    transactions = query.all()
    updated = 0

    for tx in transactions:
        label = tx.label or tx.raw_label or ""
        for rule in rules:
            if _matches(label, rule.pattern, rule.match_type):
                tx.category_id = rule.category_id
                tx.is_categorized = True
                updated += 1
                break  # Première règle qui correspond gagne (par priorité)

    if updated:
        db.commit()
    logger.info("Catégorisation automatique : %d transaction(s) mises à jour", updated)
    return updated
