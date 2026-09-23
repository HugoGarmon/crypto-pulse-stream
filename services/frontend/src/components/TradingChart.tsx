"use client";

import React, { useEffect, useRef } from "react";
import {
  ColorType,
  CrosshairMode,
  ISeriesApi,
  UTCTimestamp,
  createChart,
} from "lightweight-charts";
import { CandleData } from "../types/crypto";

interface TradingChartProps {
  symbol: string;
  inFlightCandle: any;
  apiUrl: string;
}

export const TradingChart: React.FC<TradingChartProps> = ({
  symbol,
  inFlightCandle,
  apiUrl,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const vwapSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  // 1. Inicialización del gráfico
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const container = chartContainerRef.current;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: 480,
      layout: {
        background: { type: ColorType.Solid, color: "#090d16" },
        textColor: "#94a3b8",
        fontSize: 12,
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: "#1e293b",
        scaleMargins: {
          top: 0.1,
          bottom: 0.25,
        },
      },
      timeScale: {
        borderColor: "#1e293b",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Series de Velas OHLCV
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });
    candleSeriesRef.current = candleSeries;

    // Serie de VWAP
    const vwapSeries = chart.addLineSeries({
      color: "#3b82f6",
      lineWidth: 2,
      priceLineVisible: false,
      title: "VWAP",
    });
    vwapSeriesRef.current = vwapSeries;

    // Serie de Volumen (Histograma en la base)
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: {
        type: "volume",
      },
      priceScaleId: "", // escala overlay
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });
    volumeSeriesRef.current = volumeSeries;

    // Observador para diseño responsive
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length === 0 || !entries[0].contentRect) return;
      const { width, height } = entries[0].contentRect;
      chart.applyOptions({ width, height: height || 480 });
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      vwapSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []);

  // 2. Cargar histórico inicial desde FastAPI / ClickHouse cuando cambia el símbolo
  useEffect(() => {
    let isCancelled = false;

    const fetchHistory = async () => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/metrics/history?symbol=${symbol}&limit=120`);
        if (!res.ok) return;
        const data: CandleData[] = await res.json();
        if (isCancelled || !Array.isArray(data) || data.length === 0) return;

        const candleData: any[] = [];
        const vwapData: any[] = [];
        const volumeData: any[] = [];

        // Asegurar orden cronológico estricto sin duplicados
        const sorted = [...data].sort((a, b) => a.time - b.time);
        const seenTimes = new Set<number>();

        for (const c of sorted) {
          if (seenTimes.has(c.time)) continue;
          seenTimes.add(c.time);

          candleData.push({
            time: c.time as UTCTimestamp,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
          });

          if (c.vwap) {
            vwapData.push({
              time: c.time as UTCTimestamp,
              value: c.vwap,
            });
          }

          volumeData.push({
            time: c.time as UTCTimestamp,
            value: c.volume,
            color: c.close >= c.open ? "rgba(16, 185, 129, 0.35)" : "rgba(239, 68, 68, 0.35)",
          });
        }

        if (candleSeriesRef.current) candleSeriesRef.current.setData(candleData);
        if (vwapSeriesRef.current) vwapSeriesRef.current.setData(vwapData);
        if (volumeSeriesRef.current) volumeSeriesRef.current.setData(volumeData);
      } catch (err) {
        console.error("Error al cargar velas históricas:", err);
      }
    };

    fetchHistory();

    return () => {
      isCancelled = true;
    };
  }, [symbol, apiUrl]);

  // 3. Actualización de tick en tiempo real vía WebSocket
  useEffect(() => {
    if (!inFlightCandle || !candleSeriesRef.current) return;

    try {
      const candleTime = (inFlightCandle.candle_time || inFlightCandle.time) as UTCTimestamp;
      if (!candleTime) return;

      candleSeriesRef.current.update({
        time: candleTime,
        open: inFlightCandle.open,
        high: inFlightCandle.high,
        low: inFlightCandle.low,
        close: inFlightCandle.close,
      });

      if (vwapSeriesRef.current && inFlightCandle.vwap) {
        vwapSeriesRef.current.update({
          time: candleTime,
          value: inFlightCandle.vwap,
        });
      }

      if (volumeSeriesRef.current && inFlightCandle.volume) {
        volumeSeriesRef.current.update({
          time: candleTime,
          value: inFlightCandle.volume,
          color:
            inFlightCandle.close >= inFlightCandle.open
              ? "rgba(16, 185, 129, 0.45)"
              : "rgba(239, 68, 68, 0.45)",
        });
      }
    } catch {
      // Ignorar actualizaciones si la marca temporal es anterior al dataset
    }
  }, [inFlightCandle]);

  return (
    <div className="relative w-full h-[480px] bg-[#090d16] rounded-xl border border-surfaceBorder overflow-hidden shadow-2xl">
      <div className="absolute top-3 left-4 z-10 flex items-center gap-3 pointer-events-none">
        <span className="text-xs font-bold text-slate-300 font-mono tracking-wider bg-surface/80 px-2.5 py-1 rounded border border-surfaceBorder">
          {symbol} · 1m OHLCV + VWAP
        </span>
        <span className="text-xs font-semibold text-blue-400 font-mono flex items-center gap-1.5 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse"></span>
          Streaming 60 FPS
        </span>
      </div>
      <div ref={chartContainerRef} className="w-full h-full" />
    </div>
  );
};
