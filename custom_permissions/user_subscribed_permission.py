from rest_framework import permissions

class IsSubscribed(permissions.BasePermission):
    """
    Allows access only to authenticated users who are subscribed.
    Works for both view-level and object-level checks.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'subscribed', True)
