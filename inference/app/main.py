import logging
import os
from contextlib import asynccontextmanager

import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

log = logging.getLogger("inference")

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "bank-marketing")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "champion")

# Readable request field -> column name the model was trained with
COLUMNS = {
    "age": "V1", "job": "V2", "marital": "V3", "education": "V4",
    "default": "V5", "balance": "V6", "housing": "V7", "loan": "V8",
    "contact": "V9", "day": "V10", "month": "V11", "duration": "V12",
    "campaign": "V13", "pdays": "V14", "previous": "V15", "poutcome": "V16",
}

state = {"model": None, "version": None}


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


def load_champion():
    """Load the model behind the champion alias from the MLflow registry."""
    mlflow.set_tracking_uri(TRACKING_URI)
    uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"
    state["model"] = mlflow.sklearn.load_model(uri)
    version = mlflow.MlflowClient().get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
    state["version"] = version.version
    log.info("Loaded %s version %s", uri, state["version"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        load_champion()
    except Exception:
        log.exception("Could not load the champion model, starting without it")
    yield


app = FastAPI(title="Bank marketing inference", lifespan=lifespan)


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
