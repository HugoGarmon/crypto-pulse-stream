CREATE DATABASE IF NOT EXISTS crypto_intelligence;

-- -----------------------------------------------------------------------------
-- 1. Tabla de Ticks Brutos: crypto_trades_raw
-- Almacena cada transacción individual validada desde el streaming de Binance.
-- Motor MergeTree particionado por día para optimizar retención y compresión columnar.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crypto_intelligence.crypto_trades_raw (
    timestamp DateTime64(3, 'UTC') CODEC(DoubleDelta, ZSTD(1)),
    symbol LowCardinality(String) CODEC(ZSTD(1)),
    price Float64 CODEC(Gorilla, ZSTD(1)),
    quantity Float64 CODEC(Gorilla, ZSTD(1)),
    volume_usd Float64 CODEC(Gorilla, ZSTD(1)),
    is_buyer_maker UInt8 CODEC(ZSTD(1)),
    trade_id UInt64 CODEC(DoubleDelta, ZSTD(1))
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (symbol, timestamp, trade_id)
SETTINGS index_granularity = 8192;

-- -----------------------------------------------------------------------------
-- 2. Tabla de Velas de 1 Minuto: crypto_candles_1m
-- Guarda velas OHLCV precalculadas por el Stream Engine con VWAP y número de operaciones.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crypto_intelligence.crypto_candles_1m (
    candle_time DateTime('UTC') CODEC(DoubleDelta, ZSTD(1)),
    symbol LowCardinality(String) CODEC(ZSTD(1)),
    open Float64 CODEC(Gorilla, ZSTD(1)),
    high Float64 CODEC(Gorilla, ZSTD(1)),
    low Float64 CODEC(Gorilla, ZSTD(1)),
    close Float64 CODEC(Gorilla, ZSTD(1)),
    volume Float64 CODEC(Gorilla, ZSTD(1)),
    volume_usd Float64 CODEC(Gorilla, ZSTD(1)),
    vwap Float64 CODEC(Gorilla, ZSTD(1)),
    trades_count UInt32 CODEC(DoubleDelta, ZSTD(1))
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(candle_time)
ORDER BY (symbol, candle_time)
SETTINGS index_granularity = 8192;

-- -----------------------------------------------------------------------------
-- 3. Tabla de Alertas de Gran Volumen (Whales): crypto_whale_alerts
-- Histórico de transacciones institucionales detectadas por el pipeline.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crypto_intelligence.crypto_whale_alerts (
    timestamp DateTime64(3, 'UTC') CODEC(DoubleDelta, ZSTD(1)),
    symbol LowCardinality(String) CODEC(ZSTD(1)),
    price Float64 CODEC(Gorilla, ZSTD(1)),
    quantity Float64 CODEC(Gorilla, ZSTD(1)),
    volume_usd Float64 CODEC(Gorilla, ZSTD(1)),
    is_buyer_maker UInt8 CODEC(ZSTD(1)),
    trade_id UInt64 CODEC(DoubleDelta, ZSTD(1))
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (symbol, timestamp, trade_id)
SETTINGS index_granularity = 8192;
