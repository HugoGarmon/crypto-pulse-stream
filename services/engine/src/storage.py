import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import clickhouse_connect
from config import settings
from schemas import CandleData, CryptoTrade, WhaleAlert

logger = logging.getLogger("crypto_engine_storage")


class ClickHouseStorage:
    """Gestiona persistencia analítica de alto rendimiento mediante micro-batching a ClickHouse."""

    def __init__(self) -> None:
        self.client: Any = None
        self.trades_buffer: list[list[Any]] = []
        self.candles_buffer: list[list[Any]] = []
        self.whales_buffer: list[list[Any]] = []
        self.last_flush_time: float = 0.0

    def connect(self) -> None:
        """Inicializa conexión con ClickHouse con reintentos."""
        logger.info(
            "Conectando a ClickHouse en %s:%s (DB: %s)...",
            settings.clickhouse_host,
            settings.clickhouse_port,
            settings.clickhouse_db,
        )
        self.client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            database=settings.clickhouse_db,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            connect_timeout=10,
            send_receive_timeout=15,
        )
        logger.info("Conexión con ClickHouse establecida exitosamente.")

    def add_trade(self, trade: CryptoTrade) -> None:
        """Agrega un trade bruto al buffer de inserción por lotes."""
        dt = datetime.fromtimestamp(trade.timestamp / 1000.0, tz=UTC)
        self.trades_buffer.append(
            [
                dt,
                trade.symbol,
                trade.price,
                trade.quantity,
                trade.volume_usd,
                1 if trade.is_buyer_maker else 0,
                trade.trade_id,
            ]
        )

    def add_candle(self, candle: CandleData) -> None:
        """Agrega una vela completada al buffer de velas."""
        dt = datetime.fromtimestamp(candle.candle_time, tz=UTC)
        self.candles_buffer.append(
            [
                dt,
                candle.symbol,
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
                candle.volume_usd,
                candle.vwap,
                candle.trades_count,
            ]
        )

    def add_whale(self, whale: WhaleAlert) -> None:
        """Agrega una alerta institucional al buffer de ballenas."""
        dt = datetime.fromtimestamp(whale.timestamp / 1000.0, tz=UTC)
        self.whales_buffer.append(
            [
                dt,
                whale.symbol,
                whale.price,
                whale.quantity,
                whale.volume_usd,
                1 if whale.is_buyer_maker else 0,
                whale.trade_id,
            ]
        )

    def should_flush(self, now: float) -> bool:
        """Evalúa si se debe realizar un flush por volumen o por intervalo de tiempo."""
        time_elapsed = (now - self.last_flush_time) >= settings.engine_microbatch_interval_sec
        size_reached = len(self.trades_buffer) >= settings.engine_microbatch_size
        return (time_elapsed or size_reached) and (
            bool(self.trades_buffer) or bool(self.candles_buffer) or bool(self.whales_buffer)
        )

    async def flush(self) -> None:
        """Ejecuta la inserción en bloque de forma asíncrona mediante executor."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_flush)

    def _sync_flush(self) -> None:
        """Inserción síncrona en bloque ejecutada en worker thread."""
        if not self.client:
            return

        # 1. Flush de trades brutos
        if self.trades_buffer:
            trades_to_insert = self.trades_buffer
            self.trades_buffer = []
            try:
                self.client.insert(
                    "crypto_trades_raw",
                    trades_to_insert,
                    column_names=[
                        "timestamp",
                        "symbol",
                        "price",
                        "quantity",
                        "volume_usd",
                        "is_buyer_maker",
                        "trade_id",
                    ],
                )
                logger.debug(
                    "Micro-batch insertado: %d trades en ClickHouse.", len(trades_to_insert)
                )
            except Exception as exc:
                logger.error("Error insertando micro-batch en crypto_trades_raw: %s", exc)

        # 2. Flush de velas
        if self.candles_buffer:
            candles_to_insert = self.candles_buffer
            self.candles_buffer = []
            try:
                self.client.insert(
                    "crypto_candles_1m",
                    candles_to_insert,
                    column_names=[
                        "candle_time",
                        "symbol",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "volume_usd",
                        "vwap",
                        "trades_count",
                    ],
                )
                logger.info("Guardadas %d velas de 1m en ClickHouse.", len(candles_to_insert))
            except Exception as exc:
                logger.error("Error insertando velas en crypto_candles_1m: %s", exc)

        # 3. Flush de ballenas
        if self.whales_buffer:
            whales_to_insert = self.whales_buffer
            self.whales_buffer = []
            try:
                self.client.insert(
                    "crypto_whale_alerts",
                    whales_to_insert,
                    column_names=[
                        "timestamp",
                        "symbol",
                        "price",
                        "quantity",
                        "volume_usd",
                        "is_buyer_maker",
                        "trade_id",
                    ],
                )
                logger.warning(
                    "Guardadas %d transacciones ballena en ClickHouse.", len(whales_to_insert)
                )
            except Exception as exc:
                logger.error("Error insertando ballenas en crypto_whale_alerts: %s", exc)
