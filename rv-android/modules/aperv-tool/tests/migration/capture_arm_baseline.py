"""Capture what each arm actually configures, before any arm is re-expressed.

Run once, against the unmodified `tool.py`. The output is the only record of what the 29
pre-change arms meant, and every later group's regeneration diff is measured against it.

**The capture must precede the first edit.** If an arm were re-expressed first, the baseline
would record the new behaviour and the diff would compare the code against itself — a
tautology that passes no matter what the migration broke.

What is captured is the *effective configuration*, not the properties text. A property file
is exactly the thing this change reshapes: the pre-change file lists 18–33 expanded keys, the
post-change one lists a preset and its deltas, and comparing them textually would report
every arm as changed while telling us nothing. The effective configuration is what both
shapes resolve to — every key the arm sets, overlaid on the jar's declared defaults for the
keys it leaves alone — and that is the thing the migration must preserve.

Values are typed through each key's declared `ValueType` for the same reason: the `aperv`
preset writes `ape.llmPercentageNoSubstrate=-1` where the jar's default is `-1.0`, so a text
comparison would flag every arm on formatting and bury the real signal.

Usage:
    APE_REPO=<stage-2 ape checkout> python -m tests.migration.capture_arm_baseline
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from aperv_tool.tools.aperv.tool import APERV_PROPERTY_MAPPING, ApeRVTool

from .jar_tables import KeySpec, load_key_specs, resolve_ape_repo, source_provenance

# Where the derived MOP artifact lands on the device. Written as ape.mopDataPath by
# _push_properties() whenever the arm's mop_data triggered the push, so it is part of the
# effective plan even though it has no APERV_PROPERTY_MAPPING entry.
DEVICE_ARTIFACT_PATH = "/data/local/tmp/mop-artifact.json"

BASELINE_FILE = Path(__file__).parent / "arm_effective_baseline.json"


def typed(value: Any, spec: KeySpec | None) -> Any:
    """Parse a property value through the key's declared jar type.

    An unknown key (no spec) keeps its text: the sweep reports it as dead rather than
    guessing what it would have meant.
    """
    text = _as_property_text(value)
    if spec is None:
        return text
    if spec.value_type == "BOOLEAN":
        return text == "true"
    if spec.value_type in ("INT", "LONG"):
        return int(float(text))
    if spec.value_type == "DOUBLE":
        return float(text)
    return text


def _as_property_text(value: Any) -> str:
    """The exact text `_push_properties()` would write for this value.

    Going through the text is deliberate rather than a detour: it is what makes the Python
    bool `True` and the string `"true"` — both of which the pre-change arms use for the same
    jar key — compare equal, because both reach the device as `true`.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def effective_config(
    arm: Dict[str, Any], key_specs: Dict[str, KeySpec], mop_pushed: bool
) -> Dict[str, Any]:
    """The typed plan an arm resolves to: what it sets, over the jar's defaults.

    Restricted to the keys reachable through `APERV_PROPERTY_MAPPING` plus `ape.mopDataPath`,
    which is exactly the surface the Python side can influence. A key whose jar default is
    `null` and which the arm does not set is omitted: it has no value in the plan, and
    recording one would invent a fact.
    """
    config: Dict[str, Any] = {}

    for python_key, java_key in APERV_PROPERTY_MAPPING.items():
        spec = key_specs.get(java_key)
        if python_key in arm:
            config[java_key] = typed(arm[python_key], spec)
        elif spec is not None and spec.default is not None:
            config[java_key] = typed(spec.default, spec)

    if mop_pushed:
        config["ape.mopDataPath"] = DEVICE_ARTIFACT_PATH
    return config


def capture(key_specs: Dict[str, KeySpec]) -> Dict[str, Any]:
    """Every arm `get_variants()` currently offers, as name -> effective configuration."""
    arms: Dict[str, Any] = {}
    for name, arm in ApeRVTool.get_variants().items():
        arms[name] = {
            "strategy": arm.get("strategy"),
            "mop_data": arm.get("mop_data"),
            "config": effective_config(
                arm, key_specs, mop_pushed=arm.get("mop_data") == "static_analysis"
            ),
        }
    return arms


def main() -> None:
    ape_repo = resolve_ape_repo()
    key_specs = load_key_specs(ape_repo)
    document = {
        "provenance": source_provenance(ape_repo),
        "arms": capture(key_specs),
    }
    BASELINE_FILE.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(f"captured {len(document['arms'])} arms -> {BASELINE_FILE}")


if __name__ == "__main__":
    main()
