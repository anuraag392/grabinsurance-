/** @type {import('tailwindcss').Config} */
export default {
    content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
    theme: {
        extend: {
            colors: {
                brand: {
                    50: '#f0f4ff',
                    100: '#e0e9ff',
                    400: '#5b8af5',
                    500: '#3b6ef7',
                    600: '#2555e8',
                    700: '#1a42c4',
                },
                surface: '#0f172a',
                card: '#1e293b',
                border: '#334155',
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
