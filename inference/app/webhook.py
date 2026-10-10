import logging

from fastapi import APIRouter, BackgroundTasks, Request

from app.model_store import reload_if_changed

log = logging.getLogger("inference.webhook")

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/mlflow", status_code=202)
async def mlflow_webhook(request: Request, background: BackgroundTasks):
    """MLflow calls this when an alias is set. The payload is only a hint:
    the registry is re-read, so a forged or duplicated request cannot inject a model."""
    body = await request.body()
    log.info("webhook headers=%s body=%s", dict(request.headers), body[:2000])
    # TODO: verify the HMAC signature once the header name and scheme are confirmed
    background.add_task(reload_if_changed)
    return {"accepted": True}
