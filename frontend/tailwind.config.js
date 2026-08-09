/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mesh: {
          dark: '#080C14',
          surface: '#0F172A',
          card: '#162032',
          cardHover: '#1D2A42',
          border: '#24334D',
          borderLight: '#334766',
          primary: '#2563EB',
          accent: '#38BDF8',
          supervisor: '#6366F1',
          inventory: '#10B981',
          procurement: '#F59E0B',
          finance: '#EC4899',
          logistics: '#8B5CF6',
          audit: '#14B8A6',
          danger: '#EF4444',
          textMuted: '#94A3B8',
          textMain: '#F8FAFC',
        }
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s infinite alternate',
        'flow-dash': 'flowDash 1.5s linear infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%': { filter: 'drop-shadow(0 0 2px rgba(56, 189, 248, 0.3))' },
          '100%': { filter: 'drop-shadow(0 0 12px rgba(56, 189, 248, 0.8))' },
        },
        flowDash: {
          'to': { strokeDashoffset: '-20' },
        }
      }
    },
  },
  plugins: [],
}
