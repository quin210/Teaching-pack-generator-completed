/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    fontFamily: {
      'lexend': ['Lexend', 'sans-serif'],
      'sans': ['Lexend', 'sans-serif'],
    },
    colors: {
      primary: {
        50: '#fef3c7',
        100: '#fde68a',
        500: '#fbbf24',
        600: '#f59e0b',
        700: '#d97706',
        900: '#78350f',
      },
      stone: {
        50: '#fafaf9',
        100: '#f5f5f4',
        200: '#e7e5e4',
        300: '#d6d3d1',
        400: '#a8a29e',
        500: '#78716c',
        600: '#57534e',
        700: '#44403c',
        800: '#292524',
        900: '#1c1917',
      },
      zinc: {
        800: '#27272a',
        900: '#18181b',
      },
      white: '#ffffff',
      black: '#000000',
    },
    animation: {
      float: 'float 6s ease-in-out infinite',
      slideUp: 'slideUp 0.5s ease-out',
      slideIn: 'slideIn 0.4s ease-out',
      fadeIn: 'fadeIn 0.4s ease-out',
      spin: 'spin 0.8s linear infinite',
    },
    keyframes: {
      float: {
        '0%, 100%': { transform: 'translateY(0px)' },
        '50%': { transform: 'translateY(-20px)' },
      },
      slideUp: {
        from: { opacity: '0', transform: 'translateY(20px)' },
        to: { opacity: '1', transform: 'translateY(0)' },
      },
      slideIn: {
          from: { opacity: '0', transform: 'translateX(-20px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'scale(0.9)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  plugins: [],
}
