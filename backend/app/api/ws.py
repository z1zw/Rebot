from fastapi import APIRouter, WebSocket
from app.core.events import get_event_bus
from app.core.auth import evaluate_api_key, extract_api_key_from_headers
from app.core.settings import settings

router = APIRouter()


@router.websocket("/events")
async def events(ws: WebSocket):
    provided = extract_api_key_from_headers(ws.headers)
    if not provided:
        provided = (ws.query_params.get("api_key") or "").strip()
    decision = evaluate_api_key(
        mode=settings.auth_mode,
        expected=settings.server_api_key or "",
        provided=provided,
    )
    if not decision.allowed:
        await ws.close(code=4401, reason=decision.reason)
        return

    await ws.accept()
    bus = get_event_bus()
    while True:
        batch = await bus.next()
        await ws.send_json(batch)
