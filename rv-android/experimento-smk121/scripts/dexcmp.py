#!/usr/bin/env python3
"""Per-DEX comparison of APKs: raw md5, method_ids, normalised `dexdump -d` md5.

usage: dexcmp.py --work-dir DIR LABEL=apk [LABEL=apk ...]

Prints one line per (label, classes*.dex entry): the entry, its method_ids count
(header offset 0x58), the md5 of its bytes, and the `dexnorm` digest and counters.
With exactly two labels it then prints one `cmp` line per entry, `same` or `diff`
for the raw and the normalised digests (`missing` when one APK lacks the entry).

Each DEX is written to a temporary file inside the work directory for `dexdump`,
which reads files only, and deleted right after. `dexdump` is the one of
`$ANDROID_HOME/build-tools/35.0.1`.
"""
import argparse
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dexnorm import normalise  # noqa: E402

DEXDUMP = os.path.join(os.environ.get("ANDROID_HOME", ""), "build-tools", "35.0.1", "dexdump")


def dex_entries(apk):
    """The `classes*.dex` entries of `apk`, in classes, classes2, ... order."""
    with zipfile.ZipFile(apk) as z:
        names = [n for n in z.namelist() if n.startswith("classes") and n.endswith(".dex")]
    return sorted(names, key=lambda n: int(n[7:-4] or 1))


def describe(apk, entry, work_dir):
    """Return `(method_ids, raw md5, norm digest, counters)` of one DEX entry."""
    with zipfile.ZipFile(apk) as z:
        data = z.read(entry)
    method_ids = struct.unpack_from("<I", data, 0x58)[0]
    raw = hashlib.md5(data).hexdigest()
    with tempfile.NamedTemporaryFile(suffix=".dex", dir=work_dir, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    del data
    try:
        with subprocess.Popen(
            [DEXDUMP, "-d", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            errors="replace",
        ) as dexdump:
            norm, counters = normalise(dexdump.stdout)
        if dexdump.returncode != 0:
            raise SystemExit(f"dexdump failed on {entry} of {apk}")
    finally:
        os.unlink(path)
    return method_ids, raw, norm, counters


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work-dir", required=True, help="directory for temporary DEX files")
    parser.add_argument("apks", nargs="+", metavar="LABEL=apk")
    args = parser.parse_args()
    os.makedirs(args.work_dir, exist_ok=True)

    results = {}
    for arg in args.apks:
        label, apk = arg.split("=", 1)
        results[label] = {}
        for entry in dex_entries(apk):
            method_ids, raw, norm, counters = describe(apk, entry, args.work_dir)
            results[label][entry] = (raw, norm)
            counts = " ".join("%s=%d" % kv for kv in counters.items())
            print(
                f"{label}\t{entry}\tmethod_ids={method_ids}\traw={raw}\tnorm={norm} {counts}",
                flush=True,
            )

    if len(results) == 2:
        (_, a), (_, b) = results.items()
        for entry in sorted(set(a) | set(b), key=lambda n: int(n[7:-4] or 1)):
            if entry not in a or entry not in b:
                print(f"cmp\t{entry}\tmissing")
                continue
            raw = "same" if a[entry][0] == b[entry][0] else "diff"
            norm = "same" if a[entry][1] == b[entry][1] else "diff"
            print(f"cmp\t{entry}\traw={raw}\tnorm={norm}")


if __name__ == "__main__":
    main()
