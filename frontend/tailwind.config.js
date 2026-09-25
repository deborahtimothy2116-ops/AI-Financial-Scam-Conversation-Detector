/** Tailwind build config. Rebuild CSS with: npx tailwindcss@3 -c frontend/tailwind.config.js -i frontend/tailwind.input.css -o frontend/tailwind.css --minify */
module.exports = {
  content: [__dirname + "/index.html", __dirname + "/app.js"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "surface": "#faf8ff",
        "surface-dim": "#d2d9f4",
        "surface-bright": "#faf8ff",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f2f3ff",
        "surface-container": "#eaedff",
        "surface-container-high": "#e2e7ff",
        "surface-container-highest": "#dae2fd",
        "on-surface": "#131b2e",
        "on-surface-variant": "#434655",
        "outline": "#747686",
        "outline-variant": "#c4c5d7",
        "primary": "#0037b0",
        "primary-container": "#1d4ed8",
        "on-primary": "#ffffff",
        "on-primary-container": "#cad3ff",
        "primary-fixed": "#dce1ff",
        "primary-fixed-dim": "#b7c4ff",
        "secondary": "#4b41e1",
        "secondary-container": "#645efb",
        "on-secondary": "#ffffff",
        "secondary-fixed": "#e2dfff",
        "tertiary": "#004f35",
        "tertiary-container": "#006948",
        "on-tertiary": "#ffffff",
        "tertiary-fixed": "#85f8c4",
        "tertiary-fixed-dim": "#68dba9",
        "on-tertiary-fixed": "#002114",
        "on-tertiary-container": "#7ff2bd",
        "error": "#ba1a1a",
        "error-container": "#ffdad6",
        "on-error": "#ffffff",
        "on-error-container": "#93000a",
        "inverse-surface": "#283044",
        "inverse-on-surface": "#eef0ff",
      },
      fontFamily: {
        display: ["Plus Jakarta Sans", "sans-serif"],
        headline: ["Plus Jakarta Sans", "sans-serif"],
        body: ["Inter", "sans-serif"],
        code: ["Inter", "monospace"],
      }
    }
  }
};
