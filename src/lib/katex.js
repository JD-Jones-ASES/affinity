// Build-time KaTeX rendering. Used in Astro frontmatter to turn LaTeX into HTML so the player islands
// never ship KaTeX to the browser (ADR-0001). The check:katex gate guarantees every string renders, so
// throwOnError can stay false here (a survived string is known-good).
import katex from "katex";

export function tex(latex, displayMode = true) {
  return katex.renderToString(latex, { throwOnError: false, displayMode });
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Lightweight markdown emphasis on already-HTML-escaped, non-math text: **bold** -> <strong>, *italic* -> <em>.
// Bold is matched first so a `**x**` doesn't leave stray single asterisks.
function emphasize(s) {
  return s
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

// Plain-text projection of an authored string: drop the $…$ math delimiters and **emphasis** markers, keeping
// the readable text. Used for meta descriptions and list previews so authoring markup never leaks into
// SEO/social snippets (the on-page copy is rendered separately by inline()).
export function plain(s) {
  if (s == null) return s;
  return String(s)
    .replace(/\$([^$]+)\$/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1");
}

// Render a prose string that may contain inline math delimited by $...$, returning HTML. Math segments become
// inline KaTeX; the surrounding text is HTML-escaped and gets markdown emphasis. Used for scenarios, claims,
// notes, labels — anywhere math may sit inside a sentence.
export function inline(s) {
  if (s == null) return s;
  const parts = String(s).split(/(\$[^$]+\$)/g);
  let out = "";
  for (const part of parts) {
    const isMath = part.length > 2 && part.startsWith("$") && part.endsWith("$");
    if (isMath) {
      out += katex.renderToString(part.slice(1, -1), { throwOnError: false, displayMode: false });
    } else {
      out += emphasize(escapeHtml(part));
    }
  }
  return out;
}
