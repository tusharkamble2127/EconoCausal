/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Volume II Chapter 9.7 color palette.
        brand: {
          primary: "#1F4E79",
          secondary: "#2E86AB",
          success: "#2E7D32",
          warning: "#ED6C02",
          danger: "#C62828",
          accent: "#7C3AED",
        },
      },
    },
  },
  plugins: [],
};
