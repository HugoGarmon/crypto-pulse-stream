import asyncio
import logging
from collections import defaultdict
from typing import Any

import orjson
from aiokafka import AIOKafkaConsumer
from config import settings
from fastapi import WebSocket

logger = logging.getLogger("crypto_gateway_broadcaster")


class ConnectionManager:
    """Administra conexiones activas de WebSockets particionadas por símbolo."""

    def __init__(self) -> None:
        self.active_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, symbol: str) -> None:
        await websocket.accept()
        symbol_key = symbol.upper()
        async with self._lock:
            self.active_connections[symbol_key].add(websocket)
        logger.info(
            "Cliente WS conectado a símbolo '%s'. Conexiones activas: %d",
            symbol_key,
            len(self.active_connections[symbol_key]),
        )

    async def disconnect(self, websocket: WebSocket, symbol: str) -> None:
        symbol_key = symbol.upper()
        async with self._lock:
            self.active_connections[symbol_key].discard(websocket)
            if not self.active_connections[symbol_key]:
                self.active_connections.pop(symbol_key, None)
        logger.info("Cliente WS desconectado de símbolo '%s'.", symbol_key)

    async def broadcast(self, symbol: str, message: dict[str, Any]) -> None:
        """Difunde el mensaje a todos los clientes suscritos al símbolo y a 'ALL'."""
        symbol_key = symbol.upper()
        targets: list[WebSocket] = []

        async with self._lock:
            targets.extend(self.active_connections.get(symbol_key, set()))
            if symbol_key != "ALL":
                targets.extend(self.active_connections.get("ALL", set()))

        if not targets:
            return

        payload_bytes = orjson.dumps(message)
        payload_str = payload_bytes.decode("utf-8")

        dead_connections: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(payload_str)
            except Exception:
                dead_connections.append(ws)

        if dead_connections:
            async with self._lock:
                for ws in dead_connections:
                    self.active_connections[symbol_key].discard(ws)
                    self.active_connections.get("ALL", set()).discard(ws)


class KafkaBroadcastWorker:
    """Consume del topic processed-crypto-metrics y distribuye a WebSockets."""

    def __init__(self, manager: ConnectionManager) -> None:
        self.manager = manager
        self.consumer: AIOKafkaConsumer | None = None
        self.is_running: bool = False
        self.task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.is_running = True
        logger.info(
            "Iniciando KafkaBroadcastWorker hacia topic: %s",
            settings.kafka_topic_processed_metrics,
        )
        self.consumer = AIOKafkaConsumer(
            settings.kafka_topic_processed_metrics,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda v: orjson.loads(v),
        )

        # Reintento de conexión a Kafka
        connected = False
        for attempt in range(10):
            try:
                await self.consumer.start()
                connected = True
                break
            except Exception as exc:
                logger.warning(
                    "Error conectando consumidor WS a Kafka (%s). Reintento %d/10...",
                    exc,
                    attempt + 1,
                )
                await asyncio.sleep(2)

        if not connected:
            logger.error("No se pudo conectar KafkaBroadcastWorker tras 10 intentos.")
            return

        self.task = asyncio.create_task(self._consume_loop())
        logger.info("KafkaBroadcastWorker iniciado y escuchando.")

    async def stop(self) -> None:
        self.is_running = False
        if self.task:
            self.task.cancel()
        if self.consumer:
            await self.consumer.stop()
        logger.info("KafkaBroadcastWorker detenido.")

    async def _consume_loop(self) -> None:
        if not self.consumer:
            return

        try:
            async for msg in self.consumer:
                if not self.is_running:
                    break
                try:
                    event: dict[str, Any] = msg.value
                    symbol = event.get("symbol", "ALL")
                    await self.manager.broadcast(symbol, event)
                except Exception as exc:
                    logger.error("Error transmitiendo mensaje WS: %s", exc)
        except asyncio.CancelledError:
            pass


manager = ConnectionManager()
worker = KafkaBroadcastWorker(manager)
