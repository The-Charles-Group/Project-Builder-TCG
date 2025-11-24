/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Exact colors from main app - DO NOT MODIFY
        primary: {
          bg: '#0f1117',
          card: '#151a22',
          text: '#e6eaf2',
          muted: '#9aa4b2',
          border: '#232a35',
        },
        accent: {
          blue: '#6aa3ff',
          green: '#3ddc97',
        },
        input: {
          bg: '#0b0e13',
        },
        selection: {
          bg: '#1a2332',
          border: '#2a3a4a',
        },
      },
      fontFamily: {
        sans: ['system-ui', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
      },
      fontSize: {
        'base': '14px',
        'lg': '16px',
        'xl': '18px',
        '2xl': '20px',
      },
      lineHeight: {
        'base': '1.5',
      },
      borderRadius: {
        'card': '12px',
        'input': '8px',
        'button': '8px',
        'small': '6px',
      },
      spacing: {
        'card': '20px',
      },
    },
  },
  plugins: [],
}
