
from timan_intelligence.registry.feature_registry import (
    IMPLEMENTATION_STATUSES,
    VERIFICATION_STATUSES,
    get_all_features,
    get_feature,
    get_features_by_implementation_status,
    get_features_by_verification_status,
    get_registry_summary,
    validate_registry,
)


def test_registry_contains_features():
    features = get_all_features()

    assert len(features) > 0


def test_feature_ids_are_unique():
    features = get_all_features()
    feature_ids = [feature.feature_id for feature in features]

    assert len(feature_ids) == len(set(feature_ids))


def test_all_features_have_valid_implementation_status():
    features = get_all_features()

    for feature in features:
        assert feature.implementation_status in IMPLEMENTATION_STATUSES


def test_all_features_have_valid_verification_status():
    features = get_all_features()

    for feature in features:
        assert feature.verification_status in VERIFICATION_STATUSES


def test_every_feature_has_required_information():
    features = get_all_features()

    for feature in features:
        assert feature.feature_id.strip()
        assert feature.name.strip()
        assert feature.module.strip()
        assert feature.description.strip()


def test_get_feature_returns_existing_feature():
    features = get_all_features()
    expected = features[0]

    result = get_feature(expected.feature_id)

    assert result == expected


def test_get_feature_returns_none_for_unknown_id():
    result = get_feature("NON-EXISTENT-FEATURE")

    assert result is None


def test_implementation_status_filter():
    features = get_all_features()

    for status in IMPLEMENTATION_STATUSES:
        result = get_features_by_implementation_status(status)

        assert all(
            feature.implementation_status == status
            for feature in result
        )

    assert sum(
        len(get_features_by_implementation_status(status))
        for status in IMPLEMENTATION_STATUSES
    ) == len(features)


def test_verification_status_filter():
    features = get_all_features()

    for status in VERIFICATION_STATUSES:
        result = get_features_by_verification_status(status)

        assert all(
            feature.verification_status == status
            for feature in result
        )

    assert sum(
        len(get_features_by_verification_status(status))
        for status in VERIFICATION_STATUSES
    ) == len(features)


def test_registry_summary_is_generated():
    summary = get_registry_summary()

    assert isinstance(summary, dict)
    assert summary


def test_registry_validation_returns_a_list():
    errors = validate_registry()

    assert isinstance(errors, list)


def test_registry_has_no_validation_errors():
    errors = validate_registry()

    assert errors == []
