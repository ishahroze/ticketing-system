from rest_framework import permissions


class IsOwnerAgentOrAdmin(permissions.BasePermission):
    """
    - Customers can view/edit only tickets they created.
    - Agents/Admins can view and manage all tickets.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or user.is_agent_or_admin():
            return True
        if request.method in permissions.SAFE_METHODS:
            return obj.created_by_id == user.id
        return obj.created_by_id == user.id


class IsAgentOrAdmin(permissions.BasePermission):
    """Restrict an action (e.g. triggering AI analysis, assigning) to staff roles."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_agent_or_admin()))
