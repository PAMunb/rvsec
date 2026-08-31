"""Neutralize the build-type suffix a Gradle build appends to the applicationId.

A release build declares `com.example.app`; the debug variant of the same source
tree declares `com.example.app.debug`. The classes are compiled under the source
package either way — `applicationIdSuffix` renames the *application*, not the
code — so a study that scopes app-owned classes by the declared applicationId
scopes 75 of the 162 corpus APKs by a package under which nothing was ever
compiled. That is not a small error: under such a key the class universe is
empty, and every coverage percentage divides by whatever survived a library
demotion by accident.

The rule lives in one function, in `rv-android-core`, and not in the GATOR argv
(D-2). Repeating a denylist whose subtleties are exactly the kind that drift —
case, repetition, a floor — on the Java side would create a second answer to the
same question. And neutralizing inside the argv builder rather than on `App`
would leave `App.code_package` reporting one key while GATOR used another, which
is the two-key problem this whole change exists to end.

The denylist is deliberately **not** total (INV-CORE-59). Forty of the 219
broad-corpus APKs are unresolvable by any string rule — `de.grobox.liberario`
ships as `de.grobox.transportr`, the thirteen `metadude` apps as
`nerd.tuxmobil.fahrplan.congress` — and no longer list closes that gap. The
backstop for those is the denominator gate (INV-ANA-69), which refuses an
implausible universe loudly, not a bigger list that fails silently.
"""

from __future__ import annotations

# Segments a Gradle `applicationIdSuffix` conventionally appends. Compared in
# lowercase, so `.BETA` and `.Debug` are covered by the lowercase entries.
BUILD_TYPE_DENYLIST = frozenset(
    {
        "debug",
        "dev",
        "beta",
        "staging",
        "qa",
        "nightly",
        "alpha",
        "snapshot",
        "current",
        "head",
        "indev",
    }
)

# An applicationId of one segment is not a package prefix anyone can scope by,
# and stripping down to it would turn a key into a namespace-wide wildcard —
# `com` would match every library in the Scene. Two segments is the floor.
MIN_SEGMENTS = 2


def neutralize_build_type_suffix(application_id: str) -> str:
    """Strip trailing build-type segments from a declared applicationId.

    Applied repeatedly, because suffixes stack: `com.example.app.qa.debug` is a
    single Gradle variant, not two. Compared in lowercase so `.BETA` is caught,
    while the returned value keeps the original spelling of what survives — the
    key must still match compiled class names, which are case-sensitive.

    Args:
        application_id: The declared applicationId, as the manifest carries it.

    Returns:
        The input with trailing denied segments removed, never reduced below
        `MIN_SEGMENTS`. Returned unchanged when no segment is denied, and when
        the input is malformed — a rule that cannot resolve a key says so by
        changing nothing, and the gate is what catches the consequence.
    """
    if not application_id:
        return application_id

    segments = application_id.split(".")
    while len(segments) > MIN_SEGMENTS and segments[-1].lower() in BUILD_TYPE_DENYLIST:
        segments.pop()
    return ".".join(segments)
