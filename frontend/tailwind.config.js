/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        soc: {
          bg: "#050b08",
          panel: "#0d1511",
          panelAlt: "#101d16",
          border: "#1d3128",
          borderStrong: "#2b4a3a",
          text: "#edf5ef",
          textMuted: "#b0c5b5",
          textDim: "#7f9388",
          accent: "#34d399",
          accentDim: "#16a34a",
          accentSoft: "#86efac",
        },
        sev: {
          critical: "#f87171",
          high: "#fb923c",
          medium: "#facc15",
          low: "#4ade80",
          info: "#94a3b8",
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