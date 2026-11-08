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

Safaricom's callbacks are not cryptographically signed. TimanStat therefore
does not settle an invoice from the STK callback alone. It correlates the
CheckoutRequestID to the pending ledger attempt and queries the STK Push Query
API. For a successful STK result, it submits the callback receipt to
Safaricom's asynchronous Transaction Status API using the configured
initiator and encrypted SecurityCredential.

The invoice remains pending until the Transaction Status result callback
matches the server-created OriginatorConversationID and confirms the same
ReceiptNo, whole-shilling Amount, and `TransactionStatus=Completed` as the
payment attempt. TimanStat then rechecks the STK status and uses the existing
idempotent billing settlement path. Failed/cancelled STK results are queried
against Safaricom before being recorded. Transaction-status timeouts do not
settle a payment; they remain pending for operational review.

The Transaction Status result callback is also an unsigned callback. Its
unpredictable request correlation and independently returned transaction
fields improve reconciliation, but do not constitute cryptographic callback
authentication. Keep HTTPS, request-size and rate limits, monitoring, and
network-level restrictions where Safaricom's published infrastructure
permits. Do not treat browser returns, STK acknowledgements, or unverified
callbacks as proof of payment.

## Sandbox and production

Use Daraja sandbox credentials and Safaricom's test shortcode for integration
testing. Although production credentials may be obtained through Safaricom's
onboarding, setting `DARAJA_ENVIRONMENT=production` currently causes the
adapter to fail closed. Do not remove this guard until Safaricom sandbox end-to-end testing, callback
hardening, timeout/retry operations, and a production-readiness review are complete. No live credentials are included
in this repository.
