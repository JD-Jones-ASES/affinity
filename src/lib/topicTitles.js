// Humanize a lesson/gym `topic` slug for breadcrumbs (QC 2026-07-09 C6). Topics are finer-grained than the
// curriculum tiers (a tier spans several), so this is a small explicit map with a sentence-case fallback for any
// topic added later. Mirrors the lessonTitles.js pattern: one shared source of truth the pages import, so the
// breadcrumb reads "Equilibrium & acid–base" instead of the raw "equilibrium" slug.
const TITLES = {
  "dimensional-analysis": "Dimensional analysis",
  nomenclature: "Ionic nomenclature",
  balancing: "Balancing equations",
  stoichiometry: "Stoichiometry",
  "reaction-families": "Reaction families",
  "periodic-trends": "Periodic trends",
  precipitation: "Precipitation",
  neutralization: "Neutralization",
  "percent-yield": "Percent yield",
  gases: "Gas laws",
  "gas-stoichiometry": "Gas stoichiometry",
  thermochemistry: "Thermochemistry",
  bonding: "Bonding & structure",
  equilibrium: "Equilibrium & acid–base",
  kinetics: "Kinetics",
  electrochemistry: "Electrochemistry",
};

export function topicTitle(slug) {
  if (!slug) return "";
  return TITLES[slug] ?? slug.replace(/-/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}
