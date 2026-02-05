/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        'k2-bg': '#242424',
        'k2-surface': '#303030',
        'k2-surface-hover': '#3d3d3d',
        'k2-border': '#484848',
        'k2-text': '#ffffff',
        'k2-text-secondary': '#9a9a9a',
        'k2-accent': '#3584e4',
        'k2-accent-hover': '#4a9cf8',
        'k2-success': '#33d17a',
        'k2-warning': '#f6d32d',
        'k2-error': '#e01b24',
        'led-red': '#ff3333',
        'led-amber': '#ffaa00',
        'led-green': '#00ff66',
        'led-off': '#404040',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
