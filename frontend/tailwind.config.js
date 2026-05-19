/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        nexus: { DEFAULT: "#534AB7", light: "#EEEDFE", dark: "#3C3489" },
      },
    },
  },
  plugins: [],
};
