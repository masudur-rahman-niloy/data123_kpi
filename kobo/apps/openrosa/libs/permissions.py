from django.contrib.auth.models import Permission
from django_request_cache import cache_for_request

from kobo.apps.openrosa.libs.utils.guardian import get_users_with_perms
from .constants import OPENROSA_DB_ALIAS


def get_object_users_with_permissions(obj, exclude=None, serializable=False):
    """Returns users, roles and permissions for a object.
    When called with with `serializable=True`, return usernames (strings)
    instead of User objects, which cannot be serialized by REST Framework.
    """
    result = []

    if obj:
        users_with_perms = get_users_with_perms(
            obj, attach_perms=True, with_group_users=False).items()

        result = [{
            'user': user if not serializable else user.username,
            'permissions': permissions} for user, permissions in
            users_with_perms
        ]

    return result


@cache_for_request
def get_model_permission_codenames():
    return Permission.objects.using(OPENROSA_DB_ALIAS).values_list(
        'codename', flat=True
    )