"""Customer Feedback Analyser: web page + /predict API (Phases 12-13, extended)."""
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

import joblib
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

from src.alerts.telegram_alert import send_negative_alert, telegram_configured  # noqa: E402
from src.data.preprocess import clean_text  # noqa: E402  (same cleaning as training)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("feedback")

# Saved by Phase 9 training. The vectorizer and model must always be a matching pair.
model = joblib.load(BASE_DIR / "models" / "sentiment_model.pkl")
vectorizer = joblib.load(BASE_DIR / "models" / "tfidf_vectorizer.pkl")

RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "5"))  # submissions per IP per minute
_hits = defaultdict(deque)

app = FastAPI(title="Customer Feedback Analyser")


class Review(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    text: str = Field(..., min_length=3, max_length=2000)
    contact: Optional[str] = Field(None, max_length=100)  # name / phone / email, optional


def _check_rate_limit(ip: str) -> None:
    """Stops one visitor from flooding the owner's Telegram."""
    now, q = time.monotonic(), _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "Too many submissions. Please wait a minute and try again.")
    q.append(now)


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "frontend" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "telegram_configured": telegram_configured()}


@app.post("/predict")
def predict(review: Review, request: Request, background: BackgroundTasks):
    _check_rate_limit(request.client.host if request.client else "unknown")

    cleaned = clean_text(review.text)
    if not cleaned.strip():
        raise HTTPException(
            422, "We couldn't find any words to analyse. Please describe your experience in a sentence or two."
        )

    probs = model.predict_proba(vectorizer.transform([cleaned]))[0]
    scores = {label: round(float(p), 4) for label, p in zip(model.classes_, probs)}
    sentiment = max(scores, key=scores.get)  # same label model.predict() would return

    owner_alerted = False
    if sentiment == "negative":
        if telegram_configured():
            # Runs after the response is sent, so Telegram latency never slows the customer.
            background.add_task(send_negative_alert, review.text, scores[sentiment], review.contact)
            owner_alerted = True
        else:
            log.warning("Negative feedback received but Telegram is not configured.")

    return {
        "sentiment": sentiment,
        "confidence": scores[sentiment],
        "scores": scores,
        "owner_alerted": owner_alerted,
    }
