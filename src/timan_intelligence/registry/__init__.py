"""Feature registry package for TimanStat."""

from .feature_registry import (
    IMPLEMENTATION_STATUSES,
    VERIFICATION_STATUSES,
    Feature,
    get_all_features,
    get_feature,
    get_features_by_implementation_status,
    get_features_by_verification_status,
    get_registry_summary,
    validate_registry,
)

__all__ = [
    "IMPLEMENTATION_STATUSES",
    "VERIFICATION_STATUSES",
    "Feature",
    "get_all_features",
    "get_feature",
    "get_features_by_implementation_status",
    "get_features_by_verification_status",
    "get_registry_summary",
    "validate_registry",
]

from .method_catalogue import (
    CATALOGUE_VERSION,
    IMPLEMENTED_METHODS,
    create_statistical_method_repository,
    get_statistical_method,
    get_statistical_method_summary,
    get_statistical_methods,
    validate_statistical_method_catalogue,
)

__all__ += [
    "CATALOGUE_VERSION",
    "IMPLEMENTED_METHODS",
    "create_statistical_method_repository",
    "get_statistical_method",
    "get_statistical_method_summary",
    "get_statistical_methods",
    "validate_statistical_method_catalogue",
]
