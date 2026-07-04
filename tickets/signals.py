import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Ticket

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Ticket)
def auto_analyze_new_ticket(sender, instance: Ticket, created: bool, **kwargs):
    """
    When AI_AUTO_ANALYZE_ON_CREATE=True, automatically run the LangGraph triage
    pipeline the moment a ticket is created. Disabled by default so that API
    costs are only incurred when explicitly requested via the /analyze/ endpoint,
    or you can flip this on and wire it to a Celery task for production use.
    """
    if not created or not getattr(settings, "AI_AUTO_ANALYZE_ON_CREATE", False):
        return

    from ai_engine.services import analyze_ticket_and_save

    try:
        analyze_ticket_and_save(instance)
    except Exception:  # pragma: no cover - defensive, don't break ticket creation
        logger.exception("Auto AI analysis failed for ticket #%s", instance.id)
