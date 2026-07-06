"use client";

import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { adminFetch } from "@/lib/api";

interface Payment {
  id: number;
  user_id: number;
  provider: string;
  provider_payment_id: string | null;
  amount: string;
  currency: string;
  status: string;
  created_at: string;
  paid_at: string | null;
}

const badge: Record<string, string> = {
  SUCCESS: "badge-green",
  PENDING: "badge-yellow",
  FAILED: "badge-red",
  EXPIRED: "badge-gray",
};

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [status, setStatus] = useState("");
  const [provider, setProvider] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (provider) params.set("provider", provider);
    adminFetch<Payment[]>(`/admin/payments?${params}`)
      .then(setPayments)
      .catch((e) => setError(e.message));
  }, [status, provider]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Shell>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <h2 className="text-lg font-semibold mr-auto">Payments</h2>
        <select className="input max-w-40" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option>PENDING</option>
          <option>SUCCESS</option>
          <option>FAILED</option>
          <option>EXPIRED</option>
        </select>
        <select className="input max-w-40" value={provider} onChange={(e) => setProvider(e.target.value)}>
          <option value="">All providers</option>
          <option value="cryptobot">cryptobot</option>
          <option value="stars">stars</option>
        </select>
      </div>
      {error && <p className="text-danger text-sm mb-3">{error}</p>}
      <div className="card overflow-x-auto">
        <table className="table-base">
          <thead>
            <tr>
              <th>ID</th>
              <th>User</th>
              <th>Provider</th>
              <th>External ID</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Created</th>
              <th>Paid</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.user_id}</td>
                <td>{p.provider}</td>
                <td className="text-muted text-xs">{p.provider_payment_id ?? "—"}</td>
                <td>
                  {p.amount} {p.currency}
                </td>
                <td>
                  <span className={`badge ${badge[p.status] ?? "badge-gray"}`}>{p.status}</span>
                </td>
                <td className="text-muted">{p.created_at.slice(0, 16).replace("T", " ")}</td>
                <td className="text-muted">{p.paid_at ? p.paid_at.slice(0, 16).replace("T", " ") : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
