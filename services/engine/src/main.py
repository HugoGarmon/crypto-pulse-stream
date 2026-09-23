import asyncio
import logging
import signal
import sys
import time
from typing import Any

import orjson
from aggregator import StreamAggregator
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from config import settings
from schemas import CryptoTrade, ProcessedMetricMessage
from storage import ClickHouseStorage

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ENGINE] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("crypto_stream_engine")


class CryptoStreamEngine:
    """Motor de procesamiento en streaming:
    Agregaciones, VWAP, Detección de Ballenas y Persistencia OLAP.
    """

    def __init__(self) -> None:
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.storage = ClickHouseStorage()
        self.aggregator = StreamAggregator(whale_threshold_usd=settings.whale_threshold_usd)
        self.is_running: bool = True
        self.total_processed: int = 0
        self.last_stats_log: float = time.time()
        self.trades_in_window: int = 0

    async def initialize(self) -> None:
        """Inicializa conexiones a ClickHouse y Kafka/Redpanda con reintentos."""
        logger.info("Inicializando Crypto Stream Engine...")

        # 1. ClickHouse
        retries = 10
        for i in range(retries):
            try:
                self.storage.connect()
                break
            except Exception as exc:
                logger.warning(
                    "ClickHouse no disponible aún (%s). Reintentando en 3s (%d/%d)...",
                    exc,
                    i + 1,
                    retries,
                )
                await asyncio.sleep(3)

        # 2. Kafka Consumer & Producer
        logger.info(
            "Conectando consumidor y productor Kafka en: %s", settings.kafka_bootstrap_servers
        )
        self.consumer = AIOKafkaConsumer(
            settings.kafka_topic_raw_trades,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            auto_commit_interval_ms=2000,
            value_deserializer=lambda v: orjson.loads(v),
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: orjson.dumps(v),
            key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
            acks=1,
            linger_ms=5,
        )

        await self.consumer.start()
        await self.producer.start()
        self.storage.last_flush_time = time.time()
        logger.info(
            "Stream Engine conectado exitosamente a topics '%s' y '%s'.",
            settings.kafka_topic_raw_trades,
            settings.kafka_topic_processed_metrics,
        )

    async def stop(self) -> None:
        """Cierre ordenado y volcado final de buffers."""
        logger.info("Deteniendo Crypto Stream Engine...")
        self.is_running = False
        if self.consumer:
            await self.consumer.stop()
        if self.storage:
            await self.storage.flush()
        if self.producer:
            await self.producer.stop()
        logger.info("Stream Engine cerrado de forma limpia.")

    async def _emit_event(self, event_type: str, symbol: str, payload: dict[str, Any]) -> None:
        if not self.producer:
            return
        msg = ProcessedMetricMessage(
            event_type=event_type,
            symbol=symbol,
            payload=payload,
        )
        await self.producer.send(
            topic=settings.kafka_topic_processed_metrics,
            key=symbol,
            value=msg.model_dump(),
        )

    async def _periodic_flush_worker(self) -> None:
        """Tarea en background para asegurar flush a ClickHouse periódicamente."""
        while self.is_running:
            await asyncio.sleep(settings.engine_microbatch_interval_sec)
            now = time.time()
            if self.storage.should_flush(now):
                self.storage.last_flush_time = now
                await self.storage.flush()

    async def run(self) -> None:
        """Bucle principal de consumo y procesamiento analítico en streaming."""
        await self.initialize()
        asyncio.create_task(self._periodic_flush_worker())

        logger.info("Motor en marcha. Esperando eventos de mercado...")

        if not self.consumer:
            return

        async for msg in self.consumer:
            if not self.is_running:
                break

            try:
                raw_payload = msg.value
                trade = CryptoTrade.model_validate(raw_payload)

                # 1. Procesamiento analítico en memoria
                completed_candle, whale_alert, ticker_update = self.aggregator.process_trade(trade)

                # 2. Persistencia en micro-batch
                self.storage.add_trade(trade)

                # 3. Emisión de Ticker en vivo (incluye la vela en formación actual para el chart)
                current_candle = self.aggregator.get_in_flight_candle(trade.symbol)
                ticker_payload = ticker_update.model_dump()
                ticker_payload["in_flight_candle"] = current_candle

                await self._emit_event(
                    event_type="ticker",
                    symbol=trade.symbol,
                    payload=ticker_payload,
                )

                # Emisión de trade para el live tape del frontend
                await self._emit_event(
                    event_type="trade",
                    symbol=trade.symbol,
                    payload=trade.model_dump(),
                )

                # 4. Manejo de vela completada
                if completed_candle:
                    self.storage.add_candle(completed_candle)
                    await self._emit_event(
                        event_type="candle",
                        symbol=trade.symbol,
                        payload=completed_candle.model_dump(),
                    )

                # 5. Manejo de alerta ballena
                if whale_alert:
                    self.storage.add_whale(whale_alert)
                    await self._emit_event(
                        event_type="whale",
                        symbol=trade.symbol,
                        payload=whale_alert.model_dump(),
                    )

                self.total_processed += 1
                self.trades_in_window += 1

                # 6. Flush por volumen si se alcanzó el tamaño de micro-batch
                now = time.time()
                if self.storage.should_flush(now):
                    self.storage.last_flush_time = now
                    await self.storage.flush()

                # Métricas de throughput del Engine
                elapsed = now - self.last_stats_log
                if elapsed >= 5.0:
                    rate = self.trades_in_window / elapsed
                    logger.info(
                        "Engine Throughput: %.2f trades/s | Total procesado: %d eventos",
                        rate,
                        self.total_processed,
                    )
                    self.trades_in_window = 0
                    self.last_stats_log = now

            except Exception as exc:
                logger.error("Error procesando mensaje en Engine: %s", exc, exc_info=True)


async def main() -> None:
    engine = CryptoStreamEngine()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(engine.stop()))
        except NotImplementedError:
            pass

    try:
        await engine.run()
    except asyncio.CancelledError:
        logger.info("Tarea de engine cancelada.")
    finally:
        await engine.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Motor finalizado por interrupción de usuario.")
