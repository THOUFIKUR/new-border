/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // BorderPulse dark security ops palette
        bp: {
          bg:       "#080d1a",
          surface:  "#0d1525",
          card:     "#111d2e",
          border:   "#1a2d47",
          accent:   "#00d4ff",
          danger:   "#ff3a3a",
          warning:  "#ffaa00",
          safe:     "#00ff88",
          muted:    "#6b7fa3",
          text:     "#e2e8f0",
          dim:      "#94a3b8",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "pulse-danger": "pulse 1s ease-in-out infinite",
        "scan-line":    "scanLine 3s linear infinite",
        "fade-in":      "fadeIn 0.3s ease-in",
        "slide-up":     "slideUp 0.3s ease-out",
        "glow":         "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        scanLine: {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        fadeIn: {
          from: { opacity: 0 },
          to:   { opacity: 1 },
        },
        slideUp: {
          from: { transform: "translateY(10px)", opacity: 0 },
          to:   { transform: "translateY(0)",    opacity: 1 },
        },
        glow: {
          from: { boxShadow: "0 0 5px #00d4ff44" },
          to:   { boxShadow: "0 0 20px #00d4ff88, 0 0 40px #00d4ff22" },
        },
      },
    },
  },
  plugins: [],
};
