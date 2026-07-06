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
    <div className="flex flex-col items-center gap-4 pt-16 text-center">
      {state === "waiting" && (
        <>
          <div className="h-16 w-16 rounded-full border-4 border-primary border-t-transparent animate-spin" />
          <h1 className="text-lg font-semibold">To'lov tasdiqlanmoqda…</h1>
          <p className="text-sm text-muted">
            Odatda bu bir necha soniya davom etadi. Obuna to'lov tasdiqlangach avtomatik faollashadi.
          </p>
        </>
      )}
      {state === "active" && (
        <>
          <p className="text-5xl">✅</p>
          <h1 className="text-lg font-semibold">Obuna faollashtirildi!</h1>
          <Link href="/connect" className="btn-primary max-w-xs">
            🚀 VPN'ni ulash
          </Link>
        </>
      )}
      {state === "slow" && (
        <>
          <p className="text-5xl">⏳</p>
          <h1 className="text-lg font-semibold">To'lov hali tasdiqlanmadi</h1>
          <p className="text-sm text-muted">
            Tarmoq tasdiqlashi kechikishi mumkin. Bir necha daqiqadan so'ng profilni tekshiring.
          </p>
          <Link href="/profile" className="btn-ghost max-w-xs">
            👤 Profilga o'tish
          </Link>
        </>
      )}
    </div>
  );
}
