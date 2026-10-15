"""WebSocket endpoint. For now it just sends a heartbeat with server time;
later it will push a BridgeSnapshot on every poll."""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(
                {"type": "heartbeat", "server_time": datetime.now(UTC).isoformat()}
            )
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
