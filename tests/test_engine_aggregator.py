import sys
from pathlib import Path

# Agregar services/engine/src al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "engine" / "src"))

from aggregator import StreamAggregator, SymbolCandleBuilder
from schemas import CryptoTrade


def test_symbol_candle_builder() -> None:
    builder = SymbolCandleBuilder("BTCUSDT")

    # Trade en el minuto 0 (t = 10_000 ms)
    trade1 = CryptoTrade(
        symbol="BTCUSDT",
        price=60000.0,
        quantity=1.0,
        volume_usd=60000.0,
        is_buyer_maker=False,
        trade_id=1,
        timestamp=10000,
        received_at=10010,
    )
    res1 = builder.process_trade(trade1)
    assert res1 is None  # Aún no termina el minuto

    # Trade en el mismo minuto a precio más alto
    trade2 = CryptoTrade(
        symbol="BTCUSDT",
        price=61000.0,
        quantity=2.0,
        volume_usd=122000.0,
        is_buyer_maker=True,
        trade_id=2,
        timestamp=20000,
        received_at=20010,
    )
    res2 = builder.process_trade(trade2)
    assert res2 is None

    # Trade en el siguiente minuto (t = 65_000 ms -> minuto 60)
    trade3 = CryptoTrade(
        symbol="BTCUSDT",
        price=60500.0,
        quantity=0.5,
        volume_usd=30250.0,
        is_buyer_maker=False,
        trade_id=3,
        timestamp=65000,
        received_at=65010,
    )
    completed_candle = builder.process_trade(trade3)
    assert completed_candle is not None
    assert completed_candle.open == 60000.0
    assert completed_candle.high == 61000.0
    assert completed_candle.low == 60000.0
    assert completed_candle.close == 61000.0
    assert completed_candle.volume == 3.0
    assert completed_candle.volume_usd == 182000.0
    # VWAP = 182000 / 3 = 60666.6667
    assert abs(completed_candle.vwap - 60666.6667) < 0.01
    assert completed_candle.trades_count == 2


def test_whale_alert_detection() -> None:
    aggregator = StreamAggregator(whale_threshold_usd=100000.0)

    # Trade normal
    normal_trade = CryptoTrade(
        symbol="ETHUSDT",
        price=3000.0,
        quantity=5.0,
        volume_usd=15000.0,
        is_buyer_maker=False,
        trade_id=101,
        timestamp=1000,
        received_at=1010,
    )
    _, whale1, ticker1 = aggregator.process_trade(normal_trade)
    assert whale1 is None
    assert ticker1.price == 3000.0

    # Trade institucional / ballena (> $100,000)
    whale_trade = CryptoTrade(
        symbol="ETHUSDT",
        price=3100.0,
        quantity=50.0,
        volume_usd=155000.0,
        is_buyer_maker=True,
        trade_id=102,
        timestamp=2000,
        received_at=2010,
    )
    _, whale2, ticker2 = aggregator.process_trade(whale_trade)
    assert whale2 is not None
    assert whale2.volume_usd == 155000.0
    assert whale2.symbol == "ETHUSDT"
    assert ticker2.trades_count_session == 2
