import json
import logging

from fastapi import APIRouter, BackgroundTasks, Request

from app.model_store import reload_if_changed

log = logging.getLogger("inference.webhook")

router = APIRouter(prefix="/webhook", tags=["webhook"])

_SENSITIVE = ("signature", "authorization", "secret", "token")
_MAX_BODY = 2000


def _safe_headers(headers):
    """Header names are useful for debugging. Values that look like credentials are hidden."""
    return {
        name: ("<redacted>" if any(word in name.lower() for word in _SENSITIVE) else value)
        for name, value in headers.items()
    }


@router.post("/mlflow", status_code=202, include_in_schema=False)
async def mlflow_webhook(request: Request, background: BackgroundTasks):
    """MLflow calls this when an alias is set. The payload is only a hint: the registry
    is re-read, so a forged or duplicated request cannot inject a model."""
    raw = await request.body()
    try:
        payload = json.dumps(json.loads(raw))[:_MAX_BODY]
    except ValueError:
        payload = repr(raw[:_MAX_BODY])

    client = request.client.host if request.client else "-"
    log.info("event=webhook_received client=%s payload=%s", client, payload)
    log.info("event=webhook_headers headers=%s", _safe_headers(request.headers))

    background.add_task(reload_if_changed)
    return {"accepted": True}
