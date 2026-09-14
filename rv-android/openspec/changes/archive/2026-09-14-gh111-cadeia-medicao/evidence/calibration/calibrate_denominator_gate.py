"""Calibrate the denominator gate's threshold over the 162-APK article corpus.

Why this reads the DEX headers instead of the artefacts. The gate's input is
``class_defs_under_key``, which task 1.4 makes the producer record — so only
artefacts written after the reactor rebuild carry it, and the 162 stored ones do
not. Re-running GATOR over 162 APKs to obtain it is 81-243 h. The count is
nothing but the compiled class universe under a key, which the DEX headers give
directly: ``class_defs`` names every class in the file, and the walk is about a
minute for the whole corpus.

The production gate is unaffected by this: it stays a pure artefact predicate
(task 2.4). This script exists to prove the tripwire is correctly placed, and to
answer the question the threshold turns on — does the corrected ratio separate
the collapsed artefacts from the healthy ones, and by how much.

Two riders the numbers demand.

**The ratio is corrected on both sides.** The compiled side applies the client's
own ``isAppClass`` predicate as INV-ANA-71 rewrites it (last-segment anchored),
and the parsed side is re-filtered by the same predicate — the 162 artefacts were
written under the root-anchored rule and carry 505 module-level resource classes
that a post-change run would not emit. One predicate on both terms is what makes
the healthy band land exactly at 1.0 rather than approximately.

**The calibration holds under the neutralized key.** Under the literal manifest
key, 75 of the 162 have no compiled class at all: 0/0 is not a low ratio, it is
no ratio, and a 0.15 gate would refuse 75 apps, 71 of them healthy. That is why
task 2.6 lands the gate warn-only until D2 supplies a key that resolves.

Usage:
    uv run python openspec/changes/gh111-cadeia-medicao/evidence/calibration/\\
        calibrate_denominator_gate.py <corpus-dir> [--out report.md]
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[5]
        / "modules"
        / "rv-android-core"
        / "src"
    ),
)
from rv_android_core.util.android.build_type_suffix import (  # noqa: E402
    neutralize_build_type_suffix,
)

# ---------------------------------------------------------------- DEX reading

_HEADER_STRING_IDS_SIZE = 56
_HEADER_TYPE_IDS_SIZE = 64
_HEADER_CLASS_DEFS_SIZE = 96
_CLASS_DEF_ITEM_SIZE = 32


def _uleb128(buf: bytes, off: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        b = buf[off]
        off += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, off
        shift += 7


def dex_class_names(dex: bytes) -> list[str]:
    """Every class defined in one DEX, as dotted binary names.

    Walks class_defs -> type_ids -> string_ids -> string_data, which is the
    minimum needed to turn a class_def into a name. Descriptors arrive in JVM
    form (``Lcom/example/Foo$Bar;``) and come back as ``com.example.Foo$Bar``,
    the spelling ``SootClass.getName()`` produces and the artefact carries.
    """
    (string_ids_size, string_ids_off) = struct.unpack_from(
        "<II", dex, _HEADER_STRING_IDS_SIZE
    )
    (type_ids_size, type_ids_off) = struct.unpack_from(
        "<II", dex, _HEADER_TYPE_IDS_SIZE
    )
    (class_defs_size, class_defs_off) = struct.unpack_from(
        "<II", dex, _HEADER_CLASS_DEFS_SIZE
    )

    names: list[str] = []
    for i in range(class_defs_size):
        (type_idx,) = struct.unpack_from(
            "<I", dex, class_defs_off + i * _CLASS_DEF_ITEM_SIZE
        )
        if type_idx >= type_ids_size:
            continue
        (descriptor_idx,) = struct.unpack_from("<I", dex, type_ids_off + type_idx * 4)
        if descriptor_idx >= string_ids_size:
            continue
        (data_off,) = struct.unpack_from("<I", dex, string_ids_off + descriptor_idx * 4)
        length, off = _uleb128(dex, data_off)
        raw = dex[off : dex.index(b"\x00", off)].decode("utf-8", "replace")
        if raw.startswith("L") and raw.endswith(";"):
            names.append(raw[1:-1].replace("/", "."))
    return names


def apk_class_names(apk_path: Path) -> list[str]:
    names: list[str] = []
    with zipfile.ZipFile(apk_path) as z:
        for entry in z.namelist():
            if entry.startswith("classes") and entry.endswith(".dex"):
                names.extend(dex_class_names(z.read(entry)))
    return names


# ------------------------------------------------- the client's own predicate


def is_generated_resource_class(name: str) -> bool:
    """``RvsecAnalysisClient.isGeneratedResourceClass`` as INV-ANA-71 writes it."""
    segment = name.rsplit(".", 1)[-1]
    return (
        segment == "R"
        or segment.startswith("R$")
        or segment == "BuildConfig"
        or segment == "Manifest"
        or segment.startswith("Manifest$")
    )


def is_app_class(name: str, key: str) -> bool:
    return name.startswith(key) and not is_generated_resource_class(name)


# ------------------------------------------------------------------ the sweep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("corpus", type=Path, help="directory of <apk> + <apk>.json pairs")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    rows = []
    for apk in sorted(args.corpus.glob("*.apk")):
        artefact = apk.with_suffix(".apk.json")
        if not artefact.is_file():
            continue
        data = json.loads(artefact.read_text(encoding="utf-8"))
        manifest_key = data.get("package") or ""
        key = neutralize_build_type_suffix(manifest_key)

        compiled = apk_class_names(apk)
        compiled_net = sum(1 for n in compiled if is_app_class(n, key))
        compiled_manifest_key = sum(
            1 for n in compiled if is_app_class(n, manifest_key)
        )

        parsed_all = [c["className"] for c in data.get("reachability", [])]
        # The artefacts were written under the root-anchored rule; re-filter so
        # both terms answer to one predicate.
        parsed_net = sum(1 for n in parsed_all if not is_generated_resource_class(n))

        rows.append(
            {
                "apk": apk.name,
                "manifest_key": manifest_key,
                "key": key,
                "neutralized": key != manifest_key,
                "parsed_raw": len(parsed_all),
                "parsed_net": parsed_net,
                "compiled_net": compiled_net,
                "compiled_net_manifest_key": compiled_manifest_key,
                "ratio": (parsed_net / compiled_net) if compiled_net else None,
            }
        )

    collapsed = [r for r in rows if r["ratio"] is not None and r["ratio"] < 0.15]
    admitted = [r for r in rows if r["ratio"] is not None and r["ratio"] >= 0.15]
    zero_universe = [r for r in rows if r["ratio"] is None]
    zero_under_manifest = [
        r for r in rows if r["compiled_net_manifest_key"] == 0
    ]

    report = []
    report.append("# Task 2.5 — denominator gate calibration over the corpus\n")
    report.append(f"- APKs measured: **{len(rows)}**")
    report.append(f"- refused (ratio < 0.15): **{len(collapsed)}**")
    report.append(f"- admitted (ratio >= 0.15): **{len(admitted)}**")
    report.append(f"- zero compiled universe under the NEUTRALIZED key: {len(zero_universe)}")
    report.append(
        f"- zero compiled universe under the LITERAL MANIFEST key: "
        f"**{len(zero_under_manifest)}** — the reason task 2.6 lands warn-only"
    )
    if admitted:
        lo = min(admitted, key=lambda r: r["ratio"])
        report.append(
            f"- **min(admitted) = {lo['ratio']:.4f}**  ({lo['apk']}, "
            f"{lo['parsed_net']}/{lo['compiled_net']})"
        )
    if collapsed:
        hi = max(collapsed, key=lambda r: r["ratio"])
        report.append(
            f"- **max(refused) = {hi['ratio']:.4f}**  ({hi['apk']}, "
            f"{hi['parsed_net']}/{hi['compiled_net']})"
        )
        report.append("\n## Refused\n")
        report.append("| APK | manifest key | neutralized key | parsed | compiled | ratio |")
        report.append("|---|---|---|---:|---:|---:|")
        for r in sorted(collapsed, key=lambda r: r["ratio"]):
            report.append(
                f"| `{r['apk']}` | `{r['manifest_key']}` | `{r['key']}` | "
                f"{r['parsed_net']} | {r['compiled_net']} | {r['ratio']:.4f} |"
            )
    if zero_universe:
        report.append("\n## Zero compiled universe under the neutralized key\n")
        for r in zero_universe:
            report.append(f"- `{r['apk']}` key `{r['key']}` parsed {r['parsed_net']}")

    below_one = [r for r in admitted if r["ratio"] < 0.999]
    report.append(
        f"\n## Admitted band\n\nAdmitted APKs below 1.0: **{len(below_one)}**"
    )
    for r in sorted(below_one, key=lambda r: r["ratio"])[:20]:
        report.append(
            f"- `{r['apk']}` {r['parsed_net']}/{r['compiled_net']} = {r['ratio']:.4f}"
        )

    text = "\n".join(report) + "\n"
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        (args.out.parent / "calibration_rows.json").write_text(
            json.dumps(rows, indent=1), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
