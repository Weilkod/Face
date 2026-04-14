import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#f7f7f7",
        coral: {
          DEFAULT: "#F26B4E",
          light: "#FEF3F0",
          dark: "#C54A30",
        },
        mint: {
          DEFAULT: "#059669",
          light: "#D1FAE5",
          dark: "#065F46",
        },
        ink: {
          DEFAULT: "#111827",
          title: "#0A192F",
          muted: "#6B7280",
          faint: "#9CA3AF",
        },
      },
      fontFamily: {
        sans: ['"Pretendard Variable"', "Pretendard", "system-ui", "sans-serif"],
      },
      keyframes: {
        "bar-fill": {
          from: { width: "0%" },
          to: { width: "var(--pct, 0%)" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(20px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "radar-in": {
          from: { opacity: "0", transform: "scale(0.92)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "bar-fill": "bar-fill 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.15s both",
        "fade-up": "fade-up 0.7s ease-out both",
        "radar-in": "radar-in 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(17,24,39,0.04), 0 8px 24px rgba(17,24,39,0.05)",
      },
    },
  },
  plugins: [],
};

export default config;
