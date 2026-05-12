import logging

import app.core.config  # noqa: F401 — triggers load_dotenv at startup
from fastapi import FastAPI

from app.routers import webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="PR Reviewer", version="0.1.0")

app.include_router(webhook.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
