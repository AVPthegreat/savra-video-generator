import { heroui } from "@heroui/react";

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B0B0F",
        surface: "#15151A",
        accent: {
          blue: "#3B82F6",
          purple: "#8B5CF6",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
      },
      boxShadow: {
        "premium-sm": "0 2px 8px -2px rgba(0,0,0,0.5), 0 1px 4px -1px rgba(0,0,0,0.3)",
        "premium-lg": "0 20px 40px -12px rgba(0,0,0,0.8)",
        "glow-purple": "0 0 40px -10px rgba(139, 92, 246, 0.3)",
        "glow-blue": "0 0 40px -10px rgba(59, 130, 246, 0.3)",
      },
    },
  },
  darkMode: "class",
  plugins: [heroui()],
};
