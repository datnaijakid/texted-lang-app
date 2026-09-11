/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: {
          950: '#0a0b0f',
          900: '#111319',
          800: '#181b23',
          700: '#232733',
          600: '#2e3341',
        },
        accent: {
          DEFAULT: '#6ee7c2',
          soft: '#3d8a71',
        },
        bubble: {
          me: '#3b82f6',
          them: '#232733',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        xl2: '1.25rem',
      },
      keyframes: {
        'pop-in': {
          '0%': { opacity: 0, transform: 'translateY(6px) scale(0.98)' },
          '100%': { opacity: 1, transform: 'translateY(0) scale(1)' },
        },
      },
      animation: {
        'pop-in': 'pop-in 0.2s ease-out',
      },
    },
  },
  plugins: [],
}
