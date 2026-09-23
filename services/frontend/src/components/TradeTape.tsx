"use client";

import React from "react";
import { TradeEvent } from "../types/crypto";
import { Gauge } from "lucide-react";

interface TradeTapeProps {
  trades: TradeEvent[];
  selectedSymbol: string;
}

export const TradeTape: React.FC<TradeTapeProps> = ({ trades, selectedSymbol }) => {
  const filteredTrades = trades.filter((t) => t.symbol === selectedSymbol).slice(0, 30);

  return (
    <div className="bg-[#090d16] rounded-xl border border-surfaceBorder overflow-hidden flex flex-col h-full shadow-lg">
      <div className="px-4 py-3 border-b border-surfaceBorder bg-surface/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Gauge className="h-4 w-4 text-blue-400" />
          <h2 className="text-xs font-bold tracking-wider uppercase text-slate-200">
            Live Trades Tape ({selectedSymbol})
          </h2>
        </div>
        <span className="text-[11px] font-mono text-slate-400">Ticks directos</span>
      </div>

      <div className="flex-1 overflow-y-auto font-mono text-xs max-h-[380px] divide-y divide-surfaceBorder/30">
        {filteredTrades.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            Esperando stream de transacciones...
          </div>
        ) : (
          filteredTrades.map((t) => {
            const isBuy = !t.is_buyer_maker;
            const timeStr = new Date(t.timestamp).toLocaleTimeString("es-ES", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            });

            return (
              <div
                key={`${t.trade_id}-${t.timestamp}`}
                className="px-4 py-1.5 flex items-center justify-between hover:bg-surface/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-slate-500">{timeStr}</span>
                  <span
                    className={`font-semibold ${
                      isBuy ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {t.price.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-right">
                  <span className="text-slate-400">{t.quantity.toFixed(4)}</span>
                  <span className="text-slate-200 font-semibold w-20 text-right">
                    ${t.volume_usd.toLocaleString("en-US", { maximumFractionDigits: 0 })}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
