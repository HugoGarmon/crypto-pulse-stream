"use client";

import React, { useEffect, useRef, useState } from "react";
import { Header } from "../components/Header";
import { TickerBar } from "../components/TickerBar";
import { TradingChart } from "../components/TradingChart";
import { WhaleFeed } from "../components/WhaleFeed";
import { TradeTape } from "../components/TradeTape";
import { TickerData, TradeEvent, WhaleAlert } from "../types/crypto";
import { Cpu, Database, Network } from "lucide-react";

export default function Dashboard() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>("BTCUSDT");
  const [ticker, setTicker] = useState<TickerData | null>(null);
  const [inFlightCandle, setInFlightCandle] = useState<any>(null);
  const [whales, setWhales] = useState<WhaleAlert[]>([]);
  const [trades, setTrades] = useState<TradeEvent[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [latencyMs, setLatencyMs] = useState<number>(0);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

  // WebSocket Connection Lifecycle
  useEffect(() => {
    let isCancelled = false;

    const connectWebSocket = () => {
      if (isCancelled) return;

      const wsEndpoint = `${wsBaseUrl}/ws/live/ALL`;
      console.log(`Conectando a WebSocket: ${wsEndpoint}`);
      const ws = new WebSocket(wsEndpoint);
      socketRef.current = ws;

      ws.onopen = () => {
        if (!isCancelled) {
          setIsConnected(true);
          console.log("WebSocket conectado al Gateway.");
        }
      };

      ws.onmessage = (event) => {
        if (isCancelled) return;
        try {
          const msg = JSON.parse(event.data);
          const { event_type, symbol, payload } = msg;

          if (event_type === "ticker") {
            if (symbol === selectedSymbol) {
              setTicker(payload);
              if (payload.latency_ms !== undefined) {
                setLatencyMs(payload.latency_ms);
              }
              if (payload.in_flight_candle) {
                setInFlightCandle(payload.in_flight_candle);
              }
            }
          } else if (event_type === "candle") {
            if (symbol === selectedSymbol) {
              setInFlightCandle(payload);
            }
          } else if (event_type === "whale") {
            setWhales((prev) => [payload, ...prev.slice(0, 25)]);
          } else if (event_type === "trade") {
            setTrades((prev) => [payload, ...prev.slice(0, 30)]);
          }
        } catch (err) {
          console.error("Error al procesar mensaje WebSocket:", err);
        }
      };

      ws.onclose = () => {
        if (!isCancelled) {
          setIsConnected(false);
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000);
        }
      };

      ws.onerror = (err) => {
        console.warn("WebSocket error:", err);
        ws.close();
      };
    };

    connectWebSocket();

    return () => {
      isCancelled = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [wsBaseUrl, selectedSymbol]);

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-slate-100">
      {/* 1. Header con estado y selector de pares */}
      <Header
        selectedSymbol={selectedSymbol}
        onSelectSymbol={(sym) => {
          setSelectedSymbol(sym);
          setTicker(null);
          setInFlightCandle(null);
        }}
        isConnected={isConnected}
        latencyMs={latencyMs}
      />

      {/* 2. Ticker superior con métricas clave */}
      <TickerBar ticker={ticker} selectedSymbol={selectedSymbol} />

      {/* 3. Área Principal: Gráficos interactivos y Feeds en tiempo real */}
      <main className="flex-1 p-4 max-w-[1700px] w-full mx-auto grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Columna Izquierda: Gráfico TradingView Lightweight Charts */}
        <section className="lg:col-span-2 flex flex-col gap-4">
          <TradingChart
            symbol={selectedSymbol}
            inFlightCandle={inFlightCandle}
            apiUrl={apiUrl}
          />

          {/* Banner de Arquitectura e Infraestructura */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-surface/40 border border-surfaceBorder flex items-center gap-3">
              <Network className="h-5 w-5 text-orange-400" />
              <div>
                <div className="text-xs font-bold text-slate-200">Redpanda C++ Broker</div>
                <div className="text-[11px] text-slate-400">Zero-JVM · Throughput masivo</div>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-surface/40 border border-surfaceBorder flex items-center gap-3">
              <Database className="h-5 w-5 text-amber-400" />
              <div>
                <div className="text-xs font-bold text-slate-200">ClickHouse OLAP</div>
                <div className="text-[11px] text-slate-400">Micro-batching columnar</div>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-surface/40 border border-surfaceBorder flex items-center gap-3">
              <Cpu className="h-5 w-5 text-blue-400" />
              <div>
                <div className="text-xs font-bold text-slate-200">Stream Engine</div>
                <div className="text-[11px] text-slate-400">VWAP & Ventanas en memoria</div>
              </div>
            </div>
          </div>
        </section>

        {/* Columna Derecha: Alertas de Ballenas y Tapes en vivo */}
        <section className="flex flex-col gap-4">
          <div className="flex-1 min-h-[300px]">
            <WhaleFeed whales={whales} apiUrl={apiUrl} />
          </div>
          <div className="flex-1 min-h-[250px]">
            <TradeTape trades={trades} selectedSymbol={selectedSymbol} />
          </div>
        </section>
      </main>

      {/* Footer minimalista */}
      <footer className="border-t border-surfaceBorder bg-surface/40 px-6 py-3 text-xs text-slate-500 font-mono flex items-center justify-between">
        <div>CryptoPulse Stream © 2026 · Pipeline de Inteligencia Financiera</div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
          <span>Docker Multi-Container Unificado</span>
        </div>
      </footer>
    </div>
  );
}
