"use client";

import { useEffect, useState } from "react";
import { apiPublic } from "@/lib/api";

interface Server {
  id: number;
  name: string;
  country: string;
  city: string | null;
  status: "ONLINE" | "MAINTENANCE" | "OFFLINE";
}

const FLAGS: Record<string, string> = {
  DE: "🇩🇪", NL: "🇳🇱", FI: "🇫🇮", US: "🇺🇸", TR: "🇹🇷", AT: "🇦🇹", SE: "🇸🇪", GB: "🇬🇧", FR: "🇫🇷", PL: "🇵🇱",
};
const STATUS: Record<string, { label: string; cls: string; dot: string }> = {
  ONLINE: { label: "Onlayn", cls: "text-accent bg-accent/10", dot: "bg-accent shadow-glow-accent" },
  MAINTENANCE: { label: "Texnik ishlar", cls: "text-warning bg-warning/10", dot: "bg-warning" },
  OFFLINE: { label: "O'chiq", cls: "text-danger bg-danger/10", dot: "bg-danger" },
};

export default function Servers() {
  const [servers, setServers] = useState<Server[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiPublic<Server[]>("/servers").then(setServers).catch((e) => setError(e.message));
  }, []);

  const online = servers?.filter((s) => s.status === "ONLINE").length ?? 0;

  return (
    <div className="flex flex-col gap-4 animate-fade-up">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Serverlar</h1>
          <p className="text-sm text-muted mt-1">Global tezkor tarmoq</p>
        </div>
        {servers && (
          <span className="chip text-accent bg-accent/10 flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-glow-accent" />
            {online} onlayn
          </span>
        )}
      </div>

      {error && <div className="glass !border-danger/40 text-danger text-sm p-4">{error}</div>}
      {!servers && !error && (
        <>
          <div className="skeleton h-[68px]" />
          <div className="skeleton h-[68px]" />
        </>
      )}
      {servers?.length === 0 && <p className="text-muted text-sm">Serverlar hali qo'shilmagan.</p>}

      {servers?.map((s, i) => {
        const st = STATUS[s.status] ?? STATUS.OFFLINE;
        return (
          <div
            key={s.id}
            style={{ animationDelay: `${i * 50}ms` }}
            className="glass p-4 flex items-center justify-between animate-fade-up"
          >
            <div className="flex items-center gap-3">
              <span className="h-11 w-11 rounded-2xl bg-white/[0.05] flex items-center justify-center text-2xl">
                {FLAGS[s.country] ?? "🌐"}
              </span>
              <div>
                <p className="font-semibold">
                  {s.country}
                  {s.city ? ` · ${s.city}` : ""}
                </p>
                <p className="text-xs text-muted">{s.name}</p>
              </div>
            </div>
            <span className={`chip flex items-center gap-1.5 ${st.cls}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`} />
              {st.label}
            </span>
          </div>
        );
      })}

      <p className="text-xs text-muted text-center px-4 mt-2">
        Obunangiz barcha onlayn serverlarni o'z ichiga oladi — ilovada istalganini tanlang.
      </p>
    </div>
  );
}
