// Curriculum ordering — the single source of truth for how lessons and gyms are SEQUENCED for a learner
// (QC 2026-07-09 C1). The indexes previously sorted alphabetically, so a first-timer met "Bonding" before the
// mole and the buffer lesson before the weak-acid one it builds on. This groups both indexes under tier headers
// in the natural first-year-chemistry progression, mirroring the ROADMAP tiers and the species-ledger thesis arc
// (recipes → the ledger underneath, tier by tier). Owner-chosen: curriculum-tier order, a curated frontend map
// (this file), and bidirectional lesson↔gym cross-links. Adding a lesson/gym? Add its slug to a tier below — the
// build-time assertComplete() FAILS THE BUILD if any shipped slug is missing here, so nothing silently drops out.

// Ordered tiers. `lessons` / `gyms` are slugs in intra-tier learning order.
export const TIERS = [
  {
    id: "foundations",
    title: "Foundations — the mole, naming, and balancing",
    blurb: "The accounting every reaction rests on: converting amounts, naming compounds, balancing equations, and tracking who runs out. Start here.",
    gyms: ["solution-conversions", "ionic-compounds", "periodic-trends", "balance-equations", "reaction-families", "mass-stoichiometry", "limiting-reagent", "percent-yield"],
    lessons: ["calcium-carbonate-limiting", "calcium-phosphate-limiting", "zinc-carbonate-percent-yield", "hydrochloric-sodium-hydroxide"],
  },
  {
    id: "gases-thermochemistry",
    title: "Gases & thermochemistry",
    blurb: "The ledger under two more constraints: a gas volume from PV = nRT, and the heat a reaction releases via Hess's law.",
    gyms: ["gas-laws", "calorimetry"],
    lessons: ["zinc-hydrochloric-hydrogen", "methane-combustion-enthalpy"],
  },
  {
    id: "bonding-structure",
    title: "Bonding & structure",
    blurb: "Why molecules take the shapes they do: the Lewis electron ledger, VSEPR geometry, polarity, and the forces between molecules.",
    gyms: ["lewis-structures"],
    lessons: ["water-molecular-shape", "carbon-dioxide-molecular-shape", "boiling-points-and-imfs"],
  },
  {
    id: "equilibrium-acid-base",
    title: "Equilibrium & acid–base",
    blurb: "The ledger's extent solved from mass action, not the limiting reagent: weak-acid and weak-base pH, buffers, polyprotic acids, solubility, titration, and precipitation prediction.",
    gyms: ["weak-acid-ph"],
    lessons: ["acetic-acid-ph", "ammonia-ph", "acetate-buffer", "phosphoric-acid-ph", "calcium-fluoride-solubility", "calcium-fluoride-common-ion", "acetic-acid-titration", "calcium-fluoride-precipitation", "magnesium-hydroxide-no-precipitate"],
  },
  {
    id: "kinetics",
    title: "Kinetics — the ledger in time",
    blurb: "The extent evolving in time. Three orders, one contrast: what a constant half-life actually means.",
    gyms: ["kinetics"],
    lessons: ["hydrogen-peroxide-decomposition", "butadiene-dimerization", "ammonia-decomposition"],
  },
  {
    id: "electrochemistry",
    title: "Electrochemistry — the electron ledger",
    blurb: "The ledger with electrons as the tracked quantity: oxidation numbers, half-reactions, cell potential, and free energy per charge.",
    gyms: [],
    lessons: ["daniell-cell"],
  },
];

// Per-lesson related gyms (the practice that drills that lesson's skills). The reverse map (gym → lessons) is
// derived from this, so associations live in one place.
export const lessonGyms = {
  "calcium-carbonate-limiting": ["limiting-reagent", "balance-equations", "reaction-families"],
  "calcium-phosphate-limiting": ["limiting-reagent", "mass-stoichiometry"],
  "zinc-carbonate-percent-yield": ["percent-yield", "mass-stoichiometry"],
  "hydrochloric-sodium-hydroxide": ["limiting-reagent", "reaction-families"],
  "zinc-hydrochloric-hydrogen": ["gas-laws", "mass-stoichiometry"],
  "methane-combustion-enthalpy": ["calorimetry"],
  "water-molecular-shape": ["lewis-structures"],
  "carbon-dioxide-molecular-shape": ["lewis-structures"],
  "boiling-points-and-imfs": ["lewis-structures"],
  "acetic-acid-ph": ["weak-acid-ph"],
  "ammonia-ph": ["weak-acid-ph"],
  "acetate-buffer": ["weak-acid-ph"],
  "phosphoric-acid-ph": ["weak-acid-ph"],
  "calcium-fluoride-solubility": ["weak-acid-ph"],
  "calcium-fluoride-common-ion": ["weak-acid-ph"],
  "acetic-acid-titration": ["weak-acid-ph"],
  "calcium-fluoride-precipitation": ["weak-acid-ph"],
  "magnesium-hydroxide-no-precipitate": ["weak-acid-ph"],
  "hydrogen-peroxide-decomposition": ["kinetics"],
  "butadiene-dimerization": ["kinetics"],
  "ammonia-decomposition": ["kinetics"],
  "daniell-cell": [],
};

// gym slug → lesson slugs that use it (inverse of lessonGyms), in curriculum order.
const lessonOrder = TIERS.flatMap((t) => t.lessons);
export const gymLessons = {};
for (const [lesson, gyms] of Object.entries(lessonGyms))
  for (const g of gyms) (gymLessons[g] ??= []).push(lesson);
for (const g of Object.keys(gymLessons))
  gymLessons[g].sort((a, b) => lessonOrder.indexOf(a) - lessonOrder.indexOf(b));

// Fail the build if any shipped lesson/gym slug is not placed in a tier (so a new one can't silently vanish from
// the ordered indexes). Called from the index pages with the actual globbed slugs.
export function assertComplete(lessonSlugs, gymSlugs) {
  const placedLessons = new Set(TIERS.flatMap((t) => t.lessons));
  const placedGyms = new Set(TIERS.flatMap((t) => t.gyms));
  const missingL = [...lessonSlugs].filter((s) => !placedLessons.has(s));
  const missingG = [...gymSlugs].filter((s) => !placedGyms.has(s));
  const strayL = [...placedLessons].filter((s) => !lessonSlugs.includes(s));
  const strayG = [...placedGyms].filter((s) => !gymSlugs.includes(s));
  const problems = [];
  if (missingL.length) problems.push(`lessons not placed in any curriculum tier: ${missingL.join(", ")}`);
  if (missingG.length) problems.push(`gyms not placed in any curriculum tier: ${missingG.join(", ")}`);
  if (strayL.length) problems.push(`curriculum lists lessons that do not exist: ${strayL.join(", ")}`);
  if (strayG.length) problems.push(`curriculum lists gyms that do not exist: ${strayG.join(", ")}`);
  if (problems.length) throw new Error(`src/lib/curriculum.js out of sync — ${problems.join("; ")}`);
}
