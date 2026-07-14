"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { clearTokens, isLoggedIn } from "@/lib/api";

const nav = [
  { href: "/", label: "Dashboard" },
  { href: "/users", label: "Users" },
  { href: "/payments", label: "Payments" },
  { href: "/plans", label: "Plans" },
  { href: "/servers", label: "Servers" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  return (
    <div className="min-h-dvh flex">
      <aside className="w-52 shrink-0 border-r border-white/5 p-4 flex flex-col gap-1">
        <h1 className="font-bold text-lg mb-4">🛡 VPN Admin</h1>
        {nav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-lg px-3 py-2 text-sm transition ${
              pathname === item.href ? "bg-primary/20 text-secondary" : "text-muted hover:bg-white/5"
            }`}
          >
            {item.label}
          </Link>
        ))}
        <button
          className="mt-auto btn-outline"
          onClick={() => {
            clearTokens();
            router.replace("/login");
          }}
        >
          Logout
        </button>
      </aside>
      <main className="flex-1 p-6 overflow-x-auto">{children}</main>
    </div>
  );
}
