#!/usr/bin/env python3
"""Conformance verdict for every .mop in the derived set against its generated rule.

The `jca_android` set was produced by derivation rather than by a second hand
translation: ten files had an allow-list changed to follow a generated API 30
rule and thirteen were carried over from `jca` unchanged. Only three of the
thirteen state why. "Carried verbatim" is not a verdict -- it does not say
whether the corresponding rule was checked and found not to contradict the file,
or whether no rule corresponds at all.

This script produces the verdict for all 23, so the traceability table stops
being prose and becomes an artefact that can be re-run:

    anchored        a generated rule constrains this list and the list follows it
    uncontradicted  the rule was checked and imposes nothing this list violates
    no-anchor       no generated rule corresponds, with the reason

It also answers the second question the derivation left open. The `.mop` compares
algorithm names as strings where CrySL compares algorithm identity, so the 2022
translation carried spelling variants -- `HMAC-SHA256` beside `HmacSHA256`,
`SHA256` beside `SHA-256` -- that no upstream rule contains. Two columns report
them, and the distinction matters: `aliases` are literals absent from the
generated rule but folding onto one of its members, while `spelling_variants` are
groups within the allow-list itself that name the same algorithm. The second is
computed without reference to any rule, which is what lets the question be asked
of `SecretKeySpecSpec`, whose derived rule constrains nothing at all.

Usage:
    gh101_conformance_check.py [--specs <dir>] [--frozen-specs <dir>]
                               [--rules <dir>] [-o <out.csv>]
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from pathlib import Path

DEFAULT_RULES = Path(
    "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv"
    "/MetaCrySL/generated/api30"
)

SECTION = re.compile(
    r"^\s*(SPEC|OBJECTS|EVENTS|ORDER|CONSTRAINTS|REQUIRES|ENSURES|NEGATES|FORBIDDEN)\b"
)
# `alg in {...}` names the object directly; `part(0,"/",transformation) in {...}`
# names a component of it, which is how the Cipher rule states its algorithm
# catalogue. Both forms are membership constraints and both are read here.
MEMBERSHIP = re.compile(
    r"(?:part\(\s*0\s*,[^,]*,\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\)?\s+in\s+\{([^}]*)\}"
)
ALLOW_LIST = re.compile(r"(\w+)\s*=\s*Arrays\.asList\(", re.MULTILINE)
LITERAL = re.compile(r'"([^"]*)"|(\d+)')

# What each .mop's allow-list is anchored to: the generated rule, the variable
# holding the list, and the rule object the membership constraint governs.
# A `None` rule means no generated rule corresponds; a `None` variable means the
# file carries no allow-list of its own.
Anchor = tuple[str | None, str | None, str | None, str]
ANCHORS: dict[str, Anchor] = {
    "CipherInputStreamSpec.mop": (
        "CipherInputStream", None, None,
        "the rule carries no membership constraint; the specification monitors "
        "stream sequencing, not algorithm choice",
    ),
    "CipherOutputStreamSpec.mop": (
        "CipherOutputStream", None, None,
        "the rule carries no membership constraint; the specification monitors "
        "stream sequencing, not algorithm choice",
    ),
    "CipherSpec.mop": (
        "Cipher", None, "transformation",
        "the only specification with an algorithm constraint and no allow-list of "
        "its own: it delegates to isValid() in shared Java. Closed by this change "
        "in the derived set through a utility of its own (D-S3), not in the .mop",
    ),
    "DHGenParameterSpecSpec.mop": (
        "DHGenParameterSpec", None, None,
        "the rule constrains key size through an implication, not a membership set",
    ),
    "GCMParameterSpecSpec.mop": ("GCMParameterSpec", "validLengths", "tLen", ""),
    "HMACParameterSpecSpec.mop": (
        "HMACParameterSpec", None, None, "the rule carries no membership constraint"
    ),
    "IvParameterSpec.mop": (
        "IvParameterSpec", None, None,
        "the rule constrains only the randomness of the IV, which the .mop reads "
        "as a predicate rather than a list",
    ),
    "KeyGeneratorSpec.mop": ("KeyGenerator", "safeAlgorithms", "alg", ""),
    "KeyManagerFactorySpec.mop": ("KeyManagerFactory", "safeAlgorithms", "algo", ""),
    "KeyPairGeneratorSpec.mop": ("KeyPairGenerator", "safeAlgorithms", "alg", ""),
    "KeyPairSpec.mop": (
        "KeyPair", None, None, "the rule carries no membership constraint"
    ),
    "KeyStoreSpec.mop": ("KeyStore", "types", "keyStoreAlg", ""),
    "MacSpec.mop": ("Mac", "safeAlgorithms", "macAlg", ""),
    "MessageDigestSpec.mop": ("MessageDigest", "algorithms", "digestAlg", ""),
    "PBEKeySpecSpec.mop": (
        "PBEKeySpec", None, None,
        "the rule constrains iteration count and key length through implications, "
        "not a membership set",
    ),
    "PBEParameterSpecSpec.mop": (
        "PBEParameterSpec", None, None,
        "the rule constrains iteration count through an implication, not a "
        "membership set",
    ),
    "RandomStringPassword.mop": (
        None, None, None,
        "no CrySL counterpart at all. It is not a JCA specification: it propagates "
        "randomness taint through String.valueOf and toCharArray so a password "
        "derived from SecureRandom is not accused by PBEKeySpecSpec",
    ),
    "SSLContextSpec.mop": ("SSLContext", "protocols", "protocol", ""),
    "SecretKeySpec.mop": (
        "SecretKey", None, None,
        "anchored to SecretKey.crysl despite the file name; the rule carries no "
        "membership constraint",
    ),
    "SecretKeySpecSpec.mop": (
        "SecretKeySpec", "algorithms", None,
        "the derived rule imposes no membership constraint at all -- the MetaCrySL "
        "base specification dropped the one CrySL 1.5.2 carried -- so the list has "
        "no derived anchor either way and stays a declared hand translation",
    ),
    "SecureRandomSpec.mop": ("SecureRandom", "algorithms", "randAlg", ""),
    "SignatureSpec.mop": ("Signature", "algorithms", "alg", ""),
    "TrustManagerFactorySpec.mop": ("TrustManagerFactory", "algorithms", "algo", ""),
}

FIELDS = [
    "mop_file", "rule", "variable", "rule_object", "verdict", "changed_from_jca",
    "mop_literals", "rule_literals", "spelling_variants", "aliases", "unmatched",
    "absent_from_mop", "reason",
]


def spelling_variants(literals: list[str]) -> str:
    """Groups of literals in one allow-list that name the same algorithm.

    The .mop compares algorithm names as strings where CrySL compares algorithm
    identity, so the 2022 translation listed several spellings of the same thing:
    `HmacSHA256`, `HMACSHA256`, `HMAC-SHA256` and `HMAC/SHA256` all reach the same
    provider. Reporting them independently of any rule is what lets the question
    be asked of files whose rule imposes no constraint at all.
    """
    groups: dict[str, list[str]] = {}
    for item in literals:
        groups.setdefault(normalise(item), []).append(item)
    return " | ".join(
        " ".join(members) for _, members in sorted(groups.items()) if len(members) > 1
    )


def normalise(literal: str) -> str:
    """Fold the spelling variants the translation carried: case, dashes, slashes."""
    return literal.replace("-", "").replace("/", "").replace("_", "").lower()


def mop_allow_list(path: Path, variable: str) -> list[str]:
    """The literals of one `Arrays.asList` binding, across however many lines it spans."""
    text = path.read_text(encoding="utf-8")
    for match in ALLOW_LIST.finditer(text):
        if match.group(1) != variable:
            continue
        depth, index = 1, match.end()
        while depth and index < len(text):
            depth += {"(": 1, ")": -1}.get(text[index], 0)
            index += 1
        return [a or b for a, b in LITERAL.findall(text[match.end() : index - 1])]
    raise LookupError(f"{path.name}: no Arrays.asList bound to `{variable}`")


def rule_membership(path: Path, obj: str) -> list[str]:
    """The literals of the widest membership constraint the rule places on one object.

    A generated rule states several constraints over the same object -- the
    catalogue of admissible algorithms, then per-algorithm implications such as
    `alg in {"RSA"} => keySize in {2048, 4096}`. The allow-list of a .mop
    corresponds to the catalogue, which is the widest of them.
    """
    section, widest = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if match := SECTION.match(line):
            section = match.group(1)
            continue
        if section != "CONSTRAINTS" or not line.strip():
            continue
        # An implication's antecedent constrains the same object; take the
        # consequent's side only when the object is not the one being implied on.
        for var, literals in MEMBERSHIP.findall(line.split("=>")[0]):
            if var != obj:
                continue
            values = [item.strip().strip('"') for item in literals.split(",") if item.strip()]
            if len(values) > len(widest):
                widest = values
    return widest


def check(specs_dir: Path, rules_dir: Path, frozen_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for mop_file, (rule, variable, obj, reason) in sorted(ANCHORS.items()):
        row = {
            "mop_file": mop_file, "rule": rule or "", "variable": variable or "",
            "rule_object": obj or "", "changed_from_jca": "", "mop_literals": "",
            "rule_literals": "", "spelling_variants": "", "aliases": "",
            "unmatched": "", "absent_from_mop": "", "reason": reason,
        }

        if rule is None:
            row["verdict"] = "no-anchor"
            rows.append(row)
            continue

        rule_literals = rule_membership(rules_dir / f"{rule}.cryptsl", obj) if obj else []
        row["rule_literals"] = " ".join(sorted(rule_literals))

        if variable is None:
            # Nothing in the file to contradict, or -- for CipherSpec -- the
            # constraint lives in Java and is this change's Group 2.
            row["verdict"] = "uncontradicted" if not rule_literals else "no-anchor"
            rows.append(row)
            continue

        mop_literals = mop_allow_list(specs_dir / mop_file, variable)
        frozen_literals = mop_allow_list(frozen_dir / mop_file, variable)
        changed = mop_literals != frozen_literals
        row["mop_literals"] = " ".join(mop_literals)
        row["changed_from_jca"] = "yes" if changed else "no"
        row["spelling_variants"] = spelling_variants(mop_literals)

        if not rule_literals:
            row["verdict"] = "uncontradicted"
            rows.append(row)
            continue

        folded = {normalise(item) for item in rule_literals}
        exact = set(rule_literals)
        aliases = [i for i in mop_literals if i not in exact and normalise(i) in folded]
        unmatched = [i for i in mop_literals if normalise(i) not in folded]
        absent = [i for i in rule_literals if normalise(i) not in {normalise(m) for m in mop_literals}]

        row["aliases"] = " ".join(sorted(set(aliases)))
        row["unmatched"] = " ".join(sorted(set(unmatched)))
        row["absent_from_mop"] = " ".join(sorted(absent))

        # D-S4 distinguishes the two by whether the derivation acted: `anchored`
        # means the rule contradicted the inherited list and the list was changed
        # to follow it; `uncontradicted` means the rule was checked and the
        # inherited list stands. A list left unchanged while the rule contradicts
        # it is neither, and is the one outcome that must not appear.
        if unmatched or absent:
            row["verdict"] = "contradicted" if not changed else "anchored-with-deviation"
        else:
            row["verdict"] = "anchored" if changed else "uncontradicted"
        rows.append(row)

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mop_base = Path(os.environ.get("RVSEC_HOME", "")) / "rvsec/rvsec-mop/src/main/resources"
    parser.add_argument("--specs", type=Path, default=mop_base / "jca_android")
    parser.add_argument("--frozen-specs", type=Path, default=mop_base / "jca")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    for label, path in (("specs", args.specs), ("frozen specs", args.frozen_specs), ("rules", args.rules)):
        if not path.is_dir():
            print(f"{label} directory not found: {path}", file=sys.stderr)
            return 1

    rows = check(args.specs, args.rules, args.frozen_specs)
    handle = args.output.open("w", encoding="utf-8", newline="") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.output:
            handle.close()

    blank = [row["mop_file"] for row in rows if not row["verdict"]]
    if blank:
        print(f"INV-INS-113 violated -- no verdict for: {', '.join(blank)}", file=sys.stderr)
        return 1
    print(f"{len(rows)} verdicts, none blank", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
