// dimension.mjs — the pure-Node mirror of chemkernel/dimension.py (ADR-0039). A shared, DEFINITIONAL
// unit -> SI-dimension table (the dimension of "atm" is a matter of SI structure, not an empirical value),
// used by validate-reference.mjs to RE-DERIVE the dimensional homogeneity of every formula-sheet entry from
// the emitted per-variable units + term factor powers — the ADR-0028 "emit the matrix, re-tally in Node"
// pattern applied to reference relations. If this table and dimension.py ever disagree on a unit, the two
// independent derivations diverge and the gate fails (as the two formula parsers must agree, ADR-0028).

// SI base dimensions, fixed order (luminous dropped; current kept for future electrochemistry).
export const BASES = ["mass", "length", "time", "amount", "temperature", "current"];
const N = BASES.length;

const mk = (o) => BASES.map((b) => o[b] ?? 0);

const ENERGY = mk({ mass: 1, length: 2, time: -2 });
const PRESSURE = mk({ mass: 1, length: -1, time: -2 });
const VOLUME = mk({ length: 3 });
const AMOUNT = mk({ amount: 1 });
const MASS = mk({ mass: 1 });
const TEMPERATURE = mk({ temperature: 1 });
const CONCENTRATION = mk({ length: -3, amount: 1 });
const MOLAR_MASS = mk({ mass: 1, amount: -1 });

export const DIMENSIONLESS = mk({});

// unit label -> SI dimension vector. Mirrors dimension.py `_UNIT_DIM` byte-for-byte.
const UNIT_DIM = {
  "": DIMENSIONLESS,
  "1": DIMENSIONLESS,
  "%": DIMENSIONLESS,
  mol: AMOUNT,
  "mol^-1": mk({ amount: -1 }),
  "1/mol": mk({ amount: -1 }),
  g: MASS,
  kg: MASS,
  mg: MASS,
  L: VOLUME,
  mL: VOLUME,
  M: CONCENTRATION,
  "mol/L": CONCENTRATION,
  "g/mol": MOLAR_MASS,
  "kg/mol": MOLAR_MASS,
  atm: PRESSURE,
  Pa: PRESSURE,
  kPa: PRESSURE,
  K: TEMPERATURE,
  J: ENERGY,
  kJ: ENERGY,
  "J/mol": mk({ mass: 1, length: 2, time: -2, amount: -1 }),
  "kJ/mol": mk({ mass: 1, length: 2, time: -2, amount: -1 }),
  "J/(g*K)": mk({ length: 2, time: -2, temperature: -1 }),
  "J/(mol*K)": mk({ mass: 1, length: 2, time: -2, amount: -1, temperature: -1 }),
  "L*atm/(mol*K)": mk({ mass: 1, length: 2, time: -2, amount: -1, temperature: -1 }),
};

export function unitDimension(unit) {
  if (!(unit in UNIT_DIM)) throw new Error(`unknown unit '${unit}'`);
  return UNIT_DIM[unit];
}

export const eq = (a, b) => a.length === N && b.length === N && a.every((x, i) => x === b[i]);

export function addScaled(total, dim, power) {
  return total.map((x, i) => x + dim[i] * power);
}
