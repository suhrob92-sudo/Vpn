import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#080B12",
        card: "#111722",
        primary: "#6C5CE7",
        secondary: "#00D2FF",
        success: "#22C55E",
        warning: "#F59E0B",
        danger: "#EF4444",
        txt: "#F8FAFC",
        muted: "#94A3B8",
      },
      boxShadow: {
        glow: "0 0 40px rgba(108, 92, 231, 0.45)",
      },
    },
  },
  plugins: [],
};
export default config;
