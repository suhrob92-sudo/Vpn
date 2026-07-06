import type { Metadata, Viewport } from "next";
import Script from "next/script";
import "./globals.css";
import BottomNav from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "VPN",
  description: "Tezkor va xavfsiz VPN xizmati",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#080B12",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz">
      <body>
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
        <main className="mx-auto max-w-md min-h-dvh px-4 pt-4 pb-24">{children}</main>
        <BottomNav />
      </body>
    </html>
  );
}
