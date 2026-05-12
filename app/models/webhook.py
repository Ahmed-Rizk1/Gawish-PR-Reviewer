from pydantic import BaseModel
from typing import Any, Dict


class WebhookPayload(BaseModel):
    """Generic model for incoming GitHub webhook payloads."""
    model_config = {"extra": "allow"}

    action: str | None = None
    repository: Dict[str, Any] | None = None
    pull_request: Dict[str, Any] | None = None
    sender: Dict[str, Any] | None = None
