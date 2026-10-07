#!/usr/bin/env python3
"""Normalise `dexdump -d` text; print the md5 of the normalised text and stamp counters.

usage: dexdump -d classes.dex | dexnorm.py

Normalisation removes what shifts when a DEX gains method references or a method
gains an instruction: file offsets, the raw code-unit column, code offsets
(instruction offsets, branch targets, try ranges, positions) and pool indices. It
maps every setter invoke the stamp rewrites (`invoke-virtual` on the original
owner, `invoke-static` on `Lmop/RvsecStamp;`) to one token that keeps the setter
name and the register list, and drops the inserted `composeNode` calls. An off dump
and an on dump of the same DEX therefore normalise to the same text when the only
differences are setter rewrites and `composeNode` insertions.

Counters:
  stamp_static      setter invokes routed to Lmop/RvsecStamp;
  setter_virtual    setter invokes left as invoke-virtual (any owner)
  compose_inserted  composeNode calls (dropped from the digest)
  setter_super      invoke-super of a setter (never rewritten)
  insns_lines       instruction lines, composeNode calls excluded
"""
import hashlib
import re
import sys

INSN = re.compile(r"^[0-9a-f]{6}: [0-9a-f ]*\|[0-9a-f]{4}: ")
METHOD_HEADER = re.compile(r"^[0-9a-f]{6}:\s+\|\[[0-9a-f]+\] ")
POOL = re.compile(
    r"\s*// (method|type|string|field|call_site|method_handle|proto)@[0-9a-f]+"
)
TARGET = re.compile(r"[0-9a-f]{4,8} // [+-][0-9a-f]+$")
CODE_OFFSET = re.compile(r"0x[0-9a-f]{4,}")
SOURCE_INDEX = re.compile(r"(source_file_idx\s*:\s*)\d+")
INSNS_SIZE = re.compile(r"^\s*insns size\s*:")
SETTER = re.compile(
    r"invoke-(virtual|static)(/range)? \{([^}]*)\}, L[^;]+;\."
    r"(setOnClickListener|setOnLongClickListener|setAccessibilityDelegate):"
    r"\((?:Landroid/view/View;)?(Landroid/view/View\$(?:OnClickListener|OnLongClickListener|AccessibilityDelegate);)\)V"
)
COMPOSE = re.compile(r"invoke-static(/range)? \{[^}]*\}, Lmop/RvsecStamp;\.composeNode:")
SUPER = re.compile(
    r"invoke-super(/range)? \{[^}]*\}, L[^;]+;\."
    r"(setOnClickListener|setOnLongClickListener|setAccessibilityDelegate):"
)


def normalise(lines):
    """Return `(md5 hex digest, counters)` of the normalised `dexdump -d` lines."""
    digest = hashlib.md5()
    counters = {
        "stamp_static": 0,
        "setter_virtual": 0,
        "compose_inserted": 0,
        "setter_super": 0,
        "insns_lines": 0,
    }
    for line in lines:
        if line.startswith(("Processing '", "Opened '")):
            continue
        if INSNS_SIZE.match(line):
            continue
        is_insn = INSN.match(line) is not None
        line = INSN.sub("", line)
        line = METHOD_HEADER.sub("METHOD ", line)
        line = POOL.sub("", line)
        line = TARGET.sub("TARGET", line.rstrip("\n"))
        line = CODE_OFFSET.sub("0x?", line)
        line = SOURCE_INDEX.sub(r"\1?", line)
        if COMPOSE.search(line):
            counters["compose_inserted"] += 1
            continue
        match = SETTER.search(line)
        # A static setter on any class other than the helper is app code, not a
        # rewrite, and stays as it is.
        if match and (match.group(1) == "virtual" or "Lmop/RvsecStamp;" in line):
            if match.group(1) == "virtual":
                counters["setter_virtual"] += 1
            else:
                counters["stamp_static"] += 1
            line = (
                line[: match.start()]
                + "SETTER(%s){%s}" % (match.group(4), match.group(3))
                + line[match.end() :]
            )
        if SUPER.search(line):
            counters["setter_super"] += 1
        if is_insn:
            counters["insns_lines"] += 1
        digest.update(line.encode() + b"\n")
    return digest.hexdigest(), counters


def main():
    digest, counters = normalise(sys.stdin)
    print(digest, " ".join("%s=%d" % kv for kv in counters.items()))


if __name__ == "__main__":
    main()
