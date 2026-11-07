# TimanStat authentication rate limiting

TimanStat stores rate-limit state in the `rate_limit_states` database table.
Identifiers are normalised and protected with a keyed HMAC-SHA-256 digest
before storage. The raw usernames, email addresses, and account IDs are not
stored in this table. The HMAC key is configured separately from the database.

## Active limits

| Workflow | Limit | Lockout / cooldown |
|---|---:|---:|
| Password login | 5 failed attempts | 15 minutes |
| TOTP enrolment confirmation | 5 failed attempts | 15 minutes |
| TOTP verification | 5 failed attempts | 15 minutes |
| TOTP recovery-code verification | 5 failed attempts | 15 minutes |
| Email-verification resend | 1 request | 60 seconds |
| Password-reset request | 1 request | 60 seconds |

Successful password or second-factor authentication clears the matching
failure history. TOTP operations use separate keys, so a failure in one
operation does not consume another operation's allowance.

Email request throttles are consumed before account lookup. This limits
repeated requests while preserving generic responses that do not reveal
whether an email address belongs to an account. Requests fail closed when
the shared request-throttling service is unavailable.

## Deployment requirements

Configure the dedicated HMAC secret in every application environment:

```toml
TIMANSTAT_RATE_LIMIT_HMAC_KEY = "YOUR_GENERATED_SECRET"
```

The secret must contain at least 32 UTF-8 bytes. Generate it locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not commit the secret, put it in source code, or share it in support
messages. All workers in the same deployment must use the same secret.
Changing the key changes every identifier digest and therefore starts a new
rate-limit namespace; existing lockout history will not carry over.

For multiple application workers or replicas, configure them to use the
same PostgreSQL database through `DATABASE_URL`. PostgreSQL's atomic upsert
operations provide shared rate-limit state across workers for password
login, email verification, password reset, and TOTP.

SQLite is suitable for local development and automated tests, but it is not
a distributed coordination service across separate machines or containers.
Password-login, email-verification, and password-reset limiters use the
SQLite database file. TOTP deliberately uses process-local rate-limit state
with SQLite to avoid single-writer contention; consequently, TOTP limits are
not shared across multiple SQLite-backed workers. Use PostgreSQL for shared
production TOTP enforcement.

All application workers should keep their system clocks synchronised with a
reliable time source because rate-limit windows use epoch timestamps.

## Client IP controls

The current application layer applies account-identifier and email-address
limits. It does not infer client IP addresses from untrusted forwarded
headers. Do not trust `X-Forwarded-For` or browser-visible IP metadata as
the transport peer address. For a public deployment, add trusted edge-proxy
or WAF IP-based limits as a complementary control. The trusted-proxy resolver
in the codebase is a foundation only; it is not yet connected to a trusted
server-side transport-peer source in the Streamlit application.

## Operational handling

Rate-limit state is operational security data. Restrict database access to
the application, retain only the active window and lockout records, and
never expose the hashed keys through user-facing administration screens.
