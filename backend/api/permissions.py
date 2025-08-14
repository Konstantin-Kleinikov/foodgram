from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS


class IsAdminAuthorOrReadOnly(permissions.BasePermission):
    """Права доступа для автора или анонимного пользователя."""

    class IsAuthorOrReadOnly(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            return (
                request.method in SAFE_METHODS
                or obj.author == request.user
            )
