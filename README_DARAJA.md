# M-Pesa Daraja integration

TimanStat supports Kenya M-Pesa Express (STK Push) for KES invoices. The
integration uses Safaricom's Daraja OAuth, STK Push and STK Push Query APIs.
The synchronous STK acknowledgement means only that Safaricom accepted the
request; it is not evidence of payment.

## Runtime configuration

Configure these as deployment secrets/environment variables (never commit
actual credentials):

- `DARAJA_ENVIRONMENT`: `sandbox` (default) or `production`
- `DARAJA_CONSUMER_KEY`
- `DARAJA_CONSUMER_SECRET`
- `DARAJA_BUSINESS_SHORTCODE`
- `DARAJA_PASSKEY`
- `DARAJA_CALLBACK_URL`: public HTTPS URL ending in
  `/api/v1/payments/mpesa/callback`
- `DARAJA_INITIATOR_NAME`: Safaricom M-Pesa API initiator username with Transaction Status Query permission
- `DARAJA_SECURITY_CREDENTIAL`: Safaricom RSA-encrypted initiator credential for the active environment
- `DARAJA_TRANSACTION_STATUS_RESULT_URL`: public HTTPS URL ending in
  `/api/v1/payments/mpesa/transaction-status/result`
- `DARAJA_TRANSACTION_STATUS_TIMEOUT_URL`: public HTTPS URL ending in
  `/api/v1/payments/mpesa/transaction-status/timeout`
- `DARAJA_IDENTIFIER_TYPE`: receiving organisation identifier type (default `4` for shortcode)

The callback service is started separately from Streamlit:

```bash
uvicorn timan_intelligence.payment_api:app --host 0.0.0.0 --port 8000
```

Point all three configured callback URLs to the public HTTPS endpoints routed
to that service. Keep the endpoints behind TLS and standard infrastructure
protections (request-size limits, rate limits, monitoring and restricted
network exposure where possible).

## Starting a payment

On the Subscription & Plans page, expand an eligible invoice and enter the
Kenyan phone number that should receive the STK prompt. The checkout is scoped
to the signed-in user's personal account or selected organisation. Phone
numbers may be entered as Kenyan 07..., 01..., or 254... numbers. Only
whole-shilling KES invoice balances are supported. The underlying service is
also available through `initiate_mpesa_payment(invoice_id, phone, user_id=...)`
or `organisation_id=...`. The customer completes the prompt on their phone.

## Callback and reconciliation

Daraja's STK callback is not cryptographically signed. TimanStat does not
trust a callback success by itself: it matches CheckoutRequestID to a pending
M-Pesa ledger transaction, then queries Safaricom's STK Push Query API. An STK Push Query response does not independently attest the callback's
amount and receipt metadata. Therefore sandbox settlement is suitable only
for integration testing; it is not a production-grade reconciliation control.
Production mode is deliberately blocked in the adapter until an independent
Safaricom Transaction Status reconciliation flow verifies the receipt,
amount, currency and transaction identity before settlement. Failed/cancelled
callbacks are queried against Safaricom before being recorded. Duplicate
callbacks are idempotently handled by the existing webhook-event ledger.

A production deployment should also schedule reconciliation for pending
requests where Safaricom does not deliver a callback. Never use the browser
return, STK request acknowledgement, or an unverified callback to activate
a subscription.

## Sandbox and production

Use Daraja sandbox credentials and Safaricom's test shortcode for integration
testing. Although production credentials may be obtained through Safaricom's
onboarding, setting `DARAJA_ENVIRONMENT=production` currently causes the
adapter to fail closed. Do not remove this guard until Safaricom sandbox end-to-end testing, callback
hardening, reconciliation retry controls, and production-readiness review are complete. No live credentials are included
in this repository.
