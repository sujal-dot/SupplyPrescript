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
          base: '#07111F',
          secondary: '#0B1426',
        },
        brand: {
          cyan: '#22D3EE',
          blue: '#3B82F6',
          success: '#34D399',
          warning: '#FBBF24',
          error: '#FB7185',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'Fira Code',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.04)',
        'glass-hover': '0 16px 40px rgba(0, 0, 0, 0.35), 0 0 20px rgba(34, 211, 238, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
        'glass-glow': '0 0 24px rgba(34, 211, 238, 0.25)',
      },
      borderRadius: {
        'glass': '20px',
      },
    },
  },
  plugins: [],
}
