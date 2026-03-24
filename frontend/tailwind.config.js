/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: 'rgb(var(--brand) / <alpha-value>)',
        background: 'rgb(var(--bg-primary) / <alpha-value>)',
        surface: 'rgb(var(--surface) / <alpha-value>)',
        subtle: 'rgb(var(--bg-secondary) / <alpha-value>)',
        primary: 'rgb(var(--text-primary) / <alpha-value>)',
        muted: 'rgb(var(--text-muted) / <alpha-value>)',
        border: 'rgb(var(--border) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow': '0 0 20px rgba(var(--brand) / 0.5)',
        'soft': '0 4px 20px -2px rgba(0, 0, 0, 0.05)',
      },
      backgroundImage: {
        'noise': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")",
      }
    },
  },
  plugins: [],
}
