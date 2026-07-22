import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    // Brutalist: sharp everything; full stays round for stickers.
    borderRadius: {
      none: "0",
      sm: "0",
      DEFAULT: "0",
      md: "0",
      lg: "0",
      xl: "0",
      "2xl": "0",
      full: "9999px",
    },
    extend: {
      colors: {
        // Brutalist pop: warm white paper, black ink, yellow fields,
        // violet interaction, red for exceptional signal. All solid.
        ink: "#FFFDF5",
        surface: "#FFFFFF",
        panel: "#FFEE99",
        line: "#0A0A0A",
        fg: "#0A0A0A",
        muted: "#3D3D3D",
        faint: "#757575",
        accent: "#6C2BD9",
        yolk: "#FFE600",
        ember: {
          dim: "#5620B0",
          DEFAULT: "#6C2BD9",
          hot: "#6C2BD9",
        },
        // Scores >= 75 scream in red-orange.
        alarm: "#FF2E00",
        // Solid tones for dark (bg-fg black) contexts.
        fgline: "#2E2E2E",
        fgmuted: "#B5B5B5",
        fgfaint: "#8A8A8A",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        sans: ["var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
