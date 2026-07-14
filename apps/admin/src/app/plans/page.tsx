"use client";

import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { adminFetch } from "@/lib/api";

interface Plan {
  id: number;
  name: string;
  description: string | null;
  price: string;
  currency: string;
  price_stars: number;
  duration_days: number;
  traffic_limit_gb: number;
  device_hint: number;
  discount_percent: number;
  is_popular: boolean;
  is_active: boolean;
  sort_order: number;
}

const empty = {
  name: "",
  description: "",
  price: "149",
  currency: "RUB",
  price_stars: 100,
  duration_days: 30,
  traffic_limit_gb: 0,
  device_hint: 3,
  discount_percent: 0,
  is_popular: false,
  is_active: true,
  sort_order: 0,
};

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [form, setForm] = useState<any>(null); // null = closed; {} = create; {id} = edit
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    adminFetch<Plan[]>("/admin/plans").then(setPlans).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function save() {
    setError(null);
    try {
      const body = { ...form, price: String(form.price) };
      if (form.id) {
        await adminFetch(`/admin/plans/${form.id}`, { method: "PATCH", body: JSON.stringify(body) });
      } else {
        await adminFetch("/admin/plans", { method: "POST", body: JSON.stringify(body) });
      }
      setForm(null);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  function field(key: string, label: string, type: "text" | "number" | "checkbox" = "text") {
    return (
      <label className="flex flex-col gap-1 text-xs text-muted">
        {label}
        {type === "checkbox" ? (
          <input
            type="checkbox"
            checked={!!form[key]}
            onChange={(e) => setForm({ ...form, [key]: e.target.checked })}
          />
        ) : (
          <input
            className="input"
            type={type}
            value={form[key] ?? ""}
            onChange={(e) =>
              setForm({ ...form, [key]: type === "number" ? Number(e.target.value) : e.target.value })
            }
          />
        )}
      </label>
    );
  }

  return (
    <Shell>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Plans</h2>
        <button className="btn" onClick={() => setForm({ ...empty })}>
          + New plan
        </button>
      </div>
      {error && <p className="text-danger text-sm mb-3">{error}</p>}

      {form && (
        <div className="card mb-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          {field("name", "Name")}
          {field("description", "Description")}
          {field("price", "Card price")}
          {field("currency", "Currency (RUB/USDT)")}
          {field("price_stars", "Stars price (0 = off)", "number")}
          {field("duration_days", "Duration days", "number")}
          {field("traffic_limit_gb", "Traffic GB (0=∞)", "number")}
          {field("device_hint", "Device hint", "number")}
          {field("discount_percent", "Discount %", "number")}
          {field("sort_order", "Sort order", "number")}
          {field("is_popular", "Popular", "checkbox")}
          {field("is_active", "Active", "checkbox")}
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
              <th>Price</th>
              <th>Days</th>
              <th>Traffic</th>
              <th>Flags</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.name}</td>
                <td>
                  {parseFloat(p.price)} {p.currency}
                  {p.discount_percent > 0 && (
                    <span className="text-success text-xs"> −{p.discount_percent}%</span>
                  )}
                </td>
                <td>{p.duration_days}</td>
                <td>{p.traffic_limit_gb > 0 ? `${p.traffic_limit_gb} GB` : "∞"}</td>
                <td className="space-x-1">
                  {p.is_popular && <span className="badge badge-yellow">popular</span>}
                  <span className={`badge ${p.is_active ? "badge-green" : "badge-gray"}`}>
                    {p.is_active ? "active" : "off"}
                  </span>
                </td>
                <td>
                  <button className="btn-outline" onClick={() => setForm({ ...p, price: parseFloat(p.price) })}>
                    Edit
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
