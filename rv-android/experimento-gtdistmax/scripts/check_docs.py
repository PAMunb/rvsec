"""Group 5 comparisons of two GATOR documents of the same analysis.

Usage:
  python check_docs.py same A.json B.json
      A and B hold the same content: same members in the same order, every member equal
      after parsing, `transitions` equal as a multiset (its order follows identity-hash
      iteration, INV-ANA-86). Like experimento-gh125/compare_docs.py, plus newline counts.
  python check_docs.py plus-distmax WITHOUT.json WITH.json N
      WITH equals WITHOUT apart from the member `distMax: N`, which sits right after
      `class_defs_under_key` (INV-ANA-99, INV-ANA-101).
  python check_docs.py histogram DOC.json
      Member order, newline count, and the count of targetDistances pairs per distance.
Exits 1 when a check fails.
"""

import collections
import json
import sys


def load(path):
    with open(path, "rb") as handle:
        raw = handle.read()
    return raw, json.loads(raw)


def same_content(a, b, label):
    ok = list(a) == list(b)
    print(f"{label} members {'same order' if ok else 'DIFFERENT'}: {list(a)}")
    for key in a:
        if key not in b:
            print(f"{label} {key} MISSING in second")
            ok = False
            continue
        if key == "transitions":
            ca = sorted(json.dumps(t, sort_keys=True) for t in a[key])
            cb = sorted(json.dumps(t, sort_keys=True) for t in b[key])
            verdict = "order-equal" if a[key] == b[key] else ("multiset-equal" if ca == cb else "DIFFERENT")
            ok &= verdict != "DIFFERENT"
            print(f"{label} {key} {verdict} ({len(a[key])} edges)")
        else:
            equal = a[key] == b[key]
            ok &= equal
            print(f"{label} {key} {'equal' if equal else 'DIFFERENT'}")
    return ok


def main():
    mode = sys.argv[1]
    if mode == "same":
        (raw_a, a), (raw_b, b) = load(sys.argv[2]), load(sys.argv[3])
        print(f"bytes {len(raw_a)} vs {len(raw_b)}; newlines {raw_a.count(b'\n')} vs {raw_b.count(b'\n')}; "
              f"bytes-identical {raw_a == raw_b}")
        ok = same_content(a, b, "")
    elif mode == "plus-distmax":
        (raw_a, a), (raw_b, b) = load(sys.argv[2]), load(sys.argv[3])
        n = int(sys.argv[4])
        keys_b = list(b)
        expected = list(a)
        expected.insert(expected.index("class_defs_under_key") + 1, "distMax")
        ok = keys_b == expected and b.get("distMax") == n and isinstance(b.get("distMax"), int)
        print(f"member order with distMax right after class_defs_under_key: {keys_b == expected}; "
              f"distMax={b.get('distMax')!r}; newlines in WITH: {raw_b.count(b'\n')}")
        stripped = {k: v for k, v in b.items() if k != "distMax"}
        ok &= same_content(a, stripped, "without-distMax:")
    elif mode == "histogram":
        raw, d = load(sys.argv[2])
        hist = collections.Counter()
        methods = 0
        for cls in d.get("reachability", []):
            for m in cls.get("methods", []):
                pairs = m.get("targetDistances", [])
                methods += bool(pairs)
                for _, dist in pairs:
                    hist[dist] += 1
        print(f"bytes {len(raw)} newlines {raw.count(b'\n')} members {list(d)}")
        print(f"distMax={d.get('distMax')!r} distancePairs={d.get('distancePairs')!r} "
              f"targets={len(d.get('distanceTargets', []))} methods_with_pairs={methods} "
              f"pairs_per_d={sorted(hist.items())} max_d={max(hist) if hist else None}")
        ok = True
    else:
        sys.exit(f"unknown mode {mode}")
    print("RESULT", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
