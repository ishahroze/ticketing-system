from django.contrib import admin

from .models import Category, Comment, Ticket


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "status", "priority", "category",
        "created_by", "assigned_to", "ai_sentiment", "created_at",
    )
    list_filter = ("status", "priority", "category", "ai_sentiment")
    search_fields = ("title", "description")
    readonly_fields = (
        "ai_suggested_category", "ai_suggested_priority", "ai_sentiment",
        "ai_summary", "ai_suggested_response", "ai_confidence", "ai_analyzed_at",
        "created_at", "updated_at",
    )
    inlines = [CommentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "is_ai_generated", "created_at")
    list_filter = ("is_ai_generated",)
