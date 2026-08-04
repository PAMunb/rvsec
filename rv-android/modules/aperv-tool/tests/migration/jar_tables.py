"""Read the jar's preset vectors and key-ownership table out of the ape source checkout.

The migration check has to know what a preset *contains* and what type each ``ape.*``
key carries, and there is exactly one authority for both: ``Presets.java`` and
``KeyOwnership.java`` on the ape side. This module parses them.

Parsing rather than vendoring a JSON copy is the whole point. A vendored copy would be a
second statement of what the ``mop`` preset contains, which is the duplication this change
exists to delete — and it would go stale silently, since nothing would compare it against
the jar again. Reading the Java keeps one authority and confines the coupling to tooling
that is deleted at sign-off.

The parser is deliberately shallow: regex over ``put(...)`` / ``base(...)`` /
``feature(...)`` lines, with just enough structure to follow the composition
(``mop()`` starts from ``aperv()``, ``llm_mop`` is ``mop()`` plus the LLM block). It has one
caller and a lifetime measured in this change, so a full Java parser would be complexity
bought for nobody. What it does NOT do is degrade: a file it cannot find, or a method whose
body yields nothing, raises. A parse failure that returned an empty preset would make the
regeneration diff pass by comparing nothing against nothing, which is the one outcome worse
than a crash.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

RUNTIME_PACKAGE = Path("src/main/java/com/android/commands/monkey/ape/runtime")
PRESETS_FILE = RUNTIME_PACKAGE / "Presets.java"
KEY_OWNERSHIP_FILE = RUNTIME_PACKAGE / "KeyOwnership.java"

# Presets.java. `private static Map<String, String> aperv() { ... }` — the preset
# building blocks.
_METHOD_RE = re.compile(
    r"private\s+static\s+Map<String,\s*String>\s+(\w+)\(\)\s*\{(.*?)\n    \}",
    re.DOTALL,
)
# `if (APERV.equals(name)) { ... }` — how resolve() wires a preset name to those blocks.
_BRANCH_RE = re.compile(
    r"if\s*\((\w+)\.equals\(name\)\)\s*\{(.*?)\n        \}",
    re.DOTALL,
)
# Both files name presets and keys through constants, so an identifier has to be resolved
# back to the literal it stands for before it means anything here.
_CONSTANT_RE = re.compile(r'public\s+static\s+final\s+String\s+(\w+)\s*=\s*"([^"]*)"')
# `Map<String, String> vector = aperv();`, `vector.putAll(llmBlock());` and `return mop();`
# all mean the same thing to us: fold that method's map in at this point.
_INHERIT_RE = re.compile(r"(?:=\s*|putAll\(|return\s+)(\w+)\(\)")
_PUT_RE = re.compile(r'\.put\("([^"]+)",\s*"([^"]*)"\)')

# KeyOwnership.java. The three ways the jar declares a key it accepts — unconditional,
# owned by a Feature, computed by a resolver — plus the graveyard of the ones it rejects.
_BASE_RE = re.compile(r'base\("([^"]+)",\s*ValueType\.(\w+),\s*(null|"[^"]*")\)')
_FEATURE_RE = re.compile(
    r'feature\(Feature\.(\w+),\s*"([^"]+)",\s*ValueType\.(\w+),\s*(null|"[^"]*")\)'
)
_RESOLVER_RE = re.compile(r"resolver\((\w+)\)")
_RETIRED_RE = re.compile(r'RETIRED\.put\("([^"]+)",')


@dataclass(frozen=True)
class KeySpec:
    """One ``ape.*`` key as the jar declares it: its type and its default.

    A plain dataclass rather than a Pydantic model on purpose (P1): it crosses no system
    boundary, has one producer and one consumer, and is deleted with the migration.

    Attributes:
        value_type: The jar's ``ValueType`` enum name as written in the Java —
            ``STRING``, ``BOOLEAN``, ``INT``, ``LONG``, ``DOUBLE``. Kept as text because
            its consumer, ``capture_arm_baseline.typed()``, dispatches on the name.
        default: The default as the Java source spells it (``"200"``, ``"-1.0"``), left
            untyped for the same reason. None when the declaration says ``null``, which
            means a key with no default — not one defaulting to the string "null".
    """

    value_type: str
    default: str | None


class JarTableError(RuntimeError):
    """The ape source could not be located or a table could not be parsed.

    Its own type so a caller cannot mistake a parse failure for an empty table.
    """


def resolve_ape_repo() -> Path:
    """Locate the ape source checkout: ``$APE_REPO``, else ``$RVSEC_HOME/ape``.

    Returns:
        The checkout root — the directory the other loaders take, not the Java file
        itself. The first candidate holding ``Presets.java`` wins, so ``$APE_REPO``
        overrides the ``$RVSEC_HOME`` fallback.

    Raises:
        JarTableError: when neither is set, or the path holds no stage-2 runtime package.
    """
    candidates: List[Path] = []
    if os.environ.get("APE_REPO"):
        candidates.append(Path(os.environ["APE_REPO"]))
    if os.environ.get("RVSEC_HOME"):
        candidates.append(Path(os.environ["RVSEC_HOME"]) / "ape")

    if not candidates:
        raise JarTableError(
            "no ape source checkout: set $APE_REPO to a checkout carrying "
            "rearch-02-runspec (or $RVSEC_HOME, whose ape/ subdirectory is tried)"
        )
    for candidate in candidates:
        if (candidate / PRESETS_FILE).is_file():
            return candidate
    raise JarTableError(
        f"none of {[str(c) for c in candidates]} holds {PRESETS_FILE} — "
        "point $APE_REPO at a stage-2 checkout"
    )


def _literal(java_literal: str) -> str | None:
    """A Java string literal or the bare token ``null`` as its Python value."""
    return None if java_literal == "null" else java_literal.strip('"')


def _read(ape_repo: Path, relative: Path) -> str:
    """Read one table file, reporting an unreadable path as JarTableError, not OSError."""
    path = ape_repo / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JarTableError(f"cannot read {path}: {exc}") from exc


def _evaluate(body: str, methods: Dict[str, str]) -> Dict[str, str]:
    """Fold one method body into a key vector, following its inherits in source order.

    Order matters: ``mop()`` inherits ``aperv()`` and then overrides, so a put encountered
    after an inherit must win over the inherited value.

    Args:
        body: The Java source of one method body, or of one ``resolve()`` branch — both
            are just lines carrying inherits and puts.
        methods: Every building-block method in the file, by name, so an inherit can be
            followed. A name absent from it is left alone rather than guessed at.

    Returns:
        ``{ape.key: text value}`` with inherited keys folded in and later puts winning.
    """
    vector: Dict[str, str] = {}
    for line in body.splitlines():
        inherited = _INHERIT_RE.search(line)
        if inherited and inherited.group(1) in methods:
            vector.update(_evaluate(methods[inherited.group(1)], methods))
            continue
        entry = _PUT_RE.search(line)
        if entry:
            vector[entry.group(1)] = entry.group(2)
    return vector


def load_presets(ape_repo: Path) -> Dict[str, Dict[str, str]]:
    """The four preset vectors, keyed by the name ``ape.preset`` accepts.

    Args:
        ape_repo: Checkout root, as :func:`resolve_ape_repo` returns it.

    Returns:
        preset name -> ``{ape.key: text value}``, values kept as the Java literal text
        (typing is the caller's job, through :func:`load_key_specs`).

    Raises:
        JarTableError: when a branch resolves to an empty vector — the shallow parser
            stopped matching the file's shape and a silent empty preset would make the
            regeneration diff vacuous.
    """
    source = _read(ape_repo, PRESETS_FILE)
    methods = {name: body for name, body in _METHOD_RE.findall(source)}
    constants = dict(_CONSTANT_RE.findall(source))

    presets: Dict[str, Dict[str, str]] = {}
    for constant, body in _BRANCH_RE.findall(source):
        name = constants.get(constant)
        if name is None:
            raise JarTableError(
                f"{PRESETS_FILE}: resolve() branches on unknown constant {constant}"
            )
        vector = _evaluate(body, methods)
        if not vector:
            raise JarTableError(
                f"{PRESETS_FILE}: preset '{name}' parsed to an empty vector"
            )
        presets[name] = vector

    if not presets:
        raise JarTableError(f"{PRESETS_FILE}: no preset branches found in resolve()")
    return presets


def load_key_specs(ape_repo: Path) -> Dict[str, KeySpec]:
    """Every ``ape.*`` key the jar accepts, with its declared type and default.

    Covers all three ownership kinds — base, feature-owned and resolver-owned — because
    acceptance is what the sweep in task 1.5 checks, and the jar accepts all three.

    Args:
        ape_repo: Checkout root, as :func:`resolve_ape_repo` returns it.

    Returns:
        ``{ape.key: KeySpec}``. Resolver-owned keys carry ``STRING`` with no default —
        the jar computes their value at run time, so there is nothing to read.

    Raises:
        JarTableError: when the table parses empty.
    """
    source = _read(ape_repo, KEY_OWNERSHIP_FILE)
    constants = dict(_CONSTANT_RE.findall(source))
    specs: Dict[str, KeySpec] = {}

    for key, value_type, default in _BASE_RE.findall(source):
        specs[key] = KeySpec(value_type, _literal(default))
    for _feature, key, value_type, default in _FEATURE_RE.findall(source):
        specs[key] = KeySpec(value_type, _literal(default))
    for constant in _RESOLVER_RE.findall(source):
        key = constants.get(constant)
        if key is None:
            raise JarTableError(
                f"{KEY_OWNERSHIP_FILE}: resolver() names unknown constant {constant}"
            )
        specs[key] = KeySpec("STRING", None)

    if not specs:
        raise JarTableError(f"{KEY_OWNERSHIP_FILE}: no key declarations found")
    return specs


def load_retired_keys(ape_repo: Path) -> Dict[str, str]:
    """The retired ``ape.*`` keys — those a properties file may no longer carry.

    The reason text is kept because a dead mapping entry is reported with the jar's own
    explanation of why it died, which is more useful than "not in the accepted set".

    Args:
        ape_repo: Checkout root, as :func:`resolve_ape_repo` returns it.

    Returns:
        ``{ape.key: reason}``, the reason being the jar's own retirement message with its
        Java string concatenation joined back into one line.

    Raises:
        JarTableError: when no retired key is found. The jar retires several, so an empty
            table means the parser stopped matching rather than that nothing is retired —
            and an empty one would make every dead mapping entry read as merely unknown.
    """
    source = _read(ape_repo, KEY_OWNERSHIP_FILE)
    retired: Dict[str, str] = {}
    for match in _RETIRED_RE.finditer(source):
        retired[match.group(1)] = _reason_after(source, match.end())
    if not retired:
        raise JarTableError(f"{KEY_OWNERSHIP_FILE}: no retired keys found")
    return retired


def _reason_after(source: str, start: int) -> str:
    """Join the Java string-concatenation that follows a ``RETIRED.put(key,`` up to its ``);``."""
    end = source.find(");", start)
    fragment = source[start:end] if end != -1 else source[start : start + 400]
    return " ".join(re.findall(r'"([^"]*)"', fragment)).strip()


def source_provenance(ape_repo: Path) -> Dict[str, str]:
    """What was read, so the migration record can name it rather than say "the ape source".

    The commit is best-effort — a checkout with no git metadata still yields usable
    digests, and the digests are what actually pin the content.

    Args:
        ape_repo: Checkout root, as :func:`resolve_ape_repo` returns it.

    Returns:
        Dictionary with keys:
        - "ape_repo" (str): The checkout that was read.
        - "commit" (str): Its ``HEAD``, or ``"unknown"`` when git cannot answer.
        - "Presets.java" (str): SHA-256 of the file as read.
        - "KeyOwnership.java" (str): SHA-256 of the file as read.
    """
    provenance: Dict[str, str] = {"ape_repo": str(ape_repo), "commit": "unknown"}
    try:
        provenance["commit"] = subprocess.run(
            ["git", "-C", str(ape_repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pass

    for relative in (PRESETS_FILE, KEY_OWNERSHIP_FILE):
        # Digest the same text the loaders parsed, through the same reader, so an
        # unreadable file fails as a JarTableError here too rather than as a bare OSError
        # — the provenance record must not be the one place the module's error contract
        # does not hold.
        digest = hashlib.sha256(_read(ape_repo, relative).encode("utf-8")).hexdigest()
        provenance[relative.name] = digest
    return provenance
