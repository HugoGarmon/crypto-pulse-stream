from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProducerSettings(BaseSettings):
    """Configuración tipada del servicio de ingesta con variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kafka_bootstrap_servers: str = "localhost:19092"
    kafka_topic_raw_trades: str = "raw-crypto-trades"
    binance_ws_base_url: str = "wss://stream.binance.com:9443"
    tracked_symbols_raw: str = Field(
        default="btcusdt,ethusdt",
        validation_alias="TRACKED_SYMBOLS",
    )

    @property
    def tracked_symbols(self) -> list[str]:
        return [s.strip().lower() for s in self.tracked_symbols_raw.split(",") if s.strip()]

    @property
    def binance_combined_stream_url(self) -> str:
        base = self.binance_ws_base_url.rstrip("/")
        if base.endswith("/ws"):
            base = base[:-3]
        streams = "/".join(f"{s}@aggTrade" for s in self.tracked_symbols)
        return f"{base}/stream?streams={streams}"


settings = ProducerSettings()
