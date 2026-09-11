/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        soc: {
          bg: "#0a0e1a",
          panel: "#0f1626",
          panelAlt: "#131b2e",
          border: "#1f2a44",
          borderStrong: "#2c3a5c",
          text: "#e2e8f0",
          textMuted: "#94a3b8",
          textDim: "#64748b",
          accent: "#38bdf8",
          accentDim: "#0ea5e9",
        },
        sev: {
          critical: "#dc2626",
          high: "#ea580c",
          medium: "#eab308",
          low: "#22c55e",
          info: "#64748b",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        "2xs": "0.6875rem",
      },
    },
  },
  plugins: [],
};