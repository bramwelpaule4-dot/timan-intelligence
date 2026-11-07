# TimanStat authentication rate limiting

TimanStat stores rate-limit state in the shared `rate_limit_states` database
table. Identifiers are normalised and SHA-256 hashed before storage; raw
usernames, email addresses, and account IDs are not stored in this table.

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
whether an email address belongs to an account.

## Deployment requirement

For multiple application workers or replicas, configure all of them to use
the **same PostgreSQL database** through `DATABASE_URL`. PostgreSQL's atomic
upsert operations make each counter update safe across concurrent workers.

SQLite uses the same persistent implementation, but only coordinates
processes that access the same database file on the same host. It is not a
distributed coordination service across separate machines or containers.
Do not deploy multiple independent SQLite files and assume they share limits.

All application workers should keep their system clocks synchronised
with a reliable time source because rate-limit windows use UTC epoch time.

The current application layer applies account-identifier and email-address
limits. It does not infer client IP addresses from untrusted forwarded headers.
For a public multi-replica deployment, add trusted edge-proxy or WAF IP-based
limits as a complementary control.

Rate-limit state is operational security data. Restrict database access to
the application, retain only the active window/lockout records, and never
expose the hashed keys through user-facing administration screens.
