"""
Augment /home/pedro/.../JOAO/PLANILHA.csv with APK metadata extracted via aapt.

Reads the original planilha, derives an `apk_filename` from the `apk_url`
column (last path segment), locates the APK in the local mirror, and appends
one column per relevant aapt/`unzip` field. Rows whose APK is not present
locally keep the new columns empty.

The update is IN PLACE — the input CSV is overwritten. A timestamped backup
is written alongside so the previous state can be recovered.

The script is idempotent: if the expected new columns already exist, they
are refreshed with the current APK state (useful after re-downloading or
after new instrumentation passes fill in the reserved columns).

Run:
    uv run python scripts/augment_planilha.py
"""

import csv
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

JOAO = Path("/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO")
PLANILHA = JOAO / "PLANILHA.csv"
APKS_DIR = JOAO / "APKs"

AAPT = os.environ.get(
    "AAPT",
    "/home/pedro/desenvolvimento/aplicativos/android/sdk/build-tools/35.0.1/aapt",
)

# Columns we append.
NEW_COLS = [
    "apk_filename",
    "apk_exists_locally",
    "apk_size_mb",
    "dex_count",
    "package_name",
    "version_code",
    "version_name",
    "min_sdk",
    "target_sdk",
    "max_sdk",
    "compile_sdk",
    "native_code_abis",
    "launchable_activity",
    # Dataset curation — manually flipped to "no" to exclude a row from
    # experiments without deleting it. `obs` holds the reason (install
    # failure, ABI mismatch, known-broken instrumentation, etc.).
    "approved",
    "obs",
    # Reserved for later passes (kept empty here):
    "jca_instrumented",
    "sa_classes",
    "sa_methods",
    "sa_reaches_target",
]

# Idempotency: columns listed here are NOT overwritten when re-running the
# script. They are intended to capture human or downstream-process decisions
# that must survive a re-scan of the APK metadata.
PRESERVE_COLS = {"approved", "obs", "jca_instrumented", "sa_classes",
                 "sa_methods", "sa_reaches_target"}


def aapt_badging(apk: Path) -> dict:
    """Return a dict of aapt fields. Missing fields map to empty strings."""
    try:
        out = subprocess.check_output(
            [AAPT, "dump", "badging", str(apk)],
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).decode("utf-8", errors="replace")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return {}

    d: dict = {}

    # package line: package: name='X' versionCode='Y' versionName='Z' compileSdkVersion='W'
    m = re.search(r"^package: (.*)$", out, re.MULTILINE)
    if m:
        pairs = dict(re.findall(r"(\w+)='([^']*)'", m.group(1)))
        d["package_name"] = pairs.get("name", "")
        d["version_code"] = pairs.get("versionCode", "")
        d["version_name"] = pairs.get("versionName", "")
        d["compile_sdk"] = pairs.get("compileSdkVersion", "")

    m = re.search(r"^sdkVersion:'(\d+)'", out, re.MULTILINE)
    d["min_sdk"] = m.group(1) if m else ""
    m = re.search(r"^targetSdkVersion:'(\d+)'", out, re.MULTILINE)
    d["target_sdk"] = m.group(1) if m else ""
    m = re.search(r"^maxSdkVersion:'(\d+)'", out, re.MULTILINE)
    d["max_sdk"] = m.group(1) if m else ""

    m = re.search(r"^native-code: (.*)$", out, re.MULTILINE)
    if m:
        abis = re.findall(r"'([^']+)'", m.group(1))
        d["native_code_abis"] = ";".join(abis)
    else:
        d["native_code_abis"] = ""

    m = re.search(r"^launchable-activity: name='([^']+)'", out, re.MULTILINE)
    d["launchable_activity"] = m.group(1) if m else ""

    return d


def dex_count(apk: Path) -> str:
    try:
        with zipfile.ZipFile(apk) as z:
            return str(sum(1 for n in z.namelist() if n.endswith(".dex") and "/" not in n))
    except Exception:
        return ""


def size_mb(apk: Path) -> str:
    try:
        return f"{apk.stat().st_size / (1024 * 1024):.1f}"
    except OSError:
        return ""


def apk_filename_from_url(url: str) -> str:
    # Last path segment — matches F-Droid layout: .../repo/<pkg>_<ver>.apk
    return url.rsplit("/", 1)[-1] if url else ""


def main() -> int:
    if not PLANILHA.exists():
        print(f"ERROR: {PLANILHA} not found")
        return 1
    if not APKS_DIR.is_dir():
        print(f"ERROR: {APKS_DIR} not found")
        return 1

    with open(PLANILHA, newline="") as f:
        reader = csv.DictReader(f)
        original_fields = list(reader.fieldnames or [])
        rows = list(reader)

    # Idempotent header: keep original order + append only new columns.
    existing = set(original_fields)
    fieldnames = original_fields + [c for c in NEW_COLS if c not in existing]

    # Timestamped backup so the previous state is recoverable.
    from datetime import datetime
    backup = PLANILHA.with_suffix(
        f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv.bak"
    )
    backup.write_bytes(PLANILHA.read_bytes())
    print(f"Backup: {backup}")

    augmented_rows = []
    total = len(rows)
    processed_ok = 0
    missing = 0
    for i, row in enumerate(rows, 1):
        # Stash the preserve columns before re-deriving from the APK so human
        # curation (approved=no, obs=...) survives re-runs of this script.
        preserved = {k: row.get(k, "") for k in PRESERVE_COLS}

        apk_name = apk_filename_from_url(row.get("apk_url", ""))
        row["apk_filename"] = apk_name
        apk_path = APKS_DIR / apk_name
        if apk_path.is_file():
            row["apk_exists_locally"] = "yes"
            row["apk_size_mb"] = size_mb(apk_path)
            row["dex_count"] = dex_count(apk_path)
            row.update(aapt_badging(apk_path))
            processed_ok += 1
        else:
            row["apk_exists_locally"] = "no"
            missing += 1
            for col in NEW_COLS[2:]:  # skip filename + exists_locally
                if col not in row:
                    row[col] = ""

        # `approved` is ternary: "" (not yet evaluated), "yes" (cleared for
        # experiments), "no" (excluded — `obs` records why). Default is empty
        # so the column never commits to a decision we haven't made; a human
        # or a downstream script flips it to yes/no deliberately. Re-runs of
        # this augmenter always preserve whatever is already there.
        for col in PRESERVE_COLS:
            row[col] = preserved.get(col, "")

        augmented_rows.append(row)

        if i % 50 == 0 or i == total:
            print(f"  processed {i}/{total}")

    with open(PLANILHA, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(augmented_rows)

    print(f"\nUpdated {PLANILHA} in place")
    print(f"  total rows: {total}")
    print(f"  APKs found locally: {processed_ok}")
    print(f"  APKs missing: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
