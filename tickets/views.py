from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Comment, Ticket
from .permissions import IsAgentOrAdmin, IsOwnerAgentOrAdmin
from .serializers import (
    CategorySerializer,
    CommentSerializer,
    TicketCreateSerializer,
    TicketDetailSerializer,
    TicketListSerializer,
)

User = get_user_model()


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAgentOrAdmin()]
        return [permissions.IsAuthenticated()]


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwnerAgentOrAdmin]
    filterset_fields = ["status", "priority", "category", "assigned_to"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "priority", "status"]
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related(
            "category", "created_by", "assigned_to", "ai_suggested_category"
        ).prefetch_related("comments")
        if user.is_staff or user.is_agent_or_admin():
            return qs
        return qs.filter(created_by=user)

    def get_serializer_class(self):
        if self.action == "create":
            return TicketCreateSerializer
        if self.action == "list":
            return TicketListSerializer
        return TicketDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsOwnerAgentOrAdmin])
    def analyze(self, request, pk=None):
        """
        Runs the LangGraph AI triage pipeline on this ticket: classifies category
        and priority, detects sentiment, generates a summary, and drafts a
        suggested first response. Results are saved onto the ticket.
        """
        from ai_engine.services import analyze_ticket_and_save

        ticket = self.get_object()
        try:
            analyze_ticket_and_save(ticket)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"detail": f"AI analysis failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        ticket.refresh_from_db()
        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAgentOrAdmin])
    def apply_ai_suggestions(self, request, pk=None):
        """Accept the AI's suggested category/priority and apply them to the ticket."""
        ticket = self.get_object()
        if ticket.ai_suggested_category_id:
            ticket.category_id = ticket.ai_suggested_category_id
        if ticket.ai_suggested_priority:
            ticket.priority = ticket.ai_suggested_priority
        ticket.save(update_fields=["category", "priority"])
        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAgentOrAdmin])
    def assign(self, request, pk=None):
        """Assign the ticket to an agent. Body: {"user_id": <id>}"""
        ticket = self.get_object()
        user_id = request.data.get("user_id")
        if user_id is None:
            ticket.assigned_to = None
        else:
            try:
                ticket.assigned_to = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        ticket.save(update_fields=["assigned_to"])
        return Response(TicketDetailSerializer(ticket).data)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Comment.objects.select_related("author", "ticket")
        if user.is_staff or user.is_agent_or_admin():
            return qs
        return qs.filter(ticket__created_by=user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
