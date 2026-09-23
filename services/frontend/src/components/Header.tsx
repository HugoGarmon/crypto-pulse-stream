"use client";

import React from "react";
import { Activity, Radio, Wifi, WifiOff } from "lucide-react";

interface HeaderProps {
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  isConnected: boolean;
  latencyMs: number;
}

export const Header: React.FC<HeaderProps> = ({
  selectedSymbol,
  onSelectSymbol,
  isConnected,
  latencyMs,
}) => {
  const symbols = ["BTCUSDT", "ETHUSDT"];

  return (
    <header className="border-b border-surfaceBorder bg-surface/80 backdrop-blur-md px-6 py-3 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
      {/* Brand & Title */}
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
          <Activity className="h-5 w-5 animate-pulse text-blue-400" />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            CryptoPulse <span className="text-blue-500 text-sm font-semibold tracking-wider uppercase bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">Stream</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono">
            Event-Driven OLAP & Real-Time Engine
          </p>
        </div>
      </div>

      {/* Symbol Tabs */}
      <div className="flex items-center bg-[#090d16] p-1 rounded-lg border border-surfaceBorder">
        {symbols.map((sym) => {
          const isActive = selectedSymbol.toUpperCase() === sym;
          const displayLabel = sym.replace("USDT", " / USDT");
          return (
            <button
              key={sym}
              onClick={() => onSelectSymbol(sym)}
              className={`px-4 py-1.5 rounded-md text-xs font-semibold tracking-wide transition-all ${
                isActive
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-surface"
              }`}
            >
              {displayLabel}
            </button>
          );
        })}
      </div>

      {/* Connection Status & Latency */}
      <div className="flex items-center gap-4 text-xs font-mono">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#090d16] border border-surfaceBorder">
          <Radio className="h-3.5 w-3.5 text-blue-400 animate-pulse" />
          <span className="text-slate-400">Latencia:</span>
          <span className={`font-bold ${latencyMs < 50 ? "text-emerald-400" : latencyMs < 150 ? "text-amber-400" : "text-rose-400"}`}>
            {latencyMs.toFixed(1)} ms
          </span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#090d16] border border-surfaceBorder">
          {isConnected ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <Wifi className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-medium">EN VIVO</span>
            </>
          ) : (
            <>
              <WifiOff className="h-3.5 w-3.5 text-rose-400" />
              <span className="text-rose-400 font-medium">RECONECTANDO...</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
