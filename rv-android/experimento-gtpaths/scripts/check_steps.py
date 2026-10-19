"""6.4: check every app->app step of a document with paths against the APK's bytecode.

A step v -> n holds when v's body has an invoke whose method name is n's name (the class may
differ: virtual dispatch and empty-site edges resolve a call named on a supertype). Steps into
a lambda body (LambdaEdges, INV-ANA-77) are reported apart.

Run with the main tree's androguard venv:
  .venv/bin/python -I check_steps.py <apk> <document-with-paths>
"""

import json
import logging
import re
import sys

from androguard.misc import AnalyzeAPK

logging.disable(logging.CRITICAL)
SIG = re.compile(r"<([^:]+): \S+ ([^(]+)\(")


def parse(sig: str) -> tuple[str, str]:
    m = SIG.match(sig)
    return m.group(1), m.group(2)


def main() -> None:
    apk, path = sys.argv[1], sys.argv[2]
    d = json.load(open(path))
    app = {m["signature"] for c in d["reachability"] for m in c["methods"]}
    pm = d["pathMethods"]
    steps = [(pm[v], pm[n]) for _, v, n in d["distancePaths"] if pm[v] in app and pm[n] in app]
    steps = sorted(set(steps))
    _, _, dx = AnalyzeAPK(apk)
    invoked = {}
    ok = lam = bad = 0
    for v, n in steps:
        if v not in invoked:
            cls, name = parse(v)
            cn = "L" + cls.replace(".", "/") + ";"
            names = set()
            for ma in dx.find_methods(classname="^" + re.escape(cn) + "$", methodname="^" + re.escape(name) + "$"):
                m = ma.get_method()
                if hasattr(m, "get_instructions"):
                    for ins in m.get_instructions():
                        if ins.get_name().startswith("invoke"):
                            out = ins.get_output()
                            mm = re.search(r"->([^(]+)\(", out)
                            if mm:
                                names.add(mm.group(1))
            invoked[v] = names
        ncls, nname = parse(n)
        if nname in invoked[v]:
            ok += 1
        elif "lambda$" in nname or "$$ExternalSyntheticLambda" in ncls or "$$Lambda" in ncls:
            lam += 1
        else:
            bad += 1
            print(f"   UNEXPLAINED {v} -> {n}")
    print(f"{apk.split('/')[-1]}: app->app steps {len(steps)}, invoke by name {ok}, into lambda {lam}, unexplained {bad}")


if __name__ == "__main__":
    main()
