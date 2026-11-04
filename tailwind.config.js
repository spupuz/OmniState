/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './*.html',
    './server/dashboard/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#070b14',
        'bg-soft': '#0b1224',
        card: 'rgba(15,23,42,.55)',
        'card-solid': '#111d36',
        border: 'rgba(255,255,255,.08)',
        'border-strong': 'rgba(255,255,255,.14)',
        text: '#f1f5f9',
        muted: '#94a3b8',
        'muted-2': '#64748b',
        accent: '#3b82f6',
        'accent-2': '#60a5fa',
        'accent-glow': 'rgba(59,130,246,.35)',
        success: '#10b981',
        warn: '#f59e0b',
        danger: '#ef4444',
      },
      borderRadius: {
        sm: '.5rem',
        lg: '.75rem',
      },
      shadow: {
        DEFAULT: '0 8px 32px rgba(2,6,23,.45)',
        sm: '0 2px 10px rgba(2,6,23,.35)',
      },
    },
  },
  plugins: [],
}