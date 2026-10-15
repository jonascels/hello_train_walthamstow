"""WebSocket /ws: sends a LiveUpdate on connect and after every poll."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.poller import Poller

router = APIRouter()


@router.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    poller: Poller = websocket.app.state.poller
    await websocket.accept()
    queue = poller.subscribe()

    async def send_updates() -> None:
        # Send what we have straight away, so a new screen isn't blank for 30 s.
        await websocket.send_text(poller.live_update().model_dump_json())
        while True:
            update = await queue.get()
            await websocket.send_text(update.model_dump_json())

    sender = asyncio.create_task(send_updates())
    try:
        # Clients never send anything, but we must keep receiving to notice
        # when they disconnect (or the server shuts down); otherwise this
        # handler would wait on the queue forever and block server reloads.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        sender.cancel()
        poller.unsubscribe(queue)
