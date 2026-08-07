#!/usr/bin/env python3
"""Turn `javap` output into the member table PointcutBudget consumes.

The point of this script is that overload sets are exactly the kind of thing everyone is
confident and wrong about. Never hand-write the member list: read it out of the jar you are
actually going to weave against.

    python3 api_members.py $ANDROID_HOME/platforms/android-30/android.jar \
        javax.crypto.Cipher > cipher.tsv

Optionally restrict to the methods you care about, which keeps the matrix readable:

    python3 api_members.py <jar> <fqn> --only getInstance init update doFinal wrap getIV

Output is TSV, one member per line:

    tag <TAB> name <TAB> paramDescriptors(comma-separated) <TAB> returnDescriptor <TAB> 0|1

The last column is 1 for static members. `tag` is a short label used in the matrix; it
defaults to the signature, and you are meant to edit the column by hand to carry the rule's
event names (`i4`, `f2`, …) so the matrix reads against the oracle.
"""

import argparse
import re
import subprocess
import sys

PRIMITIVES = {
    "void": "V", "boolean": "Z", "byte": "B", "char": "C", "short": "S",
    "int": "I", "long": "J", "float": "F", "double": "D",
}

# `public static final javax.crypto.Cipher getInstance(java.lang.String) throws ...;`
SIGNATURE = re.compile(
    r"^\s*(?P<mods>(?:\w+\s+)*?)"
    r"(?P<ret>[\w.$]+(?:\[\])*)\s+"
    r"(?P<name>[\w$]+)\s*"
    r"\((?P<params>[^)]*)\)"
)


def descriptor(java_type: str) -> str:
    """Java source type -> DEX/JVM descriptor. `byte[]` -> `[B`, `java.lang.String` -> `L…;`."""
    java_type = java_type.strip()
    dims = 0
    while java_type.endswith("[]"):
        dims += 1
        java_type = java_type[:-2].strip()
    java_type = java_type.split("<", 1)[0]  # erase generics
    base = PRIMITIVES.get(java_type) or "L" + java_type.replace(".", "/") + ";"
    return "[" * dims + base


def split_params(params: str) -> list[str]:
    """Split a parameter list on top-level commas (generics may contain their own)."""
    out, depth, current = [], 0, ""
    for ch in params:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        out.append(current)
    return [p.strip() for p in out if p.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("jar", help="path to android.jar (or any jar on the weaving classpath)")
    ap.add_argument("fqn", help="fully qualified class name, e.g. javax.crypto.Cipher")
    ap.add_argument("--only", nargs="*", default=None,
                    help="restrict to these method names (default: all)")
    args = ap.parse_args()

    try:
        raw = subprocess.run(["javap", "-classpath", args.jar, args.fqn],
                             capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError as exc:
        print(f"javap failed: {exc.stderr.strip()}", file=sys.stderr)
        return 1

    count = 0
    seen: dict[str, int] = {}
    for line in raw.splitlines():
        line = line.split(" throws ", 1)[0].rstrip(";").rstrip()
        m = SIGNATURE.match(line)
        if not m:
            continue                                   # class header, fields, constructors
        name = m.group("name")
        if name == args.fqn.rsplit(".", 1)[-1]:
            continue                                   # constructor
        if args.only and name not in args.only:
            continue
        params = [descriptor(p) for p in split_params(m.group("params"))]
        ret = descriptor(m.group("ret"))
        is_static = "1" if "static" in m.group("mods").split() else "0"
        # Tags key the overlap report, so overloads that share a name and an arity have to be
        # told apart. Replace these by the rule's event names once you have the table.
        tag = f"{name}/{len(params)}"
        seen[tag] = seen.get(tag, 0) + 1
        if seen[tag] > 1:
            tag = f"{tag}#{seen[tag]}"
        print("\t".join([tag, name, ",".join(params), ret, is_static]))
        count += 1

    if count == 0:
        print(f"no members matched in {args.fqn}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
