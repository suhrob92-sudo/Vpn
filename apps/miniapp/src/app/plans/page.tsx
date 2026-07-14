"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, apiPublic } from "@/lib/api";
import { openExternal, openInvoice } from "@/lib/telegram";
import { useI18n } from "@/lib/i18n";

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
}

export default function Plans() {
  const { t } = useI18n();
  const router = useRouter();
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [balance, setBalance] = useState(0);
  const [methods, setMethods] = useState<{ card: boolean; stars: boolean }>({ card: false, stars: true });
  const [buying, setBuying] = useState<string | null>(null); // `${id}:${method}`
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiPublic<Plan[]>("/plans").then(setPlans).catch((e) => setError(e.message));
    apiPublic<{ card: boolean; stars: boolean }>("/payments/methods").then(setMethods).catch(() => {});
    apiFetch<{ balance: string }>("/users/me")
      .then((d) => setBalance(parseFloat(d.balance ?? "0")))
      .catch(() => {});
  }, []);

  async function buyBalance(plan: Plan) {
    if (!confirm(`${plan.name} (${parseFloat(plan.price)} ₽) ${t("buy_balance_confirm")}`)) return;
    setBuying(`${plan.id}:balance`);
    setError(null);
    try {
      await apiFetch("/payments/balance/pay", {
        method: "POST",
        body: JSON.stringify({ plan_id: plan.id }),
      });
      router.push("/payment/success");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBuying(null);
    }
  }

  async function buyCard(plan: Plan) {
    setBuying(`${plan.id}:card`);
    setError(null);
    try {
      const payment = await apiFetch<{ invoice_url: string }>("/payments/create", {
        method: "POST",
        body: JSON.stringify({ plan_id: plan.id }), // provider = backend default (YooKassa)
      });
      if (payment.invoice_url) openExternal(payment.invoice_url);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBuying(null);
    }
  }

  async function buyStars(plan: Plan) {
    setBuying(`${plan.id}:stars`);
    setError(null);
    try {
      const { invoice_link } = await apiFetch<{ invoice_link: string }>("/payments/stars/create", {
        method: "POST",
        body: JSON.stringify({ plan_id: plan.id }),
      });
      const status = await openInvoice(invoice_link);
      if (status === "paid") router.push("/payment/success");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBuying(null);
    }
  }

  const cur = (c: string) => (c === "RUB" ? "₽" : c);

  return (
    <div className="flex flex-col gap-4 animate-fade-up">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("plans_title")}</h1>
        <p className="text-sm text-muted mt-1">
          {methods.card ? t("plans_sub_card") : t("plans_sub_stars")} {t("plans_sub_tail")}
        </p>
      </div>

      {balance > 0 && (
        <div className="glass p-4 flex items-center justify-between">
          <p className="text-sm text-muted flex items-center gap-2">
            <span className="h-8 w-8 rounded-xl bg-accent/15 flex items-center justify-center text-accent">💰</span>
            {t("your_balance")}
          </p>
          <p className="font-bold text-lg">{balance} ₽</p>
        </div>
      )}

      {error && <div className="glass !border-danger/40 text-danger text-sm p-4">{error}</div>}

      {!plans && !error && (
        <>
          <div className="skeleton h-40" />
          <div className="skeleton h-40" />
        </>
      )}

      {plans?.map((plan, i) => (
        <div
          key={plan.id}
          style={{ animationDelay: `${i * 60}ms` }}
          className={`relative p-5 animate-fade-up ${
            plan.is_popular ? "glass-hi glow-border shadow-glow" : "glass"
          }`}
        >
          {plan.is_popular && (
            <span className="absolute -top-2.5 left-5 chip text-white bg-gradient-to-r from-primary to-secondary shadow-glow">
              {t("popular")}
            </span>
          )}
          <div className="flex items-start justify-between">
            <div>
              <h2 className="font-semibold text-lg">{plan.name}</h2>
              <p className="text-sm text-muted">{plan.description}</p>
            </div>
            <div className="text-right shrink-0">
              <p className="font-bold text-2xl leading-none bg-gradient-to-r from-white to-muted bg-clip-text text-transparent">
                {parseFloat(plan.price)}
                <span className="text-base"> {cur(plan.currency)}</span>
              </p>
              {plan.discount_percent > 0 && (
                <span className="chip text-accent bg-accent/10 mt-1 inline-block">
                  -{plan.discount_percent}%
                </span>
              )}
            </div>
          </div>
          <ul className="mt-4 grid grid-cols-3 gap-2 text-center">
            <li className="rounded-2xl bg-white/[0.04] py-2">
              <p className="text-sm font-semibold">{plan.duration_days}</p>
              <p className="text-[10px] text-muted">{t("days")}</p>
            </li>
            <li className="rounded-2xl bg-white/[0.04] py-2">
              <p className="text-sm font-semibold">
                {plan.traffic_limit_gb > 0 ? `${plan.traffic_limit_gb}GB` : "∞"}
              </p>
              <p className="text-[10px] text-muted">{t("traffic")}</p>
            </li>
            <li className="rounded-2xl bg-white/[0.04] py-2">
              <p className="text-sm font-semibold">{plan.device_hint}</p>
              <p className="text-[10px] text-muted">{t("devices")}</p>
            </li>
          </ul>
          <div className="mt-4 flex flex-col gap-2">
            {methods.card && (
              <button
                className="btn-primary"
                disabled={buying === `${plan.id}:card`}
                onClick={() => buyCard(plan)}
              >
                {buying === `${plan.id}:card`
                  ? t("opening")
                  : `💳 ${t("pay_card")} · ${parseFloat(plan.price)} ${cur(plan.currency)}`}
              </button>
            )}
            {plan.price_stars > 0 && (
              <button
                className="btn-ghost"
                disabled={buying === `${plan.id}:stars`}
                onClick={() => buyStars(plan)}
              >
                {buying === `${plan.id}:stars` ? t("opening") : `⭐ ${t("pay_stars")} · ${plan.price_stars}`}
              </button>
            )}
            {balance >= parseFloat(plan.price) && (
              <button
                className="btn-ghost"
                disabled={buying === `${plan.id}:balance`}
                onClick={() => buyBalance(plan)}
              >
                {buying === `${plan.id}:balance`
                  ? t("paying")
                  : `💰 ${t("pay_balance")} · ${parseFloat(plan.price)} ₽`}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
