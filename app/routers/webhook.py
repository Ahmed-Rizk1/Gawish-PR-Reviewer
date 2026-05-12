from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.webhook import WebhookPayload
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhook", tags=["webhook"])
_service = WebhookService()


@router.post("", status_code=200)
async def receive_webhook(request: Request) -> JSONResponse:
    raw = await request.json()
    payload = WebhookPayload(**raw)
    result = await _service.handle_event(payload)
    return JSONResponse(content=result, status_code=200)
