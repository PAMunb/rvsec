#!/usr/bin/env python3
"""Pre-instrument the gov.br dataset (dexlib2 + JCA monitors, NO static analysis).

Runs preprocessing-only (`rv-experiment run --skip-execution`) inside the rvandroid
Docker image across N parallel worker containers, then collects the instrumented
`.apk` files into a flat destination directory (the resume-safe dataset the 8-container
run will execute over).

Why this exists (vs scripts/preprocess_docker.py): this experiment SKIPS static analysis
and forces the dexlib2 variant (the CLI default is `ajc`). We also collect only `.apk`
(no `.apk.json`, since static is skipped) — the plain `ape` tool does not need it.

The Docker image carries RVSEC_HOME + Java 8 + the dexlib2 weaver, so there are no
host-side toolchain deps. The entrypoint is overridden (bash -c) because the frozen
image's docker-entrypoint.sh maps RV_SKIP_* env vars (which invert outside the
entrypoint); we pass the explicit `--skip-*` CLI flags instead.

Usage:
    uv run python experimento-gov/scripts/instrument_gov.py \
        --apks-dir /home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/APKS \
        --filter  experimento-gov/filters/gov_all_34.txt \
        --out     experimento-gov/instrumentation/out \
        --dest    /home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/APKS_INSTRUMENTADOS \
        --workers 8
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

IMAGE = "phtcosta/rvandroid:0.9.2"
STAGGER_S = 10  # avoid a monitor-gen boot-storm across workers


def read_filter(path: Path) -> list[str]:
    names = []
    for line in path.read_text().splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            names.append(s)
    return names


def round_robin(names: list[str], n: int) -> list[list[str]]:
    b = [[] for _ in range(n)]
    for i, x in enumerate(names):
        b[i % n].append(x)
    return b


def gen_compose(n: int, apks_dir: str, out_dir: str, image: str, cpus: int, mem: str) -> dict:
    apks_dir = str(Path(apks_dir).resolve())
    out_dir = str(Path(out_dir).resolve())
    services = {}
    for i in range(n):
        name = f"gov_instr_{i:02d}"
        services[name] = {
            "image": image,
            "container_name": name,
            "entrypoint": ["bash", "-c"],
            "command": [
                f"sleep {i * STAGGER_S} && "
                "uv run rv-experiment run "
                "--tools monkey "            # dummy; --skip-execution never runs it
                "--skip-execution "
                "--skip-static "             # <-- only static is skipped
                "--instrumentation-variant dexlib2 "  # <-- CLI default is ajc; force dexlib2
                "--specification-set jca "
                "--apks-dir /opt/rvsec/rv-android/apks "
                "--apks-filter /opt/rvsec/rv-android/filters/filter.txt "
                "--output-dir /opt/rvsec/rv-android/out "
                "--no-window"
            ],
            "volumes": [
                f"{apks_dir}:/opt/rvsec/rv-android/apks:ro",
                f"{out_dir}/{name}_filter.txt:/opt/rvsec/rv-android/filters/filter.txt:ro",
                f"{out_dir}/{name}:/opt/rvsec/rv-android/out",
            ],
            "devices": ["/dev/kvm:/dev/kvm"],
            "deploy": {"resources": {"limits": {"cpus": str(cpus), "memory": mem}}},
        }
    return {"services": services}


def collect(out_dir: Path, n: int, dest: Path) -> tuple[int, list[str]]:
    dest.mkdir(parents=True, exist_ok=True)
    copied, found = 0, []
    for i in range(n):
        src = out_dir / f"gov_instr_{i:02d}" / "instrumented_apks"
        if not src.is_dir():
            print(f"WARN: missing worker output {src}", file=sys.stderr)
            continue
        for f in src.glob("*.apk"):
            shutil.copy2(f, dest / f.name)
            found.append(f.name)
            copied += 1
    return copied, sorted(found)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apks-dir", required=True)
    ap.add_argument("--filter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--cpus", type=int, default=4)
    ap.add_argument("--memory", default="10g")
    ap.add_argument("--generate-only", action="store_true")
    a = ap.parse_args()

    names = read_filter(Path(a.filter))
    if not names:
        sys.exit("ERROR: empty filter")
    n = min(a.workers, len(names))
    batches = round_robin(names, n)

    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for i, b in enumerate(batches):
        (out / f"gov_instr_{i:02d}_filter.txt").write_text("\n".join(b) + "\n")
    print(f"{len(names)} APKs across {n} workers: " + ", ".join(str(len(b)) for b in batches))

    compose = gen_compose(n, a.apks_dir, str(out), a.image, a.cpus, a.memory)
    compose_path = out / "docker-compose.instrument.yml"
    compose_path.write_text(yaml.dump(compose, default_flow_style=False, sort_keys=False))
    print(f"compose: {compose_path}")
    if a.generate_only:
        return

    names = [f"gov_instr_{i:02d}" for i in range(n)]
    try:
        subprocess.run(["docker", "compose", "-f", str(compose_path), "up", "-d"], check=False)
        # Block until every worker container has exited (each instruments its slice then stops).
        subprocess.run(["docker", "wait", *names], check=False)
    finally:
        subprocess.run(["docker", "compose", "-f", str(compose_path), "down"], check=False)

    copied, found = collect(out, n, Path(a.dest).resolve())
    missing = sorted(set(names) - set(found))
    print("=" * 60)
    print(f"INSTRUMENTED: {copied}/{len(names)} -> {a.dest}")
    if missing:
        print(f"MISSING ({len(missing)}): " + ", ".join(missing))
        (out / "instrument_missing.txt").write_text("\n".join(missing) + "\n")
    else:
        print("ALL APKs instrumented OK.")


if __name__ == "__main__":
    main()
