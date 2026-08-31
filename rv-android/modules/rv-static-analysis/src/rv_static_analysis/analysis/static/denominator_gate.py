"""The denominator gate — refuse a coverage denominator that cannot be right.

Every coverage percentage this pipeline publishes divides by the class list a
GATOR artefact carries. When that list collapses — the guard and the client
answering to different scope keys, a stale jar, a scope key no rule resolved —
the published number is not wrong in a way a reader can see: it is a small
percentage of a small denominator, which looks like an app that was barely
exercised. Four APKs of the 162-artefact corpus reached publication that way,
with denominators of 1, 2, 6 and 21 classes against universes of 762, 1952,
3578 and 535 (INV-ANA-69).

The gate is a pure predicate over the artefact. It divides the classes the
parser loaded by ``class_defs_under_key``, which the producer recorded already
**net** (INV-ANA-66): the compiled classes under the effective key that survive
``RvsecAnalysisClient.isAppClass`` — the same predicate that filtered the parsed
side. That is what lets this function merely divide. The subtraction cannot live
here: it holds a count, and filtering by name needs the names.

**What the threshold catches, once the guard is repaired.** With both sides
answering to one key, the ratio is 1.0 by construction, and the corpus
measurement found exactly that for all 158 healthy artefacts. A key no rule
resolved lands in the zero-universe branch, not the degenerate one. So the
degenerate branch fires on one live condition and it is a valuable one: a stale
jar — the client filtering by the new key while the guard still runs the old —
plus any future regression of INV-ANA-65. It is a tripwire on the repair, not a
discriminator over the corpus.
"""

from __future__ import annotations

from rv_android_core.domain.classes import Classes
from rv_android_core.util.error.exceptions import RVAndroidError

# Calibrated over the 162 corpus APKs (task 2.5): on the corrected ratio the 158
# healthy artefacts sit at exactly 1.0 and the four collapsed ones at 0.0010 to
# 0.0393, a 25x separation. 0.15 sits 3.8x above the collapsed ceiling and 6.7x
# below the healthy floor. The separation is invariant to the strip rule, because
# both terms of the ratio answer to isAppClass.
MIN_PARSED_RATIO = 0.15

# Appended to the artefact a refusal moves aside. Every consumer of the analysis
# finds the file by its exact name, so a suffix is what makes "refused" read as
# "absent" downstream while keeping the evidence for diagnosis.
REFUSED_ARTIFACT_SUFFIX = ".refused"


class DenominatorImplausibleError(RVAndroidError):
    """The artefact's class list cannot be the app's class universe.

    Defined here rather than imported from ``static_analysis``: that module
    imports this one to wire the gate, so importing its exception type back
    would close a cycle.
    """


def check_denominator(classes: Classes, compiled_under_key: int, key: str) -> None:
    """Refuse an empty, degenerate or universe-less denominator.

    Args:
        classes: What the parser loaded from the artefact's ``reachability``.
        compiled_under_key: ``class_defs_under_key`` as the artefact records it —
            already net of generated classes (INV-ANA-66).
        key: The effective scope key, for the message. A refusal that does not
            name the key it judged is not actionable.

    Raises:
        DenominatorImplausibleError: on an empty parsed side, on a ratio below
            ``MIN_PARSED_RATIO``, or on a zero compiled universe.
    """
    parsed = len(classes.classes)

    # Ordered before the division, and not merely to avoid ZeroDivisionError:
    # 0/0 is not a low ratio, it is no ratio. It is the signature of a key that
    # matches nothing compiled — the state of 75 of the 162 corpus APKs under
    # the literal manifest key, which is the condition the build-type suffix
    # policy exists to resolve before this gate judges anything.
    if compiled_under_key == 0:
        raise DenominatorImplausibleError(
            f"no compiled class lies under the scope key '{key}': the artefact "
            f"records class_defs_under_key=0, so there is no universe to measure "
            f"coverage against (parsed {parsed} classes)"
        )

    if parsed == 0:
        raise DenominatorImplausibleError(
            f"the artefact carries no class at all under the scope key '{key}', "
            f"against {compiled_under_key} compiled classes — every coverage "
            f"percentage computed from it would divide by zero and read as 0%"
        )

    ratio = parsed / compiled_under_key
    if ratio < MIN_PARSED_RATIO:
        raise DenominatorImplausibleError(
            f"denominator implausible for scope key '{key}': {parsed} parsed "
            f"classes against {compiled_under_key} compiled ones "
            f"(ratio {ratio:.4f} < {MIN_PARSED_RATIO}). Both counts answer to the "
            f"same filter, so a healthy artefact sits at 1.0; this is the "
            f"signature of a guard and a client reading different keys — check "
            f"that lib/gator/ carries the jar this run's key was resolved against"
        )
