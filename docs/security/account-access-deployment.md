# TimanStat account-access deployment checklist

This checklist is for the deployed Streamlit application. It covers the
configuration required for a new user to register, verify an email address,
sign in, retain a session, and recover access.

## 1. Required production secrets

In the Streamlit deployment, open **Manage app → Settings → Secrets** and
configure the following values. Do not commit real credentials to GitHub or
send them in support messages.

```toml
TIMAN_APP_BASE_URL = "https://YOUR-PUBLIC-TIMANSTAT-APP-URL"
TIMAN_ENVIRONMENT = "production"

# Real email delivery is mandatory for public registration.
TIMAN_EMAIL_PROVIDER = "smtp"
TIMAN_EMAIL_SENDER = "YOUR-VERIFIED-SENDER-ADDRESS"
TIMAN_EMAIL_SENDER_NAME = "TimanStat"
TIMAN_EMAIL_SMTP_HOST = "smtp.gmail.com"
TIMAN_EMAIL_SMTP_PORT = "587"
TIMAN_EMAIL_SMTP_USERNAME = "YOUR-SMTP-USERNAME"
TIMAN_EMAIL_SMTP_PASSWORD = "YOUR-SMTP-APP-PASSWORD"
TIMAN_EMAIL_USE_STARTTLS = "true"
TIMAN_EMAIL_TIMEOUT = "20"

# Generate a unique secret locally; use the same value on every app worker.
TIMANSTAT_RATE_LIMIT_HMAC_KEY = "REPLACE-WITH-A-SECRET-OF-AT-LEAST-32-BYTES"

# Use a persistent PostgreSQL database for production account records.
[database]
url = "postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
```

The values above are placeholders. Replace them with the actual application
URL, verified sender, SMTP credentials, and PostgreSQL connection string.
For another SMTP provider, use that provider's host, port, authentication,
and TLS requirements.

Generate the rate-limit key locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use the same HMAC key on every worker. Do not rotate it casually: a new key
creates a new rate-limit identifier namespace.

For Gmail, use an app password where the Google account supports it. Do not
use the normal account password. The sender address must be authorised by the
SMTP provider.

## 2. Database requirements

The application runs versioned database migrations during startup. The
configured database must be reachable and the application database user must
have permission to create and update the required tables.

Use a persistent PostgreSQL service for production. SQLite is suitable for
local development and tests, but a local application file is not a reliable
shared account store across separate containers or replicas.

The database connection is read from the `[database]` Streamlit Secrets
section (`url`) or the `DATABASE_URL` environment variable.

## 3. Email-verification behaviour

- New accounts are created with `email_verified = false`.
- A new account cannot sign in until its email is verified.
- Verification links contain a random, single-use token.
- Only a SHA-256 hash of the token is stored in the database.
- Verification tokens expire after 30 minutes by default.
- Resending a link invalidates the previous outstanding token.
- Public registration and resend flows reject the in-memory mock email
  provider. A mock message is not a delivered email.
- The mock sender is available only through the explicitly authorised
  development simulator on an approved development hostname.

A successful SMTP submission means the provider accepted the message; it
does not guarantee inbox placement. Check spam/junk folders and provider
delivery logs when a test message is not visible.

## 4. Sign-in and session behaviour

- Users can sign in using their username or registered email address.
- Passwords must be at least 12 characters and are stored as scrypt hashes.
- Unverified or inactive accounts cannot sign in.
- Accounts without two-factor authentication receive a session after valid
  password authentication.
- Accounts with authenticator-based two-factor authentication must complete
  the second factor using an authenticator code or an unused recovery code.
- Sessions expire after 30 minutes of inactivity or 12 hours absolutely.
- Password changes and other security-sensitive changes can revoke existing
  sessions.

The shared login and email-request rate limiters require the HMAC secret
listed above. If the key is missing or too short, authentication fails closed.

## 5. Production acceptance test

After saving the deployment secrets, restart or reboot the Streamlit app and
complete this test using an email inbox you control:

1. Open the public application URL in a private/incognito browser window.
2. Create a new account with a unique username, accessible email address,
   full name, and password.
3. Confirm the application reports that the verification email was submitted.
4. Confirm the email arrives and its link points to the production app URL.
5. Open the link once. The application must confirm that the email is verified.
6. Attempt to reuse the same link. It must be rejected as already used.
7. Sign in using the new account's email address and password.
8. Confirm the application opens the authenticated TimanStat workspace.
9. Sign out, then sign in using the username and password.
10. If two-factor authentication is enabled, complete the authenticator or
    recovery-code challenge and confirm workspace access.
11. Use the password-recovery flow with the same inbox and verify that the
    reset link allows a password change and that the new password works.
12. Restart the app and sign in again. The account must still exist.

Do not treat GitHub Actions passing as proof that the production SMTP account,
database, or Streamlit Secrets are configured. Automated tests verify the
application logic; the production acceptance test verifies the live services.

## 6. If a user cannot access an account

- **No verification email:** check the SMTP secrets, sender authorisation,
  provider logs, and spam/junk folder; then use **Resend verification email**.
- **Verification link expired or already used:** request a fresh link.
- **Password forgotten:** use **Forgot password?** and complete the reset link.
- **Sign-in temporarily unavailable:** check database connectivity and
  `TIMANSTAT_RATE_LIMIT_HMAC_KEY` before treating the issue as a bad password.
- **Authenticator unavailable:** use an unused recovery code. If all recovery
  codes are exhausted, an authorised administrator must follow the account
  recovery procedure; do not bypass MFA in application code.

Never manually set `email_verified = true` as a normal user-support shortcut.
