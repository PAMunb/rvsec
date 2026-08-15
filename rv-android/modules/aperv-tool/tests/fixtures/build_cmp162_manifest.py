#!/usr/bin/env python3
"""Regenerate ``cmp162_manifest.json`` — the pin of FIXTURE-REAL.

cmp162 is a fixture, not a corpus: no number computed on it answers a research
question, and its role is to exercise code paths against real file formats. That
role only holds if "the tests pass" means the same thing tomorrow as today, which
is why every file a test reads is pinned by sha256 here rather than merely by
path. A refactor that quietly changed which bytes a parity test consumed would
otherwise read as a green suite.

The manifest also carries the campaign's identity arithmetic as *facts* rather
than as constants inside a test: 1458 identities, 1455 completed, 3 dead, 28
recovered retry records out of 31 ERROR records. Those are measured here, from
``tasks.json``, so the test that asserts them is asserting agreement between the
loader and the tree — not agreement between the loader and a number someone typed.

The tree itself lives outside the repository (it is ~40 GB of campaign output)
and is never copied in. When it is absent, ``test_fixture_manifest.py`` skips the
dependent tests with an explicit reason; it never passes silently.

Run from the rv-android root::

    .venv/bin/python modules/aperv-tool/tests/fixtures/build_cmp162_manifest.py

Read-only over the campaign tree. No device, no emulator (INV-APV-35).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

# The campaign root, relative to the rv-android repository root. Every path in
# the manifest is relative to this directory, so a tree relocated wholesale is
# still verifiable by pointing the loader at its new parent.
CAMPAIGN = Path("experimento-comp162")

# The consolidated per-batch CSVs rv-platform writes beside tasks.json.
BATCH_CSVS = (
    "summary.csv",
    "errors.csv",
    "coverage.csv",
    "performance.csv",
    "app_events.csv",
)

# The three golden artefacts the campaign itself produced. They are *parity*
# inputs: reproducing them proves the pipeline is unchanged, not that the
# estimator is right (INV-CAN-21). Correctness lives in FIXTURE-SYNTH.
PARITY_FILES = (
    "consolidado/wilcoxon.csv",
    "consolidado/per_apk_paired.csv",
    "consolidado/per_rep.csv",
    "consolidado/per_apk_admissivel.csv",
    "consolidado/per_tool_summary.csv",
    "censo_substrato.csv",
)

# The twelve applications whose raw .trace / .logcat pairs are pinned. Hashing
# all 1458 pairs would pin ~40 GB for no gain: the tests that read raw streams
# read a handful of runs, and the ones that read all of them read the CSVs.
#
# The subset is declared, not sampled, and each entry earns its place:
#   - the two smoke applications of the campaign (experimento-comp162/scripts/
#     make_filters.py:49) — the runs whose RUN_START gates were checked by hand
#     before the campaign was allowed to proceed;
#   - com.ds.avare_404.apk — the only application with dead identities (all three
#     replicas of aperv:mop_on_llm_off), so the liveness tests have a real
#     exclusion rather than a synthesised one;
#   - app.eduroam.geteduroam_2685.apk and com.flxrs.dankchat_40038.apk — a
#     single-activity and a multi-activity application, the two shapes the
#     activity-visit segmenter behaves differently on;
#   - seven more from the first batch, chosen so the subset overlaps the
#     measured-figure basis below and spans one to three activities per run.
TRACE_SUBSET = (
    "io.keepalive.android_133.apk",
    "de.markusfisch.android.binaryeye_174.apk",
    "com.ds.avare_404.apk",
    "app.eduroam.geteduroam_2685.apk",
    "com.flxrs.dankchat_40038.apk",
    "br.com.colman.petals_3040000.apk",
    "com.antony.muzei.pixiv_327.apk",
    "com.daniebeler.pfpixelix_40.apk",
    "com.etesync.syncadapter_20700.apk",
    "com.gelakinetic.mtgfam_99.apk",
    "com.tk.quicksearch_65.apk",
    "org.totschnig.myexpenses_858.apk",
)

# The arm whose traces carry the measured activity-visit distributions, and how
# many of them the measurement covered. The ordering is the plain sorted path
# order of the measurement script, so "the first 60" is reproducible from the
# tree alone.
MEASURED_ARM = "aperv:mop_on_llm_off"
MEASURED_N = 60

# The distributions the segmenter must reproduce over those 60 traces. They were
# measured on 2026-08-15 and are recorded here so the test asserts against the
# manifest rather than against literals scattered through a test file.
MEASURED_FIGURES = {
    "runs": 60,
    "steps": 15702,
    "activity_visits_per_run_median": 14.5,
    "activity_visit_len_mean": 11.0,
    "activity_visit_len_median": 2,
    "activity_visit_len_p90": 32,
    "activity_visit_len_max": 294,
    "activity_visit_share_len1": 0.378,
    "distinct_states_per_activity_visit_mean": 2.68,
    "state_visits_per_run_median": 156.5,
    "state_visit_len_mean": 1.66,
    "state_visit_len_median": 1,
    "state_visit_share_len1": 0.755,
    "state_exit_kind_share": {
        "state_transition": 0.846,
        "activity_transition": 0.085,
        "no_outcome": 0.059,
        "teardown": 0.006,
        "key_change_without_outcome": 0.003,
    },
    "edittext_clicks_total": 954,
    "edittext_clicks_changing_state_same_activity": 382,
    "heartbeats": 15701,
    "heartbeat_gap": 1,
}

# The UICOV ⋈ STATE.key join, measured over 120 runs on 2026-08-15: a total
# bijection in both directions.
UICOV_JOIN = {
    "runs": 120,
    "uicov_states": 3801,
    "state_keys_matched": 3801,
    "orphans": 0,
}


def sha256_of(path: Path) -> str:
    """Stream a file into a sha256 digest; traces run to hundreds of megabytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def arm_label(tool_name: str | None, variant: str | None) -> str:
    """The arm string as it appears in filenames and in the ``tool`` column.

    The builtin ``ape`` records ``variant='default'`` in its tool config and the
    consolidator collapses that to a bare ``ape``. Reproducing that collapse here
    is what makes the identity counts below agree with the campaign's own.
    """
    return "ape" if tool_name == "ape" else f"{tool_name}:{variant}"


def measure_identities(campaign: Path) -> dict:
    """Derive the identity arithmetic from ``tasks.json``, the only honest source.

    ``performance.csv`` and the other four consolidated CSVs hold COMPLETED rows
    only — 1455 of 1455 — so a loader built on them sees a campaign with no
    failures at all. Every failure fact below is invisible outside ``tasks.json``.
    """
    records = 0
    states: collections.Counter[str] = collections.Counter()
    by_identity: dict[tuple, list[str]] = collections.defaultdict(list)

    for tasks_json in sorted(campaign.glob("results/*/*/tasks.json")):
        document = json.loads(tasks_json.read_text())
        entries = document["tasks"] if isinstance(document, dict) else document
        records += len(entries)
        for entry in entries:
            config = entry.get("config") or {}
            tool_config = config.get("tool_config") or {}
            identity = (
                config.get("apk_name"),
                arm_label(tool_config.get("name"), tool_config.get("variant")),
                config.get("repetition"),
                config.get("timeout"),
            )
            state = (entry.get("result") or {}).get("state")
            states[state] += 1
            by_identity[identity].append(state)

    dead = sorted(k for k, v in by_identity.items() if "COMPLETED" not in v)
    recovered_identities = [
        k
        for k, v in by_identity.items()
        if "COMPLETED" in v and any(s != "COMPLETED" for s in v)
    ]
    recovered_records = sum(
        1
        for k, v in by_identity.items()
        if "COMPLETED" in v
        for s in v
        if s != "COMPLETED"
    )

    return {
        "task_records": records,
        "identities": len(by_identity),
        "completed_identities": len(by_identity) - len(dead),
        "error_records": states.get("ERROR", 0),
        "dead_identities": len(dead),
        "dead_identity_list": [list(k) for k in dead],
        "recovered_retry_records": recovered_records,
        "recovered_retry_identities": len(recovered_identities),
        "arms": sorted({k[1] for k in by_identity}),
        "repetitions": sorted({k[2] for k in by_identity}),
        "timeouts_s": sorted({k[3] for k in by_identity}),
        "applications": len({k[0] for k in by_identity}),
    }


def collect_files(campaign: Path) -> tuple[dict[str, str], list[str]]:
    """Hash everything a test may read, and name the measured-figure traces.

    Returns the ``{relative path: sha256}`` map and, separately, the ordered list
    of the traces the measured-figure test walks — ordered, because "the first
    60" is only meaningful against a stated ordering.
    """
    files: dict[str, str] = {}

    def add(path: Path) -> None:
        files[str(path.relative_to(campaign))] = sha256_of(path)

    for name in PARITY_FILES:
        add(campaign / name)

    for batch_tasks in sorted(campaign.glob("results/*/*/tasks.json")):
        add(batch_tasks)
        for csv_name in BATCH_CSVS:
            candidate = batch_tasks.parent / csv_name
            if candidate.exists():
                add(candidate)

    # The 162 static-analysis artefacts. `*.mop.json` is deliberately excluded:
    # no reader under analysis/ may open one (INV-CAN-24), and pinning a file the
    # library must never read would invite exactly that.
    for static_json in sorted(campaign.glob("results/*/*/*.apk/*.apk.json")):
        if static_json.name.endswith(".mop.json"):
            continue
        add(static_json)

    for application in TRACE_SUBSET:
        for stream in sorted(campaign.glob(f"results/*/*/{application}/*")):
            if stream.suffix in (".trace", ".logcat"):
                add(stream)

    measured = [
        str(path.relative_to(campaign))
        for path in sorted(campaign.glob(f"results/*/*/*/*__{MEASURED_ARM}.trace"))
    ][:MEASURED_N]
    for relative in measured:
        if relative not in files:
            add(campaign / relative)

    return files, measured


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign",
        type=Path,
        default=CAMPAIGN,
        help="path to experimento-comp162 (default: relative to the repo root)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "cmp162_manifest.json",
    )
    arguments = parser.parse_args()

    campaign = arguments.campaign
    if not campaign.is_dir():
        raise SystemExit(f"campaign tree not found: {campaign}")

    facts = measure_identities(campaign)
    files, measured = collect_files(campaign)

    manifest = {
        "fixture_class": "FIXTURE-REAL",
        "campaign": "comp162",
        "campaign_root": str(campaign),
        "generated_by": "modules/aperv-tool/tests/fixtures/build_cmp162_manifest.py",
        "note": (
            "cmp162 is a fixture, not a corpus: no number computed on it answers a "
            "research question. The three parity files reproduce the campaign's own "
            "output and prove the pipeline unchanged, never that an estimator is "
            "right (INV-CAN-21)."
        ),
        "facts": facts,
        "artefact_counts": {
            "traces": len(list(campaign.glob("results/*/*/*/*.trace"))),
            "logcats": len(list(campaign.glob("results/*/*/*/*.logcat"))),
            "trace_ndjson_gz": len(
                list(campaign.glob("results/*/*/*/*.trace.ndjson.gz"))
            ),
            "static_json": len(
                [
                    p
                    for p in campaign.glob("results/*/*/*.apk/*.apk.json")
                    if not p.name.endswith(".mop.json")
                ]
            ),
        },
        "parity_files": list(PARITY_FILES),
        "trace_subset": {
            "applications": list(TRACE_SUBSET),
            "reason": (
                "raw .trace/.logcat pairs are pinned for these twelve applications "
                "only; the rest of the campaign is reached through the consolidated "
                "CSVs and tasks.json"
            ),
        },
        "smoke_applications": list(TRACE_SUBSET[:2]),
        "measured_figures": {
            "arm": MEASURED_ARM,
            "ordering": "sorted path order of results/*/*/*/*__<arm>.trace",
            "traces": measured,
            **MEASURED_FIGURES,
        },
        "uicov_join": UICOV_JOIN,
        "files": files,
    }

    arguments.out.write_text(json.dumps(manifest, indent=1, sort_keys=False) + "\n")
    print(
        f"{arguments.out}: {len(files)} files pinned, facts={facts['identities']} identities"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
