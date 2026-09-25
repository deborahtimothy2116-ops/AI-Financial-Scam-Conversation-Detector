/** Tailwind build config. Rebuild CSS with: npx tailwindcss@3 -c frontend/tailwind.config.js -i frontend/tailwind.input.css -o frontend/tailwind.css --minify */
// Enterprise palette: neutral greys, one business-blue accent, and status colours used only for status.
module.exports = {
  content: [__dirname + "/index.html", __dirname + "/app.js"],
  theme: {
    extend: {
      colors: {
        "surface": "#f4f6f8",                  // page background
        "surface-container-lowest": "#ffffff", // panels
        "surface-container-low": "#f7f8fa",
        "surface-container": "#eef1f4",
        "surface-container-high": "#e3e8ee",
        "surface-container-highest": "#d9e0e8",
        "on-surface": "#1d2733",
        "on-surface-variant": "#556170",
        "outline": "#8a95a3",
        "outline-variant": "#d5dbe3",
        "shell": "#1d2d3e",                    // top shell bar
        "shell-muted": "#9aa7b6",
        "primary": "#0a5dc2",
        "primary-container": "#084c9e",        // hover / pressed
        "on-primary": "#ffffff",
        "primary-fixed": "#e6f0fb",            // selected / tint
        "primary-fixed-dim": "#b9d3f2",
        "tertiary": "#107e3e",                 // positive
        "tertiary-container": "#e8f4ec",
        "on-tertiary": "#ffffff",
        "on-tertiary-container": "#0b5a2c",
        "tertiary-fixed": "#cfe9d8",
        "on-tertiary-fixed": "#0b5a2c",
        "error": "#bb0000",                    // negative
        "error-container": "#fdecec",
        "on-error": "#ffffff",
        "on-error-container": "#8a0000",
        "inverse-surface": "#1d2d3e",
        "inverse-on-surface": "#f4f6f8",
      },
      fontFamily: {
        display: ["Inter", "system-ui", "sans-serif"],
        headline: ["Inter", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        code: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
};
