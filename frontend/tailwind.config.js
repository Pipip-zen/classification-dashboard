/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        aerospace: {
          bg: '#080B10',
          stage: '#05070B',
          surface: '#0E141F',
          panel: '#151E2E',
          card: 'rgba(14, 20, 31, 0.85)',
          border: '#1E2C42',
          borderLight: '#2A3C59',
        },
        tactical: {
          cyan: '#00E5FF',
          emerald: '#00FF66',
          red: '#FF3B30',
          amber: '#FFB703',
          blue: '#00B4FF',
          purple: '#B5179E',
          muted: '#64748B',
          text: '#E2E8F0',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'glow-cyan': '0 0 15px rgba(0, 229, 255, 0.25)',
        'glow-emerald': '0 0 15px rgba(0, 255, 102, 0.25)',
        'glow-red': '0 0 15px rgba(255, 59, 48, 0.25)',
      }
    },
  },
  plugins: [],
}
