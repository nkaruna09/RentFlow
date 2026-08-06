// Tailwind configuration.
// TODO: define the RentFlow design tokens (colors, radii, typography) here,
// backed by the CSS custom properties declared in src/app/globals.css.

import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      // colors: {},
      // borderRadius: {},
      // fontFamily: {},
    },
  },
  plugins: [],
};

export default config;
