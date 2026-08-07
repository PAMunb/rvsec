#!/usr/bin/env python3
"""Which CrySL predicate clauses the specification set actually implements.

A CrySL rule states three kinds of predicate clause: `ENSURES` (this call
establishes a fact), `REQUIRES` (this call is only correct if a fact holds), and
`NEGATES` (this call destroys a fact). A JavaMOP translation of that rule turns
each into an `ExecutionContext` site -- a write, a read, a removal. This script
takes the clauses on one side and the committed predicate inventory on the other
and reports, per clause, whether the edge exists.

The anchor is the **CrySL 1.5.2** corpus, not the generated API 30 rules. The two
answer different questions and this change asks both: the generated rules are the
anchor for allow-lists (see gh101_conformance_check.py), because membership
constraints are what varies with API level, while `ORDER`, `REQUIRES`, `ENSURES`
and `NEGATES` describe API semantics. The predicate graph is therefore checked
against the corpus the specifications were translated from in the first place,
which is where a translation defect is a defect.

The output is what makes Groups 3 to 5 checkable by counting: each editing task
carries the number of edges its file must close, and completion is arithmetic
rather than review.

Usage:
    gh101_predicate_edges.py --inventory <inventory.csv> [--rules <dir>]
                             [--edges <out.csv>] [--counts <out.csv>]
"""

from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
from pathlib import Path

DEFAULT_RULES = Path(
    "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv"
    "/rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules"
)

SECTION = re.compile(
    r"^\s*(SPEC|OBJECTS|EVENTS|ORDER|CONSTRAINTS|REQUIRES|ENSURES|NEGATES|FORBIDDEN)\b"
)
# A predicate clause is `name[arg, ...]`, optionally negated, optionally guarded
# by a constraint and an implication. Only the predicate and its first argument
# are needed: the argument is what distinguishes `randomized[seed]` from
# `randomized[lSeed]`, which is the difference between an expressible edge and
# an inexpressible one.
PREDICATE = re.compile(r"(!?)\s*([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^,\]]*)")

# Which CrySL rule each .mop translates. Two file names mislead and are worth the
# note: `SecretKeySpec.mop` declares `SecretKeySpec` but its javadoc anchors it to
# SecretKey.crysl, while `SecretKeySpecSpec.mop` is the SecretKeySpec translation.
# `RandomStringPassword.mop` is absent on purpose -- it has no CrySL counterpart
# and is a taint propagator invented by the translation.
MOP_TO_RULE = {
    "CipherInputStreamSpec.mop": "CipherInputStream",
    "CipherOutputStreamSpec.mop": "CipherOutputStream",
    "CipherSpec.mop": "Cipher",
    "DHGenParameterSpecSpec.mop": "DHGenParameterSpec",
    "GCMParameterSpecSpec.mop": "GCMParameterSpec",
    "HMACParameterSpecSpec.mop": "HMACParameterSpec",
    "IvParameterSpec.mop": "IvParameterSpec",
    "KeyGeneratorSpec.mop": "KeyGenerator",
    "KeyManagerFactorySpec.mop": "KeyManagerFactory",
    "KeyPairGeneratorSpec.mop": "KeyPairGenerator",
    "KeyPairSpec.mop": "KeyPair",
    "KeyStoreSpec.mop": "KeyStore",
    "MacSpec.mop": "Mac",
    "MessageDigestSpec.mop": "MessageDigest",
    "PBEKeySpecSpec.mop": "PBEKeySpec",
    "PBEParameterSpecSpec.mop": "PBEParameterSpec",
    "SSLContextSpec.mop": "SSLContext",
    "SecretKeySpec.mop": "SecretKey",
    "SecretKeySpecSpec.mop": "SecretKeySpec",
    "SecureRandomSpec.mop": "SecureRandom",
    "SignatureSpec.mop": "Signature",
    "TrustManagerFactorySpec.mop": "TrustManagerFactory",
}

# The vocabulary the translation chose for each CrySL predicate. A predicate with
# no entry has no `Property` constant at all, which is a different kind of defect:
# closing that edge means adding to `rvsec-core`, not editing one .mop.
PREDICATE_TO_PROPERTY = {
    "digested": "DIGESTED",
    "encrypted": "ENCRYPTED",
    "generatedKey": "GENERATED_KEY",
    "generatedKeyManager": "GENERATED_KEY_MANAGERS",
    "generatedKeyManagers": "GENERATED_KEY_MANAGERS",
    "generatedKeyStore": "GENERATED_KEY_STORE",
    "generatedKeypair": "GENERATED_KEY_PAIR",
    "generatedPrivkey": "GENERATED_PRIVATE_KEY",
    "generatedPubkey": "GENERATED_PUBLIC_KEY",
    "generatedSSLContext": "GENERATE_SSL_CONTEXT",
    "generatedSSLEngine": "GENERATE_SSL_ENGINE",
    "generatedTrustManager": "GENERATED_TRUST_MANAGER",
    "generatedTrustManagers": "GENERATED_TRUST_MANAGERS",
    "macced": "GENERATED_MAC",
    "preparedDH": "PREPARED_DH",
    "preparedGCM": "PREPARED_GCM",
    "preparedHMAC": "PREPARED_HMAC",
    "preparedIV": "PREPARED_IV",
    "preparedPBE": "PREPARED_PBE",
    "randomized": "RANDOMIZED",
    "signed": "SIGNED",
    "speccedKey": "SPECCED_KEY",
    "verified": "VERIFIED",
    "wrappedKey": "WRAPPED_KEY",
}

# A predicate the translation carries under a different constant on purpose.
# `preparedKeyMaterial` has no constant of its own: SecretKeySpec.mop writes
# RANDOMIZED over the encoded key bytes and SecretKeySpecSpec.mop reads RANDOMIZED
# over the key material, so the edge exists under a borrowed name. Declared here
# so it counts as present on both sides rather than as a defect on one.
SURROGATE = {"preparedKeyMaterial": "RANDOMIZED"}

# A clause whose site exists but names a neighbouring specification's constant.
# Both sides are enum members, so the file compiles, runs, and reports nothing;
# nothing but this table or a reader's eye connects the write to the read. The two
# entries are the two such defects in the corpus, each a two-token edit. Declared
# rather than inferred: "some site of the right kind exists in this file" would
# label every ordinary missing read a wrong constant. Keyed by
# (rule, clause, predicate, argument); the line numbers are jca_android's.
WRONG_CONSTANT = {
    ("KeyPair", "ENSURES", "generatedPrivkey", "retPrivateKey"): (
        "KeyPairSpec.mop:38 writes GENERATED_PUBLIC_KEY over the private key -- a "
        "copy of :32 with the value changed and the constant not. Partially "
        "self-masking: the disjunction at CipherSpec.mop:71 still accepts, so "
        "there is no false positive, only the loss of the public/private "
        "distinction the CrySL predicates exist to make."
    ),
    ("TrustManagerFactory", "ENSURES", "generatedTrustManagers", "trustManager"): (
        "TrustManagerFactorySpec.mop:65 writes GENERATED_KEY_MANAGERS, copied from "
        "KeyManagerFactorySpec, so GENERATED_TRUST_MANAGERS is never written and "
        "only ever removed."
    ),
}

# Clauses whose absence is a decision, not a defect. Keyed by (rule, clause,
# predicate) so a second clause of the same predicate is not silently absolved.
DELIBERATE_OMISSION = {
    ("MessageDigest", "ENSURES", "generatedMessageDigest"): (
        "Every `ENSURES p[this] after Init/Get` is rewritten as "
        "setObjectAsInAcceptingState(md) in the @match handler "
        "(ExecutionContext.java:107-114). The substitution is half-built: "
        "isInAcceptingState is never read from any .mop, so the mechanism is "
        "inert at runtime."
    ),
    ("Cipher", "ENSURES", "generatedCipher"): (
        "Same substitution: CipherSpec.mop:217 marks the cipher as in an "
        "accepting state instead of writing a predicate over `this`. The two "
        "REQUIRES of generatedCipher in the stream specifications are a separate "
        "matter -- they need a constant and a reader, and are not absolved here."
    ),
}

# Clauses the substrate cannot represent at all. `ExecutionContext` keys its map
# by equals/hashCode; a predicate asserting provenance over a primitive is
# therefore keyed by value, and no new constant repairs that.
INEXPRESSIBLE = {
    ("SecureRandom", "REQUIRES", "randomized", "lSeed"): (
        "randomized[lSeed] asserts that a long came from a CSPRNG -- provenance, "
        "not value. ExecutionContext keys by equals, so a boxed primitive is "
        "matched by value. The write side already commits the matching "
        "unsoundness: SecureRandomSpec.mop writes RANDOMIZED over ints, and the "
        "Integer cache (-128..127) makes one small nextInt() mark every equal "
        "literal in the process."
    ),
}

# The two hot specifications are repaired in their own group, because their
# authoring defects and their graph edges live in the same lines.
GROUP_3_FILES = {"SSLContextSpec.mop", "TrustManagerFactorySpec.mop"}

CLAUSE_TO_KIND = {"ENSURES": "WRITE", "REQUIRES": "READ", "NEGATES": "REMOVE"}

EDGE_FIELDS = [
    "mop_file", "rule", "clause", "predicate", "negated", "argument",
    "property", "verdict", "bucket", "group", "note",
]
COUNT_FIELDS = [
    "mop_file", "rule", "clauses", "present", "to_close", "recorded", "group",
]


def parse_clauses(rule_path: Path) -> list[tuple[str, str, str, str]]:
    """(clause, predicate, negated, first argument) for every predicate in a rule."""
    clauses: list[tuple[str, str, str, str]] = []
    section = None
    for line in rule_path.read_text(encoding="utf-8").splitlines():
        if match := SECTION.match(line):
            section = match.group(1)
            continue
        if section in CLAUSE_TO_KIND and line.strip():
            for negated, predicate, argument in PREDICATE.findall(line):
                clauses.append((section, predicate, negated, argument.strip()))
    return clauses


def load_inventory(path: Path) -> dict[str, set[tuple[str, str]]]:
    """(property, kind) pairs present in each .mop, from the committed inventory."""
    sites: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            sites[row["file"]].add((row["property"], row["kind"]))
    return sites


def classify(
    mop_file: str,
    rule: str,
    clause: str,
    predicate: str,
    argument: str,
    sites: set[tuple[str, str]],
) -> tuple[str, str, str, str]:
    """(verdict, bucket, group, note) for one clause."""
    kind = CLAUSE_TO_KIND[clause]

    group = "3" if mop_file in GROUP_3_FILES else "4"

    if note := INEXPRESSIBLE.get((rule, clause, predicate, argument)):
        return "recorded", "inexpressible", "4.4", note
    if note := DELIBERATE_OMISSION.get((rule, clause, predicate)):
        return "recorded", "deliberate-omission", "4.3", note
    if note := WRONG_CONSTANT.get((rule, clause, predicate, argument)):
        return "wrong-constant", "translation-defect", group, note

    if surrogate := SURROGATE.get(predicate):
        if (surrogate, kind) in sites:
            return "present-surrogate", "", "", f"carried as Property.{surrogate}"
        return "missing", "capability-absent", "5", f"surrogate Property.{surrogate} absent"

    prop = PREDICATE_TO_PROPERTY.get(predicate)
    if prop is None:
        return "missing", "capability-absent", "5", "no Property constant exists"
    if (prop, kind) in sites:
        return "present", "", "", ""
    return "missing", "translation-defect", group, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--edges", type=Path, help="per-clause CSV (default: stdout)")
    parser.add_argument("--counts", type=Path, help="per-file summary CSV")
    args = parser.parse_args()

    if not args.rules.is_dir():
        print(f"CrySL rules not found: {args.rules}", file=sys.stderr)
        return 1

    sites = load_inventory(args.inventory)
    rows: list[dict[str, str]] = []
    for mop_file, rule in sorted(MOP_TO_RULE.items()):
        for clause, predicate, negated, argument in parse_clauses(args.rules / f"{rule}.crysl"):
            verdict, bucket, group, note = classify(
                mop_file, rule, clause, predicate, argument, sites[mop_file]
            )
            rows.append(
                {
                    "mop_file": mop_file,
                    "rule": rule,
                    "clause": clause,
                    "predicate": predicate,
                    "negated": "yes" if negated else "no",
                    "argument": argument,
                    "property": PREDICATE_TO_PROPERTY.get(predicate, SURROGATE.get(predicate, "")),
                    "verdict": verdict,
                    "bucket": bucket,
                    "group": group,
                    "note": note,
                }
            )

    handle = args.edges.open("w", encoding="utf-8", newline="") if args.edges else sys.stdout
    try:
        writer = csv.DictWriter(handle, fieldnames=EDGE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.edges:
            handle.close()

    if args.counts:
        with args.counts.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COUNT_FIELDS, lineterminator="\n")
            writer.writeheader()
            for mop_file, rule in sorted(MOP_TO_RULE.items()):
                own = [row for row in rows if row["mop_file"] == mop_file]
                to_close = [row for row in own if row["verdict"] in ("missing", "wrong-constant")]
                groups = sorted({row["group"] for row in to_close})
                writer.writerow(
                    {
                        "mop_file": mop_file,
                        "rule": rule,
                        "clauses": len(own),
                        "present": sum(row["verdict"].startswith("present") for row in own),
                        "to_close": len(to_close),
                        "recorded": sum(row["verdict"] == "recorded" for row in own),
                        "group": "+".join(groups),
                    }
                )

    tally = collections.Counter(row["verdict"] for row in rows)
    print(
        f"{len(rows)} clauses over {len(MOP_TO_RULE)} rules: "
        + ", ".join(f"{count} {verdict}" for verdict, count in sorted(tally.items())),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
