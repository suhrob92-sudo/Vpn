"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

// Cosmetic page only. Activation happens strictly on the payment webhook —
// we poll the subscription until the backend confirms it.
export default function PaymentSuccess() {
  const { t } = useI18n();
  const [state, setState] = useState<"waiting" | "active" | "slow">("waiting");

  useEffect(() => {
    let tries = 0;
    const timer = setInterval(async () => {
      tries += 1;
      try {
        const sub = await apiFetch<{ status: string } | null>("/subscriptions/me");
        if (sub && sub.status === "ACTIVE") {
          setState("active");
          clearInterval(timer);
          return;
        }
      } catch {
        /* keep polling */
      }
      if (tries >= 20) {
        setState("slow");
        clearInterval(timer);
      }
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex flex-col items-center gap-5 pt-20 text-center animate-fade-up">
      {state === "waiting" && (
        <>
          <div className="relative h-28 w-28">
            <span className="ring" />
            <div className="h-28 w-28 rounded-full orb-idle flex items-center justify-center">
              <div className="h-12 w-12 rounded-full border-[3px] border-secondary border-t-transparent animate-spin" />
            </div>
          </div>
          <h1 className="text-xl font-bold">{t("pay_verifying")}</h1>
          <p className="text-sm text-muted max-w-xs">{t("pay_verifying_desc")}</p>
        </>
      )}
      {state === "active" && (
        <>
          <div className="relative h-32 w-32 animate-float">
            <span className="ring" />
            <span className="ring ring-2" />
            <div className="h-32 w-32 rounded-full orb flex items-center justify-center text-5xl shadow-glow">
              🛡️
            </div>
          </div>
          <h1 className="text-2xl font-bold">{t("pay_activated")}</h1>
          <p className="text-sm text-muted max-w-xs">{t("pay_activated_desc")}</p>
          <div className="flex flex-col gap-3 w-full max-w-xs mt-2">
            <Link href="/connect" className="btn-primary">{t("pay_connect")}</Link>
            <Link href="/" className="btn-ghost">{t("pay_back_home")}</Link>
          </div>
        </>
      )}
      {state === "slow" && (
        <>
          <div className="h-28 w-28 rounded-full glass-hi flex items-center justify-center text-5xl">⏳</div>
          <h1 className="text-xl font-bold">{t("pay_slow")}</h1>
          <p className="text-sm text-muted max-w-xs">{t("pay_slow_desc")}</p>
          <Link href="/profile" className="btn-ghost max-w-xs">{t("pay_go_profile")}</Link>
        </>
      )}
    </div>
  );
}
