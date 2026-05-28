/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#080b0c",
        surface: "#0f1517",
        surface2: "#161d20",
        line: "#233037",
        "line-bright": "#324249",
        signal: "#caff47",
        "signal-dim": "#8aa831",
        amber: "#f5a623",
        cyan: "#4ad6c1",
        rose: "#ff6b6b",
        ink: "#e4ebe7",
        muted: "#7e8e88",
        faint: "#4d5a54",
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        body: ['"Hanken Grotesk"', "system-ui", "sans-serif"],
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        sweep: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(220%)" },
        },
        blip: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.35", transform: "scale(0.82)" },
        },
        grow: {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
      },
      animation: {
        rise: "rise 0.5s cubic-bezier(0.22,1,0.36,1) both",
        sweep: "sweep 2.6s ease-in-out infinite",
        blip: "blip 1.4s ease-in-out infinite",
        grow: "grow 0.7s cubic-bezier(0.22,1,0.36,1) both",
      },
    },
  },
  plugins: [],
};
