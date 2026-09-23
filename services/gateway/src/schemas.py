from typing import Any

from pydantic import BaseModel, Field


class CandleResponse(BaseModel):
    """Vela OHLCV histórica formateada para gráficos financieros."""

    time: int = Field(description="Timestamp Unix en segundos")
    open: float
    high: float
    low: float
    close: float
    volume: float
    volume_usd: float
    vwap: float
    trades_count: int


class WhaleResponse(BaseModel):
    """Registro histórico de transacción ballena."""

    timestamp: str
    symbol: str
    price: float
    quantity: float
    volume_usd: float
    is_buyer_maker: bool
    trade_id: int


class SystemStatsResponse(BaseModel):
    """Estadísticas agregadas del pipeline y almacenamiento OLAP."""

    total_raw_trades: int
    total_candles_1m: int
    total_whale_alerts: int
    total_volume_usd: float
    active_symbols: list[str]


class HealthCheckResponse(BaseModel):
    """Estado de salud de servicios dependientes."""

    status: str
    clickhouse: bool
    kafka: bool
    details: dict[str, Any]
