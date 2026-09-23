"use client";

import React, { useEffect, useRef, useState } from "react";
import { TickerData } from "../types/crypto";
import { ArrowDownRight, ArrowUpRight, BarChart3, DollarSign, Layers } from "lucide-react";

interface TickerBarProps {
  ticker: TickerData | null;
  selectedSymbol: string;
}

export const TickerBar: React.FC<TickerBarProps> = ({ ticker, selectedSymbol }) => {
  const [flashColor, setFlashColor] = useState<"up" | "down" | null>(null);
  const prevPriceRef = useRef<number | null>(null);

  useEffect(() => {
    if (!ticker) return;
    if (prevPriceRef.current !== null) {
      if (ticker.price > prevPriceRef.current) {
        setFlashColor("up");
      } else if (ticker.price < prevPriceRef.current) {
        setFlashColor("down");
      }
      const timer = setTimeout(() => setFlashColor(null), 400);
      return () => clearTimeout(timer);
    }
    prevPriceRef.current = ticker.price;
  }, [ticker?.price]);

  const price = ticker?.price ?? 0;
  const vwap = ticker?.vwap_session ?? 0;
  const volumeUsd = ticker?.volume_usd_session ?? 0;
  const tradesCount = ticker?.trades_count_session ?? 0;
  const high = ticker?.high_session ?? 0;
  const low = ticker?.low_session ?? 0;

  const isAboveVwap = price >= vwap;
  const vwapDiffPct = vwap > 0 ? ((price - vwap) / vwap) * 100 : 0;

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: val < 10 ? 4 : 2,
      maximumFractionDigits: val < 10 ? 4 : 2,
    }).format(val);
  };

  const formatLargeNumber = (num: number) => {
    if (num >= 1_000_000_000) return `$${(num / 1_000_000_000).toFixed(2)}B`;
    if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(2)}M`;
    if (num >= 1_000) return `$${(num / 1_000).toFixed(1)}K`;
    return `$${num.toFixed(0)}`;
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 p-4 bg-surface/50 border-b border-surfaceBorder text-slate-200">
      {/* 1. Precio Actual con Flash */}
      <div className="flex flex-col justify-center px-4 py-2 rounded-lg bg-[#090d16] border border-surfaceBorder">
        <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">
          Precio Actual ({selectedSymbol})
        </span>
        <div className="flex items-center gap-2 mt-1">
          <span
            className={`text-2xl font-bold font-mono transition-colors duration-200 ${
              flashColor === "up"
                ? "text-emerald-400"
                : flashColor === "down"
                ? "text-rose-400"
                : "text-white"
            }`}
          >
            {price > 0 ? formatCurrency(price) : "---"}
          </span>
          {price > 0 && (
            flashColor === "up" ? (
              <ArrowUpRight className="h-5 w-5 text-emerald-400" />
            ) : flashColor === "down" ? (
              <ArrowDownRight className="h-5 w-5 text-rose-400" />
            ) : null
          )}
        </div>
      </div>

      {/* 2. VWAP de Sesión */}
      <div className="flex flex-col justify-center px-4 py-2 rounded-lg bg-[#090d16] border border-surfaceBorder">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">
            VWAP Sesión (OLAP)
          </span>
          <span
            className={`text-[10px] font-bold px-1.5 py-0.5 rounded font-mono ${
              isAboveVwap
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
            }`}
          >
            {vwapDiffPct >= 0 ? `+${vwapDiffPct.toFixed(2)}%` : `${vwapDiffPct.toFixed(2)}%`}
          </span>
        </div>
        <span className="text-lg font-bold font-mono text-blue-400 mt-1">
          {vwap > 0 ? formatCurrency(vwap) : "---"}
        </span>
      </div>

      {/* 3. Volumen Acumulado USD */}
      <div className="flex flex-col justify-center px-4 py-2 rounded-lg bg-[#090d16] border border-surfaceBorder">
        <span className="text-xs text-slate-400 font-medium uppercase tracking-wider flex items-center gap-1">
          <DollarSign className="h-3.5 w-3.5 text-slate-500" />
          Volumen Sesión (USD)
        </span>
        <span className="text-lg font-bold font-mono text-slate-100 mt-1">
          {formatLargeNumber(volumeUsd)}
        </span>
      </div>

      {/* 4. Rango de Precios (High / Low) */}
      <div className="flex flex-col justify-center px-4 py-2 rounded-lg bg-[#090d16] border border-surfaceBorder">
        <span className="text-xs text-slate-400 font-medium uppercase tracking-wider flex items-center gap-1">
          <BarChart3 className="h-3.5 w-3.5 text-slate-500" />
          High / Low
        </span>
        <div className="flex items-center gap-2 mt-1 text-xs font-mono">
          <span className="text-emerald-400 font-semibold">{high > 0 ? high.toFixed(2) : "---"}</span>
          <span className="text-slate-600">/</span>
          <span className="text-rose-400 font-semibold">{low > 0 ? low.toFixed(2) : "---"}</span>
        </div>
      </div>

      {/* 5. Transacciones Totales */}
      <div className="flex flex-col justify-center px-4 py-2 rounded-lg bg-[#090d16] border border-surfaceBorder col-span-2 md:col-span-1">
        <span className="text-xs text-slate-400 font-medium uppercase tracking-wider flex items-center gap-1">
          <Layers className="h-3.5 w-3.5 text-slate-500" />
          Trades Procesados
        </span>
        <span className="text-lg font-bold font-mono text-purple-400 mt-1">
          {tradesCount.toLocaleString()}
        </span>
      </div>
    </div>
  );
};
