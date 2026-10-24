/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          base: '#0C0406',
          secondary: '#16070B',
        },
        brand: {
          red: '#EF4444',
          rose: '#F43F5E',
          crimson: '#DC2626',
          ruby: '#E11D48',
          success: '#34D399',
          warning: '#FBBF24',
          error: '#F87171',
        },
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Display',
          'SF Pro Text',
          'Inter',
          'system-ui',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'sans-serif',
        ],
        mono: [
          'SF Mono',
          'JetBrains Mono',
          'Fira Code',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      boxShadow: {
        'glass': '0 12px 36px -4px rgba(0, 0, 0, 0.50), 0 1px 2px 0 rgba(0, 0, 0, 0.30), inset 0 1px 1px 0 rgba(255, 255, 255, 0.22), inset 0 0 0 1px rgba(255, 255, 255, 0.05)',
        'glass-hover': '0 20px 48px -8px rgba(0, 0, 0, 0.65), 0 0 24px 0 rgba(239, 68, 68, 0.25), inset 0 1px 1.5px 0 rgba(255, 255, 255, 0.38), inset 0 0 0 1px rgba(255, 255, 255, 0.10)',
        'glass-glow': '0 0 28px rgba(239, 68, 68, 0.40), inset 0 1px 1px 0 rgba(255, 255, 255, 0.30)',
        'apple-card': '0 10px 36px -4px rgba(0, 0, 0, 0.50), 0 1px 2px 0 rgba(0, 0, 0, 0.30), inset 0 1px 1px 0 rgba(255, 255, 255, 0.22)',
        'apple-pill': 'inset 0 1px 1px 0 rgba(255, 255, 255, 0.30), 0 2px 8px 0 rgba(0, 0, 0, 0.30)',
        'apple-btn': 'inset 0 1px 1.5px 0 rgba(255, 255, 255, 0.50), inset 0 -1px 1px 0 rgba(0, 0, 0, 0.25), 0 4px 18px 0 rgba(220, 38, 38, 0.42)',
      },
      borderRadius: {
        'glass': '24px',
        'squircle': '22px',
      },
    },
  },
  plugins: [],
}
