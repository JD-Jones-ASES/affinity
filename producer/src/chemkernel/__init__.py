"""ChemKernel — the build-time chemistry producer for Affinity.

Turns authored specs + curated data into verified, schema-shaped JSON. It REFUSES TO EMIT any object
that fails a check — formula parse, atom balance, charge balance, unit homogeneity, nonnegative extent,
missing badge (ADR-0008). "Verification breaks the build" at the source; CI re-gates the committed output.

The central emitted object is the species ledger over reaction extent (ADR-0002). This module tree grows
bottom-up: data (curated datasets) -> formula (parser) -> balance (conservation) -> extent/ledger -> emit.
"""

__version__ = "0.1.0"


class BuildError(Exception):
    """Loud, named build failure. The message must identify the species/reaction/step that failed."""
