export interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  volume_usd?: number;
  vwap?: number;
  trades_count?: number;
}

export interface WhaleAlert {
  timestamp: string | number;
  symbol: string;
  price: number;
  quantity: number;
  volume_usd: number;
  is_buyer_maker: boolean;
  trade_id: number;
}

export interface TickerData {
  symbol: string;
  price: number;
  vwap_session: number;
  volume_usd_session: number;
  trades_count_session: number;
  high_session: number;
  low_session: number;
  timestamp: number;
  latency_ms: number;
  in_flight_candle?: CandleData | null;
}

export interface TradeEvent {
  symbol: string;
  price: number;
  quantity: number;
  volume_usd: number;
  is_buyer_maker: boolean;
  trade_id: number;
  timestamp: number;
  received_at?: number;
}

export interface WebSocketMessage {
  event_type: "ticker" | "candle" | "whale" | "trade";
  symbol: string;
  payload: any;
}
