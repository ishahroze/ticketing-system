from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, CommentViewSet, TicketViewSet

router = DefaultRouter()
router.register(r"tickets", TicketViewSet, basename="ticket")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"comments", CommentViewSet, basename="comment")

urlpatterns = router.urls
