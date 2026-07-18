import type { Config } from "tailwindcss";

/**
 * Design system: "Data-Dense Dashboard" (ui-ux-pro-max).
 * Blue data chrome + amber call-to-action, on a cool slate surface.
 *
 * Two colour families that must never be mixed:
 *  - `brand` / `accent` — chrome, navigation, actions. Meaningless as data.
 *  - `risk`             — a RESERVED status ramp. Only ever encodes shortage
 *                         severity, always paired with a text label, never
 *                         used as a generic "series 3" colour.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
          DEFAULT: "#1e40af",
          dark: "#1e3a8a",
        },
        accent: {
          DEFAULT: "#f59e0b",
          dark: "#b45309",
          light: "#fef3c7",
        },
        // Reserved 5-level shortage status ramp.
        risk: {
          green: "#15803d",
          yellow: "#ca8a04",
          orange: "#ea580c",
          red: "#dc2626",
          critical: "#7f1d1d",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        // Dense-dashboard scale: tighter than Tailwind's default.
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.06)",
        pop: "0 4px 16px -2px rgb(15 23 42 / 0.12)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.25s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
