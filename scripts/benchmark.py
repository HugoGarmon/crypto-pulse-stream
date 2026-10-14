"""CryptoPulse Stream - Performance & Stress Benchmark Engine.

Mide el rendimiento, throughput de eventos y latencia del motor analítico
(StreamAggregator, cálculo de VWAP, detección de ballenas y serialización).

Uso:
    python scripts/benchmark.py --events 50000 --batch-size 1000
"""

import argparse
import random
import sys
import time
from pathlib import Path

# Agregar services/engine/src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "engine" / "src"))

import numpy as np
import orjson
from aggregator import StreamAggregator
from schemas import CryptoTrade


def generate_synthetic_trade(
    trade_id: int, base_time: int, symbol: str, price: float
) -> CryptoTrade:
    """Genera un evento de trade sintético ultrarrápido con micro-variaciones."""
    # Variación aleatoria (-0.1% a +0.1%)
    price_change = price * random.uniform(-0.001, 0.001)
    current_price = round(price + price_change, 2)
    qty = round(random.uniform(0.001, 3.5), 5)
    vol_usd = round(current_price * qty, 4)

    return CryptoTrade(
        symbol=symbol,
        price=current_price,
        quantity=qty,
        volume_usd=vol_usd,
        is_buyer_maker=random.choice([True, False]),
        trade_id=trade_id,
        timestamp=base_time + (trade_id * 5),  # 5ms entre trades
        received_at=base_time + (trade_id * 5) + random.randint(1, 15),
    )


def run_benchmark(total_events: int = 50_000, batch_size: int = 1_000) -> dict:
    print("\n" + "=" * 70)
    print("⚡ CryptoPulse Stream - Benchmark de Estrés y Rendimiento ⚡")
    print("=" * 70)
    print(f"[*] Generando {total_events:,} eventos sintéticos de mercado...")

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    base_prices = {"BTCUSDT": 85_000.0, "ETHUSDT": 3_200.0, "SOLUSDT": 180.0}
    base_time = int(time.time() * 1000)

    trades = [
        generate_synthetic_trade(
            trade_id=i + 1,
            base_time=base_time,
            symbol=random.choice(symbols),
            price=base_prices["BTCUSDT"],
        )
        for i in range(total_events)
    ]

    print(f"[✓] {len(trades):,} trades listos en memoria.")
    print("[*] Iniciando prueba de procesamiento en streaming (Engine + Agregador)...")

    aggregator = StreamAggregator(whale_threshold_usd=100_000.0)

    latencies_us = []
    completed_candles = 0
    whales_detected = 0

    # Simulación de buffer de micro-batching
    batch_buffer = []
    flushed_batches = 0

    start_total = time.perf_counter()

    for trade in trades:
        t0 = time.perf_counter()

        # 1. Agregación analítica en memoria (VWAP, Candles, Ticker)
        candle, whale, ticker = aggregator.process_trade(trade)

        # 2. Serialización JSON (orjson)
        _ = orjson.dumps(ticker.model_dump())

        # 3. Micro-batching acumulativo
        batch_buffer.append(trade)
        if len(batch_buffer) >= batch_size:
            # Simulación de formateo del lote
            _ = len(batch_buffer)
            batch_buffer.clear()
            flushed_batches += 1

        t1 = time.perf_counter()
        latencies_us.append((t1 - t0) * 1_000_000)  # Microsegundos

        if candle:
            completed_candles += 1
        if whale:
            whales_detected += 1

    total_time_sec = time.perf_counter() - start_total
    throughput = total_events / total_time_sec

    # Cálculo de métricas estadísticas
    latencies_arr = np.array(latencies_us)
    p50_us = np.percentile(latencies_arr, 50)
    p95_us = np.percentile(latencies_arr, 95)
    p99_us = np.percentile(latencies_arr, 99)
    avg_us = np.mean(latencies_arr)

    results = {
        "total_events": total_events,
        "total_time_sec": total_time_sec,
        "throughput_ops_sec": throughput,
        "avg_latency_us": avg_us,
        "p50_latency_us": p50_us,
        "p95_latency_us": p95_us,
        "p99_latency_us": p99_us,
        "completed_candles": completed_candles,
        "whales_detected": whales_detected,
        "flushed_batches": flushed_batches,
    }

    # Imprimir Reporte Profesional
    print("\n" + "-" * 70)
    print("📊 RESULTADOS DEL BENCHMARK")
    print("-" * 70)
    print(f"▸ Total de eventos procesados : {total_events:,}")
    print(f"▸ Tiempo total de ejecución   : {total_time_sec:.3f} s")
    print(f"▸ Throughput Sostenido        : {throughput:,.2f} eventos/segundo 🚀")
    print(f"▸ Latencia Media              : {avg_us:.2f} µs ({avg_us / 1000:.3f} ms)")
    print(f"▸ Latencia Mediana (p50)      : {p50_us:.2f} µs ({p50_us / 1000:.3f} ms)")
    print(f"▸ Latencia p95                : {p95_us:.2f} µs ({p95_us / 1000:.3f} ms)")
    print(f"▸ Latencia p99                : {p99_us:.2f} µs ({p99_us / 1000:.3f} ms)")
    print(f"▸ Velas OHLCV 1m Generadas    : {completed_candles:,}")
    print(f"▸ Alertas Institucionales     : {whales_detected:,}")
    print(f"▸ Micro-batches Formateados   : {flushed_batches:,}")
    print("=" * 70 + "\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CryptoPulse Stream Benchmark")
    parser.add_argument(
        "--events",
        type=int,
        default=50_000,
        help="Número total de eventos a simular (default: 50,000)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1_000,
        help="Tamaño de lote para simulación de micro-batching (default: 1,000)",
    )
    args = parser.parse_args()

    run_benchmark(total_events=args.events, batch_size=args.batch_size)
