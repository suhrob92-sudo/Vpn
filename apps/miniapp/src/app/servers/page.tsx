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

const FLAGS: Record<string, string> = { DE: "🇩🇪", NL: "🇳🇱", FI: "🇫🇮", US: "🇺🇸", TR: "🇹🇷" };
const STATUS: Record<string, { label: string; cls: string }> = {
  ONLINE: { label: "Onlayn", cls: "bg-success/15 text-success" },
  MAINTENANCE: { label: "Texnik ishlar", cls: "bg-warning/15 text-warning" },
  OFFLINE: { label: "O'chiq", cls: "bg-danger/15 text-danger" },
};

export default function Servers() {
  const [servers, setServers] = useState<Server[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiPublic<Server[]>("/servers").then(setServers).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold">🌍 Serverlar</h1>
      {error && <div className="card border-danger/40 text-danger text-sm">{error}</div>}
      {!servers && !error && (
        <>
          <div className="skeleton h-16" />
          <div className="skeleton h-16" />
        </>
      )}
      {servers?.length === 0 && <p className="text-muted text-sm">Serverlar hali qo'shilmagan.</p>}
      {servers?.map((s) => {
        const st = STATUS[s.status] ?? STATUS.OFFLINE;
        return (
          <div key={s.id} className="card flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{FLAGS[s.country] ?? "🌐"}</span>
              <div>
                <p className="font-medium">{s.country}{s.city ? `, ${s.city}` : ""}</p>
                <p className="text-xs text-muted">{s.name}</p>
              </div>
            </div>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${st.cls}`}>
              {st.label}
            </span>
          </div>
        );
      })}
      <p className="text-xs text-muted">
        Obunangiz barcha onlayn serverlarni o'z ichiga oladi — kliyent ilovasida istalganini tanlang.
      </p>
    </div>
  );
}
