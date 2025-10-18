from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow administrators to edit objects,
    and allow read-only access to all other users.
    """

    def has_permission(self, request, view):
        # Allow read-only access for all users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allow full access for administrators
        return request.user and request.user.is_superuser