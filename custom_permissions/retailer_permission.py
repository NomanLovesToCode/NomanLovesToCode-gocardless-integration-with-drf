from rest_framework import permissions

class IsOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        # Allow GET, HEAD, or OPTIONS requests (read-only access) for any authenticated user.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user.retailer:
            raise permissions.PermissionDenied("Only retailers can perform this action.")
        
        

        return obj.user == request.user