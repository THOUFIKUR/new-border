/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // BorderPulse dark command-center SOC palette
        bp: {
          bg:       "#060A0C",
          surface:  "#0A1014",
          card:     "#0E161B",
          border:   "#15222B",
          accent:   "#00E5FF",
          green:    "#00FF66",
          danger:   "#FF2A2A",
          warning:  "#FFB700",
          safe:     "#00FF66",
          muted:    "#526673",
          text:     "#E6F1F5",
          dim:      "#8A9EA8",
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
