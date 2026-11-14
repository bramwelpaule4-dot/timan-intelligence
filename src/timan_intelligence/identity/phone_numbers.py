"""International phone-number validation for TimanStat.

Phone numbers are stored in canonical E.164 format. Validation confirms
that a number is valid under the numbering plan; it does not prove ownership.
Ownership must be confirmed separately with a one-time verification code.
"""

from __future__ import annotations

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat


class PhoneNumberError(ValueError):
    """Raised when a phone number cannot be accepted as an SMS destination."""


def normalise_phone_number(
    phone_number: str,
    default_region: str | None = None,
) -> str:
    """Validate a phone number and return its canonical E.164 representation.

    International input should include its leading '+' country calling code.
    National-format input must include an explicit ISO 3166-1 alpha-2
    default_region, such as 'KE' or 'GB'. No country is assumed automatically.

    Extensions are rejected because SMS destinations must be mobile numbers
    addressable without a telephone extension.
    """

    if not isinstance(phone_number, str) or not phone_number.strip():
        raise PhoneNumberError("Enter a phone number.")

    raw_number = phone_number.strip()
    region = default_region.strip().upper() if isinstance(default_region, str) else None

    if raw_number.startswith("+"):
        region = None
    elif not region or len(region) != 2 or not region.isalpha():
        raise PhoneNumberError(
            "Select the phone number's country or enter the full number "
            "with its international '+' country calling code."
        )

    try:
        parsed = phonenumbers.parse(raw_number, region)
    except NumberParseException as exc:
        raise PhoneNumberError(
            "The phone number could not be understood. Check the country "
            "code and number."
        ) from exc

    if parsed.extension:
        raise PhoneNumberError(
            "Phone extensions are not supported for SMS verification."
        )

    if not phonenumbers.is_possible_number(parsed):
        raise PhoneNumberError(
            "The phone number length is not valid for the selected country."
        )

    if not phonenumbers.is_valid_number(parsed):
        raise PhoneNumberError(
            "The phone number is not valid under the selected country's "
            "numbering plan."
        )

    number_type = phonenumbers.number_type(parsed)
    if number_type not in {
        phonenumbers.PhoneNumberType.MOBILE,
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
    }:
        raise PhoneNumberError(
            "Enter a mobile number that can be used as an SMS destination."
        )

    formatted = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    if not formatted.startswith("+"):
        raise PhoneNumberError("The phone number could not be normalised.")

    return formatted


def format_phone_number_international(phone_number: str) -> str:
    """Format an already-normalised E.164 number for human display."""

    canonical = normalise_phone_number(phone_number)
    parsed = phonenumbers.parse(canonical, None)
    return phonenumbers.format_number(
        parsed,
        PhoneNumberFormat.INTERNATIONAL,
    )
