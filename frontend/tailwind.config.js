/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // State colors from docs/ARCHITECTURE.md 3.7 — meaning stays fixed across screens
        resolved: "#0F6E56",   // teal
        stopped: "#993C1D",    // coral
        pending: "#854F0B",    // amber
        neutral: "#5F5E5A",    // gray
      },
    },
  },
  plugins: [],
};
