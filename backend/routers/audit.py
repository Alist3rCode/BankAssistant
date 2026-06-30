from fastapi import APIRouter, Query
from sqlalchemy import desc
from dependencies import CurrentUser, DB
from models.models import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("/")
async def list_audit_logs(
    current_user: CurrentUser,
    db: DB,
    limit: int = Query(100, le=500),
):
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "action": log.action,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
