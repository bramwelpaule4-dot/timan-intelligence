"""Tests for international phone-number validation."""

import pytest

from timan_intelligence.identity.phone_numbers import (
    PhoneNumberError,
    format_phone_number_international,
    normalise_phone_number,
)


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        ("+254 712 345 678", "+254712345678"),
        ("+211 912 345 678", "+211912345678"),
        ("+256 772 123456", "+256772123456"),
        ("+44 20 7946 0018", "+442079460018"),
    ],
)
def test_normalises_international_numbers(number, expected):
    assert normalise_phone_number(number) == expected


def test_normalises_national_number_with_explicit_region():
    assert normalise_phone_number("0712 345 678", "KE") == "+254712345678"


def test_rejects_national_number_without_country_context():
    with pytest.raises(PhoneNumberError, match="Select the phone number's country"):
        normalise_phone_number("0712 345 678")


def test_rejects_invalid_number():
    with pytest.raises(PhoneNumberError):
        normalise_phone_number("+254 000 000 000")


def test_rejects_extension():
    with pytest.raises(PhoneNumberError, match="extensions are not supported"):
        normalise_phone_number("+1 202 555 0123 ext. 45")


def test_formats_canonical_number_for_display():
    assert format_phone_number_international("+254712345678") == "+254 712 345 678"
