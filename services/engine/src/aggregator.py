import time
from collections import defaultdict
from typing import Any

from schemas import CandleData, CryptoTrade, TickerUpdate, WhaleAlert


class SymbolCandleBuilder:
    """Acumula ticks en memoria para construir velas OHLCV de 1 minuto."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.current_window_sec: int | None = None
        self.open: float = 0.0
        self.high: float = 0.0
        self.low: float = 0.0
        self.close: float = 0.0
        self.volume: float = 0.0
        self.volume_usd: float = 0.0
        self.trades_count: int = 0

    def process_trade(self, trade: CryptoTrade) -> CandleData | None:
        """Procesa un trade. Si pertenece a una nueva ventana de 1m, retorna la vela completada."""
        # Timestamp de la vela en segundos (truncado al inicio del minuto)
        trade_sec = trade.timestamp // 1000
        window_sec = (trade_sec // 60) * 60

        completed_candle: CandleData | None = None

        if self.current_window_sec is None:
            self._start_new_window(window_sec, trade)
        elif window_sec > self.current_window_sec:
            # Ventana anterior completada
            completed_candle = self._build_candle()
            self._start_new_window(window_sec, trade)
        else:
            # Actualizar ventana en curso
            self._update_window(trade)

        return completed_candle

    def _start_new_window(self, window_sec: int, trade: CryptoTrade) -> None:
        self.current_window_sec = window_sec
        self.open = trade.price
        self.high = trade.price
        self.low = trade.price
        self.close = trade.price
        self.volume = trade.quantity
        self.volume_usd = trade.volume_usd
        self.trades_count = 1

    def _update_window(self, trade: CryptoTrade) -> None:
        if trade.price > self.high:
            self.high = trade.price
        if trade.price < self.low:
            self.low = trade.price
        self.close = trade.price
        self.volume += trade.quantity
        self.volume_usd += trade.volume_usd
        self.trades_count += 1

    def _build_candle(self) -> CandleData:
        vwap = round(self.volume_usd / self.volume, 4) if self.volume > 0 else self.close
        return CandleData(
            candle_time=self.current_window_sec or 0,
            symbol=self.symbol,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=round(self.volume, 6),
            volume_usd=round(self.volume_usd, 2),
            vwap=vwap,
            trades_count=self.trades_count,
        )

    def get_current_candle_snapshot(self) -> dict[str, Any] | None:
        """Obtiene un snapshot de la vela que se está formando actualmente."""
        if self.current_window_sec is None:
            return None
        vwap = round(self.volume_usd / self.volume, 4) if self.volume > 0 else self.close
        return {
            "candle_time": self.current_window_sec,
            "symbol": self.symbol,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": round(self.volume, 6),
            "volume_usd": round(self.volume_usd, 2),
            "vwap": vwap,
            "trades_count": self.trades_count,
        }


class StreamAggregator:
    """Orquesta las agregaciones en streaming para todos los símbolos monitoreados."""

    def __init__(self, whale_threshold_usd: float = 100000.0) -> None:
        self.whale_threshold_usd = whale_threshold_usd
        self.candle_builders: dict[str, SymbolCandleBuilder] = defaultdict(
            lambda: SymbolCandleBuilder("")
        )
        # Métricas de sesión en memoria
        self.session_volume_usd: dict[str, float] = defaultdict(float)
        self.session_volume_base: dict[str, float] = defaultdict(float)
        self.session_trades: dict[str, int] = defaultdict(int)
        self.session_high: dict[str, float] = defaultdict(lambda: 0.0)
        self.session_low: dict[str, float] = defaultdict(lambda: float("inf"))

    def _get_builder(self, symbol: str) -> SymbolCandleBuilder:
        if symbol not in self.candle_builders:
            self.candle_builders[symbol] = SymbolCandleBuilder(symbol)
        return self.candle_builders[symbol]

    def process_trade(
        self, trade: CryptoTrade
    ) -> tuple[CandleData | None, WhaleAlert | None, TickerUpdate]:
        """Procesa un trade y retorna la tupla:
        (vela_completada_si_aplica, alerta_ballena_si_aplica, ticker_update).
        """
        symbol = trade.symbol

        # 1. Actualizar métricas de sesión
        self.session_volume_usd[symbol] += trade.volume_usd
        self.session_volume_base[symbol] += trade.quantity
        self.session_trades[symbol] += 1
        if trade.price > self.session_high[symbol]:
            self.session_high[symbol] = trade.price
        if trade.price < self.session_low[symbol]:
            self.session_low[symbol] = trade.price

        session_vwap = (
            round(self.session_volume_usd[symbol] / self.session_volume_base[symbol], 4)
            if self.session_volume_base[symbol] > 0
            else trade.price
        )

        # 2. Detección de transacción ballena
        whale_alert: WhaleAlert | None = None
        if trade.volume_usd >= self.whale_threshold_usd:
            whale_alert = WhaleAlert(
                timestamp=trade.timestamp,
                symbol=symbol,
                price=trade.price,
                quantity=trade.quantity,
                volume_usd=trade.volume_usd,
                is_buyer_maker=trade.is_buyer_maker,
                trade_id=trade.trade_id,
            )

        # 3. Construcción de velas de 1m
        builder = self._get_builder(symbol)
        completed_candle = builder.process_trade(trade)

        # 4. Cálculo de ticker en tiempo real y latencia
        now_ms = int(time.time() * 1000)
        latency_ms = max(0.0, float(now_ms - trade.timestamp))

        low_val = (
            self.session_low[symbol]
            if self.session_low[symbol] != float("inf")
            else trade.price
        )

        ticker_update = TickerUpdate(
            symbol=symbol,
            price=trade.price,
            vwap_session=session_vwap,
            volume_usd_session=round(self.session_volume_usd[symbol], 2),
            trades_count_session=self.session_trades[symbol],
            high_session=self.session_high[symbol],
            low_session=low_val,
            timestamp=trade.timestamp,
            latency_ms=latency_ms,
        )

        return completed_candle, whale_alert, ticker_update

    def get_in_flight_candle(self, symbol: str) -> dict[str, Any] | None:
        if symbol in self.candle_builders:
            return self.candle_builders[symbol].get_current_candle_snapshot()
        return None
