from rest_framework import serializers

from accounts.serializers import UserSerializer
from .models import Category, Comment, Ticket


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "description")


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "ticket", "author", "content", "is_ai_generated", "created_at")
        read_only_fields = ("id", "author", "is_ai_generated", "created_at")


class TicketListSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = (
            "id", "title", "status", "priority", "category",
            "created_by", "assigned_to", "ai_sentiment",
            "created_at", "updated_at",
        )


class TicketDetailSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    ai_suggested_category = CategorySerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.all(), write_only=True, required=False, allow_null=True
    )
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        source="assigned_to", queryset=UserSerializer.Meta.model.objects.all(),
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Ticket
        fields = (
            "id", "title", "description", "status", "priority", "category", "category_id",
            "created_by", "assigned_to", "assigned_to_id",
            "ai_suggested_category", "ai_suggested_priority", "ai_sentiment",
            "ai_summary", "ai_suggested_response", "ai_confidence", "ai_analyzed_at",
            "comments", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "created_by", "ai_suggested_category", "ai_suggested_priority",
            "ai_sentiment", "ai_summary", "ai_suggested_response", "ai_confidence",
            "ai_analyzed_at", "created_at", "updated_at",
        )


class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id", "title", "description", "priority", "category")
        read_only_fields = ("id",)
