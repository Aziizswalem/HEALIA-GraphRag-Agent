import type { Config } from 'tailwindcss'
import colors from 'tailwindcss/colors'

const config: Config = {
  darkMode: 'class',
  content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './components/**/*.{js,ts,jsx,tsx,mdx}', './node_modules/@tremor/**/*.{js,mjs,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        healia: {
          dark: '#047063',
          teal: '#4bb8bd',
          green: '#4da73c',
        },
        tremor: {
          brand: { DEFAULT: colors.cyan[500], ...colors.cyan },
          background: colors.slate[50],
          content: colors.slate[500],
          border: colors.slate[200],
          ring: colors.slate[200],
          input: colors.slate[50],
        },
        'dark-tremor': {
          brand: { DEFAULT: colors.cyan[400], ...colors.cyan },
          background: colors.slate[950],
          content: colors.slate[400],
          border: colors.slate[800],
          ring: colors.slate[800],
          input: colors.slate[950],
        },
      },
      fontFamily: {
        heading: ['Poppins', 'system-ui', 'sans-serif'],
        body: ['Poppins', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'tremor-default': '0.5rem',
        'tremor-small': '0.375rem',
        'tremor-full': '9999px',
      },
      fontSize: {
        'tremor-default': ['0.875rem', { lineHeight: '1.25rem' }],
        'tremor-label': ['0.75rem', { lineHeight: '1rem' }],
        'tremor-title': ['1.125rem', { lineHeight: '1.75rem' }],
        'tremor-metric': ['1.875rem', { lineHeight: '2.25rem' }],
      },
      boxShadow: {
        'tremor-card': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'tremor-input': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        'dark-tremor-card': '0 1px 3px 0 rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.2)',
        'dark-tremor-input': '0 1px 2px 0 rgb(0 0 0 / 0.3)',
      },
    },
  },
  safelist: [
    { pattern: /^(fill|stroke)-(cyan|teal|emerald|amber|rose|violet|blue)-(500|600)$/ },
    { pattern: /^bg-(cyan|teal|emerald|amber|rose|violet|blue)-(50|100|200|500)$/ },
    { pattern: /^text-(cyan|teal|emerald|amber|rose|violet|blue)-(500|600)$/ },
  ],
  plugins: [
    require('@tailwindcss/typography'),
  ],
}

export default config
