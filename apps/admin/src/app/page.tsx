"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { adminFetch } from "@/lib/api";

interface Dashboard {
  total_users: number;
  new_users_24h: number;
  active_subscriptions: number;
  expired_subscriptions: number;
  revenue_24h: string;
  revenue_30d: string;
  servers: { id: number; name: string; country: string; status: string }[];
}

const statusBadge: Record<string, string> = {
  ONLINE: "badge-green",
  MAINTENANCE: "badge-yellow",
  OFFLINE: "badge-red",
};

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminFetch<Dashboard>("/admin/dashboard").then(setData).catch((e) => setError(e.message));
  }, []);

  const stats = data
    ? [
        { label: "Total users", value: data.total_users },
        { label: "New (24h)", value: data.new_users_24h },
        { label: "Active subs", value: data.active_subscriptions },
        { label: "Expired subs", value: data.expired_subscriptions },
        { label: "Revenue 24h", value: `${data.revenue_24h} USDT` },
        { label: "Revenue 30d", value: `${data.revenue_30d} USDT` },
      ]
    : [];

  return (
    <Shell>
      <h2 className="text-lg font-semibold mb-4">Dashboard</h2>
      {error && <p className="text-danger text-sm mb-4">{error}</p>}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        {stats.map((s) => (
          <div key={s.label} className="card">
            <p className="text-muted text-xs">{s.label}</p>
            <p className="text-xl font-bold mt-1">{s.value}</p>
          </div>
        ))}
      </div>
      {data && (
        <div className="card">
          <h3 className="font-semibold mb-3">Servers</h3>
          <div className="flex flex-col gap-2">
            {data.servers.length === 0 && <p className="text-muted text-sm">No servers yet.</p>}
            {data.servers.map((s) => (
              <div key={s.id} className="flex items-center justify-between text-sm">
                <span>
                  {s.country} — {s.name}
                </span>
                <span className={`badge ${statusBadge[s.status] ?? "badge-gray"}`}>{s.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Shell>
  );
}
