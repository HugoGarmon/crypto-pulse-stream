from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineSettings(BaseSettings):
    """Configuración tipada del motor de procesamiento en streaming."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kafka_bootstrap_servers: str = "localhost:19092"
    kafka_topic_raw_trades: str = "raw-crypto-trades"
    kafka_topic_processed_metrics: str = "processed-crypto-metrics"
    kafka_consumer_group: str = "crypto-stream-engine-group"

    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_db: str = "crypto_intelligence"
    clickhouse_user: str = "default"
    clickhouse_password: str = "clickhouse123"

    engine_microbatch_size: int = 1000
    engine_microbatch_interval_sec: float = 2.0
    whale_threshold_usd: float = 100000.0

    tracked_symbols_raw: str = Field(
        default="btcusdt,ethusdt",
        validation_alias="TRACKED_SYMBOLS",
    )

    @property
    def tracked_symbols(self) -> list[str]:
        return [s.strip().upper() for s in self.tracked_symbols_raw.split(",") if s.strip()]


settings = EngineSettings()
