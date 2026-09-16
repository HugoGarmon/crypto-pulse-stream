import asyncio
import logging
import signal
import sys
import time
from typing import Any

import orjson
import websockets
from aiokafka import AIOKafkaProducer
from config import settings
from schemas import BinanceCombinedStreamMessage, CryptoTrade
from websockets.exceptions import ConnectionClosed

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [PRODUCER] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("crypto_producer")


class BinanceStreamingProducer:
    """Ingiere eventos de trading en tiempo real desde Binance WebSocket y publica a Redpanda."""

    def __init__(self) -> None:
        self.producer: AIOKafkaProducer | None = None
        self.is_running: bool = True
        self.total_messages_ingested: int = 0
        self.messages_window: int = 0
        self.last_metrics_log: float = time.time()

    async def init_kafka(self) -> None:
        """Inicializa el cliente de aiokafka con reintentos."""
        logger.info(
            "Conectando a broker Redpanda/Kafka en: %s",
            settings.kafka_bootstrap_servers,
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: orjson.dumps(v),
            key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
            acks=1,
            linger_ms=5,  # Micro-loteado ligero para alto throughput
        )
        await self.producer.start()
        logger.info("Conexión con Redpanda establecida exitosamente.")

    async def stop(self) -> None:
        """Cierre ordenado de conexiones."""
        logger.info("Deteniendo servicio Producer...")
        self.is_running = False
        if self.producer:
            await self.producer.stop()
            logger.info("Productor Kafka cerrado limpiamente.")

    async def _log_throughput(self) -> None:
        """Imprime métricas de throughput cada 5 segundos."""
        now = time.time()
        elapsed = now - self.last_metrics_log
        if elapsed >= 5.0:
            rate = self.messages_window / elapsed
            logger.info(
                "Throughput actual: %.2f trades/seg | Total acumulado: %d trades",
                rate,
                self.total_messages_ingested,
            )
            self.messages_window = 0
            self.last_metrics_log = now

    async def run(self) -> None:
        """Bucle principal de conexión a Binance WebSocket con Exponential Backoff."""
        await self.init_kafka()

        retry_delay = 1
        max_delay = 30
        stream_url = settings.binance_combined_stream_url

        while self.is_running:
            try:
                logger.info("Conectando a Binance WebSocket: %s", stream_url)
                async with websockets.connect(
                    stream_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    logger.info("Conexión WebSocket activa con Binance. Ingestando ticks...")
                    retry_delay = 1  # Reset tras conexión exitosa

                    async for message in ws:
                        if not self.is_running:
                            break

                        payload: dict[str, Any] = orjson.loads(message)

                        # En stream combinado viene empaquetado en {"stream": "...", "data": {...}}
                        if "data" in payload:
                            trade_data = BinanceCombinedStreamMessage.model_validate(payload).data
                        else:
                            # Caso stream directo individual
                            trade_data = BinanceCombinedStreamMessage.model_validate(
                                {"stream": "", "data": payload}
                            ).data

                        trade = CryptoTrade.from_binance_agg_trade(trade_data)

                        # Enviar a Redpanda particionado por símbolo
                        await self.producer.send(
                            topic=settings.kafka_topic_raw_trades,
                            key=trade.symbol,
                            value=trade.model_dump(),
                        )

                        self.total_messages_ingested += 1
                        self.messages_window += 1
                        await self._log_throughput()

            except (ConnectionClosed, OSError) as exc:
                logger.warning(
                    "Conexión con Binance interrumpida: %s. Reintentando en %ds...",
                    exc,
                    retry_delay,
                )
            except Exception as exc:
                logger.error("Error inesperado en loop de ingesta: %s", exc, exc_info=True)

            if self.is_running:
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)


async def main() -> None:
    producer_service = BinanceStreamingProducer()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(producer_service.stop()))
        except NotImplementedError:
            # En Windows add_signal_handler puede no estar soportado para todos los loops
            pass

    try:
        await producer_service.run()
    except asyncio.CancelledError:
        logger.info("Tarea principal cancelada.")
    finally:
        await producer_service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Proceso terminado por usuario.")
