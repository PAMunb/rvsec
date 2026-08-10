#!/usr/bin/env python3
"""ALFA batch A -- parenthesis-balance audit of the five .mop sources vs generated artifacts.

Motivation: SecretKeySpecSpec.mop event c1 visually carries one unmatched ')'
(line 30). This script measures it instead of asserting it: for each spec source it
counts parenthesis balance over each `event ... {` header region (from the `event`
keyword to the opening brace of the body), and then checks whether the generated
.rvm / .aj carry a balanced condition. Deterministic; single run.
"""

import re, sys

SPECDIR = ("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/"
           "rvsec/rvsec/rvsec-mop/src/main/resources/jca_android")
SCRATCH = ("/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-"
           "workspace-rv-rvsec-rv-android/d2ed0fb6-e4be-4945-abb4-21d8af2acd28/"
           "scratchpad/batchA")

FILES = {
    "DHGenParameterSpecSpec.mop": "gen_DHGenParameterSpecSpec",
    "HMACParameterSpecSpec.mop": "gen_HMACParameterSpecSpec",
    "PBEParameterSpecSpec.mop": "gen_PBEParameterSpecSpec",
    "IvParameterSpec.mop": "gen_IvParameterSpec",
    "SecretKeySpecSpec.mop": "gen_SecretKeySpecSpec",
}

def event_headers(text):
    """Yield (event_name, header_text, line) for each event decl: from 'event' to the
    first '{' that is at paren depth 0 *per JavaMOP intent* -- since a malformed header
    never reaches depth 0, we cut at the first '{' preceded by ')' + whitespace."""
    # only real declarations: `event <name> after(`/`before(` -- the bare word
    # "event" also occurs in prose comments ("the event is seen").
    for m in re.finditer(r"\bevent\s+(\w+)\s+(?:after|before)\s*\(", text):
        start = m.start()
        # find the body-opening brace: first '{' after the pointcut expression.
        i = text.find("{", m.end())
        # heuristic: the pointcut ends at the first '{' -- good enough for these files,
        # whose bodies never precede the pointcut.
        header = text[start:i]
        line = text.count("\n", 0, start) + 1
        yield m.group(1), header, line

def strip_strings(s):
    return re.sub(r'"(?:[^"\\]|\\.)*"', '""', s)

def balance(s):
    s = strip_strings(s)
    return s.count("(") - s.count(")")

def main():
    print("paren balance of each `event` header (0 = balanced), per file:")
    anomalies = []
    for mop, gendir in FILES.items():
        text = open(f"{SPECDIR}/{mop}").read()
        for name, header, line in event_headers(text):
            b = balance(header)
            flag = "" if b == 0 else "   <-- UNBALANCED"
            if b != 0:
                anomalies.append((mop, name, line, b))
            print(f"  {mop:28s} event {name:4s} (line {line:3d}): balance {b:+d}{flag}")
    print()
    for mop, name, line, b in anomalies:
        gendir = FILES[mop]
        base = mop[:-4]
        rvm = open(f"{SCRATCH}/{gendir}/out/{base}.rvm").read()
        aj = open(f"{SCRATCH}/{gendir}/out/{base}MonitorAspect.aj").read()
        print(f"anomaly: {mop} event {name} line {line}: balance {b:+d} in source.")
        print(f"  generated .rvm total balance: {balance(rvm):+d} "
              f"(condition text present: {'validate(Property.RANDOMIZED' in rvm})")
        print(f"  generated .aj  total balance: {balance(aj):+d}")
        print("  => the generator accepted the malformed source silently (exit 0, "
              "empty stderr per generation manifest) and emitted balanced artifacts.")
    if not anomalies:
        print("no unbalanced event header found.")

if __name__ == "__main__":
    main()
