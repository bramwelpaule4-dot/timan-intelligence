"""Platform administration services for TimanStat."""

from timan_intelligence.administration.audit import (
    record_audit_event,
    list_audit_events,
)

from timan_intelligence.administration.permissions import (
    get_role_permissions,
    has_permission,
    require_permission,
)

from timan_intelligence.administration.user_service import (
    list_users,
    get_user_details,
    change_user_role,
    set_user_active_status,
)

__all__ = [
    "record_audit_event",
    "list_audit_events",
    "get_role_permissions",
    "has_permission",
    "require_permission",
    "list_users",
    "get_user_details",
    "change_user_role",
    "set_user_active_status",
]
