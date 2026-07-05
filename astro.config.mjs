import { defineConfig } from "astro/config";
import svelte from "@astrojs/svelte";

// Deployed to GitHub Pages as a project site at base path /affinity (ADR-0001, ADR-0010 — publish is the
// owner's call). `base` is applied to all built asset URLs; in-app links go through withBase() in
// src/lib/withBase.js. Set LOCAL_ROOT=1 to serve from "/" for local previews (production is a subpath).
const base = process.env.LOCAL_ROOT ? "/" : (process.env.PAGES_BASE ?? "/affinity");

// Dev/preview server port: honor the harness-assigned PORT env var, falling back to 4321. Only affects
// `astro dev`/`astro preview`; the static `astro build` ignores it.
const devPort = process.env.PORT ? Number(process.env.PORT) : 4321;

export default defineConfig({
  site: "https://jd-jones-ases.github.io",
  base,
  output: "static",
  trailingSlash: "always",
  // `css: "injected"` makes every Svelte component (incl. CHILD islands like ExtentBar/BeakerSpecies that are
  // imported and rendered *inside* SolutionPlayer) ship its scoped <style> via the JS chunk and inject it on
  // mount. Without this, Astro only delivers the CSS of top-level islands used directly in .astro pages, so the
  // nested interactives render unstyled. Known trap #2 (AGENTS.md); sibling ADR-0019.
  integrations: [svelte({ compilerOptions: { css: "injected" } })],
  server: { port: devPort },
});
