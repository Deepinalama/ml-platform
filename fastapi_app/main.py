import logging
import os
import pickle
from contextlib import asynccontextmanager
from datetime import datetime

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Database connection

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin1234")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ml_platform")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
engine = create_engine(DATABASE_URL)


# Global model state

model_state = {
    "model": None,
    "version_id": None,
    "version_name": None,
    "accuracy": None,
}


def load_active_model():
    """Load the currently active model from model_versions table."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, version_name, accuracy, file_path
                FROM model_versions
                WHERE is_active = TRUE
                ORDER BY trained_at DESC
                LIMIT 1
            """))
            row = result.fetchone()

        if not row:
            logger.warning("No active model found in model_versions")
            return

        version_id, version_name, accuracy, file_path = row

        if not os.path.exists(file_path):
            logger.error(f"Model file not found at {file_path}")
            return

        with open(file_path, "rb") as f:
            model = pickle.load(f)

        model_state["model"] = model
        model_state["version_id"] = version_id
        model_state["version_name"] = version_name
        model_state["accuracy"] = float(accuracy)

        logger.info(f"Loaded model: {version_name} (accuracy: {accuracy})")

    except Exception as e:
        logger.error(f"Failed to load model: {e}")


#  load model on startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — loading active model...")
    load_active_model()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Churn Prediction API",
    description="ML inference service for customer churn prediction",
    version="1.0.0",
    lifespan=lifespan,
)


# Request / Response schemas


class PredictRequest(BaseModel):
    customer_id: str
    days_since_signup: int
    days_since_last_login: int
    avg_monthly_spend: float
    support_ticket_count: int
    is_premium: bool
    requested_by: str = "api"


class PredictResponse(BaseModel):
    customer_id: str
    will_churn: bool
    probability: float
    model_version: str


# Endpoints


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model_state["model"] is not None,
        "model_version": model_state["version_name"],
    }


@app.get("/model-info")
def model_info():
    if not model_state["model"]:
        raise HTTPException(status_code=503, detail="No model loaded")
    return {
        "version_id": model_state["version_id"],
        "version_name": model_state["version_name"],
        "accuracy": model_state["accuracy"],
    }


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if not model_state["model"]:
        raise HTTPException(status_code=503, detail="No model loaded")

    # Build feature dataframe in the same column order as training
    features = pd.DataFrame(
        [
            {
                "days_since_signup": request.days_since_signup,
                "days_since_last_login": request.days_since_last_login,
                "avg_monthly_spend": request.avg_monthly_spend,
                "support_ticket_count": request.support_ticket_count,
                "is_premium": int(request.is_premium),
            }
        ]
    )

    model = model_state["model"]
    prediction = bool(model.predict(features)[0])
    probability = round(float(model.predict_proba(features)[0][1]), 4)

    # Log prediction to predictions table
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                INSERT INTO predictions
                    (customer_id, prediction, probability, model_version_id, requested_by, predicted_at)
                VALUES
                    (:customer_id, :prediction, :probability, :model_version_id, :requested_by, :predicted_at)
            """),
                {
                    "customer_id": request.customer_id,
                    "prediction": prediction,
                    "probability": probability,
                    "model_version_id": model_state["version_id"],
                    "requested_by": request.requested_by,
                    "predicted_at": datetime.utcnow(),
                },
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log prediction: {e}")

    return PredictResponse(
        customer_id=request.customer_id,
        will_churn=prediction,
        probability=probability,
        model_version=model_state["version_name"],
    )


@app.post("/reload-model")
def reload_model():
    """Reload the active model from DB — call this after Airflow retrains."""
    load_active_model()
    if not model_state["model"]:
        raise HTTPException(status_code=503, detail="Failed to reload model")
    return {
        "message": "Model reloaded successfully",
        "version": model_state["version_name"],
    }
