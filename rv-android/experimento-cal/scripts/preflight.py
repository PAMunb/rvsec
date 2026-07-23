#!/usr/bin/env python3
"""PRE-FLIGHT — independently audit a generated calibration iteration before launch.

This is the gate of human gate G3 (methodology §3.1): the last automated check between
`gen_iteration.py` producing an `iterN/` tree and an agent launching it on the fixed image.
Its whole reason to exist is *independence*: it re-derives every number it checks with its
own parsing logic, because an agent re-running the producer's script is not verification.

Independence is a hard invariant (INV-CAL-04): this module MUST NOT import `gen_iteration`.
It re-imports the single source of truth for arm configs DIRECTLY —
`ApeRVTool.get_variants()` and `APETool.get_variants()` — and re-parses the generated
composes with `yaml.safe_load`, so a bug or hand-edit in the generated tree cannot hide
behind shared code. `test_preflight_import_independence` enforces the no-import rule by AST.

Checks performed (spec "Pre-Flight Audit", INV-CAL-01/02/03):
  (a) every manifest arm exists in get_variants() and its `keys` dict matches field-by-field;
  (b) each container service's RV_TOOLS token set equals the manifest arm token set, and its
      timeouts / reps / image / tool.py bind-mount match the manifest (run compose against the
      full arm set, smoke compose against the smoke subset);
  (c) predicted identities are distinct — ≥11 distinct (tool, variant) pairs in a full
      Phase-A manifest — and total == arms × apk_count × reps, re-derived from the filters;
  (d) the sha256 of every file in iterN/artifacts/ equals the manifest hash;
  (e) the compose image is the pinned tag AND the resolved image ID matches the manifest
      (INV-CAL-03) — via `docker inspect` when docker is available, else an explicit SKIP
      line (a live launch must NOT skip this);
  (f) the `sglang` service is present with the expected model in its command.

Exit code: 0 when every check PASSes, 1 on any FAIL, 2 on usage error. The report lists every
check with a PASS/FAIL/SKIP status so a human gate reviewer sees exactly what was verified.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

# The pinned image (INV-CAL-03). The tag is what a compose `image:` field can hold; the
# 12-char ID cannot be pinned in a compose, so it is carried in the manifest and verified
# here against the resolved image.
PINNED_IMAGE_TAG = "phtcosta/rvandroid:0.9.3"

# Phase A (`cala`) runs the full 11-arm interleaved design; the distinct-pair floor only
# binds there (other phases may legitimately run fewer arms).
PHASE_A_NAME = "cala"
PHASE_A_MIN_DISTINCT_PAIRS = 11


# --- report plumbing -------------------------------------------------------------------
@dataclasses.dataclass
class CheckRecord:
    """One audited condition: its label, a PASS/FAIL/SKIP status, and a human detail line."""

    label: str
    status: str  # "PASS" | "FAIL" | "SKIP"
    detail: str = ""


class Report:
    """Accumulates check records and tracks whether any FAILed (drives the exit code).

    SKIP does not fail the gate — it is used only for the image-ID check when docker is
    unavailable, and the printed line makes explicit that a real launch must not skip it.
    """

    def __init__(self) -> None:
        self.records: List[CheckRecord] = []

    def add(self, label: str, ok: bool, detail: str = "") -> None:
        self.records.append(CheckRecord(label, "PASS" if ok else "FAIL", detail))

    def skip(self, label: str, detail: str = "") -> None:
        self.records.append(CheckRecord(label, "SKIP", detail))

    @property
    def failed(self) -> bool:
        return any(r.status == "FAIL" for r in self.records)

    def render(self) -> str:
        lines = []
        for r in self.records:
            head = f"[{r.status}] {r.label}"
            lines.append(head if not r.detail else f"{head}\n        {r.detail}")
        verdict = "FAIL" if self.failed else "PASS"
        lines.append(f"--- PRE-FLIGHT {verdict} ---")
        return "\n".join(lines)


# --- independent arm resolution (single source of truth; NOT via gen_iteration) --------
def resolve_variants() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Re-import get_variants() from both providers, independently of the generator.

    Returns (aperv_variants, ape_variants). Kept in one function so the AST-independence
    test has a single, obvious place these imports live — and so they are provably NOT
    routed through `gen_iteration`.
    """
    from rv_tools.builtin.ape.tool import APETool

    from aperv_tool.tools.aperv.tool import ApeRVTool

    return ApeRVTool.get_variants(), APETool.get_variants()


def load_manifest(iter_dir: Path) -> Dict[str, Any]:
    return json.loads((iter_dir / "manifest.json").read_text())


def sha256_file(path: Path) -> str:
    """Hex sha256 of a file, streamed (jars are large; do not slurp into memory)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_filter_apks(iter_dir: Path) -> Set[str]:
    """Collect the distinct APK identifiers across the run filters (batch_*.txt).

    Re-deriving the subset size from the actually-generated filters — rather than trusting
    manifest.dataset.apk_count — is the whole point of check (c): a filter that lost or
    duplicated APKs would otherwise silently change the identity count.
    """
    apks: Set[str] = set()
    for batch in sorted((iter_dir / "filters").glob("batch_*.txt")):
        for line in batch.read_text().splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                apks.add(s)
    return apks


# --- (a) arms match get_variants() -----------------------------------------------------
def check_arms(manifest: Dict[str, Any], report: Report) -> None:
    """Every manifest arm must resolve in get_variants() with an identical key dict."""
    aperv_variants, ape_variants = resolve_variants()
    for arm in manifest["arms"]:
        tool, variant = arm["tool"], arm["variant"]
        source = aperv_variants if tool == "aperv" else ape_variants
        label = (
            f"arm {arm['role']} ({tool}:{variant}) resolves and matches get_variants()"
        )
        if variant not in source:
            report.add(
                label, False, f"variant {variant!r} absent from {tool} get_variants()"
            )
            continue
        resolved = dict(source[variant])
        if arm["keys"] != resolved:
            diffs = _dict_diff(arm["keys"], resolved)
            report.add(label, False, f"key mismatch: {diffs}")
        else:
            report.add(label, True)


def _dict_diff(a: Dict[str, Any], b: Dict[str, Any]) -> str:
    """Compact field-by-field diff of two dicts for a failure detail line."""
    keys = sorted(set(a) | set(b))
    parts = []
    for k in keys:
        if a.get(k) != b.get(k):
            parts.append(f"{k}: manifest={a.get(k)!r} get_variants={b.get(k)!r}")
    return "; ".join(parts) if parts else "(no field diff)"


# --- (b) composes match the manifest ---------------------------------------------------
def _audit_compose_services(
    *,
    compose: Dict[str, Any],
    expected_tokens: Set[str],
    expected_timeout: str,
    expected_reps: str,
    image_tag: str,
    mount_target: str,
    label_prefix: str,
    report: Report,
) -> None:
    """Audit every non-sglang service in a compose against the manifest-derived expectations.

    Each container is one check record so a single tampered container is named precisely
    (spec scenario "Tampered compose is detected").
    """
    services = compose.get("services", {})
    for name, svc in services.items():
        if name == "sglang":
            continue
        env = svc.get("environment", {})
        problems: List[str] = []

        tokens = [t for t in env.get("RV_TOOLS", "").split(",") if t]
        token_set = set(tokens)
        if token_set != expected_tokens:
            missing = sorted(expected_tokens - token_set)
            extra = sorted(token_set - expected_tokens)
            if missing:
                problems.append(f"RV_TOOLS missing arm(s): {missing}")
            if extra:
                problems.append(f"RV_TOOLS unexpected arm(s): {extra}")

        if str(env.get("RV_TIMEOUTS")) != expected_timeout:
            problems.append(
                f"RV_TIMEOUTS={env.get('RV_TIMEOUTS')!r} != manifest {expected_timeout!r}"
            )
        if str(env.get("RV_REPETITIONS")) != expected_reps:
            problems.append(
                f"RV_REPETITIONS={env.get('RV_REPETITIONS')!r} != manifest {expected_reps!r}"
            )
        if svc.get("image") != image_tag:
            problems.append(f"image={svc.get('image')!r} != manifest tag {image_tag!r}")

        want_mount = f"./artifacts/tool.py:{mount_target}:ro"
        tool_mounts = [v for v in svc.get("volumes", []) if "artifacts/tool.py" in v]
        if tool_mounts != [want_mount]:
            problems.append(f"tool.py mount {tool_mounts} != [{want_mount!r}]")

        label = f"{label_prefix} container {name} matches manifest"
        if problems:
            report.add(label, False, "; ".join(problems))
        else:
            report.add(label, True)


def check_composes(manifest: Dict[str, Any], iter_dir: Path, report: Report) -> None:
    """Audit both the run compose (full arm set) and the smoke compose (smoke subset)."""
    phase = manifest["phase"]
    mount_target = manifest["mount_target"]
    image_tag = manifest["image"]["tag"]

    run_tokens = {a["rv_tools_token"] for a in manifest["arms"]}
    run_path = iter_dir / f"docker-compose.{phase}.yml"
    run_compose = yaml.safe_load(run_path.read_text())
    _audit_compose_services(
        compose=run_compose,
        expected_tokens=run_tokens,
        expected_timeout=str(manifest["timeout"]),
        expected_reps=str(manifest["reps"]),
        image_tag=image_tag,
        mount_target=mount_target,
        label_prefix="run",
        report=report,
    )

    smoke = manifest["smoke"]
    smoke_tokens = set(smoke["tokens"])
    smoke_path = iter_dir / "docker-compose.smoke.yml"
    smoke_compose = yaml.safe_load(smoke_path.read_text())
    _audit_compose_services(
        compose=smoke_compose,
        expected_tokens=smoke_tokens,
        expected_timeout=str(smoke["timeout"]),
        expected_reps=str(smoke["reps"]),
        image_tag=image_tag,
        mount_target=mount_target,
        label_prefix="smoke",
        report=report,
    )


# --- (c) identity counts re-derived from first principles -------------------------------
@dataclasses.dataclass
class IdentityCounts:
    """The identity arithmetic re-derived independently from the manifest + filters.

    total = n_arms × apk_count × reps, with apk_count taken from the *actual* run filters,
    not the manifest field (so a filter that lost/duplicated APKs is caught). distinct_pairs
    counts unique (tool, variant) arm identities — INV-CAL-05 forbids two arms colliding.
    """

    n_arms: int
    apk_count: int
    reps: int
    total: int
    distinct_pairs: int
    manifest_total: int
    manifest_apk_count: int
    phase: str

    @property
    def ok(self) -> bool:
        floor_ok = (
            self.distinct_pairs >= PHASE_A_MIN_DISTINCT_PAIRS
            if self.phase == PHASE_A_NAME
            else True
        )
        return (
            self.distinct_pairs == self.n_arms
            and self.apk_count == self.manifest_apk_count
            and self.total == self.manifest_total
            and floor_ok
        )


def check_identities(manifest: Dict[str, Any], iter_dir: Path) -> IdentityCounts:
    """Re-derive the predicted identity count and distinct-arm count from first principles."""
    arms = manifest["arms"]
    reps = int(manifest["reps"])
    apk_count = len(read_filter_apks(iter_dir))
    distinct_pairs = len({(a["tool"], a["variant"]) for a in arms})
    return IdentityCounts(
        n_arms=len(arms),
        apk_count=apk_count,
        reps=reps,
        total=len(arms) * apk_count * reps,
        distinct_pairs=distinct_pairs,
        manifest_total=int(manifest["predicted_identities"]),
        manifest_apk_count=int(manifest["dataset"]["apk_count"]),
        phase=manifest["phase"],
    )


def add_identity_check(
    manifest: Dict[str, Any], iter_dir: Path, report: Report
) -> None:
    c = check_identities(manifest, iter_dir)
    detail = (
        f"arms={c.n_arms} × apk_count={c.apk_count} × reps={c.reps} = {c.total} "
        f"(manifest predicted_identities={c.manifest_total}); "
        f"distinct (tool,variant) pairs={c.distinct_pairs}"
    )
    if c.phase == PHASE_A_NAME:
        detail += f" (Phase-A floor {PHASE_A_MIN_DISTINCT_PAIRS})"
    report.add("identity count re-derives from filters + manifest", c.ok, detail)


# --- (d) artifact hashes ---------------------------------------------------------------
def check_artifacts(manifest: Dict[str, Any], iter_dir: Path, report: Report) -> None:
    """Every file in artifacts/ must hash to the manifest value (INV-CAL-02).

    Remediation on drift is to GENERATE A NEW ITERATION, never re-snapshot in place: the
    manifest is the launch contract and its recorded hash is the provenance anchor.
    """
    artifacts_dir = iter_dir / "artifacts"
    recorded: Dict[str, str] = manifest.get("artifacts", {})
    files = sorted(p for p in artifacts_dir.iterdir() if p.is_file())
    seen: Set[str] = set()
    for path in files:
        seen.add(path.name)
        label = f"artifact {path.name} hash matches manifest"
        if path.name not in recorded:
            report.add(
                label, False, "file present in artifacts/ but absent from manifest"
            )
            continue
        actual = sha256_file(path)
        if actual != recorded[path.name]:
            report.add(
                label,
                False,
                f"sha256 {actual} != manifest {recorded[path.name]}. "
                "Remediation: generate a NEW iteration (do not re-snapshot in place).",
            )
        else:
            report.add(label, True)
    for name in recorded:
        if name not in seen:
            report.add(
                f"artifact {name} present",
                False,
                "recorded in manifest but missing from artifacts/",
            )


# --- (e) image tag + resolved ID -------------------------------------------------------
def resolve_image_id(tag: str) -> Optional[str]:
    """The full image ID docker resolves for `tag`, or None if docker/image unavailable.

    Read-only metadata lookup (`docker inspect`) — it launches nothing. None means "cannot
    resolve" (docker missing, or the image not pulled), which becomes a SKIP, not a FAIL.
    """
    if not shutil.which("docker"):
        return None
    try:
        out = subprocess.run(
            ["docker", "inspect", "--format", "{{.Id}}", tag],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def check_image(
    manifest: Dict[str, Any], report: Report, allow_docker: bool = True
) -> None:
    """Tag must be the pinned tag; the resolved ID must match the manifest (INV-CAL-03)."""
    tag = manifest["image"]["tag"]
    manifest_id = manifest["image"]["id"]
    report.add(
        "image tag is the pinned tag",
        tag == PINNED_IMAGE_TAG,
        f"manifest image tag={tag!r} (pinned {PINNED_IMAGE_TAG!r})",
    )

    if not allow_docker:
        report.skip(
            "image ID matches manifest",
            "SKIPPED-image-id-check (docker verification disabled). "
            "A live launch MUST verify the resolved ID against the manifest.",
        )
        return

    resolved = resolve_image_id(tag)
    if resolved is None:
        report.skip(
            "image ID matches manifest",
            "SKIPPED-image-id-check (docker unavailable or image not pulled). "
            "A live launch MUST NOT skip this — the 12-char ID cannot be pinned in compose.",
        )
        return

    bare = resolved.split(":", 1)[1] if ":" in resolved else resolved
    ok = bare.startswith(manifest_id)
    report.add(
        "image ID matches manifest",
        ok,
        f"resolved {resolved} vs manifest id {manifest_id}",
    )


# --- (f) sglang service ----------------------------------------------------------------
def check_sglang(manifest: Dict[str, Any], iter_dir: Path, report: Report) -> None:
    """Both composes must carry the sglang service with the expected model in its command."""
    model = manifest["expected_server_model"]
    phase = manifest["phase"]
    for compose_name in (f"docker-compose.{phase}.yml", "docker-compose.smoke.yml"):
        compose = yaml.safe_load((iter_dir / compose_name).read_text())
        services = compose.get("services", {})
        label = f"sglang service present with model in {compose_name}"
        if "sglang" not in services:
            report.add(label, False, "sglang service absent")
            continue
        command = services["sglang"].get("command", "")
        if isinstance(command, list):
            command = " ".join(str(c) for c in command)
        report.add(
            label,
            model in command,
            f"expected model {model!r} {'found' if model in command else 'NOT found'} in command",
        )


# --- orchestration ---------------------------------------------------------------------
def run_preflight(iter_dir: Path, allow_docker: bool = True) -> Report:
    """Run every audit against `iter_dir` and return the populated report."""
    manifest = load_manifest(iter_dir)
    report = Report()
    check_arms(manifest, report)
    check_composes(manifest, iter_dir, report)
    add_identity_check(manifest, iter_dir, report)
    check_artifacts(manifest, iter_dir, report)
    check_image(manifest, report, allow_docker=allow_docker)
    check_sglang(manifest, iter_dir, report)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--iter-dir", required=True, help="path to the generated iterN/ directory"
    )
    parser.add_argument(
        "--skip-image-id",
        action="store_true",
        help=(
            "skip the docker image-ID resolution (INV-CAL-03). Use ONLY when docker is "
            "unavailable; a live launch must verify the ID."
        ),
    )
    args = parser.parse_args(argv)

    iter_dir = Path(args.iter_dir)
    if not (iter_dir / "manifest.json").exists():
        sys.stderr.write(f"no manifest.json under iter-dir: {iter_dir}\n")
        return 2

    report = run_preflight(iter_dir, allow_docker=not args.skip_image_id)
    print(report.render())
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
