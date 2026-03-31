import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#F5F6F8",
        card: "#FFFFFF",
        border: "#E5E7EB",
        ink: "#111827",
        muted: "#6B7280",
        navy: "#1F3A5F",
        slateblue: "#64748B",
        lightslate: "#CBD5E1",
        watch: "#F59E0B",
        warning: "#EA580C",
        critical: "#DC2626",
        stable: "#16A34A",
      },
      boxShadow: {
        soft: "0 10px 30px rgba(15, 23, 42, 0.06)",
      },
      borderRadius: {
        "2xl": "1.25rem",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
