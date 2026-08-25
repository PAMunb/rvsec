#!/usr/bin/env python3
"""G-SIG, G-FORB and G-BIND: three classes of specification defect the gate layer missed.

Each of the three is here because an audit found an instance of it that had survived
every gate the change already had, and each is decidable from artifacts the tree
already carries -- the `.mop`, the platform jar, the CrySL rule.

**G-SIG -- the pointcut names a signature the platform does not declare.**
`SSLContextSpec.mop` declared `call(public void SSLContext.createSSLEngine(..))`
where android-30 declares `public final SSLEngine createSSLEngine()`. Both weavers
gate the return type exactly, so the advice was generated and never fired: an event
that is present in the automaton, present in the monitor, and dead. Nine task groups
read that file without seeing it, because nothing compared a `call(...)` against the
platform.

The gate's design carries three guards, each of which a naive version gets wrong:

1. **Class presence is read from the jar's own zip entries, never from `javap`.**
   `javap` resolves `java.*` and `javax.*` from the running JDK's own modules
   whatever `-cp` says, and neither `--system none` nor `-bootclasspath` stops it on
   a modular JDK. Measured on `javax.xml.crypto.dsig.spec.HMACParameterSpec`: javap
   reports it present while android-30.jar has zero entries under `javax/xml/crypto`.
   A gate that asked javap would greenlight precisely the class the record already
   knows is absent, which is the worst possible failure for a gate whose job is to
   notice absences.
2. **A member declared on a supertype resolves through the hierarchy.**
   `SecretKey.getEncoded` is declared on `Key`, and `SecureRandom.nextInt`/`ints` on
   `Random`; a gate that read only the named class would report three findings that
   are correct code. They are the DEX-residue family of `conformance_record.csv:73`.
3. **A nested type compares on its binary name**, `KeyStore$ProtectionParameter`,
   because that is what the jar holds and what `javap` prints.

**G-FORB -- a `FORBIDDEN` clause with no accusing event.** `PBEKeySpec`'s two
constructors are implemented, with `ErrorType.ForbiddenMethod` and codes of their
own; `SSLContext.getDefault()` is not, and `SSLContext.getDefault().createSSLEngine()`
is silent. The gate is **scoped to rules that have a `.mop` in the set under test**,
and the scope is load-bearing rather than cosmetic: each oracle carries **four**
rules with a `FORBIDDEN` section, not two -- `DigestInputStream` and
`DigestOutputStream` state `FORBIDDEN on(...)` and have no specification here, being
among the 27 rules out of scope for this change. Unscoped, the gate is born red on
clauses no task owns and no reader can act on. Those clauses are reported as declared
skips and counted, so the scope is visible instead of silent.

**G-BIND -- an event of a parametric specification that binds no monitored object.**
A specification declares its parameter -- `PBEKeySpecSpec(PBEKeySpec s)` -- and the
generator indexes monitors by it. An event that names no object of that type in
`returning(...)` or `target(...)` is handed the parameterless map instead, so its
body runs on the root monitor and on every live monitor of the specification: a
set-wide broadcast where the rule speaks about one object. `MacSpec.f2` was one
(repaired at task 5.3) and `PBEKeySpecSpec.f1`/`f2` were the last two (task 9.3). A
three-line check would have caught all three the day they were written.

Every gate satisfies the genericity contract of this change: it runs over the
enumerated universe of specification sets, derives its counts by enumeration rather
than asserting a literal, and declares what it skipped and why.

Usage:
    uv run python scripts/gh105_spec_gates.py --sets all
    uv run python scripts/gh105_spec_gates.py --sets jca_android --gate G-SIG --json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gh105_predicate_graph import (  # noqa: E402
    SPECIFICATION_SETS,
    MopSource,
    _find_body_brace,
    _match_delimiter,
    read_mop,
)

REPO = Path(__file__).resolve().parents[1]
REACTOR = REPO.parent
DEFAULT_SPECS_ROOT = REACTOR / "rvsec/rvsec-mop/src/main/resources"

# The two oracles, in the division D-15 settled: the pinned expert copy answers for
# values, the generated api30 rules for ORDER, alphabets and predicates. `FORBIDDEN`
# is neither -- it names a call the rule turns down outright -- so G-FORB reads both
# and requires an accusing event for a clause either of them states.
DEFAULT_EXPERT_RULES = REACTOR.parent / "RVSec-replication-package/tools/rules"
DEFAULT_API30_RULES = REACTOR.parent / "MetaCrySL/generated/api30"

RULE_EXTENSIONS = (".crysl", ".cryptsl")

# Which platform each set's pointcuts are written against. G-SIG compares a
# signature to a jar, so a set whose specifications answer to a different platform
# is outside its reach and says so, rather than reporting every class the jar does
# not carry. The mapping is written down instead of inferred, for the reason
# `order_alphabet_map.csv` is written down: a heuristic guess here is a wrong
# verdict in both directions, and the wrong direction is the silent one.
#
# `generic` and `generic_new` are JSE specifications -- Swing, JMX, `java.util` --
# and the platform they answer to is the JDK. This gate deliberately has no JDK
# oracle: `javap` resolves `java.*`/`javax.*` from the running JDK's own modules
# whatever the classpath says, which is exactly the fallback G-SIG exists to
# refuse, and a jar for the JDK the monitors are woven against is not in the tree.
# So they are declared skips, counted, and not silently green.
SET_PLATFORMS = {
    "jca": "android-30",
    "jca_android": "android-30",
    "jca_android_bug_predicate": "android-30",
    "generic": "",
    "generic_new": "",
}

# `event <name>` with the modifiers JavaMOP admits before it. Mirrors the scanner of
# `gh105_predicate_graph`, because an event this file missed is a check that silently
# did not run.
_EVENT_DECL = re.compile(r"\b(?:(?:creation|unsync|blocking)\s+)*event\s+(?P<name>\w+)\b")

# `call ( ... )` with the whitespace and line breaks the set actually uses. The body
# is delimiter-matched rather than regex-matched: a signature holds parentheses of
# its own, and `(..)` inside `(..)` is the common case.
_CALL = re.compile(r"\bcall\s*\(")
_RETURNING = re.compile(r"\breturning\s*\(")
_TARGET = re.compile(r"\btarget\s*\(")

# `public static SSLContext SSLContext.getInstance(String, String)` and
# `public PBEKeySpec.new(char[])`, after the modifiers have been stripped. The
# constructor form is what JavaMOP writes for `new`, and it declares no return type.
_MODIFIERS = ("public", "protected", "private", "static", "final", "abstract", "synchronized", "native")

# `import javax.crypto.spec.PBEKeySpec;` -- how a simple name in a pointcut becomes
# the binary name the jar is indexed by.
_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?(?P<fqn>[\w.$]+)\s*;", re.MULTILINE)

# The packages a JCA specification names without importing, because `java.lang` is
# implicit and the rest are the platform's own.
_IMPLICIT_PACKAGES = ("java.lang", "java.security", "javax.crypto", "java.util", "java.io")

# What `..` and `Object+` mean to the arity comparison: both stand for "any number of
# arguments from here", so a signature carrying either is compared on its fixed
# prefix and its arity is a lower bound rather than a number.
_WILDCARD_ARGUMENTS = ("..",)


# --------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One defect, named where a reader can act on it.

    Attributes:
        gate: `G-SIG`, `G-FORB` or `G-BIND`.
        spec_set: Specification set the subject belongs to.
        spec: Specification file stem.
        subject: The event, clause or signature the finding is about.
        message: What is wrong, in the terms the repair would use.
    """

    gate: str
    spec_set: str
    spec: str
    subject: str
    message: str


@dataclass
class GateRun:
    """What one gate saw over one selection of sets.

    Attributes:
        checked: Subjects the gate actually compared -- the denominator that makes
            a green run mean something. A gate that checked nothing is a gate that
            found nothing, and the two must not print the same.
        findings: The defects.
        notes: Facts worth reporting that are not defects: a member resolved
            through a supertype, a class the record already knows is absent.
        skipped: `(subject, reason)` for every comparison the gate declined, so the
            scope of a green verdict is on the report rather than in this file.
        allowlisted: Findings a row of `gate_allowlist.csv` accounts for. They are
            real and are reported; what the row buys is that they do not fail the
            run, which is how this change already carries G-ORDER's nine kept
            divergences.
    """

    checked: int = 0
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    allowlisted: list[Finding] = field(default_factory=list)


# --------------------------------------------------------------------------
# reading the specification set
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Pointcut:
    """One `call(...)` of one event, parsed into what the platform can be asked.

    Attributes:
        spec: Specification file stem.
        event: Event declaring the pointcut.
        line: 1-based line of the `call` keyword.
        raw: The signature as written, whitespace collapsed.
        return_type: Declared return type, empty for a constructor.
        owner: The type the member is looked up on, as written in the pointcut.
        member: Method name, or `new` for a constructor.
        arguments: Declared argument types, in order.
        variadic: Whether the signature ends in `..`, so arity is a lower bound.
    """

    spec: str
    event: str
    line: int
    raw: str
    return_type: str
    owner: str
    member: str
    arguments: tuple[str, ...]
    variadic: bool


def _balanced(neutral: str, open_paren: int) -> int:
    """Offset just past the `)` that closes the `(` at `open_paren`."""
    return _match_delimiter(neutral, open_paren, "(", ")")


def _split_types(text: str) -> list[str]:
    """Argument types at depth zero, generics and arrays kept whole."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for char in text:
        if char in "(<[":
            depth += 1
        elif char in ")>]":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return [part for part in parts if part]


def parse_signature(spec: str, event: str, line: int, body: str) -> Pointcut | None:
    """`public void SSLContext.createSSLEngine(..)` into its parts.

    Returns None for a signature this parser cannot decompose, which the caller
    records as a skip rather than as a pass: a signature nobody parsed is a
    signature nobody checked.
    """
    text = " ".join(body.split())
    open_paren = text.find("(")
    if open_paren < 0:
        return None
    head = text[:open_paren].strip()
    arguments_text = text[open_paren + 1 : text.rfind(")")]

    words = [word for word in head.split() if word not in _MODIFIERS]
    if not words:
        return None
    qualified = words[-1]
    return_type = words[-2] if len(words) >= 2 else ""

    if "." not in qualified:
        return None
    owner, _, member = qualified.rpartition(".")

    arguments = _split_types(arguments_text)
    variadic = any(argument in _WILDCARD_ARGUMENTS for argument in arguments)
    fixed = tuple(argument for argument in arguments if argument not in _WILDCARD_ARGUMENTS)

    return Pointcut(
        spec=spec,
        event=event,
        line=line,
        raw=text,
        return_type=return_type,
        owner=owner,
        member=member,
        arguments=fixed,
        variadic=variadic,
    )


@dataclass
class SpecFile:
    """One `.mop` read for the three gates.

    Attributes:
        source: The parse `gh105_predicate_graph` produces, reused rather than
            repeated: a second parser is a second set of bugs.
        headers: Event name to the header text between the declaration and the
            body brace, which is where `call`, `returning` and `target` live.
        pointcuts: Every `call(...)` of the file, parsed.
        unparsed: `(event, signature)` for every `call(...)` this file could not
            decompose.
    """

    source: MopSource
    headers: dict[str, tuple[str, int]] = field(default_factory=dict)
    pointcuts: list[Pointcut] = field(default_factory=list)
    unparsed: list[tuple[str, str]] = field(default_factory=list)


def read_spec(path: Path) -> SpecFile:
    """Parse one `.mop` and pull out every event header and every `call(...)`."""
    source = read_mop(path)
    spec_file = SpecFile(source=source)
    if source.parse_error:
        return spec_file

    neutral = source.neutral
    stem = path.stem
    for match in _EVENT_DECL.finditer(neutral):
        brace = _find_body_brace(neutral, match.end(), len(neutral))
        if brace < 0:
            continue
        header = neutral[match.end() : brace]
        spec_file.headers[match.group("name")] = (header, source.line_of(match.start()))

        for call in _CALL.finditer(header):
            open_paren = match.end() + call.end() - 1
            close = _balanced(neutral, open_paren)
            body = neutral[open_paren + 1 : close - 1]
            line = source.line_of(open_paren)
            pointcut = parse_signature(stem, match.group("name"), line, body)
            if pointcut is None:
                spec_file.unparsed.append((match.group("name"), " ".join(body.split())))
            else:
                spec_file.pointcuts.append(pointcut)
    return spec_file


def read_set(set_dir: Path) -> list[SpecFile]:
    """Every `.mop` of one set, in name order."""
    return [read_spec(path) for path in sorted(set_dir.glob("*.mop"))]


# --------------------------------------------------------------------------
# the platform jar
# --------------------------------------------------------------------------


class AndroidJar:
    """The platform, asked about classes through its zip and about members through javap.

    The split is the whole point. `javap` is a resolver: handed a class it cannot
    find on the classpath it falls back to the JDK's own modules and prints their
    declaration, so it can never answer "absent" for anything under `java.*` or
    `javax.*`. The jar's central directory can, because it is a list.
    """

    def __init__(self, jar: Path) -> None:
        self.jar = jar
        with zipfile.ZipFile(jar) as archive:
            self.entries = {
                name[: -len(".class")].replace("/", ".")
                for name in archive.namelist()
                if name.endswith(".class")
            }
        self._members: dict[str, list[str]] = {}
        self._supertypes: dict[str, list[str]] = {}

    def resolve(self, simple_or_binary: str, imports: dict[str, str]) -> str | None:
        """A name as a pointcut writes it, into the binary name the jar holds.

        Args:
            simple_or_binary: `SSLContext`, `javax.net.ssl.SSLContext`, or the
                nested `KeyStore.ProtectionParameter`.
            imports: Simple name to fully qualified name, from the file's imports.

        Returns:
            The binary name if the jar declares it, otherwise None.
        """
        if simple_or_binary in self.entries:
            return simple_or_binary

        candidates: list[str] = []
        head, _, tail = simple_or_binary.partition(".")
        if tail:
            # `KeyStore.ProtectionParameter` is `...KeyStore$ProtectionParameter`.
            outer = imports.get(head)
            if outer:
                candidates.append(f"{outer}${tail.replace('.', '$')}")
        if simple_or_binary in imports:
            candidates.append(imports[simple_or_binary])
        for package in _IMPLICIT_PACKAGES:
            candidates.append(f"{package}.{simple_or_binary}")

        for candidate in candidates:
            if candidate in self.entries:
                return candidate
        return None

    def _javap(self, binary: str) -> list[str]:
        """`javap` output for a class the zip has already confirmed present.

        Only ever called after `resolve` said yes, which is what keeps javap's
        fallback to the JDK's modules out of the verdict.
        """
        if binary in self._members:
            return self._members[binary]
        result = subprocess.run(
            ["javap", "-cp", str(self.jar), binary],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = result.stdout.splitlines() if result.returncode == 0 else []
        self._members[binary] = lines
        return lines

    def supertypes(self, binary: str) -> list[str]:
        """The class's own extends/implements chain, as far as the jar carries it."""
        if binary in self._supertypes:
            return self._supertypes[binary]
        chain: list[str] = []
        for line in self._javap(binary):
            if "class " in line or "interface " in line:
                for keyword in ("extends", "implements"):
                    if keyword in line:
                        tail = line.split(keyword, 1)[1]
                        tail = tail.split("{")[0]
                        for name in tail.replace(",", " ").split():
                            if name in ("extends", "implements"):
                                continue
                            if name in self.entries:
                                chain.append(name)
                break
        self._supertypes[binary] = chain
        return chain

    def declarations(self, binary: str, member: str) -> list[str]:
        """Every `javap` line declaring `member` on `binary` itself.

        `javap` prints a constructor under the class's own fully qualified name --
        `public javax.crypto.spec.PBEKeySpec(char[]);` -- and a method under its bare
        name, so the two are matched differently. Getting this wrong is not a
        near-miss: it reports every constructor pointcut of the set as unweavable,
        which is 15 findings that are all correct code.
        """
        found = []
        for line in self._javap(binary):
            stripped = line.strip()
            if "(" not in stripped:
                continue
            head = stripped.split("(")[0].split()
            if not head:
                continue
            if member == "new":
                if head[-1] == binary:
                    found.append(stripped)
            elif head[-1] == member:
                found.append(stripped)
        return found


# --------------------------------------------------------------------------
# G-SIG
# --------------------------------------------------------------------------


def _return_type_of(declaration: str, member: str) -> str:
    """The declared return type in a `javap` line, as `javap` spells it."""
    head = declaration.split(f" {member}(")[0]
    words = [word for word in head.split() if word not in _MODIFIERS]
    return words[-1] if words else ""


def _same_type(pointcut_type: str, javap_type: str) -> bool:
    """Two spellings of one type: the pointcut's simple name against javap's.

    A pointcut writes `SSLEngine` where javap writes `javax.net.ssl.SSLEngine`, and
    both write `void` and `byte[]` the same way. Generics are erased on both sides:
    the pointcut never carries them and javap prints them only with `-v`.
    """
    def simple(name: str) -> str:
        """`java.security.KeyStore$Entry` and `KeyStore.Entry` both become `Entry`.

        A nested type is `$`-separated in the jar and in javap's output and
        `.`-separated in a pointcut, and the pointcut usually writes the inner name
        alone. Comparing on the last segment of both separators is what makes
        `KeyStore.getEntry` returning `Entry` a pass instead of the set's second
        return-type finding.
        """
        return name.replace(" ", "").rpartition(".")[2].rpartition("$")[2]

    return (
        pointcut_type.replace(" ", "") == javap_type.replace(" ", "")
        or simple(pointcut_type) == simple(javap_type)
    )


def gate_sig(
    set_name: str, specs: list[SpecFile], jar: AndroidJar | None, run: GateRun
) -> None:
    """Every `call(...)` of the set against what the platform declares."""
    if jar is None:
        run.skipped.append((set_name, "no android.jar: set $ANDROID_HOME or pass --android-jar"))
        return
    platform = SET_PLATFORMS.get(set_name, "")
    if platform != "android-30":
        reason = (
            f"{len(specs)} `.mop` written against a platform this gate has no jar for"
            if set_name in SET_PLATFORMS
            else f"{len(specs)} `.mop` in a set with no platform declared in SET_PLATFORMS"
        )
        run.skipped.append((set_name, reason))
        return

    for spec_file in specs:
        source = spec_file.source
        if source.parse_error:
            run.skipped.append((f"{set_name}/{source.path.stem}", source.parse_error))
            continue

        imports = {
            fqn.rpartition(".")[2]: fqn for fqn in _IMPORT.findall(source.text)
        }
        for event, signature in spec_file.unparsed:
            run.skipped.append(
                (f"{set_name}/{source.path.stem}.{event}", f"unparsed signature `{signature}`")
            )

        for pointcut in spec_file.pointcuts:
            subject = f"{pointcut.spec}.{pointcut.event}:{pointcut.line}"
            binary = jar.resolve(pointcut.owner, imports)
            if binary is None:
                run.notes.append(
                    f"{set_name}/{subject}: `{pointcut.owner}` has no entry in "
                    f"{jar.jar.name} -- absent from the platform, not a signature defect"
                )
                run.skipped.append((f"{set_name}/{subject}", f"class {pointcut.owner} absent from the jar"))
                continue

            run.checked += 1
            declarations = jar.declarations(binary, pointcut.member)
            inherited_from = ""
            if not declarations:
                for supertype in jar.supertypes(binary):
                    declarations = jar.declarations(supertype, pointcut.member)
                    if declarations:
                        inherited_from = supertype
                        break
            if not declarations:
                run.findings.append(
                    Finding(
                        "G-SIG",
                        set_name,
                        pointcut.spec,
                        subject,
                        f"`{binary}` declares no member `{pointcut.member}`; the pointcut "
                        f"reads `{pointcut.raw}` and the advice can never be woven",
                    )
                )
                continue
            if inherited_from:
                run.notes.append(
                    f"{set_name}/{subject}: `{pointcut.member}` is declared on "
                    f"`{inherited_from}`, not on `{binary}` -- resolved through the hierarchy"
                )

            if pointcut.member == "new" or not pointcut.return_type:
                continue

            observed = {
                _return_type_of(declaration, pointcut.member) for declaration in declarations
            }
            if not any(_same_type(pointcut.return_type, candidate) for candidate in observed):
                run.findings.append(
                    Finding(
                        "G-SIG",
                        set_name,
                        pointcut.spec,
                        subject,
                        f"return type: the pointcut declares `{pointcut.return_type}` and "
                        f"{binary}.{pointcut.member} returns {sorted(observed)}. Both weavers "
                        f"gate the return type exactly, so the advice is generated and never fires",
                    )
                )


# --------------------------------------------------------------------------
# G-FORB
# --------------------------------------------------------------------------


def _forbidden_clauses(rule: Path) -> list[str]:
    """The `FORBIDDEN` section of a CrySL rule, one entry per clause."""
    clauses: list[str] = []
    inside = False
    for line in rule.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("FORBIDDEN"):
            inside = True
            continue
        if inside and re.match(r"^(OBJECTS|EVENTS|ORDER|CONSTRAINTS|REQUIRES|ENSURES|NEGATES)\b", stripped):
            break
        if inside:
            clauses.append(stripped.rstrip(";").strip())
    return clauses


def _clause_member(clause: str) -> tuple[str, tuple[str, ...]]:
    """`PBEKeySpec(char[],byte[],int) => Con` into the member and the types it forbids.

    The argument types matter: `PBEKeySpec` forbids two of its four constructors and
    keeps the fourth as the event the rule's ORDER is written over. Matching on the
    name alone would credit `c1` -- the conforming four-argument constructor -- with
    accusing the two-argument one, and the gate would pass on a set that forbids
    nothing.
    """
    head = clause.split("=>")[0].strip()
    name, _, tail = head.partition("(")
    arguments = _split_types(tail.rpartition(")")[0]) if tail else []
    return name.strip(), tuple(argument.replace(" ", "") for argument in arguments)


def _same_arguments(clause_types: tuple[str, ...], pointcut: Pointcut) -> bool:
    """Whether a pointcut's declared arguments are the ones a clause names.

    Compared on the simple type name, because a clause writes `java.lang.String`
    where a pointcut writes `String`, and on arity, because that is what separates
    the forbidden overloads from the permitted one. A variadic pointcut matches any
    arity from its fixed prefix on -- `(..)` is a wildcard on both sides.
    """
    if pointcut.variadic:
        return True
    if len(clause_types) != len(pointcut.arguments):
        return False
    return all(
        left.rpartition(".")[2] == right.replace(" ", "").rpartition(".")[2]
        for left, right in zip(clause_types, pointcut.arguments)
    )


def gate_forb(
    set_name: str,
    specs: list[SpecFile],
    rule_dirs: dict[str, Path],
    run: GateRun,
) -> None:
    """Every `FORBIDDEN` clause of a rule that has a `.mop` here has an accusing event.

    The scope is the reason this gate is usable. Both oracles state `FORBIDDEN` on
    four rules; two of them -- `DigestInputStream` and `DigestOutputStream` -- have
    no specification in any set, being among the 27 rules this change leaves out. A
    clause no task owns cannot be a failure, so it is a declared skip and is counted.
    """
    by_stem = {spec_file.source.path.stem: spec_file for spec_file in specs}

    # Scope, derived rather than declared: a set is in reach of a CrySL FORBIDDEN
    # clause only if its specifications are paired with CrySL rules at all. `generic`
    # and `generic_new` are not derived from CrySL and pair with nothing, so every
    # clause of every rule would be a finding against them -- a gate that fails on
    # 100 % of a set it was never told about is a gate nobody will read.
    paired = any(
        (rule_dir / f"{stem}{extension}").is_file()
        or (rule_dir / f"{stem.removesuffix('Spec')}{extension}").is_file()
        for rule_dir in rule_dirs.values()
        if rule_dir.is_dir()
        for extension in RULE_EXTENSIONS
        for stem in by_stem
    )
    if not paired:
        run.skipped.append(
            (set_name, f"{len(specs)} `.mop` and not one paired with a CrySL rule of either oracle")
        )
        return

    for oracle, rule_dir in rule_dirs.items():
        if not rule_dir.is_dir():
            run.skipped.append((oracle, f"rule directory absent: {rule_dir}"))
            continue
        for rule in sorted(rule_dir.iterdir()):
            if rule.suffix not in RULE_EXTENSIONS:
                continue
            clauses = _forbidden_clauses(rule)
            if not clauses:
                continue
            spec_file = by_stem.get(f"{rule.stem}Spec") or by_stem.get(rule.stem)
            if spec_file is None:
                run.skipped.append(
                    (
                        f"{oracle}/{rule.name}",
                        f"{len(clauses)} FORBIDDEN clause(s) on a rule with no `.mop` in "
                        f"`{set_name}` -- out of this change's scope (the 27 unpaired rules)",
                    )
                )
                continue

            bodies = {
                region.owner: spec_file.source.neutral[region.start : region.end]
                for region in spec_file.source.regions
                if region.kind == "body"
            }
            for clause in clauses:
                member, clause_types = _clause_member(clause)
                run.checked += 1
                # The accusing event is the one whose `call(...)` names the member.
                # A constructor clause names the type, which JavaMOP writes as `new`.
                accusers = [
                    pointcut
                    for pointcut in spec_file.pointcuts
                    if (
                        pointcut.member == member
                        or (pointcut.member == "new" and pointcut.owner.rpartition(".")[2] == member)
                    )
                    and _same_arguments(clause_types, pointcut)
                ]
                if not accusers:
                    run.findings.append(
                        Finding(
                            "G-FORB",
                            set_name,
                            spec_file.source.path.stem,
                            f"{spec_file.source.path.stem}.{member}",
                            f"`{oracle}` forbids `{clause}` and no event of "
                            f"`{spec_file.source.path.stem}.mop` has a `call(...)` for it, so the "
                            f"call is silent where the rule turns it down",
                        )
                    )
                    continue
                accusing = [
                    pointcut
                    for pointcut in accusers
                    if "ForbiddenMethod" in bodies.get(pointcut.event, "")
                ]
                if not accusing:
                    run.findings.append(
                        Finding(
                            "G-FORB",
                            set_name,
                            spec_file.source.path.stem,
                            f"{spec_file.source.path.stem}.{accusers[0].event}",
                            f"`{oracle}` forbids `{clause}`; the event exists "
                            f"({', '.join(sorted({p.event for p in accusers}))}) but no body of it "
                            f"raises `ErrorType.ForbiddenMethod`, so the call takes a transition "
                            f"instead of drawing the report the clause asks for",
                        )
                    )


# --------------------------------------------------------------------------
# G-BIND
# --------------------------------------------------------------------------


def gate_bind(set_name: str, specs: list[SpecFile], run: GateRun) -> None:
    """Every event of a parametric specification binds the monitored object.

    A non-parametric specification is skipped rather than passed: its generator
    emits one process-wide monitor by design, so "binds no object" is what every
    one of its events does and a finding there would be noise.
    """
    for spec_file in specs:
        source = spec_file.source
        stem = source.path.stem
        if source.parse_error:
            run.skipped.append((f"{set_name}/{stem}", source.parse_error))
            continue
        if not source.has_specification:
            run.skipped.append((f"{set_name}/{stem}", "declares events and no specification block"))
            continue
        if not source.parameters:
            run.skipped.append(
                (f"{set_name}/{stem}", "non-parametric: one process-wide monitor by declaration")
            )
            continue

        parameter_types = {declared for declared in source.parameters.values()}
        for event, (header, line) in spec_file.headers.items():
            run.checked += 1
            binds = bool(_RETURNING.search(header) or _TARGET.search(header))
            if binds:
                continue
            # An event can also name the object among its own parameters and hand
            # it to `args(...)`; that binds the argument, not the monitor, but the
            # declared type is what says whether a monitored object was in reach.
            declared = set(source.event_parameters.get(event, {}).values())
            reachable = declared & parameter_types
            detail = (
                f" -- it does bind {sorted(reachable)} as an argument, so the object is in reach"
                if reachable
                else ""
            )
            run.findings.append(
                Finding(
                    "G-BIND",
                    set_name,
                    stem,
                    f"{stem}.{event}:{line}",
                    f"`{stem}` is parametric over {sorted(parameter_types)} and `{event}` has "
                    f"neither `returning(...)` nor `target(...)`, so the generator hands it the "
                    f"parameterless map and its body runs on every live monitor of the "
                    f"specification{detail}",
                )
            )


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


GATES = ("G-SIG", "G-FORB", "G-BIND")

DEFAULT_ALLOWLIST = REPO / "data/jca_android/gate_allowlist.csv"


def read_allowlist(path: Path) -> list[dict[str, str]]:
    """The rows of `gate_allowlist.csv` that belong to these three gates.

    A row with an empty `reason` allows nothing -- the rule `gh105_order_gate.py`
    already applies, restated here rather than shared because sharing it would make
    one gate's parser the other's dependency for a four-line read.
    """
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
            if (row.get("gate") or "").strip() in GATES and (row.get("reason") or "").strip()
        ]


def _allows(row: dict[str, str], gate: str, finding: Finding) -> bool:
    """Whether one allow-list row covers one finding.

    `*` in `spec` or `event_or_state` is the wildcard the file already uses for a
    reason that covers a family; anywhere else the match is exact.
    """
    if row["gate"] != gate or row["set"] != finding.spec_set:
        return False
    if row["spec"] not in ("*", finding.spec):
        return False
    subject = finding.subject
    return row["event_or_state"] in ("*", subject, subject.split(":")[0].partition(".")[2])


def _resolve_sets(root: Path, selection: str) -> list[Path]:
    """The set directories to run over, enumerated and never counted from a literal."""
    names = SPECIFICATION_SETS if selection == "all" else (selection,)
    return [root / name for name in names if (root / name).is_dir()]


def _android_jar(explicit: Path | None) -> Path | None:
    if explicit:
        return explicit if explicit.is_file() else None
    home = os.environ.get("ANDROID_HOME")
    if not home:
        return None
    jar = Path(home) / "platforms/android-30/android.jar"
    return jar if jar.is_file() else None


def run_gates(
    specs_root: Path,
    selection: str,
    gates: tuple[str, ...],
    jar_path: Path | None,
    expert_rules: Path,
    api30_rules: Path,
    allowlist: Path | None = None,
) -> dict[str, GateRun]:
    """Run the selected gates over the selected sets, then move allowed findings aside."""
    runs = {gate: GateRun() for gate in gates}
    jar = None
    resolved = _android_jar(jar_path)
    if resolved is not None:
        jar = AndroidJar(resolved)

    rule_dirs = {"expert": expert_rules, "api30": api30_rules}

    for set_dir in _resolve_sets(specs_root, selection):
        specs = read_set(set_dir)
        if "G-SIG" in runs:
            gate_sig(set_dir.name, specs, jar, runs["G-SIG"])
        if "G-FORB" in runs:
            gate_forb(set_dir.name, specs, rule_dirs, runs["G-FORB"])
        if "G-BIND" in runs:
            gate_bind(set_dir.name, specs, runs["G-BIND"])

    rows = read_allowlist(allowlist if allowlist is not None else DEFAULT_ALLOWLIST)
    for gate, run in runs.items():
        kept: list[Finding] = []
        for finding in run.findings:
            if any(_allows(row, gate, finding) for row in rows):
                run.allowlisted.append(finding)
            else:
                kept.append(finding)
        run.findings = kept
    return runs


def main(argv: list[str] | None = None) -> int:
    """Exit 0 when every selected gate is green, 1 on a finding, 2 when nothing ran."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--specs-root", type=Path, default=DEFAULT_SPECS_ROOT)
    parser.add_argument("--sets", default="all", help="`all` or the name of one set")
    parser.add_argument(
        "--gate", action="append", choices=GATES, help="run one gate; repeatable"
    )
    parser.add_argument("--android-jar", type=Path, default=None)
    parser.add_argument("--expert-rules", type=Path, default=DEFAULT_EXPERT_RULES)
    parser.add_argument("--api30-rules", type=Path, default=DEFAULT_API30_RULES)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)

    gates = tuple(arguments.gate) if arguments.gate else GATES
    runs = run_gates(
        arguments.specs_root,
        arguments.sets,
        gates,
        arguments.android_jar,
        arguments.expert_rules,
        arguments.api30_rules,
        arguments.allowlist,
    )

    payload = {
        gate: {
            "checked": run.checked,
            "failed": len(run.findings),
            "findings": [
                {
                    "set": finding.spec_set,
                    "spec": finding.spec,
                    "subject": finding.subject,
                    "message": finding.message,
                }
                for finding in run.findings
            ],
            "notes": run.notes,
            "skipped": [{"subject": subject, "reason": reason} for subject, reason in run.skipped],
            "allowlisted": [
                {"set": finding.spec_set, "spec": finding.spec, "subject": finding.subject}
                for finding in run.allowlisted
            ],
        }
        for gate, run in runs.items()
    }

    if arguments.json:
        print(json.dumps(payload, indent=2))
    else:
        for gate, run in runs.items():
            print(
                f"{gate}: {run.checked} checked, {len(run.findings)} failed, "
                f"{len(run.allowlisted)} allow-listed, {len(run.skipped)} skipped, "
                f"{len(run.notes)} notes"
            )
            for finding in run.allowlisted:
                print(f"  allow-listed {finding.spec_set}/{finding.subject}")
            for subject, reason in run.skipped:
                print(f"  skipped {subject}: {reason}")
            for note in run.notes:
                print(f"  note {note}")
            for finding in run.findings:
                print(f"  [{gate}] {finding.spec_set}/{finding.subject}: {finding.message}")

    if not any(run.checked for run in runs.values()):
        print(
            "no gate compared anything -- check `--specs-root`, `--sets` and "
            "`--android-jar`; the skip reasons above say which",
            file=sys.stderr,
        )
        return 2
    return 1 if any(run.findings for run in runs.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
