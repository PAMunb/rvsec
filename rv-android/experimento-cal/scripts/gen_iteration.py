#!/usr/bin/env python3
"""CONFIG-GEN — generate one self-contained calibration iteration tree.

This is the first state of the calibration loop (methodology §3.1). It reads a phase
config (`phases/<phase>.json`) and the single source of truth for arm configs
(`ApeRVTool.get_variants()` / `APETool.get_variants()`) and emits a complete `iterN/`
tree that every later state audits or consumes:

    iterN/
      manifest.json              — the iteration contract (see manifest schema below)
      artifacts/tool.py          — byte snapshot of the deployed tool.py (sha256 in manifest)
      artifacts/ape-rv.jar       — byte snapshot of the jar (Phase B only, via --jar)
      docker-compose.<phase>.yml — run compose (shared sglang + N rvandroid containers)
      docker-compose.smoke.yml   — smoke compose (extreme arms, 90s, 1 rep, few APKs)
      filters/batch_NN.txt       — per-container APK sublists (run)
      filters/smoke_NN.txt       — per-container APK sublists (smoke)

Design invariants honored here (specs/calibration-control/spec.md):
  * INV-CAL-01: composes and filters are generated from the manifest, which is resolved
    from get_variants() — arm configs are NEVER re-declared in this generator.
  * INV-CAL-02: every bind-mount is sourced from iterN/artifacts/ (never a worktree path),
    and its sha256 is recorded in the manifest at generation time.
  * INV-CAL-03: the image tag is pinned in the compose; the resolved image ID is recorded
    in the manifest so PRE-FLIGHT can verify it via `docker inspect`.
  * INV-CAL-05: arms are named variants (or the `ape` builtin) — never `@override`.
  * INV-CAL-12: iterations are append-only — the script refuses to overwrite an existing
    iterN/ (exit 2).

The manifest is a *resolved echo* of get_variants(); PRE-FLIGHT re-derives the same values
by an independent code path and fails on any divergence (design decision 4).
"""

from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

# --- repository layout -----------------------------------------------------------------
# scripts/ -> experimento-cal/ -> rv-android/ (repo root).
_SCRIPTS_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = _SCRIPTS_DIR.parent  # experimento-cal/
REPO_ROOT = EXPERIMENT_ROOT.parent  # rv-android/

# The aperv-tool source that the run image ships and that every iteration bind-mounts a
# snapshot of. The mount TARGET is the path this file occupies *inside* the container
# (plan §4 "Imagem e deploy"); the SOURCE is always iterN/artifacts/tool.py.
TOOL_PY_SOURCE = REPO_ROOT / "modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py"
TOOL_PY_MOUNT_TARGET = (
    "/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py"
)

# The subset of ape.properties keys the jar echoes back on the [APE-LLM-CONFIG] trace line,
# keyed by the variant key that produces them. The smoke gate compares these field-by-field.
# llm_max_tokens is intentionally absent: the Phase-A jar hardcodes max_tokens and no cal_a*
# arm sets it (INV-APV-27).
_CONFIG_ACK_FIELDS = {
    "llm_model": "model",
    "llm_temperature": "temperature",
    "llm_top_p": "top_p",
    "llm_top_k": "top_k",
    "llm_timeout_ms": "timeout_ms",
    "llm_prompt_variant": "prompt_variant",
    "llm_percentage": "llm_percentage",
    "llm_on_new_state": "on_new_state",
    "llm_on_stagnation": "on_stagnation",
    "llm_url": "url",
}

# The SGLang service block (shared by run and smoke composes), derived verbatim from the
# experimento-20260721 template — one GPU-backed server the containers reach via host
# loopback. The `command` (with `--model-path`) is set per compose by `_sglang_service()`
# from the manifest's `expected_server_model`, the single source that also drives the smoke
# gate's expected model — so the weights loaded on the GPU and the model the gate checks
# cannot drift. Deep-copied per compose so edits never alias.
_SGLANG_SERVICE = {
    "image": "lmsysorg/sglang:v0.5.6.post2",
    "container_name": "sglang-server",
    "volumes": [
        "${HF_CACHE:-/pedro/desenvolvimento/.cache/huggingface}:/root/.cache/huggingface"
    ],
    "ipc": "host",
    "shm_size": "16g",
    "deploy": {
        "resources": {
            "reservations": {
                "devices": [{"driver": "nvidia", "count": 1, "capabilities": ["gpu"]}]
            }
        }
    },
    "healthcheck": {
        "test": ["CMD", "curl", "-f", "http://localhost:30000/health"],
        "interval": "30s",
        "timeout": "10s",
        "retries": 10,
        "start_period": "120s",
    },
}


def _sglang_command(model_path: str) -> str:
    """The sglang launch command for a given served model. `model_path` is the single source
    of the served model (the manifest `expected_server_model`); every other flag is fixed.
    The flag order/spacing is stable so the rendered compose is byte-identical across
    regenerations for a fixed model (no needless container recreate on `docker compose up`)."""
    return (
        "python3 -m sglang.launch_server "
        f"--model-path {model_path} --host 0.0.0.0 --port 30000 "
        "--trust-remote-code --attention-backend flashinfer --tool-call-parser qwen "
        "--enable-multimodal --context-length 8192"
    )


def _sglang_service(model_path: str) -> Dict[str, Any]:
    """Deep-copy the shared sglang template and set its `--model-path` from `model_path`
    (the served model). One source (`expected_server_model`) feeds both the model loaded on
    the GPU and the smoke gate's expected model, so they cannot drift."""
    service = copy.deepcopy(_SGLANG_SERVICE)
    service["command"] = _sglang_command(model_path)
    return service


# --- arm resolution (single source of truth) -------------------------------------------
def _import_variant_sources():
    """Import the two get_variants() providers. Isolated so tests can assert import paths."""
    from rv_tools.builtin.ape.tool import APETool

    from aperv_tool.tools.aperv.tool import ApeRVTool

    return ApeRVTool, APETool


def resolve_arm_keys(tool: str, variant: str) -> Dict[str, Any]:
    """Resolve an arm's full key dict from get_variants() — never declared here.

    aperv arms come from ApeRVTool.get_variants(); the `ape` builtin from APETool. Raises
    KeyError (surfaced as a usage error by the caller) if the named variant does not exist.
    """
    aperv_cls, ape_cls = _import_variant_sources()
    if tool == "aperv":
        return dict(aperv_cls.get_variants()[variant])
    if tool == "ape":
        return dict(ape_cls.get_variants()[variant])
    raise KeyError(f"unknown tool {tool!r} (expected 'ape' or 'aperv')")


def expected_config_ack(keys: Dict[str, Any]) -> Dict[str, Any]:
    """The [APE-LLM-CONFIG] fields the jar will echo for an arm, from its resolved keys.

    Empty for non-LLM arms (ape builtin, ANC2) — they emit no LLM config line.
    """
    return {
        field: keys[py_key]
        for py_key, field in _CONFIG_ACK_FIELDS.items()
        if py_key in keys
    }


def rv_tools_token(tool: str, variant: str) -> str:
    """The RV_TOOLS DSL token for an arm. Named variants only (INV-CAL-05, no @override)."""
    return f"{tool}:{variant}"


# --- helpers ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    """Hex sha256 of a file, streamed so large jars do not load into memory."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_describe(cwd: Path) -> str:
    """`git describe --dirty --always --tags` of a worktree; 'unknown' if git fails.

    Recorded in the manifest so a worktree edit that drifts from the snapshot is auditable
    (design Risks/Trade-offs). Read-only: never mutates any repository.
    """
    try:
        out = subprocess.run(
            ["git", "describe", "--dirty", "--always", "--tags"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def read_subset(subset_path: Path) -> List[str]:
    """Read APK identifiers from a subset file (one per line; blanks and #comments skipped)."""
    lines = subset_path.read_text().splitlines()
    return [s.strip() for s in lines if s.strip() and not s.strip().startswith("#")]


def partition_round_robin(items: List[str], n: int) -> List[List[str]]:
    """Split items across n buckets round-robin (bucket i = items[i::n]).

    Round-robin balances count within one across buckets regardless of ordering, so no
    container gets a systematically heavier or lighter slice of the subset.
    """
    return [items[i::n] for i in range(n)]


def rotate(tokens: List[str], by: int) -> List[str]:
    """Rotate a token list left by `by` (wrapping). Used to vary arm order per container so
    execution-order effects are balanced across the 8 containers (plan §6)."""
    if not tokens:
        return []
    k = by % len(tokens)
    return tokens[k:] + tokens[:k]


# --- manifest + composes ---------------------------------------------------------------
def build_manifest(
    phase: Dict[str, Any],
    iteration: int,
    apk_count: int,
    tool_py_hash: str,
    jar_hash: str | None,
    ape_describe: str | None,
) -> Dict[str, Any]:
    """Assemble the iteration contract from the phase config + resolved arm keys."""
    n_containers = int(phase["containers"])
    reps = int(phase["reps"])

    arms = []
    tokens = []
    for arm in phase["arms"]:
        keys = resolve_arm_keys(arm["tool"], arm["variant"])
        token = rv_tools_token(arm["tool"], arm["variant"])
        tokens.append(token)
        arms.append(
            {
                "role": arm["role"],
                "tool": arm["tool"],
                "variant": arm["variant"],
                "rv_tools_token": token,
                "keys": keys,
                "expected_config_ack": expected_config_ack(keys),
            }
        )

    # Arm-order rotation across containers (INV: same arm set, rotated order).
    arm_rotation = [rotate(tokens, i) for i in range(n_containers)]

    # Smoke arm resolution — a subset of the run arms by role.
    smoke_cfg = phase["smoke"]
    role_to_token = {a["role"]: a["rv_tools_token"] for a in arms}
    smoke_tokens = [role_to_token[r] for r in smoke_cfg["arm_roles"]]

    artifacts = {"tool.py": tool_py_hash}
    if jar_hash is not None:
        artifacts["ape-rv.jar"] = jar_hash

    return {
        "iteration": iteration,
        "phase": phase["phase"],
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "image": phase["image"],
        "expected_server_model": phase["expected_server_model"],
        "dataset": {"subset_file": phase["subset_file"], "apk_count": apk_count},
        "reps": reps,
        "timeout": int(phase["timeout"]),
        "containers": n_containers,
        "spec_set": phase["spec_set"],
        "bootstrap_seed": int(phase["bootstrap_seed"]),
        "mount_target": TOOL_PY_MOUNT_TARGET,
        "arms": arms,
        "arm_rotation": arm_rotation,
        "artifacts": artifacts,
        "worktree": {
            "rv_android_describe": git_describe(REPO_ROOT),
            "ape_describe": ape_describe,
        },
        "predicted_identities": len(arms) * apk_count * reps,
        "smoke": {
            "arm_roles": smoke_cfg["arm_roles"],
            "tokens": smoke_tokens,
            "apk_count": int(smoke_cfg["apk_count"]),
            "timeout": int(smoke_cfg["timeout"]),
            "reps": int(smoke_cfg["reps"]),
            "predicted_identities": len(smoke_tokens)
            * int(smoke_cfg["apk_count"])
            * int(smoke_cfg["reps"]),
        },
    }


def _rvandroid_service(
    *,
    name: str,
    rv_tools: str,
    reps: int,
    timeout: int,
    spec_set: str,
    apks_dir: str,
    filters_subdir: str,
    delay: int,
    logcat_diagnostics: bool,
) -> Dict[str, Any]:
    """One rvandroid container service (fully expanded — no YAML anchors, so preflight can
    round-trip it with yaml.safe_load)."""
    return {
        "image": "phtcosta/rvandroid:0.9.3",
        "container_name": name,
        "environment": {
            "RV_TOOLS": rv_tools,
            "RV_TIMEOUTS": str(timeout),
            "RV_REPETITIONS": str(reps),
            "RV_NO_WINDOW": "true",
            "RV_SPEC_SET": spec_set,
            "RV_SKIP_MONITORS": "true",
            "RV_SKIP_INSTRUMENT": "true",
            "RV_SKIP_STATIC_ANALYSIS": "true",
            "RV_APKS_DIR": "/opt/rvsec/rv-android/apks",
            "RV_DEVICE_PORT": "5554",
            "RVSMART_LLM_MODE": "true",
            "RV_LOGCAT_DIAGNOSTICS": "true" if logcat_diagnostics else "false",
            "RV_EXPERIMENT_NAME": name,
            "RV_APKS_FILTER": f"/opt/rvsec/rv-android/filters/{filters_subdir}",
            "RV_DELAY": str(delay),
        },
        "devices": ["/dev/kvm:/dev/kvm"],
        "deploy": {"resources": {"limits": {"cpus": "4", "memory": "10g"}}},
        "depends_on": {"sglang": {"condition": "service_healthy"}},
        "volumes": [
            f"{apks_dir}:/opt/rvsec/rv-android/apks:ro",
            # Flat filters dir: every container mounts the whole iterN/filters/ tree and
            # reads only its own file via RV_APKS_FILTER. iterN/ is already per-phase, so
            # no per-phase subdir is needed (unlike a flat multi-phase experiment dir).
            "./filters:/opt/rvsec/rv-android/filters:ro",
            f"./results/{name}:/opt/rvsec/rv-android/results",
            # tool.py snapshot bind-mount (INV-CAL-02): sourced from iterN/artifacts/.
            f"./artifacts/tool.py:{TOOL_PY_MOUNT_TARGET}:ro",
        ],
    }


def build_run_compose(manifest: Dict[str, Any], apks_dir: str) -> Dict[str, Any]:
    """The run compose: shared sglang + N containers, one filter batch each, arm order
    rotated per container."""
    phase = manifest["phase"]
    n = manifest["containers"]
    services: Dict[str, Any] = {
        "sglang": _sglang_service(manifest["expected_server_model"])
    }
    for i in range(n):
        name = f"{phase}_{i:02d}"
        services[name] = _rvandroid_service(
            name=name,
            rv_tools=",".join(manifest["arm_rotation"][i]),
            reps=manifest["reps"],
            timeout=manifest["timeout"],
            spec_set=manifest["spec_set"],
            apks_dir=apks_dir,
            filters_subdir=f"batch_{i:02d}.txt",
            delay=i * 10,
            logcat_diagnostics=False,
        )
    return {"services": services}


def build_smoke_compose(manifest: Dict[str, Any], apks_dir: str) -> Dict[str, Any]:
    """The smoke compose: the extreme-arm subset over a handful of APKs, 90s / 1 rep.

    Uses min(containers, smoke apk_count) containers so each carries ~1 APK — a fast gate.
    """
    phase = manifest["phase"]
    smoke = manifest["smoke"]
    n = min(manifest["containers"], smoke["apk_count"])
    smoke_tokens = smoke["tokens"]
    services: Dict[str, Any] = {
        "sglang": _sglang_service(manifest["expected_server_model"])
    }
    for i in range(n):
        name = f"{phase}_smoke_{i:02d}"
        services[name] = _rvandroid_service(
            name=name,
            rv_tools=",".join(rotate(smoke_tokens, i)),
            reps=smoke["reps"],
            timeout=smoke["timeout"],
            spec_set=manifest["spec_set"],
            apks_dir=apks_dir,
            filters_subdir=f"smoke_{i:02d}.txt",
            delay=i * 10,
            # Smoke turns logcat diagnostics ON to surface VerifyError / crashes early.
            logcat_diagnostics=True,
        )
    return {"services": services}


# --- write the iteration ---------------------------------------------------------------
def write_iteration(
    phase_path: Path, iteration: int, jar_path: Path | None, iter_root: Path
) -> Path:
    """Generate iterN/ end to end. Returns the iteration directory."""
    phase = json.loads(phase_path.read_text())
    iter_dir = iter_root / f"iter{iteration}"

    # INV-CAL-12: iterations are append-only. A discarded iteration keeps its directory as
    # provenance; overwriting would erase that record.
    if iter_dir.exists():
        sys.stderr.write(
            f"iteration directory already exists: {iter_dir}\n"
            f"iterations are append-only — use the next N (INV-CAL-12).\n"
        )
        raise SystemExit(2)

    subset_path = REPO_ROOT / phase["subset_file"]
    if not subset_path.exists():
        sys.stderr.write(
            f"subset file not found: {subset_path}\n"
            f"(Fase 0 / P3 produces it offline; it is not part of this change.)\n"
        )
        raise SystemExit(2)
    apks = read_subset(subset_path)

    # Snapshot artifacts BEFORE hashing so the manifest hash matches the mounted bytes.
    artifacts_dir = iter_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)
    shutil.copy2(TOOL_PY_SOURCE, artifacts_dir / "tool.py")
    tool_py_hash = sha256_file(artifacts_dir / "tool.py")

    jar_hash = None
    ape_describe = None
    if jar_path is not None:
        shutil.copy2(jar_path, artifacts_dir / "ape-rv.jar")
        jar_hash = sha256_file(artifacts_dir / "ape-rv.jar")
        ape_describe = git_describe(jar_path.resolve().parent)

    manifest = build_manifest(
        phase=phase,
        iteration=iteration,
        apk_count=len(apks),
        tool_py_hash=tool_py_hash,
        jar_hash=jar_hash,
        ape_describe=ape_describe,
    )
    (iter_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    apks_dir = phase["apks_dir"]
    run_compose = build_run_compose(manifest, apks_dir)
    smoke_compose = build_smoke_compose(manifest, apks_dir)
    (iter_dir / f"docker-compose.{phase['phase']}.yml").write_text(
        yaml.safe_dump(run_compose, sort_keys=False, default_flow_style=False)
    )
    (iter_dir / "docker-compose.smoke.yml").write_text(
        yaml.safe_dump(smoke_compose, sort_keys=False, default_flow_style=False)
    )

    # Filters: run batches (round-robin partition of the full subset) + smoke batches
    # (first `smoke.apk_count` APKs, one per smoke container).
    filters_dir = iter_dir / "filters"
    filters_dir.mkdir()
    for i, batch in enumerate(partition_round_robin(apks, manifest["containers"])):
        (filters_dir / f"batch_{i:02d}.txt").write_text(
            "\n".join(batch) + ("\n" if batch else "")
        )
    smoke_apks = apks[: manifest["smoke"]["apk_count"]]
    n_smoke = min(manifest["containers"], manifest["smoke"]["apk_count"])
    for i, batch in enumerate(partition_round_robin(smoke_apks, n_smoke)):
        (filters_dir / f"smoke_{i:02d}.txt").write_text(
            "\n".join(batch) + ("\n" if batch else "")
        )

    return iter_dir


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--phase", required=True, help="path to phases/<phase>.json")
    parser.add_argument("--iter", required=True, type=int, help="iteration number N")
    parser.add_argument(
        "--jar",
        default=None,
        help="optional ape-rv.jar to snapshot (Phase B); omitted in Phase A",
    )
    parser.add_argument(
        "--iter-root",
        default=str(EXPERIMENT_ROOT),
        help="root under which iterN/ is created (default: experimento-cal/)",
    )
    args = parser.parse_args(argv)

    phase_path = Path(args.phase)
    if not phase_path.is_absolute():
        phase_path = (Path.cwd() / phase_path).resolve()
    if not phase_path.exists():
        sys.stderr.write(f"phase config not found: {phase_path}\n")
        return 2

    jar_path = Path(args.jar).resolve() if args.jar else None
    if jar_path is not None and not jar_path.exists():
        sys.stderr.write(f"--jar path not found: {jar_path}\n")
        return 2

    try:
        iter_dir = write_iteration(
            phase_path, args.iter, jar_path, Path(args.iter_root)
        )
    except KeyError as exc:
        sys.stderr.write(f"unknown variant or missing phase field: {exc}\n")
        return 2
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0

    manifest = json.loads((iter_dir / "manifest.json").read_text())
    print(f"generated {iter_dir}")
    print(
        f"  arms={len(manifest['arms'])} "
        f"predicted_identities={manifest['predicted_identities']} "
        f"smoke_identities={manifest['smoke']['predicted_identities']}"
    )
    print(
        "journal line: "
        + json.dumps(
            {
                "state": "CONFIG-GEN",
                "iter": args.iter,
                "artifact": str(iter_dir / "manifest.json"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
