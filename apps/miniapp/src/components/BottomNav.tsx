"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Asosiy", icon: "🏠" },
  { href: "/servers", label: "Serverlar", icon: "🌍" },
  { href: "/plans", label: "Tariflar", icon: "💎" },
  { href: "/profile", label: "Profil", icon: "👤" },
];

export default function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-0 inset-x-0 z-20 border-t border-white/5 bg-card/90 backdrop-blur">
      <div className="mx-auto max-w-md grid grid-cols-4">
        {items.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-0.5 py-2.5 text-xs transition ${
                active ? "text-secondary" : "text-muted"
              }`}
            >
              <span className="text-lg leading-none">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
