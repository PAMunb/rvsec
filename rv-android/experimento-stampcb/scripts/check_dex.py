"""Check that a treatment APK differs from its corpus APK only in the DEX that holds the
stamp helper: every classes*.dex is byte-identical except one, and that one defines
Lmop/RvsecStamp;. Prints one line per APK and exits 1 on any other difference.

Usage: python -I check_dex.py <corpus-dir> <treatment-dir> <apk>...
"""
import sys
import zipfile
from pathlib import Path


def dexes(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist() if n.startswith("classes") and n.endswith(".dex")}


corpus, treatment = Path(sys.argv[1]), Path(sys.argv[2])
bad = 0
for apk in sys.argv[3:]:
    a, b = dexes(corpus / apk), dexes(treatment / apk)
    differ = sorted(n for n in a.keys() | b.keys() if a.get(n) != b.get(n))
    ok = len(differ) == 1 and differ[0] in a and differ[0] in b and b"Lmop/RvsecStamp;" in b[differ[0]]
    bad += not ok
    print(f"{'OK ' if ok else 'BAD'} {apk}: {len(a)} dex, differ {differ}")
sys.exit(1 if bad else 0)
