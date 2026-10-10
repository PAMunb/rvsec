"""Compare two GATOR documents of the same analysis: every member byte-equal after
re-serialisation, and `transitions` equal as a multiset (its order follows
identity-hash iteration, INV-ANA-79). Prints one verdict per member."""
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
print("members", list(a) == list(b))
for k in a:
    if k == "transitions":
        ca = sorted(json.dumps(t, sort_keys=True) for t in a[k])
        cb = sorted(json.dumps(t, sort_keys=True) for t in b[k])
        print(k, "order-equal" if a[k] == b[k] else ("multiset-equal" if ca == cb else "DIFFERENT"), len(a[k]))
    else:
        print(k, "equal" if a[k] == b[k] else "DIFFERENT")
