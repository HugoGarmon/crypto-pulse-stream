"use client";

import React, { useEffect, useState } from "react";
import { WhaleAlert } from "../types/crypto";
import { ArrowDownLeft, ArrowUpRight, ShieldAlert } from "lucide-react";

interface WhaleFeedProps {
  whales: WhaleAlert[];
  apiUrl: string;
}

export const WhaleFeed: React.FC<WhaleFeedProps> = ({ whales: liveWhales, apiUrl }) => {
  const [whaleList, setWhaleList] = useState<WhaleAlert[]>([]);

  // Carga inicial de historial de ballenas
  useEffect(() => {
    let isCancelled = false;
    const fetchInitialWhales = async () => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/whales?limit=15`);
        if (!res.ok) return;
        const data = await res.json();
        if (!isCancelled && Array.isArray(data)) {
          setWhaleList(data);
        }
      } catch (err) {
        console.error("Error al cargar historial de ballenas:", err);
      }
    };
    fetchInitialWhales();
    return () => {
      isCancelled = true;
    };
  }, [apiUrl]);

  // Prepend de nuevas ballenas en vivo
  useEffect(() => {
    if (liveWhales.length === 0) return;
    setWhaleList((prev) => {
      const newItems = liveWhales.filter(
        (nw) => !prev.some((pw) => pw.trade_id === nw.trade_id)
      );
      return [...newItems, ...prev].slice(0, 30);
    });
  }, [liveWhales]);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(val);
  };

  const formatTime = (ts: string | number) => {
    try {
      const d = typeof ts === "number" ? new Date(ts) : new Date(ts);
      return d.toLocaleTimeString("es-ES", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return "--:--:--";
    }
  };

  return (
    <div className="bg-[#090d16] rounded-xl border border-surfaceBorder overflow-hidden flex flex-col h-full shadow-lg">
      <div className="px-4 py-3 border-b border-surfaceBorder bg-surface/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-amber-400 animate-pulse" />
          <h2 className="text-xs font-bold tracking-wider uppercase text-slate-200">
            Alertas Institucionales (Whales &gt; $100K)
          </h2>
        </div>
        <span className="text-[11px] font-mono text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
          {whaleList.length} Detectadas
        </span>
      </div>

      <div className="flex-1 overflow-y-auto divide-y divide-surfaceBorder/50 font-mono text-xs max-h-[380px]">
        {whaleList.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            Monitorizando el bus Kafka en busca de órdenes institucionales...
          </div>
        ) : (
          whaleList.map((w) => {
            const isBuy = !w.is_buyer_maker;
            return (
              <div
                key={`${w.trade_id}-${w.timestamp}`}
                className="px-4 py-2.5 flex items-center justify-between hover:bg-surface/40 transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <div
                    className={`h-7 w-7 rounded-md flex items-center justify-center ${
                      isBuy
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                    }`}
                  >
                    {isBuy ? (
                      <ArrowUpRight className="h-4 w-4" />
                    ) : (
                      <ArrowDownLeft className="h-4 w-4" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5 font-bold">
                      <span className={isBuy ? "text-emerald-400" : "text-rose-400"}>
                        {isBuy ? "COMPRA" : "VENTA"}
                      </span>
                      <span className="text-slate-300">{w.symbol}</span>
                    </div>
                    <span className="text-[10px] text-slate-500">
                      @ {w.price.toLocaleString("en-US", { minimumFractionDigits: 2 })} USD
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="font-bold text-slate-100">{formatCurrency(w.volume_usd)}</div>
                  <div className="text-[10px] text-slate-500">{formatTime(w.timestamp)}</div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
