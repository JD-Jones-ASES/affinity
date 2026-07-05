// Prefix an in-app path with the configured base (e.g. "/affinity/") so links and assets resolve on
// GitHub Pages project sites as well as local previews. Mirrors the sibling portals' base discipline.
const BASE = import.meta.env.BASE_URL; // "/affinity/" in production, "/" under LOCAL_ROOT.

export function withBase(path = "") {
  const tail = path.startsWith("/") ? path.slice(1) : path;
  return BASE.endsWith("/") ? BASE + tail : BASE + "/" + tail;
}
