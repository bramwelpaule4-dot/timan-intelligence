"""Public callback API for asynchronous payment providers."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from timan_intelligence.billing.daraja import DarajaError, handle_mpesa_callback

app = FastAPI(
    title="TimanStat Payment Callbacks",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.post("/api/v1/payments/mpesa/callback")
async def mpesa_callback(request: Request):
    """Receive Safaricom's callback; settlement requires a successful status query."""
    raw_body = await request.body()
    try:
        handle_mpesa_callback(raw_body)
    except DarajaError:
        # Do not disclose payment identifiers or internal verification details.
        return JSONResponse({"ResultCode": 1, "ResultDesc": "Callback not accepted"}, status_code=400)
    except Exception:
        return JSONResponse({"ResultCode": 1, "ResultDesc": "Callback processing unavailable"}, status_code=503)
    return {"ResultCode": 0, "ResultDesc": "Accepted"}
