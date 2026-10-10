"""Share of RVSEC-BIND lines whose handler is a library class, per logcat of an e03mini smoke run.

Usage: python3 bind_share.py data/results/<c> [...]
Walks every *.logcat under each container directory and prints one Markdown row per logcat:
BIND lines of kind compose and view, how many name a handler under androidx., and the most
frequent androidx. handlers. Before gh124 every compose line of saucenao and jtx named
androidx.compose.foundation.AbstractClickableNode$$ExternalSyntheticLambdaN.
"""
import collections
import pathlib
import re
import sys

BIND = re.compile(r"RVSEC-BIND: (\w+) .*handler=(\S+)")

print("| logcat | compose | compose androidx. | view | view androidx. | top androidx. handlers |")
print("|---|---:|---:|---:|---:|---|")
for container in sys.argv[1:]:
    for logcat in sorted(pathlib.Path(container).rglob("*.logcat")):
        totals = collections.Counter()
        library = collections.Counter()
        handlers = collections.Counter()
        with open(logcat, errors="replace") as handle:
            for line in handle:
                match = BIND.search(line)
                if not match:
                    continue
                kind, handler = match.groups()
                totals[kind] += 1
                if handler.startswith("androidx."):
                    library[kind] += 1
                    handlers[handler.rsplit(".", 1)[-1]] += 1
        top = ", ".join(f"{name} {n}" for name, n in handlers.most_common(3)) or "-"
        print(f"| {logcat.name} | {totals['compose']} | {library['compose']} | {totals['view']} | "
              f"{library['view']} | {top} |")
