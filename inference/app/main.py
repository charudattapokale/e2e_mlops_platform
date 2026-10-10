import logging
import time
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.logging_config import setup_logging
from app.model_store import ChampionNotFound, load_champion, load_champion_or_fail, state
from app.webhook import router as webhook_router

setup_logging()
log = logging.getLogger("inference.app")
predict_log = logging.getLogger("inference.predict")

# Readable request field -> column name the model was trained with
COLUMNS = {
    "age": "V1", "job": "V2", "marital": "V3", "education": "V4",
    "default": "V5", "balance": "V6", "housing": "V7", "loan": "V8",
    "contact": "V9", "day": "V10", "month": "V11", "duration": "V12",
    "campaign": "V13", "pdays": "V14", "previous": "V15", "poutcome": "V16",
}


class Client(BaseModel):
    age: int
    job: str
    marital: str
    education: str
    default: str
    balance: int
    housing: str
    loan: str
    contact: str
    day: int
    month: str
    duration: int
    campaign: int
    pdays: int
    previous: int
    poutcome: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        load_champion_or_fail()
    except ChampionNotFound as exc:
        log.error("event=startup_aborted reason=no_champion detail=%s", exc)
        raise RuntimeError("no champion model, refusing to start") from exc
    except Exception as exc:
        log.error("event=startup_aborted reason=load_failed detail=%s", exc)
        raise RuntimeError("could not load the champion model, refusing to start") from exc
    yield


app = FastAPI(title="Bank marketing inference", lifespan=lifespan)
app.include_router(webhook_router)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": state["model"] is not None}


@app.post("/reload", include_in_schema=False)
def reload_model():
    try:
        load_champion()
    except ChampionNotFound as exc:
        log.warning("event=reload_failed reason=no_champion detail=%s", exc)
        raise HTTPException(status_code=503, detail="no champion model to load")
    except Exception as exc:
        log.exception("event=reload_failed")
        raise HTTPException(status_code=503, detail=f"reload failed: {exc}")
    return {"model_version": state["version"]}


@app.post("/predict")
def predict(client: Client):
    # Read both once, so a reload in another thread cannot mix a model with the wrong version
    model, version = state["model"], state["version"]
    if model is None:
        predict_log.warning("event=predict_rejected reason=no_model")
        raise HTTPException(status_code=503, detail="model not loaded")

    started = time.perf_counter()
    row = {COLUMNS[k]: v for k, v in client.model_dump().items()}
    proba = float(model.predict_proba(pd.DataFrame([row]))[0, 1])
    prediction = int(proba > 0.5)

    # Inputs are personal banking data and are never logged
    predict_log.info(
        "event=predict model_version=%s prediction=%d probability=%.4f latency_ms=%.1f",
        version, prediction, proba, (time.perf_counter() - started) * 1000,
    )
    return {"prediction": prediction, "probability": proba, "model_version": version}
