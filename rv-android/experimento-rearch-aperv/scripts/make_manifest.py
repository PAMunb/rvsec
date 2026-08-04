#!/usr/bin/env python3
"""Generate the campaign manifest from the tool's own arm definitions.

The manifest is what the pre-flight and VERIFY compare a run's `RUN_START` against, so
every value in it is generated rather than transcribed: `get_variants()` is the authority
on what an arm is, and a hand-copied expectation would check the transcription instead of
the run. Regenerate it if an arm definition changes; it is written once, before the
campaign, and read afterwards.

Two fields are left null on purpose and filled after the jar and image exist (tasks 6.2
and 6.5): `build.expected_sha` and `image.id`. They are measured facts about artifacts
that do not exist yet — the pre-registration is what gets frozen, and it records them in
its provenance appendix when they are known.

    uv run python scripts/make_manifest.py --out manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

from aperv_tool.tools.aperv.tool import APERV_PROPERTY_MAPPING, ApeRVTool

# The three arms of the E3 grid, in the order the CSV's column groups follow. Their roles
# are what the decision rule refers to: the control arm is G1's channel because it zeroes
# the MOP weights, and the reference/LLM pair is what G2 contrasts.
ARMS = [
    ("mop_on_llm_off", "reference"),
    ("mop_off_llm_off", "control"),
    ("mop_on_llm_70", "llm"),
]

CORPUS_ID = "subset40"


def corpus_basis(subset_path: Path) -> str:
    """`<corpus-id>:<sha256>` recomputed from the list file, never transcribed."""
    digest = hashlib.sha256(subset_path.read_bytes()).hexdigest()
    return f"{CORPUS_ID}:{digest}"


def arm_entry(variant: str, role: str) -> Dict[str, Any]:
    """One manifest arm: its token, its preset, and its overrides in the jar's own names.

    `expected_params` is keyed by `ape.*` because that is how `RUN_START.params` reports,
    so the comparison needs no name map on either side.
    """
    config = ApeRVTool.get_variants()[variant]
    overrides = config.get("overrides", {})
    unmapped = sorted(set(overrides) - set(APERV_PROPERTY_MAPPING))
    if unmapped:
        raise SystemExit(f"arm {variant!r} has unmapped override key(s): {unmapped}")
    return {
        "role": role,
        "tool": "aperv",
        "variant": variant,
        "rv_tools_token": f"aperv:{variant}",
        "preset": config["preset"],
        "mop_data": config.get("mop_data"),
        "expected_params": {
            APERV_PROPERTY_MAPPING[key]: value for key, value in overrides.items()
        },
    }


def build_manifest(repo_root: Path) -> Dict[str, Any]:
    subset = repo_root / "calibracao/subset40.txt"
    apks = [line for line in subset.read_text().splitlines() if line.strip()]
    return {
        "campaign": "rearch_aperv",
        "leg": "B",
        "gate": "gh97-rearch-ab-gate",
        "paired_against": "experimento-e3-decisiva/per_apk_paired.csv",
        "image": {"tag": "phtcosta/rvandroid:0.9.3-rearch", "id": None},
        "build": {"branch": "rearch", "expected_sha": None},
        "corpus": {
            "subset_file": "calibracao/subset40.txt",
            "apk_count": len(apks),
            "corpus_basis": corpus_basis(subset),
        },
        "reps": 3,
        "timeout": 1800,
        "containers": 8,
        "spec_set": "jca",
        "bootstrap_seed": 42,
        "arms": [arm_entry(variant, role) for variant, role in ARMS],
        "predicted_identities": len(apks) * len(ARMS) * 3,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="manifest.json")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="rv-android root; the corpus list is read from it",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest(Path(args.repo_root))
    Path(args.out).write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"wrote {args.out}: {len(manifest['arms'])} arms, "
        f"{manifest['corpus']['apk_count']} applications, "
        f"{manifest['predicted_identities']} identities"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
