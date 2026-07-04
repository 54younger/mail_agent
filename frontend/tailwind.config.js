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
        // Editorial-dashboard tokens (mirror the CSS custom properties).
        canvas: {
          DEFAULT: '#f4f4f7',
          tint: '#efeef6',
        },
        ink: {
          DEFAULT: '#16151f',
          soft: '#4b4a58',
          mute: '#86848f',
        },
        surface: {
          DEFAULT: '#ffffff',
          muted: '#faf9fc',
        },
        hairline: '#e8e6ef',
        primary: {
          DEFAULT: '#6d5efc',
          strong: '#5a45f0',
          tint: '#efeafe',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
        display: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        xl: '0.875rem',
        '2xl': '1.125rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(24, 22, 43, 0.05), 0 1px 3px rgba(24, 22, 43, 0.04)',
        card: '0 4px 12px rgba(24, 22, 43, 0.06), 0 2px 4px rgba(24, 22, 43, 0.04)',
        lift: '0 18px 40px -12px rgba(38, 30, 84, 0.22)',
      },
    },
  },
  plugins: [],
};
