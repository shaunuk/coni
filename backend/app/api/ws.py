"""WebSocket endpoint for real-time progress updates."""
import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections per question."""

    def __init__(self):
        self.active_connections: dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, question_id: str) -> None:
        await websocket.accept()
        if question_id not in self.active_connections:
            self.active_connections[question_id] = set()
        self.active_connections[question_id].add(websocket)

    def disconnect(self, websocket: WebSocket, question_id: str) -> None:
        if question_id in self.active_connections:
            self.active_connections[question_id].discard(websocket)
            if not self.active_connections[question_id]:
                del self.active_connections[question_id]

    async def broadcast(self, question_id: str, message: str) -> None:
        if question_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[question_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    dead_connections.add(connection)
            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[question_id].discard(conn)


manager = ConnectionManager()


async def redis_subscriber(question_id: str) -> None:
    """Subscribe to Redis channel and broadcast to WebSocket clients."""
    logger.info(f"Starting Redis subscriber for {question_id}")
    redis = await aioredis.from_url(settings.redis_url)
    pubsub = redis.pubsub()
    channel = f"progress:{question_id}"

    try:
        await pubsub.subscribe(channel)
        logger.info(f"Subscribed to channel: {channel}")

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                logger.info(f"Received message on {channel}: {data[:100]}")
                await manager.broadcast(question_id, data)

                # Check if pipeline completed
                try:
                    event = json.loads(data)
                    if event.get("type") in ("pipeline_completed", "pipeline_failed"):
                        break
                except json.JSONDecodeError:
                    pass

            # Small delay to prevent busy loop
            await asyncio.sleep(0.01)

    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis.close()


@router.websocket("/ws/progress/{question_id}")
async def websocket_progress(websocket: WebSocket, question_id: str):
    """WebSocket endpoint for receiving real-time progress updates."""
    await manager.connect(websocket, question_id)

    # Start Redis subscriber task
    subscriber_task = asyncio.create_task(redis_subscriber(question_id))

    try:
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (mainly for ping/pong)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Handle ping
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        subscriber_task.cancel()
        try:
            await subscriber_task
        except asyncio.CancelledError:
            pass
        manager.disconnect(websocket, question_id)
