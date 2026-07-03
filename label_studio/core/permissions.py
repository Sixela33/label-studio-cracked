"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license."""

import logging  # noqa: I001
from typing import Optional

from pydantic import BaseModel, ConfigDict

import rules

logger = logging.getLogger(__name__)


class AllPermissions(BaseModel):
    model_config = ConfigDict(protected_namespaces=('__.*__', '_.*'))

    organizations_create: str = 'organizations.create'
    organizations_view: str = 'organizations.view'
    organizations_change: str = 'organizations.change'
    organizations_delete: str = 'organizations.delete'
    organizations_invite: str = 'organizations.invite'
    projects_create: str = 'projects.create'
    projects_view: str = 'projects.view'
    projects_change: str = 'projects.change'
    projects_delete: str = 'projects.delete'
    projects_reset_cache: str = 'projects.reset_cache'
    tasks_create: str = 'tasks.create'
    tasks_view: str = 'tasks.view'
    tasks_change: str = 'tasks.change'
    tasks_delete: str = 'tasks.delete'
    views_reset: str = 'views.reset'
    annotations_create: str = 'annotations.create'
    annotations_view: str = 'annotations.view'
    annotations_change: str = 'annotations.change'
    annotations_delete: str = 'annotations.delete'
    actions_perform: str = 'actions.perform'
    predictions_any: str = 'predictions.any'
    avatar_any: str = 'avatar.any'
    labels_create: str = 'labels.create'
    labels_view: str = 'labels.view'
    labels_change: str = 'labels.change'
    labels_delete: str = 'labels.delete'
    models_create: str = 'models.create'
    models_view: str = 'models.view'
    models_change: str = 'models.change'
    models_delete: str = 'models.delete'
    model_provider_connection_create: str = 'model_provider_connection.create'
    model_provider_connection_view: str = 'model_provider_connection.view'
    model_provider_connection_change: str = 'model_provider_connection.change'
    model_provider_connection_delete: str = 'model_provider_connection.delete'
    webhooks_view: str = 'webhooks.view'
    webhooks_change: str = 'webhooks.change'
    users_token_any: str = 'users.token.any'

    storages_view: str = 'storages.view'
    storages_change: str = 'storages.change'
    storages_sync: str = 'storages.sync'

    views_view: str = 'views.view'
    views_create: str = 'views.create'
    views_change: str = 'views.change'
    views_delete: str = 'views.delete'


all_permissions = AllPermissions()


class ViewClassPermission(BaseModel):
    GET: Optional[str] = None
    PATCH: Optional[str] = None
    PUT: Optional[str] = None
    DELETE: Optional[str] = None
    POST: Optional[str] = None


ROLE_OWNER = 'owner'
ROLE_ADMIN = 'admin'
ROLE_MANAGER = 'manager'
ROLE_ANNOTATOR = 'annotator'

ORG_ADMIN_PERMISSIONS = {
    all_permissions.organizations_create,
    all_permissions.organizations_change,
    all_permissions.organizations_delete,
    all_permissions.organizations_invite,
    all_permissions.webhooks_change,
    all_permissions.users_token_any,
}

MANAGER_PERMISSIONS = (set(all_permissions.model_dump().values()) - ORG_ADMIN_PERMISSIONS) - {
    all_permissions.projects_create,
}

ANNOTATOR_PERMISSIONS = {
    all_permissions.projects_view,
    all_permissions.tasks_view,
    all_permissions.annotations_view,
    all_permissions.annotations_create,
    all_permissions.annotations_change,
    all_permissions.views_view,
    all_permissions.views_create,
    all_permissions.views_change,
    all_permissions.labels_view,
    all_permissions.avatar_any,
}


def _organization_from_obj(obj):
    if obj is None:
        return None
    if obj.__class__.__name__ == 'Organization':
        return obj
    if obj.__class__.__name__ == 'OrganizationMember':
        return obj.organization
    if hasattr(obj, 'organization'):
        return obj.organization
    if hasattr(obj, 'project') and hasattr(obj.project, 'organization'):
        return obj.project.organization
    if hasattr(obj, 'task') and hasattr(obj.task, 'project'):
        return obj.task.project.organization
    return None


def get_membership(user, organization=None):
    if not getattr(user, 'is_authenticated', False):
        return None

    organization = organization or getattr(user, 'active_organization', None)
    if organization is None:
        return None

    # Per-instance cache avoids N+1 queries when many permissions are
    # checked for the same user in one request (e.g. whoami's permissions list).
    cache = user.__dict__.setdefault('_org_membership_cache', {})
    if organization.pk in cache:
        return cache[organization.pk]

    from organizations.models import OrganizationMember

    membership = (
        OrganizationMember.objects.filter(user=user, organization=organization, deleted_at__isnull=True)
        .select_related('organization')
        .first()
    )
    cache[organization.pk] = membership
    return membership


def get_effective_role(user, organization=None):
    membership = get_membership(user, organization)
    if not membership:
        return None
    return membership.effective_role


def is_platform_owner(user):
    if not getattr(user, 'is_authenticated', False):
        return False

    cache_key = '_is_platform_owner_cache'
    if cache_key not in user.__dict__:
        from users.models import PlatformOwner

        user.__dict__[cache_key] = PlatformOwner.objects.filter(user=user).exists()
    return user.__dict__[cache_key]


def is_org_admin(user, organization=None):
    return is_platform_owner(user) or get_effective_role(user, organization) in {ROLE_OWNER, ROLE_ADMIN}


def is_project_member(user, project):
    if not project or not getattr(user, 'is_authenticated', False):
        return False
    if project.created_by_id == user.id:
        return True
    return project.members.filter(user=user, enabled=True).exists()


def has_project_access(user, project):
    if not project or not getattr(user, 'is_authenticated', False):
        return False

    organization = project.organization
    role = get_effective_role(user, organization)
    if role in {ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER}:
        return True
    if role == ROLE_ANNOTATOR:
        return is_project_member(user, project)
    return False


def _project_from_obj(obj):
    if obj is None:
        return None
    if obj.__class__.__name__ == 'Project':
        return obj
    if hasattr(obj, 'project'):
        return obj.project
    if hasattr(obj, 'task') and hasattr(obj.task, 'project'):
        return obj.task.project
    return None


def _has_object_scope(user, permission_name, obj):
    project = _project_from_obj(obj)
    if project is not None and not has_project_access(user, project):
        return False

    if permission_name in {all_permissions.annotations_change, all_permissions.annotations_delete}:
        if obj is not None and obj.__class__.__name__ == 'Annotation':
            role = get_effective_role(user, obj.project.organization)
            if role == ROLE_ANNOTATOR:
                return obj.completed_by_id == user.id

    organization = _organization_from_obj(obj)
    if organization is not None:
        return get_membership(user, organization) is not None

    return True


def role_has_permission(permission_name, user, obj=None):
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True

    organization = _organization_from_obj(obj) or getattr(user, 'active_organization', None)
    role = get_effective_role(user, organization)

    if organization is None and permission_name == all_permissions.organizations_create:
        # Authenticated users can create their first organization before they belong to one.
        return True

    if is_platform_owner(user):
        return _has_object_scope(user, permission_name, obj)

    if role in {ROLE_OWNER, ROLE_ADMIN}:
        return _has_object_scope(user, permission_name, obj)
    if role == ROLE_MANAGER:
        return permission_name in MANAGER_PERMISSIONS and _has_object_scope(user, permission_name, obj)
    if role == ROLE_ANNOTATOR:
        return permission_name in ANNOTATOR_PERMISSIONS and _has_object_scope(user, permission_name, obj)
    return False


def make_perm(name, pred, overwrite=False):
    if rules.perm_exists(name):
        if overwrite:
            rules.remove_perm(name)
        else:
            return
    rules.add_perm(name, pred)


def make_role_predicate(permission_name):
    def predicate(user, obj=None):
        return role_has_permission(permission_name, user, obj)

    return predicate


for _, permission_name in all_permissions:
    make_perm(permission_name, make_role_predicate(permission_name), overwrite=True)
