#!/usr/bin/env python3
"""gh91 group 4 — the per-app record, the sha256 manifests and the provenance note.

Runs AFTER `scripts/gh91_gate.py` exits 0. It reads only the re-run's own output; it never
writes into the corpus (that is the owner's group 5).

The `sa_*` block is NOT recomputed here. It comes from
`rvsec-dataset/src/rvsec_dataset/static_analysis/parser.py`, which is the authority for the
17 dataset columns and the vocabulary upstream consumes — reimplementing the counts locally
would let this record and the corpus drift apart silently (task 4.1).

Outputs, all under `SA_RERUN_gh91/record/` (a subdirectory, so gate 3.1 keeps seeing exactly
30 deliverable JSONs at the top level):
    sa_rerun_record.csv                     the per-app record (4.2)
    manifest_sa_rerun_30.sha256             the 30 new JSONs (4.4)
    manifest_static_dir_pre_install.sha256  STATIC_DIR *before* the owner copies (4.4)
    PROVENANCE.md                           argv per APK, commit, date, WTG statement (4.5)
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gh91_sa_rerun as drv  # noqa: E402  — reuses OUT_DIR/APKS_CSV, the single source of paths

# The dataset repo owns the sa_* vocabulary; import it rather than re-deriving (task 4.1).
DATASET_SRC = drv.WORKSPACE / "rvsec-dataset" / "src"
sys.path.insert(0, str(DATASET_SRC))
from rvsec_dataset.static_analysis.parser import SA_COLUMNS, parse_json  # noqa: E402

RECORD_DIR = drv.OUT_DIR / "record"
STATIC_DIR = (drv.DATASET_ROOT
              / "APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706")

# Non-sa_* columns the record adds so a reader can audit a row without opening the run.
EXTRA_COLUMNS = [
    "apk", "key_used", "manifest_package", "csv_detected_package", "relation",
    "mop_denominator_methods", "mop_reaches_target_methods",
    "round", "jvm_memory", "timeout_s", "wall_clock_s", "returncode", "timed_out",
    "json_sha256", "argv",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(paths: list[Path], out: Path, title: str) -> int:
    lines = [f"# {title}", f"# {len(paths)} files"]
    for p in sorted(paths):
        lines.append(f"{sha256_of(p)}  {p.name}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(paths)


def main() -> int:
    RECORD_DIR.mkdir(parents=True, exist_ok=True)

    with drv.APKS_CSV.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=drv.RV_ANDROID,
                            capture_output=True, text=True).stdout.strip()

    # The round an APK ran in is not in `_progress` — REGISTRO.md is where the campaign
    # records it, in its per-APK headers (`### r1 · <apk> · **COMPLETE**`).
    round_of: dict[str, str] = {}
    for line in (drv.OUT_DIR / "REGISTRO.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("### r"):
            parts = [p.strip() for p in line[4:].split("·")]
            if len(parts) >= 2:
                round_of[parts[1]] = parts[0]

    records = []
    for r in rows:
        apk, mneut = r["apk"].strip(), r["Mneut"].strip()
        json_path = drv.OUT_DIR / f"{apk}.json"
        prog = json.loads((drv.OUT_DIR / "_progress" / f"{apk}.json").read_text(encoding="utf-8"))

        # Wall clock and status come from the runner: the engine JSON carries neither.
        # The runner names the wall clock `seconds`; the dataset column is
        # `sa_analysis_seconds`.
        seconds = prog.get("seconds")
        sa = parse_json(json_path,
                        manifest_package=r["manifest_package"].strip(),
                        sa_status=prog.get("sa_status", ""),
                        sa_analysis_seconds=seconds)

        # 3.5's numerator/denominator, kept explicitly so the MOP surface is auditable
        # per row without re-reading the JSON.
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        methods = [m for c in raw.get("reachability") or [] for m in c.get("methods") or []]

        rec = {
            "apk": apk,
            "key_used": mneut,
            "manifest_package": r["manifest_package"].strip(),
            "csv_detected_package": r["detected_package"].strip(),
            "relation": r["relation"].strip(),
            "mop_denominator_methods": len(methods),
            "mop_reaches_target_methods": sum(1 for m in methods if m.get("reachesTarget")),
            "round": round_of.get(apk, ""),
            "jvm_memory": prog.get("jvm_memory", ""),
            "timeout_s": prog.get("timeout", ""),
            "wall_clock_s": seconds,
            "returncode": prog.get("returncode", ""),
            "timed_out": prog.get("timed_out", ""),
            "json_sha256": sha256_of(json_path),
            "argv": " ".join(prog.get("argv") or []),
        }
        rec.update(sa)
        records.append(rec)

    record_csv = RECORD_DIR / "sa_rerun_record.csv"
    with record_csv.open("w", newline="", encoding="utf-8") as fh:
        # `detected_package` here is the ENGINE's top-level package for the new run (the
        # dataset parser's own column), not the CSV's `detected_package`, which the record
        # keeps separately as `csv_detected_package`.
        writer = csv.DictWriter(
            fh, fieldnames=EXTRA_COLUMNS + SA_COLUMNS + ["detected_package", "sa_mismatch"])
        writer.writeheader()
        writer.writerows(records)

    n_new = write_manifest(sorted(drv.OUT_DIR.glob("*.apk.json")),
                           RECORD_DIR / "manifest_sa_rerun_30.sha256",
                           "gh91 re-run — the 30 new GATOR JSONs")
    n_pre = write_manifest(sorted(STATIC_DIR.glob("*.json")),
                           RECORD_DIR / "manifest_static_dir_pre_install.sha256",
                           f"STATIC_DIR BEFORE the group-5 copy — {STATIC_DIR.name}")

    write_provenance(records, commit, n_new, n_pre)

    print(f"record:   {record_csv}  ({len(records)} rows, "
          f"{len(EXTRA_COLUMNS + SA_COLUMNS) + 1} columns)")
    print(f"manifest: {n_new} new JSONs, {n_pre} pre-installation STATIC_DIR files")
    print(f"note:     {RECORD_DIR / 'PROVENANCE.md'}")
    return 0


def write_provenance(records: list[dict], commit: str, n_new: int, n_pre: int) -> None:
    """Task 4.5 — the note that travels with the JSONs, with 4.3's precision on the WTG."""
    lines = [
        "# gh91 — provenance of the static-analysis re-run",
        "",
        f"- rv-android commit: `{commit}`",
        "- campaign: 2026-07-30 19:42 → 2026-07-31 00:29 BRT (4.77 h, exit 0)",
        f"- output: `{drv.OUT_DIR}` — {n_new} JSONs, all carrying `\"complete\": true`",
        f"- input APKs: `{drv.APKS_DIR}` (uninstrumented; never the `APKS_INSTRUMENTED_*` copies)",
        "- engine: GATOR invoked directly (`lib/gator/gator`), client `RvsecAnalysisClient`,"
        " `-cgAlgorithm spark`, `-cgDelegation true`, JCA `mopDir` (23 specs)",
        "- validation gate `scripts/gh91_gate.py`: 3.1-3.6 all pass",
        "",
        "## What changed against the predecessor JSONs",
        "",
        "1. **The filtering key.** Each APK was analysed under `-clientParam codePackage=<Mneut>`,"
        " the neutralised manifest package, instead of the key `PackageDetector` inferred."
        " This is the point of the change.",
        "2. **The WTG is skipped** (`-clientParam skipWtg=true`) — a deliberate NEW deviation,"
        " present in none of the 30 original runs.",
        "",
        "### Precision on the WTG (task 4.3)",
        "",
        "`sa_transitions_count` is **empty by construction** in every row: the WTG is the only"
        " producer of transitions and it did not run.",
        "",
        "`sa_windows_count` is **NOT** empty and must not be flagged the same way — the client"
        " writes the full report before returning (`RvsecAnalysisClient.java:165-183`). Its"
        " caveat is different: the windows are derived from"
        " `prepareWindows(output, new HashMap<>(), null)`, so the set may differ from the"
        " post-WTG one and the window ids are fallback ids.",
        "",
        "### Observed side effect of the correct key (recorded, not a defect)",
        "",
        "Ten apps whose predecessor was filtered by a WIDER key lost classes that are all"
        " generated — `R`, `R$*`, `BuildConfig`. Across all 30 apps, **0 non-generated classes"
        " were lost and no lost class carried `reachesTarget`**. The cause is"
        " `RvsecAnalysisClient.isAppClass` (lines 277-286): it takes the class-name suffix"
        " *relative to the filter key* and drops it only when that suffix is exactly `.R`,"
        " `.R$*` or `.BuildConfig`. Under the wide key `org.musicbrainz.picard`, the class"
        " `org.musicbrainz.picard.barcodescanner.R` has suffix `.barcodescanner.R` and escaped"
        " the exclusion; under `Mneut` it is dropped as the method's own javadoc intends."
        " The old key was therefore inflating the coverage denominator with generated classes."
        " Consumers comparing `sa_classes`/`sa_methods` for these ten apps must expect the"
        " small drop and must not read it as lost analysis coverage.",
        "",
        "Two rival explanations were checked and ruled out: no rvsec-gator **production** source"
        " changed between the predecessor runs (2026-06-26) and the jar rebuild (2026-07-29) —"
        " only three test files — and the analysed APK bytes are identical (sha256) between"
        " `APKS/` and `rvsec-dataset/head_apks/`. `--skip-wtg` is ruled out too: the"
        " reachability pipeline runs before `skipWtg()` is ever read.",
        "",
        "## Manifests (task 4.4)",
        "",
        f"- `manifest_sa_rerun_30.sha256` — the {n_new} new JSONs.",
        f"- `manifest_static_dir_pre_install.sha256` — all {n_pre} JSONs in `STATIC_DIR`"
        " **before** the owner's group-5 copy, so that copy can afterwards be proven to have"
        f" touched exactly 30 files and left {n_pre - n_new} byte-identical.",
        "",
        "## Exact command per APK",
        "",
    ]
    for rec in sorted(records, key=lambda r: r["apk"]):
        lines.append(f"### {rec['apk']}")
        lines.append("")
        lines.append(f"- key: `{rec['key_used']}` · round {rec['round']} ·"
                     f" `{rec['jvm_memory']}`/{rec['timeout_s']} s ·"
                     f" {rec['wall_clock_s']} s · rc={rec['returncode']}")
        lines.append(f"- sha256: `{rec['json_sha256']}`")
        lines.append("")
        lines.append("```")
        lines.append(rec["argv"])
        lines.append("```")
        lines.append("")
    (RECORD_DIR / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
