from fastapi import APIRouter
from dependencies import CurrentUser, DB
from services.notification_service import send_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/test")
async def test_notification(current_user: CurrentUser, db: DB):
    """Envoie une notification de test pour vérifier la configuration ntfy."""
    sent = await send_notification(
        db=db,
        title="BankAssistant — Test",
        message="La configuration des notifications fonctionne correctement.",
        notification_type="TEST",
        priority="default",
        tags=["white_check_mark"],
    )
    if sent:
        return {"message": "Notification de test envoyée avec succès"}
    return {"message": "Échec de l'envoi — vérifiez l'URL et le topic ntfy dans les paramètres"}
