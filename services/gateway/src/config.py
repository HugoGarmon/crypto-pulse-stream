from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Configuración tipada del API Gateway y WebSocket Hub."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_db: str = "crypto_intelligence"
    clickhouse_user: str = "default"
    clickhouse_password: str = "clickhouse123"

    kafka_bootstrap_servers: str = "localhost:19092"
    kafka_topic_processed_metrics: str = "processed-crypto-metrics"
    kafka_consumer_group: str = "crypto-gateway-ws-group"


settings = GatewaySettings()
