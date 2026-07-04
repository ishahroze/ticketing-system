import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def analyze_ticket_and_save(ticket) -> dict:
    """
    Runs the LangGraph triage pipeline for a given Ticket instance, saves the
    AI-generated fields onto the ticket, and returns the raw result dict.
    """
    from tickets.models import Category

    from .graph import get_compiled_graph

    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Set it in your .env file to enable AI analysis."
        )

    available_categories = list(Category.objects.values_list("name", flat=True))

    graph = get_compiled_graph()
    result = graph.invoke(
        {
            "title": ticket.title,
            "description": ticket.description,
            "available_categories": available_categories,
        }
    )

    category_name = result.get("category")
    category_obj = None
    if category_name:
        category_obj, _ = Category.objects.get_or_create(
            name__iexact=category_name,
            defaults={"name": category_name},
        )

    ticket.ai_suggested_category = category_obj
    ticket.ai_suggested_priority = result.get("priority")
    ticket.ai_sentiment = result.get("sentiment")
    ticket.ai_summary = result.get("summary", "")
    ticket.ai_suggested_response = result.get("suggested_response", "")
    ticket.ai_confidence = result.get("classification_confidence")
    ticket.ai_analyzed_at = timezone.now()
    ticket.save(
        update_fields=[
            "ai_suggested_category",
            "ai_suggested_priority",
            "ai_sentiment",
            "ai_summary",
            "ai_suggested_response",
            "ai_confidence",
            "ai_analyzed_at",
        ]
    )
    logger.info("AI analysis completed for ticket #%s", ticket.id)
    return result
