"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Item = { href: string; label: string; icon: JSX.Element };

const I = {
  home: (
    <path d="M3 10.5 12 3l9 7.5M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5" />
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18" />
    </>
  ),
  bolt: <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />,
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" />
    </>
  ),
};

const items: Item[] = [
  { href: "/", label: "Asosiy", icon: I.home },
  { href: "/servers", label: "Serverlar", icon: I.globe },
  { href: "/plans", label: "Tariflar", icon: I.bolt },
  { href: "/profile", label: "Profil", icon: I.user },
];

export default function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-5 inset-x-0 z-30 px-6">
      <div className="mx-auto max-w-[22rem] glass-hi rounded-[28px] px-2 py-2 flex justify-between">
        {items.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="relative flex-1 flex flex-col items-center gap-1 py-2 rounded-2xl transition"
            >
              {active && (
                <span className="absolute inset-1 rounded-2xl bg-gradient-to-br from-primary/25 to-secondary/20 border border-white/10" />
              )}
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.7}
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`relative h-[22px] w-[22px] transition ${
                  active ? "text-secondary drop-shadow-[0_0_6px_rgba(0,229,255,0.7)]" : "text-muted"
                }`}
              >
                {item.icon}
              </svg>
              <span
                className={`relative text-[10px] font-medium transition ${
                  active ? "text-txt" : "text-muted"
                }`}
              >
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
