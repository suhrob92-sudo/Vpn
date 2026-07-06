"use client";

import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { adminFetch } from "@/lib/api";

interface Server {
  id: number;
  name: string;
  country: string;
  city: string | null;
  panel_url: string;
  panel_user: string;
  inbound_id: number;
  host: string;
  port: number;
  public_key: string;
  short_id: string;
  sni: string;
  status: string;
}

const empty = {
  name: "",
  country: "DE",
  city: "",
  panel_url: "",
  panel_user: "",
  panel_pass: "",
  inbound_id: 1,
  host: "",
  port: 443,
  public_key: "",
  short_id: "",
  sni: "",
  status: "ONLINE",
};

const badge: Record<string, string> = {
  ONLINE: "badge-green",
  MAINTENANCE: "badge-yellow",
  OFFLINE: "badge-red",
};

export default function ServersPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [form, setForm] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState<number | null>(null);
  const [checkResult, setCheckResult] = useState<string | null>(null);

  const load = useCallback(() => {
    adminFetch<Server[]>("/admin/servers").then(setServers).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function save() {
    setError(null);
    try {
      const body = { ...form };
      if (form.id && !body.panel_pass) delete body.panel_pass; // keep existing password
      if (form.id) {
        const { id, ...rest } = body;
        await adminFetch(`/admin/servers/${id}`, { method: "PATCH", body: JSON.stringify(rest) });
      } else {
        await adminFetch("/admin/servers", { method: "POST", body: JSON.stringify(body) });
      }
      setForm(null);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function check(id: number) {
    setChecking(id);
    setCheckResult(null);
    try {
      const res = await adminFetch<{ reachable: boolean; error?: string }>(
        `/admin/servers/${id}/check`,
        { method: "POST" }
      );
      setCheckResult(res.reachable ? `✅ Server #${id}: panel reachable` : `❌ Server #${id}: ${res.error}`);
    } catch (e: any) {
      setCheckResult(`❌ ${e.message}`);
    } finally {
      setChecking(null);
    }
  }

  async function remove(id: number) {
    if (!confirm(`Delete server #${id}?`)) return;
    try {
      await adminFetch(`/admin/servers/${id}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  function field(key: string, label: string, type: "text" | "number" | "password" = "text") {
    return (
      <label className="flex flex-col gap-1 text-xs text-muted">
        {label}
        <input
          className="input"
          type={type}
          value={form[key] ?? ""}
          onChange={(e) =>
            setForm({ ...form, [key]: type === "number" ? Number(e.target.value) : e.target.value })
          }
        />
      </label>
    );
  }

  return (
    <Shell>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Servers</h2>
        <button className="btn" onClick={() => setForm({ ...empty })}>
          + Add server
        </button>
      </div>
      {error && <p className="text-danger text-sm mb-3">{error}</p>}
      {checkResult && <p className="text-sm mb-3">{checkResult}</p>}

      {form && (
        <div className="card mb-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          {field("name", "Name (e.g. DE-1 Frankfurt)")}
          {field("country", "Country code (DE)")}
          {field("city", "City")}
          {field("host", "Client host/IP")}
          {field("port", "Client port", "number")}
          {field("panel_url", "Panel URL (with base path)")}
          {field("panel_user", "Panel user")}
          {field("panel_pass", form.id ? "Panel pass (blank = keep)" : "Panel pass", "password")}
          {field("inbound_id", "Inbound ID", "number")}
          {field("public_key", "Reality public key")}
          {field("short_id", "Reality short id")}
          {field("sni", "SNI (e.g. yahoo.com)")}
          <label className="flex flex-col gap-1 text-xs text-muted">
            Status
            <select
              className="input"
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
            >
              <option>ONLINE</option>
              <option>MAINTENANCE</option>
              <option>OFFLINE</option>
            </select>
          </label>
          <div className="flex items-end gap-2 col-span-2">
            <button className="btn" onClick={save}>
              Save
            </button>
            <button className="btn-outline" onClick={() => setForm(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="card overflow-x-auto">
        <table className="table-base">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Location</th>
              <th>Host</th>
              <th>Inbound</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {servers.map((s) => (
              <tr key={s.id}>
                <td>{s.id}</td>
                <td>{s.name}</td>
                <td>
                  {s.country}
                  {s.city ? `, ${s.city}` : ""}
                </td>
                <td className="text-muted">
                  {s.host}:{s.port}
                </td>
                <td>{s.inbound_id}</td>
                <td>
                  <span className={`badge ${badge[s.status] ?? "badge-gray"}`}>{s.status}</span>
                </td>
                <td className="flex gap-2 flex-wrap">
                  <button className="btn-outline" disabled={checking === s.id} onClick={() => check(s.id)}>
                    {checking === s.id ? "…" : "Check"}
                  </button>
                  <button className="btn-outline" onClick={() => setForm({ ...s, panel_pass: "" })}>
                    Edit
                  </button>
                  <button className="btn-outline text-danger" onClick={() => remove(s.id)}>
                    Delete
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
