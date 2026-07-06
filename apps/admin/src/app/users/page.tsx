"use client";

import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { adminFetch } from "@/lib/api";

interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  status: string;
  created_at: string;
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(() => {
    const params = q ? `?q=${encodeURIComponent(q)}` : "";
    adminFetch<User[]>(`/admin/users${params}`).then(setUsers).catch((e) => setError(e.message));
  }, [q]);

  useEffect(() => {
    load();
  }, [load]);

  async function action(user: User, body: object) {
    setBusy(user.id);
    setError(null);
    try {
      await adminFetch(`/admin/users/${user.id}`, { method: "PATCH", body: JSON.stringify(body) });
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  async function revoke(user: User) {
    if (!confirm(`Revoke all VPN access for user #${user.id}?`)) return;
    setBusy(user.id);
    try {
      await adminFetch(`/admin/users/${user.id}/revoke-access`, { method: "POST" });
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <Shell>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Users</h2>
        <input
          className="input max-w-xs"
          placeholder="Search username / telegram id"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>
      {error && <p className="text-danger text-sm mb-3">{error}</p>}
      <div className="card overflow-x-auto">
        <table className="table-base">
          <thead>
            <tr>
              <th>ID</th>
              <th>Telegram</th>
              <th>Name</th>
              <th>Status</th>
              <th>Joined</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>
                  {u.username ? `@${u.username}` : "—"}
                  <span className="text-muted"> ({u.telegram_id})</span>
                </td>
                <td>{u.first_name ?? "—"}</td>
                <td>
                  <span className={`badge ${u.status === "ACTIVE" ? "badge-green" : "badge-red"}`}>
                    {u.status}
                  </span>
                </td>
                <td className="text-muted">{u.created_at.slice(0, 10)}</td>
                <td className="flex gap-2 flex-wrap">
                  <button
                    className="btn-outline"
                    disabled={busy === u.id}
                    onClick={() =>
                      action(u, { status: u.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE" })
                    }
                  >
                    {u.status === "ACTIVE" ? "Suspend" : "Unsuspend"}
                  </button>
                  <button
                    className="btn-outline"
                    disabled={busy === u.id}
                    onClick={() => {
                      const days = prompt("Bonus days:", "7");
                      if (days) action(u, { bonus_days: parseInt(days, 10) });
                    }}
                  >
                    +Days
                  </button>
                  <button className="btn-outline text-danger" disabled={busy === u.id} onClick={() => revoke(u)}>
                    Revoke VPN
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
