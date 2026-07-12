"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

// Cosmetic page only. Activation happens strictly on the payment webhook —
// we poll the subscription until the backend confirms it.
export default function PaymentSuccess() {
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
          <h1 className="text-xl font-bold">To'lov tasdiqlanmoqda…</h1>
          <p className="text-sm text-muted max-w-xs">
            Odatda bir necha soniya. Obuna tasdiqlangach avtomatik faollashadi.
          </p>
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
          <h1 className="text-2xl font-bold">Obuna faollashtirildi!</h1>
          <p className="text-sm text-muted max-w-xs">Endi VPN'ni istalgan qurilmaga ulashingiz mumkin.</p>
          <div className="flex flex-col gap-3 w-full max-w-xs mt-2">
            <Link href="/connect" className="btn-primary">🚀 VPN'ni ulash</Link>
            <Link href="/" className="btn-ghost">Asosiyga qaytish</Link>
          </div>
        </>
      )}
      {state === "slow" && (
        <>
          <div className="h-28 w-28 rounded-full glass-hi flex items-center justify-center text-5xl">⏳</div>
          <h1 className="text-xl font-bold">To'lov hali tasdiqlanmadi</h1>
          <p className="text-sm text-muted max-w-xs">
            Tarmoq tasdiqlashi kechikishi mumkin. Bir necha daqiqadan so'ng profilni tekshiring.
          </p>
          <Link href="/profile" className="btn-ghost max-w-xs">👤 Profilga o'tish</Link>
        </>
      )}
    </div>
  );
}
