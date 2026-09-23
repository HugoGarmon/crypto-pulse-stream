import logging
from typing import Any

import clickhouse_connect
from config import settings
from schemas import CandleResponse, SystemStatsResponse, WhaleResponse

logger = logging.getLogger("crypto_gateway_db")


class ClickHouseGatewayDB:
    """Cliente para consultas analíticas ultra-rápidas a ClickHouse."""

    def __init__(self) -> None:
        self.client: Any = None

    def connect(self) -> None:
        try:
            self.client = clickhouse_connect.get_client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                database=settings.clickhouse_db,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password,
                connect_timeout=5,
                send_receive_timeout=10,
            )
            logger.info("Gateway conectado exitosamente a ClickHouse.")
        except Exception as exc:
            logger.warning("No se pudo conectar a ClickHouse en inicio: %s", exc)
            self.client = None

    def ping(self) -> bool:
        if not self.client:
            try:
                self.connect()
            except Exception:
                return False
        if not self.client:
            return False
        try:
            res = self.client.command("SELECT 1")
            return res == 1
        except Exception:
            return False

    def get_candles(self, symbol: str, limit: int = 100) -> list[CandleResponse]:
        """Obtiene las últimas velas OHLCV ordenadas cronológicamente para TradingView."""
        if not self.client:
            self.connect()
        if not self.client:
            return []

        query = """
            SELECT
                toUnixTimestamp(candle_time) AS time,
                open,
                high,
                low,
                close,
                volume,
                volume_usd,
                vwap,
                trades_count
            FROM crypto_candles_1m
            WHERE symbol = %(symbol)s
            ORDER BY candle_time DESC
            LIMIT %(limit)s
        """
        result = self.client.query(query, parameters={"symbol": symbol.upper(), "limit": limit})
        rows = result.result_rows

        # Invertir para orden ascendente cronológico requerido por TradingView
        candles: list[CandleResponse] = []
        for r in reversed(rows):
            candles.append(
                CandleResponse(
                    time=int(r[0]),
                    open=float(r[1]),
                    high=float(r[2]),
                    low=float(r[3]),
                    close=float(r[4]),
                    volume=float(r[5]),
                    volume_usd=float(r[6]),
                    vwap=float(r[7]),
                    trades_count=int(r[8]),
                )
            )
        return candles

    def get_whales(self, symbol: str | None = None, limit: int = 20) -> list[WhaleResponse]:
        """Obtiene las últimas transacciones institucionales detectadas."""
        if not self.client:
            self.connect()
        if not self.client:
            return []

        if symbol:
            query = """
                SELECT
                    toString(timestamp),
                    symbol,
                    price,
                    quantity,
                    volume_usd,
                    is_buyer_maker,
                    trade_id
                FROM crypto_whale_alerts
                WHERE symbol = %(symbol)s
                ORDER BY timestamp DESC
                LIMIT %(limit)s
            """
            params: dict[str, Any] = {"symbol": symbol.upper(), "limit": limit}
        else:
            query = """
                SELECT
                    toString(timestamp),
                    symbol,
                    price,
                    quantity,
                    volume_usd,
                    is_buyer_maker,
                    trade_id
                FROM crypto_whale_alerts
                ORDER BY timestamp DESC
                LIMIT %(limit)s
            """
            params = {"limit": limit}

        result = self.client.query(query, parameters=params)
        return [
            WhaleResponse(
                timestamp=str(r[0]),
                symbol=str(r[1]),
                price=float(r[2]),
                quantity=float(r[3]),
                volume_usd=float(r[4]),
                is_buyer_maker=bool(r[5]),
                trade_id=int(r[6]),
            )
            for r in result.result_rows
        ]

    def get_overview_stats(self) -> SystemStatsResponse:
        """Obtiene métricas agregadas del data warehouse."""
        if not self.client:
            self.connect()
        if not self.client:
            return SystemStatsResponse(
                total_raw_trades=0,
                total_candles_1m=0,
                total_whale_alerts=0,
                total_volume_usd=0.0,
                active_symbols=[],
            )

        try:
            trades_cnt = self.client.command("SELECT count() FROM crypto_trades_raw")
            candles_cnt = self.client.command("SELECT count() FROM crypto_candles_1m")
            whales_cnt = self.client.command("SELECT count() FROM crypto_whale_alerts")
            vol_sum = self.client.command(
                "SELECT coalesce(sum(volume_usd), 0.0) FROM crypto_trades_raw"
            )
            symbols_res = self.client.query(
                "SELECT distinct symbol FROM crypto_trades_raw"
            ).result_rows
            symbols = [str(r[0]) for r in symbols_res]

            return SystemStatsResponse(
                total_raw_trades=int(trades_cnt),
                total_candles_1m=int(candles_cnt),
                total_whale_alerts=int(whales_cnt),
                total_volume_usd=round(float(vol_sum), 2),
                active_symbols=symbols,
            )
        except Exception as exc:
            logger.error("Error obteniendo estadísticas: %s", exc)
            return SystemStatsResponse(
                total_raw_trades=0,
                total_candles_1m=0,
                total_whale_alerts=0,
                total_volume_usd=0.0,
                active_symbols=[],
            )


db = ClickHouseGatewayDB()
