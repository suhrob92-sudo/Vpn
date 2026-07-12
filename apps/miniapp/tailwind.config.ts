import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#05070D",
        surface: "#0D111C",
        primary: "#7B61FF",
        secondary: "#00E5FF",
        accent: "#36F9A8",
        danger: "#FF4D67",
        warning: "#FFC247",
        txt: "#FFFFFF",
        muted: "#9CA3AF",
      },
      boxShadow: {
        glow: "0 0 60px rgba(123, 97, 255, 0.45)",
        "glow-cyan": "0 0 50px rgba(0, 229, 255, 0.35)",
        "glow-accent": "0 0 40px rgba(54, 249, 168, 0.4)",
        card: "0 8px 32px rgba(0, 0, 0, 0.45)",
      },
      backdropBlur: {
        xl: "24px",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      keyframes: {
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        "spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
        "glow-pulse": {
          "0%,100%": { opacity: "0.6", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.05)" },
        },
        "mesh-shift": {
          "0%,100%": { transform: "translate(0,0) scale(1)" },
          "33%": { transform: "translate(8%,-6%) scale(1.1)" },
          "66%": { transform: "translate(-6%,8%) scale(0.95)" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        "spin-slow": "spin-slow 14s linear infinite",
        "glow-pulse": "glow-pulse 3s ease-in-out infinite",
        "mesh-shift": "mesh-shift 18s ease-in-out infinite",
        "fade-up": "fade-up 0.5s cubic-bezier(0.22,1,0.36,1) both",
      },
    },
  },
  plugins: [],
};
export default config;
