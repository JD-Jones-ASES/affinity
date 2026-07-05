// formula.mjs — a pure JS port of ChemKernel's grammar-v0 formula parser (ADR-0014), for the Node gates.
// Independent of the Python producer: given a formula STRING it returns element counts + signed charge, so a
// gate can re-derive a species' composition and cross-check it against the emitted data (the honesty check
// ADR-0023 flagged as future work; the balancing gate, ADR-0028, is the first user). Grammar v0: elements
// [A-Z][a-z]?, integer subscripts, nested (...) groups with subscripts, a trailing caret charge (^2-, ^+),
// and an optional trailing phase (s|l|g|aq). Hydrates/isotopes are out of scope, as in Python.

const PHASE_RE = /\((s|l|g|aq)\)$/;
const CHARGE_RE = /\^(\d*)([+-])$/;
const ELEMENT_RE = /^[A-Z][a-z]?/;

// Parse a formula string -> { counts: {element: integer}, charge: integer }. Throws on any malformed input,
// exactly where the Python parser would raise (so a bad emitted formula fails the gate loud).
export function parseFormula(text) {
  let body = String(text).trim();
  if (!body) throw new Error("empty formula");

  const ph = body.match(PHASE_RE);
  if (ph) body = body.slice(0, ph.index);

  let charge = 0;
  const cm = body.match(CHARGE_RE);
  if (cm) {
    const magnitude = cm[1] ? parseInt(cm[1], 10) : 1;
    charge = cm[2] === "+" ? magnitude : -magnitude;
    body = body.slice(0, cm.index);
  }
  if (!body) throw new Error(`formula '${text}' has a charge/phase but no chemical body`);

  const counts = parseBody(body, text);
  return { counts, charge };
}

function parseBody(body, raw) {
  const stack = [{}];
  let i = 0;
  const n = body.length;
  while (i < n) {
    const c = body[i];
    if (c === "(") {
      stack.push({});
      i += 1;
    } else if (c === ")") {
      i += 1;
      let j = i;
      while (j < n && body[j] >= "0" && body[j] <= "9") j += 1;
      const mult = j > i ? parseInt(body.slice(i, j), 10) : 1;
      i = j;
      if (stack.length === 1) throw new Error(`unbalanced ')' in '${raw}'`);
      const group = stack.pop();
      const top = stack[stack.length - 1];
      for (const [el, k] of Object.entries(group)) top[el] = (top[el] || 0) + k * mult;
    } else {
      const m = body.slice(i).match(ELEMENT_RE);
      if (!m) throw new Error(`unexpected character '${c}' in '${raw}'`);
      const el = m[0];
      i += el.length;
      let j = i;
      while (j < n && body[j] >= "0" && body[j] <= "9") j += 1;
      const sub = j > i ? parseInt(body.slice(i, j), 10) : 1;
      i = j;
      const top = stack[stack.length - 1];
      top[el] = (top[el] || 0) + sub;
    }
  }
  if (stack.length !== 1) throw new Error(`unbalanced '(' in '${raw}'`);
  if (Object.keys(stack[0]).length === 0) throw new Error(`no elements parsed from '${raw}'`);
  return stack[0];
}
