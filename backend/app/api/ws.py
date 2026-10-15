"""WebSocket /ws: sends a LiveUpdate on connect and after every poll."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.poller import Poller

router = APIRouter()


@router.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    poller: Poller = websocket.app.state.poller
    await websocket.accept()
    queue = poller.subscribe()
    try:
        # Send what we have straight away, so a new screen isn't blank for 30 s.
        await websocket.send_text(poller.live_update().model_dump_json())
        while True:
            update = await queue.get()
            await websocket.send_text(update.model_dump_json())
    except WebSocketDisconnect:
        pass
    finally:
        poller.unsubscribe(queue)
