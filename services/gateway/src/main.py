import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from broadcaster import manager, worker
from config import settings
from db import db
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from schemas import (
    CandleResponse,
    HealthCheckResponse,
    SystemStatsResponse,
    WhaleResponse,
)

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [GATEWAY] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("crypto_gateway")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ciclo de vida de la aplicación: inicialización y apagado limpio."""
    logger.info("Iniciando servicios del Gateway...")
    db.connect()
    await worker.start()
    yield
    logger.info("Deteniendo servicios del Gateway...")
    await worker.stop()


app = FastAPI(
    title="CryptoPulse Stream - API Gateway & WebSocket Hub",
    description="Backend analítico en tiempo real para criptoactivos con ClickHouse y Redpanda",
    version="1.0.0",
    lifespan=lifespan,
)

# Soporte CORS para clientes web (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check() -> HealthCheckResponse:
    """Verifica la conectividad con ClickHouse y el estado del broker Kafka/Redpanda."""
    ch_ok = db.ping()
    kafka_ok = worker.is_running and worker.consumer is not None
    overall_status = "healthy" if (ch_ok and kafka_ok) else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        clickhouse=ch_ok,
        kafka=kafka_ok,
        details={
            "clickhouse_db": settings.clickhouse_db,
            "kafka_bootstrap": settings.kafka_bootstrap_servers,
            "ws_active_symbols": list(manager.active_connections.keys()),
        },
    )


@app.get(
    "/api/v1/metrics/history",
    response_model=list[CandleResponse],
    tags=["Historical Analytics"],
)
async def get_metrics_history(
    symbol: str = Query(default="BTCUSDT", description="Par de trading (ej. BTCUSDT, ETHUSDT)"),
    limit: int = Query(
        default=100, ge=1, le=1000, description="Cantidad máxima de velas a retornar"
    ),
) -> list[CandleResponse]:
    """Retorna las últimas velas de 1 minuto precalculadas y ordenadas cronológicamente."""
    return db.get_candles(symbol=symbol, limit=limit)


@app.get(
    "/api/v1/whales",
    response_model=list[WhaleResponse],
    tags=["Whale Tracking"],
)
async def get_whale_alerts(
    symbol: str | None = Query(default=None, description="Filtrar por par de trading"),
    limit: int = Query(default=20, ge=1, le=100, description="Cantidad máxima de transacciones"),
) -> list[WhaleResponse]:
    """Retorna las transacciones institucionales más recientes detectadas por el pipeline."""
    return db.get_whales(symbol=symbol, limit=limit)


@app.get(
    "/api/v1/stats",
    response_model=SystemStatsResponse,
    tags=["System Stats"],
)
async def get_system_stats() -> SystemStatsResponse:
    """Retorna estadísticas agregadas de trades, volumen y velas en ClickHouse."""
    return db.get_overview_stats()


@app.websocket("/ws/live/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str) -> None:
    """Endpoint WebSocket bidireccional de baja latencia para streaming de ticks y velas."""
    norm_symbol = symbol.upper()
    await manager.connect(websocket, norm_symbol)
    try:
        while True:
            # Mantiene el socket abierto escuchando posibles pings del cliente
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, norm_symbol)
    except Exception as exc:
        logger.warning("Error en conexión WS para %s: %s", norm_symbol, exc)
        await manager.disconnect(websocket, norm_symbol)
