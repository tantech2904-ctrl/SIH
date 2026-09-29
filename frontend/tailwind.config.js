/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        soc: {
          bg: "rgb(var(--soc-bg) / <alpha-value>)",
          panel: "rgb(var(--soc-panel) / <alpha-value>)",
          panelAlt: "rgb(var(--soc-panel-alt) / <alpha-value>)",
          border: "rgb(var(--soc-border) / <alpha-value>)",
          borderStrong: "rgb(var(--soc-border-strong) / <alpha-value>)",
          text: "rgb(var(--soc-text) / <alpha-value>)",
          textMuted: "rgb(var(--soc-text-muted) / <alpha-value>)",
          textDim: "rgb(var(--soc-text-dim) / <alpha-value>)",
          accent: "rgb(var(--soc-accent) / <alpha-value>)",
          accentDim: "rgb(var(--soc-accent-dim) / <alpha-value>)",
          accentSoft: "rgb(var(--soc-accent-soft) / <alpha-value>)",
        },
        sev: {
          critical: "#ef4444",
          high: "#f97316",
          medium: "#eab308",
          low: "#22c55e",
          info: "#64748b",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      fontSize: {
        "2xs": "0.6875rem",
      },
    },
  },
  plugins: [],
};