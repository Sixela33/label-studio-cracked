from rest_framework.permissions import SAFE_METHODS, BasePermission


def get_required_permission(request, view):
    permission_required = getattr(view, 'permission_required', None)
    if permission_required is None:
        return None
    if isinstance(permission_required, str):
        return permission_required
    return getattr(permission_required, request.method.upper(), None)


class HasObjectPermission(BasePermission):
    def has_permission(self, request, view):
        permission = get_required_permission(request, view)
        if permission is None:
            return True
        return request.user.has_perm(permission)

    def has_object_permission(self, request, view, obj):
        permission = get_required_permission(request, view)
        if permission is not None and not request.user.has_perm(permission, obj):
            return False
        return obj.has_permission(request.user)


class MemberHasOwnerPermission(BasePermission):
    def has_permission(self, request, view):
        permission = get_required_permission(request, view)
        if permission is None:
            return True
        return request.user.has_perm(permission)

    def has_object_permission(self, request, view, obj):
        permission = get_required_permission(request, view)
        if permission is not None and not request.user.has_perm(permission, obj):
            return False
        if request.method not in SAFE_METHODS:
            from core.permissions import is_org_admin

            organization = getattr(obj, 'organization', None) or obj
            if not is_org_admin(request.user, organization):
                return False

        return obj.has_permission(request.user)
