"""Authenticated contact-method management for TimanStat."""

from __future__ import annotations

import logging

import streamlit as st

from timan_intelligence.security.auth import is_authenticated, logout
from timan_intelligence.security.one_time_password_service import (
    OTPChallengeServiceError,
    create_otp_challenge,
    get_contact_method_status,
    invalidate_otp_challenge,
    set_recovery_email_for_verification,
    verify_otp_challenge,
)
from timan_intelligence.security.otp_delivery import (
    OTPDeliveryError,
    send_email_otp,
)

logger = logging.getLogger(__name__)

_PENDING_RECOVERY_CHALLENGE = "contact_methods_recovery_email_challenge"


def _mask_email(value: object) -> str:
    """Mask a contact address before displaying it in the account UI."""
    if not isinstance(value, str) or "@" not in value:
        return "Not configured"
    local, domain = value.rsplit("@", 1)
    if not local or not domain:
        return "Not configured"
    visible = local[:1]
    return f"{visible}{'*' * min(max(len(local) - 1, 2), 6)}@{domain}"


def render_contact_methods() -> None:
    """Render recovery-email verification and the current SMS readiness."""
    st.subheader("Recovery contact methods")

    if not is_authenticated():
        st.warning("Sign in to manage recovery contact methods.")
        return

    user_id = st.session_state.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        logout()
        st.error("Your account session is invalid. Please sign in again.")
        return

    try:
        status = get_contact_method_status(user_id)
    except Exception as exc:
        logger.error(
            "TimanStat contact-method status lookup failed. error_type=%s",
            type(exc).__name__,
        )
        st.error("Recovery contact settings are temporarily unavailable.")
        return

    recovery_email = status.get("recovery_email")
    verified = bool(status.get("recovery_email_verified"))
    if isinstance(recovery_email, str) and recovery_email:
        label = "Verified" if verified else "Verification required"
        st.write(f"**Recovery email:** {_mask_email(recovery_email)}")
        st.caption(f"Status: {label}")
    else:
        st.write("**Recovery email:** Not configured")

    with st.form("timanstat_recovery_email_change_form"):
        new_email = st.text_input(
            "Recovery email address",
            placeholder="name@example.com",
            max_chars=254,
        )
        current_password = st.text_input(
            "Current password to confirm this change",
            type="password",
            max_chars=1024,
        )
        change_submitted = st.form_submit_button(
            "Save recovery email",
            use_container_width=True,
        )

    if change_submitted:
        if not new_email.strip() or not current_password:
            st.error("Enter the recovery email and your current password.")
        else:
            try:
                set_recovery_email_for_verification(
                    user_id, new_email, current_password
                )
            except OTPChallengeServiceError as exc:
                st.error(str(exc))
            except Exception as exc:
                logger.error(
                    "TimanStat recovery-email update failed. error_type=%s",
                    type(exc).__name__,
                )
                st.error("The recovery email could not be updated.")
            else:
                st.session_state.pop(_PENDING_RECOVERY_CHALLENGE, None)
                st.success(
                    "Recovery email saved as pending verification. "
                    "Send a verification code to complete setup."
                )
                st.rerun()

    # Refresh the status after a possible form submission/rerun.
    try:
        status = get_contact_method_status(user_id)
    except Exception:
        st.error("Recovery contact settings are temporarily unavailable.")
        return

    recovery_email = status.get("recovery_email")
    verified = bool(status.get("recovery_email_verified"))

    if isinstance(recovery_email, str) and recovery_email and not verified:
        if st.button(
            "Send recovery-email verification code",
            key="timanstat_send_recovery_email_otp",
            use_container_width=True,
        ):
            challenge = None
            try:
                challenge = create_otp_challenge(
                    user_id, "verify_recovery_email", "email"
                )
                send_email_otp(
                    recovery_email,
                    challenge["code"],
                    "verify_recovery_email",
                )
            except (OTPChallengeServiceError, OTPDeliveryError) as exc:
                if challenge is not None:
                    try:
                        invalidate_otp_challenge(
                            challenge["challenge_id"],
                            user_id,
                            "verify_recovery_email",
                        )
                    except Exception:
                        logger.error(
                            "TimanStat failed to invalidate undelivered OTP. "
                            "error_type=%s",
                            type(exc).__name__,
                        )
                st.error(str(exc))
            except Exception as exc:
                if challenge is not None:
                    try:
                        invalidate_otp_challenge(
                            challenge["challenge_id"],
                            user_id,
                            "verify_recovery_email",
                        )
                    except Exception:
                        pass
                logger.error(
                    "TimanStat recovery-email OTP delivery failed. error_type=%s",
                    type(exc).__name__,
                )
                st.error(
                    "The verification code could not be sent. "
                    "Please try again later."
                )
            else:
                st.session_state[_PENDING_RECOVERY_CHALLENGE] = (
                    challenge["challenge_id"]
                )
                st.success(
                    "A verification code has been sent to "
                    f"{_mask_email(recovery_email)}. It expires in five minutes."
                )

    challenge_id = st.session_state.get(_PENDING_RECOVERY_CHALLENGE)
    if isinstance(challenge_id, str) and challenge_id:
        with st.form("timanstat_recovery_email_otp_form"):
            code = st.text_input(
                "Six-digit email verification code",
                max_chars=6,
                placeholder="000000",
            )
            verify_submitted = st.form_submit_button(
                "Verify recovery email",
                use_container_width=True,
            )

        if verify_submitted:
            if not code.strip():
                st.error("Enter the six-digit verification code.")
            else:
                try:
                    success = verify_otp_challenge(
                        challenge_id,
                        user_id,
                        "verify_recovery_email",
                        code.strip(),
                    )
                except OTPChallengeServiceError as exc:
                    st.error(str(exc))
                    success = False
                except Exception as exc:
                    logger.error(
                        "TimanStat recovery-email verification failed. "
                        "error_type=%s",
                        type(exc).__name__,
                    )
                    st.error("The recovery email could not be verified.")
                    success = False

                if success:
                    st.session_state.pop(_PENDING_RECOVERY_CHALLENGE, None)
                    st.success("Your recovery email has been verified.")
                    st.rerun()
                else:
                    st.error(
                        "The code is invalid, expired, already used, "
                        "or no longer matches the current recovery email."
                    )

    phone = status.get("phone_number_e164")
    if isinstance(phone, str) and phone:
        st.write(f"**Phone number:** {phone[:3]}{'*' * 6}{phone[-2:]}")
        st.caption(
            "SMS verification is not available yet because no SMS gateway "
            "has been connected. This number cannot currently be used for "
            "account recovery or sign-in verification."
        )
    else:
        st.write("**Phone number:** Not configured")
        st.caption(
            "SMS verification will become available after an SMS gateway "
            "has been connected."
        )
