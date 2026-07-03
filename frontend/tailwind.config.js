/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Semantic job-status palette — used by the board columns/cards.
        status: {
          applied: '#6366f1', // indigo
          test: '#0ea5e9', // sky
          interview: '#f59e0b', // amber
          offer: '#10b981', // emerald
          rejected: '#ef4444', // red
          unknown: '#94a3b8', // slate
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
