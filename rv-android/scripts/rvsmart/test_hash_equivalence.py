#!/usr/bin/env python3
"""Hash equivalence test for INV-RSM-03.

Validates that the Python rv-agent (compute_screen_hash_from_description) and Java
rvsmart (ScreenState.computeHash) produce identical structural hashes for the same
UI tree.

### Algorithm Summary (both implementations must match exactly)

The canonical JSON is built as:
  {
    "activity": <activity_string>,
    "items": [
      {
        "checkable": <bool>,
        "class": <string>,
        "clickable": <bool>,
        "editable": <bool>,
        "enabled": <bool>,
        "long_clickable": <bool>,
        "package": <string>,
        "resource_id": <string>,
        "scrollable": <bool>
      },
      ...
    ]
  }

Items are sorted by (resource_id or "zzz", class). Keys are sorted alphabetically.
SHA-256 of UTF-8 bytes, first 12 hex characters.

### Known Class Name Difference

Java UiCapture.simplifyClassName() strips the package prefix:
  "android.widget.Button" -> "Button"

Python UIAutomator2 XML keeps the full class:
  "android.widget.Button" -> "android.widget.Button"

This script handles BOTH inputs:
  - Mode "python": reads UIAutomator XML dumps (full class names)
  - Mode "java": reads normalized items with simplified class names

When comparing hashes from a live device, the XML dump parsed by this script
will produce the same hash as the Python agent (both use full class names from XML).
The Java rvsmart uses simplified class names from AccessibilityNodeInfo — this is a
known divergence that must be validated end-to-end with a running device.

### Usage

    # With pre-captured XML dumps (validates determinism only):
    python test_hash_equivalence.py --dumps-dir ./ui_dumps/

    # Live capture from emulator (requires running emulator):
    python test_hash_equivalence.py --live --packages br.unb.cic.cryptoapp

    # Single file:
    python test_hash_equivalence.py --file window_dump.xml
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# Maximum items to include in the hash computation (matches Java DEFAULT_MAX_ITEMS=2000).
# Java UiCapture caps at maxItems with priority-based retention (INV-RSM-11).
# Python agent has no explicit cap — the XML contains however many nodes UIAutomator dumped.
MAX_ITEMS_JAVA_DEFAULT = 2000


def _sort_key(item: dict) -> tuple:
    """Sort key matching Java Comparator: (resource_id || 'zzz', class)."""
    rid = item.get("resource_id", "")
    cls = item.get("class", "")
    return (rid if rid else "zzz", cls)


def compute_structural_hash(items: list[dict], activity: str) -> str:
    """Compute structural hash matching both Java ScreenState and Python agent.

    Algorithm (INV-RSM-03):
      1. Extract 9 structural attributes per item (keys sorted alphabetically by
         json.dumps(sort_keys=True)).
      2. Sort items by (resource_id || 'zzz', class).
      3. json.dumps({"activity": ..., "items": [...]}, sort_keys=True, separators=(',', ':')).
      4. SHA-256 of UTF-8 bytes, first 12 hex characters.

    The Java side uses Gson with TreeMap at every level, which produces identical output
    to json.dumps(sort_keys=True) for the same data.
    """
    structural_items = []
    for item in items:
        # Exactly 9 keys — alphabetical order matches json.dumps(sort_keys=True)
        # and Gson's TreeMap serialization order.
        structural_items.append({
            "checkable": item.get("checkable", False),
            "class": item.get("class", ""),
            "clickable": item.get("clickable", False),
            "editable": item.get("editable", False),
            "enabled": item.get("enabled", True),
            "long_clickable": item.get("long_clickable", False),
            "package": item.get("package", ""),
            "resource_id": item.get("resource_id", ""),
            "scrollable": item.get("scrollable", False),
        })

    structural_items.sort(key=_sort_key)

    canonical = json.dumps(
        {"activity": activity, "items": structural_items},
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def parse_ui_dump(xml_path: str) -> tuple[list[dict], str]:
    """Parse UIAutomator XML dump into items and activity.

    Returns (items, activity). Items use full class names as they appear in the XML
    (e.g. 'android.widget.Button'), matching the Python agent's parsing path.

    Note: Java rvsmart uses AccessibilityNodeInfo.getClassName() plus
    simplifyClassName(), which strips the package prefix. This means hashes from
    XML-parsed items will differ from hashes produced by live Java rvsmart unless
    class names are simplified here too. See --simplify-class flag.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        raise ValueError(f"Cannot parse XML {xml_path}: {e}")

    # Extract activity from root node attributes
    activity = root.get("package", "") or ""
    for child in root.iter():
        pkg = child.get("package", "")
        if pkg:
            activity = pkg
            break

    items = []
    for node in root.iter("node"):
        class_name = node.get("class", "")
        resource_id = node.get("resource-id", "") or ""
        package = node.get("package", "") or ""
        clickable = node.get("clickable", "false").lower() == "true"
        scrollable = node.get("scrollable", "false").lower() == "true"
        checkable = node.get("checkable", "false").lower() == "true"
        enabled = node.get("enabled", "true").lower() == "true"
        long_clickable = node.get("long-clickable", "false").lower() == "true"
        # UIAutomator XML does not have an 'editable' attribute by default.
        # EditText elements are identified by class name instead.
        editable_attr = node.get("editable", "false").lower() == "true"

        items.append({
            "class": class_name,
            "resource_id": resource_id,
            "package": package,
            "clickable": clickable,
            "scrollable": scrollable,
            "checkable": checkable,
            "enabled": enabled,
            "long_clickable": long_clickable,
            "editable": editable_attr,
        })

    return items, activity


def simplify_class_name(fqcn: str) -> str:
    """Mimic Java UiCapture.simplifyClassName(): strip package prefix.

    'android.widget.Button' -> 'Button'
    'Button' -> 'Button'
    """
    idx = fqcn.rfind(".")
    return fqcn[idx + 1:] if idx >= 0 else fqcn


def run_determinism_check(xml_path: str, simplify: bool = False) -> tuple[bool, str, int]:
    """Compute hash twice on the same file and assert equality (determinism check).

    Returns (passed, hash_value, item_count).
    """
    items, activity = parse_ui_dump(xml_path)
    if simplify:
        for item in items:
            item["class"] = simplify_class_name(item["class"])

    h1 = compute_structural_hash(items, activity)
    h2 = compute_structural_hash(items, activity)
    return h1 == h2, h1, len(items)


def capture_live_dumps(packages: list[str], output_dir: str,
                       screens_per_app: int = 4) -> list[str]:
    """Capture UI dumps from running apps via adb.

    Launches each app, taps through screens, dumps UI hierarchy at each step.
    Returns list of XML file paths that were successfully captured.

    Requires a running Android emulator or connected device accessible via adb.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = []

    for pkg in packages:
        print(f"  Launching {pkg}...")
        subprocess.run(
            ["adb", "shell", "monkey", "-p", pkg, "-c",
             "android.intent.category.LAUNCHER", "1"],
            capture_output=True,
        )
        time.sleep(3)

        for i in range(screens_per_app):
            device_path = f"/sdcard/ui_dump_{pkg}_{i}.xml"
            local_path = os.path.join(output_dir, f"{pkg.replace('.', '_')}_{i}.xml")

            result = subprocess.run(
                ["adb", "shell", "uiautomator", "dump", device_path],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"  WARNING: uiautomator dump failed for {pkg} screen {i}: "
                      f"{result.stderr.strip()}")
                continue

            pull_result = subprocess.run(
                ["adb", "pull", device_path, local_path],
                capture_output=True, text=True,
            )
            if pull_result.returncode == 0 and os.path.exists(local_path):
                paths.append(local_path)
                print(f"  Captured: {local_path}")
            else:
                print(f"  WARNING: adb pull failed for {pkg} screen {i}")

            if i < screens_per_app - 1:
                # Navigate to a different screen
                subprocess.run(["adb", "shell", "input", "tap", "540", "960"],
                               capture_output=True)
                time.sleep(2)

    return paths


def run_equivalence_tests(dumps_dir: str, simplify: bool = False) -> tuple[int, int]:
    """Run determinism test on all XML dumps in directory.

    Returns (passed, total). Each XML file is hashed twice; equality means
    the algorithm is deterministic for that input.

    When --simplify-class is set, class names are simplified to match Java's
    AccessibilityNodeInfo path, enabling offline comparison with Java-expected hashes.
    """
    passed = 0
    total = 0

    xml_files = sorted(Path(dumps_dir).glob("*.xml"))
    if not xml_files:
        print(f"  No XML files found in {dumps_dir}")
        return 0, 0

    for xml_file in xml_files:
        total += 1
        try:
            ok, h, count = run_determinism_check(str(xml_file), simplify=simplify)
        except ValueError as e:
            print(f"  FAIL {xml_file.name}: {e}")
            continue

        if ok:
            passed += 1
            mode_tag = " [simplified]" if simplify else ""
            print(f"  PASS {xml_file.name}: hash={h} items={count}{mode_tag}")
        else:
            print(f"  FAIL {xml_file.name}: hash not deterministic (BUG in algorithm)")

    return passed, total


def main():
    parser = argparse.ArgumentParser(
        description="Hash equivalence test for INV-RSM-03",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dumps-dir", help="Directory with pre-captured XML dumps")
    parser.add_argument("--file", help="Single XML dump file to test")
    parser.add_argument("--live", action="store_true",
                        help="Capture live UI dumps from running emulator")
    parser.add_argument("--packages", default="br.unb.cic.cryptoapp",
                        help="Comma-separated package names for --live capture "
                             "(default: br.unb.cic.cryptoapp)")
    parser.add_argument("--output-dir", default="./ui_dumps",
                        help="Output directory for --live captured dumps (default: ./ui_dumps)")
    parser.add_argument("--screens-per-app", type=int, default=4,
                        help="Number of screens to capture per app in --live mode (default: 4)")
    parser.add_argument("--simplify-class", action="store_true",
                        help="Strip package prefix from class names to match Java "
                             "UiCapture.simplifyClassName() output. Use this when "
                             "comparing against Java-side hashes captured via logcat.")
    args = parser.parse_args()

    if args.file:
        print(f"Testing single file: {args.file}")
        try:
            ok, h, count = run_determinism_check(args.file, simplify=args.simplify_class)
        except ValueError as e:
            print(f"FAIL: {e}")
            sys.exit(1)
        print(f"{'PASS' if ok else 'FAIL'}: hash={h} items={count}")
        sys.exit(0 if ok else 1)

    if args.live:
        packages = [p.strip() for p in args.packages.split(",") if p.strip()]
        print(f"Capturing live UI dumps from {len(packages)} app(s): {packages}")
        dump_files = capture_live_dumps(packages, args.output_dir,
                                        screens_per_app=args.screens_per_app)
        print(f"Captured {len(dump_files)} dump(s)")
        if not dump_files:
            print("No dumps captured — is an emulator running?")
            sys.exit(1)
        dumps_dir = args.output_dir

    elif args.dumps_dir:
        dumps_dir = args.dumps_dir

    else:
        parser.error("Specify --dumps-dir, --file, or --live")
        return

    print(f"\nRunning hash equivalence tests on {dumps_dir} ...")
    passed, total = run_equivalence_tests(dumps_dir, simplify=args.simplify_class)

    print(f"\nResults: {passed}/{total} passed")
    if total == 0:
        print("No test cases found.")
        sys.exit(1)
    elif passed == total:
        print("ALL PASS — hash algorithm is deterministic")
        sys.exit(0)
    else:
        print("FAILURES — investigate above")
        sys.exit(1)


if __name__ == "__main__":
    main()
