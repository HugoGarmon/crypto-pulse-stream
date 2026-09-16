import time

from pydantic import BaseModel, Field


class BinanceAggTradeData(BaseModel):
    """Estructura interna del evento 'aggTrade' de Binance."""

    e: str = Field(description="Event type")
    E: int = Field(description="Event time in milliseconds")
    s: str = Field(description="Symbol")
    a: int = Field(description="Aggregate trade ID")
    p: str = Field(description="Price as string")
    q: str = Field(description="Quantity as string")
    f: int = Field(description="First trade ID")
    l: int = Field(description="Last trade ID")  # noqa: E741
    T: int = Field(description="Trade time in milliseconds")
    m: bool = Field(description="Is buyer maker")
    M: bool = Field(description="Ignore")


class BinanceCombinedStreamMessage(BaseModel):
    """Payload de wrapper cuando se usa stream combinado /stream?streams=..."""

    stream: str
    data: BinanceAggTradeData


class CryptoTrade(BaseModel):
    """Modelo normalizado y validado enviado al broker Redpanda."""

    symbol: str
    price: float
    quantity: float
    volume_usd: float
    is_buyer_maker: bool
    trade_id: int
    timestamp: int
    received_at: int

    @classmethod
    def from_binance_agg_trade(cls, raw: BinanceAggTradeData) -> "CryptoTrade":
        price = float(raw.p)
        quantity = float(raw.q)
        return cls(
            symbol=raw.s.upper(),
            price=price,
            quantity=quantity,
            volume_usd=round(price * quantity, 4),
            is_buyer_maker=raw.m,
            trade_id=raw.a,
            timestamp=raw.T,
            received_at=int(time.time() * 1000),
        )
