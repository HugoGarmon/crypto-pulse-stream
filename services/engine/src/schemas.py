from typing import Any

from pydantic import BaseModel, Field


class CryptoTrade(BaseModel):
    """Evento normalizado de trade individual recibido desde raw-crypto-trades."""

    symbol: str
    price: float
    quantity: float
    volume_usd: float
    is_buyer_maker: bool
    trade_id: int
    timestamp: int
    received_at: int


class CandleData(BaseModel):
    """Vela OHLCV agregada por ventana temporal de 1 minuto."""

    candle_time: int = Field(description="Timestamp Unix en segundos del inicio de la vela")
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    volume_usd: float
    vwap: float
    trades_count: int


class WhaleAlert(BaseModel):
    """Alerta de trade institucional/ballena superior al umbral configurado."""

    timestamp: int
    symbol: str
    price: float
    quantity: float
    volume_usd: float
    is_buyer_maker: bool
    trade_id: int


class TickerUpdate(BaseModel):
    """Snapshot en tiempo real del ticker para alimentar dashboards a 60 FPS."""

    symbol: str
    price: float
    vwap_session: float
    volume_usd_session: float
    trades_count_session: int
    high_session: float
    low_session: float
    timestamp: int
    latency_ms: float


class ProcessedMetricMessage(BaseModel):
    """Envelope para publicar eventos en el topic processed-crypto-metrics."""

    event_type: str = Field(description="Tipo de evento: trade | candle | whale | ticker")
    symbol: str
    payload: dict[str, Any]
