import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Limpiar posibles colisiones de módulos de otros microservicios
for mod in ["schemas", "config", "aggregator", "storage"]:
    sys.modules.pop(mod, None)

gateway_src = str(Path(__file__).parent.parent / "services" / "gateway" / "src")
if gateway_src in sys.path:
    sys.path.remove(gateway_src)
sys.path.insert(0, gateway_src)

from broadcaster import worker
from db import db
from fastapi.testclient import TestClient
from main import app
from schemas import CandleResponse, SystemStatsResponse, WhaleResponse

# Mock del worker Kafka para pruebas unitarias de la API REST
worker.start = AsyncMock()  # type: ignore
worker.stop = AsyncMock()  # type: ignore


def test_health_check_endpoint() -> None:
    db.ping = MagicMock(return_value=True)  # type: ignore

    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["clickhouse"] is True
        assert "clickhouse_db" in data["details"]


def test_metrics_history_endpoint() -> None:
    mock_candles = [
        CandleResponse(
            time=1700000000,
            open=65000.0,
            high=65500.0,
            low=64900.0,
            close=65200.0,
            volume=10.5,
            volume_usd=684600.0,
            vwap=65200.0,
            trades_count=150,
        )
    ]
    db.get_candles = MagicMock(return_value=mock_candles)  # type: ignore

    with TestClient(app) as client:
        response = client.get("/api/v1/metrics/history?symbol=BTCUSDT&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["open"] == 65000.0
        assert data[0]["trades_count"] == 150


def test_whales_endpoint() -> None:
    mock_whales = [
        WhaleResponse(
            timestamp="2026-09-23 12:00:00.000",
            symbol="BTCUSDT",
            price=65000.0,
            quantity=5.0,
            volume_usd=325000.0,
            is_buyer_maker=False,
            trade_id=999,
        )
    ]
    db.get_whales = MagicMock(return_value=mock_whales)  # type: ignore

    with TestClient(app) as client:
        response = client.get("/api/v1/whales?symbol=BTCUSDT&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["volume_usd"] == 325000.0


def test_stats_endpoint() -> None:
    mock_stats = SystemStatsResponse(
        total_raw_trades=10000,
        total_candles_1m=50,
        total_whale_alerts=12,
        total_volume_usd=50000000.0,
        active_symbols=["BTCUSDT", "ETHUSDT"],
    )
    db.get_overview_stats = MagicMock(return_value=mock_stats)  # type: ignore

    with TestClient(app) as client:
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_raw_trades"] == 10000
        assert "BTCUSDT" in data["active_symbols"]
