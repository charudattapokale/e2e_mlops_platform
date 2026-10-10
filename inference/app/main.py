import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.model_store import load_champion, state
from app.webhook import router as webhook_router

log = logging.getLogger("inference")

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
        load_champion()
    except Exception:
        log.exception("Could not load the champion model, starting without it")
    yield


app = FastAPI(title="Bank marketing inference", lifespan=lifespan)
app.include_router(webhook_router)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": state["model"] is not None}


@app.post("/reload")
def reload_model():
    try:
        load_champion()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"reload failed: {exc}")
    return {"model_version": state["version"]}


@app.post("/predict")
def predict(client: Client):
    if state["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    row = {COLUMNS[k]: v for k, v in client.model_dump().items()}
    frame = pd.DataFrame([row])
    proba = float(state["model"].predict_proba(frame)[0, 1])
    return {
        "prediction": int(proba > 0.5),
        "probability": proba,
        "model_version": state["version"],
    }
