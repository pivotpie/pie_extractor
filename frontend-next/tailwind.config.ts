import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ["class", "[data-mode='dark']"],
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      colors: {
        // Standard Tailwind colors
        transparent: 'transparent',
        current: 'currentColor',
        black: '#000000',
        white: '#ffffff',
        
        // Gray scale
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
          950: '#030712',
        },
        
        // Semantic colors - use CSS custom properties with fallbacks
        border: 'hsl(var(--border, 215 15% 90%))',
        input: 'hsl(var(--input, 215 15% 90%))',
        ring: 'hsl(var(--ring, 233 71% 55%))',
        background: 'hsl(var(--background, 216 15% 97%))',
        foreground: 'hsl(var(--foreground, 215 25% 15%))',
        
        // Primary colors
        primary: {
          DEFAULT: 'hsl(var(--primary, 233 71% 55%))',
          foreground: 'hsl(var(--primary-foreground, 210 40% 98%))',
          glow: 'hsl(var(--primary-glow, 233 71% 65%))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary, 215 20% 96%))',
          foreground: 'hsl(var(--secondary-foreground, 215 25% 25%))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive, 0 84% 60%))',
          foreground: 'hsl(var(--destructive-foreground, 210 40% 98%))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted, 215 15% 95%))',
          foreground: 'hsl(var(--muted-foreground, 215 12% 45%))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent, 264 67% 62%))',
          foreground: 'hsl(var(--accent-foreground, 210 40% 98%))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover, 0 0% 100%))',
          foreground: 'hsl(var(--popover-foreground, 215 25% 15%))',
        },
        card: {
          DEFAULT: 'hsl(var(--card, 0 0% 100%))',
          foreground: 'hsl(var(--card-foreground, 215 25% 15%))',
        },
        success: {
          DEFAULT: 'hsl(var(--success, 142 71% 45%))',
          foreground: 'hsl(var(--success-foreground, 210 40% 98%))',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning, 38 92% 55%))',
          foreground: 'hsl(var(--warning-foreground, 215 25% 15%))',
        },
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar-background, 0 0% 98%))',
          foreground: 'hsl(var(--sidebar-foreground, 240 5.3% 26.1%))',
          primary: 'hsl(var(--sidebar-primary, 240 5.9% 10%))',
          'primary-foreground': 'hsl(var(--sidebar-primary-foreground, 0 0% 98%))',
          accent: 'hsl(var(--sidebar-accent, 240 4.8% 95.9%))',
          'accent-foreground': 'hsl(var(--sidebar-accent-foreground, 240 5.9% 10%))',
          border: 'hsl(var(--sidebar-border, 220 13% 91%))',
          ring: 'hsl(var(--sidebar-ring, 217.2 91.2% 59.8%))',
        },
      },
      borderRadius: {
        none: '0px',
        sm: '0.25rem',
        DEFAULT: '0.375rem',
        md: '0.5rem',
        lg: 'var(--radius, 0.5rem)',
        xl: '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
        full: '9999px',
      },
      boxShadow: {
        'sm': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        'DEFAULT': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        'lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        'xl': '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
        '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
        'inner': 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
        'elegant': '0 4px 20px -4px hsl(var(--primary, 233 71% 55%) / 0.15)',
        'glow': '0 0 30px hsl(var(--primary-glow, 233 71% 65%) / 0.3)',
        'card': '0 2px 8px -2px hsl(215 25% 15% / 0.08)',
        'none': 'none',
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.5rem' }],
        'base': ['1rem', { lineHeight: '1.75rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        '5xl': ['3rem', { lineHeight: '1' }],
        '6xl': ['3.75rem', { lineHeight: '1' }],
        '7xl': ['4.5rem', { lineHeight: '1' }],
        '8xl': ['6rem', { lineHeight: '1' }],
        '9xl': ['8rem', { lineHeight: '1' }],
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-in': {
          '0%': {
            opacity: '0',
            transform: 'translateY(10px)',
          },
          '100%': {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        'scale-in': {
          '0%': {
            transform: 'scale(0.8)',
            opacity: '0',
          },
          '100%': {
            transform: 'scale(1)',
            opacity: '1',
          },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
        'scale-in': 'scale-in 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('tailwindcss-animate'),
  ],
} satisfies Config;

export default config;