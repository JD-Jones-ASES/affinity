// Shared slug → title map across ALL SEVEN lesson kinds (reaction/structure/comparison/equilibrium/prediction/
// kinetics/electrochemistry). The five Atlas reference pages use it to label "Used in" cross-links with the
// human lesson title instead of the raw slug — previously each page globbed only solution/structure/comparison,
// so the four newer kinds degraded to raw slugs (QC 2026-07-09 C3). One source of truth; add a kind here and
// every reference page picks it up. Paths are relative to this file (src/lib/).
const modules = {
  ...import.meta.glob("../../derived/**/*.solution.json", { eager: true }),
  ...import.meta.glob("../../derived/**/*.structure.json", { eager: true }),
  ...import.meta.glob("../../derived/**/*.comparison.json", { eager: true }),
  ...import.meta.glob("../../derived/**/*.equilibrium.json", { eager: true }),
  ...import.meta.glob("../../derived/**/*.prediction.json", { eager: true }),
  ...import.meta.glob("../../derived/**/*.kinetics.json", { eager: true }),
  ...import.meta.glob("../../derived/**/*.electrochemistry.json", { eager: true }),
};

export const lessonTitles = Object.fromEntries(
  Object.values(modules).map((m) => [m.default.slug, m.default.title]),
);
