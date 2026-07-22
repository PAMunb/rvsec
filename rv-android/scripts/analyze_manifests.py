#!/usr/bin/env python3
"""Analyze AndroidManifest.xml of APKs to find ones with Services, Receivers, and Providers."""

import subprocess
from pathlib import Path

ANDROID_NS = "http://schemas.android.com/apk/res/android"
APKS_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS")


def extract_manifest(apk_path: Path) -> str | None:
    """Extract AndroidManifest.xml from APK using aapt2."""
    try:
        result = subprocess.run(
            [
                "aapt2",
                "dump",
                "xmltree",
                str(apk_path),
                "--file",
                "AndroidManifest.xml",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass

    # Fallback: use aapt
    try:
        result = subprocess.run(
            ["aapt", "dump", "xmltree", str(apk_path), "AndroidManifest.xml"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


def count_components_aapt(apk_path: Path) -> dict:
    """Count components using aapt dump badging (more reliable for counting)."""
    info = {
        "apk": apk_path.name,
        "package": "",
        "activities": 0,
        "services": [],
        "receivers": [],
        "providers": [],
        "has_exported": False,
    }

    try:
        result = subprocess.run(
            ["aapt", "dump", "xmltree", str(apk_path), "AndroidManifest.xml"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return info

        lines = result.stdout.split("\n")
        current_element = None
        current_name = None
        current_exported = None
        current_authorities = None
        indent_level = 0
        component_indent = 0

        for line in lines:
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)

            if stripped.startswith("E: service "):
                current_element = "service"
                component_indent = current_indent
                current_name = None
                current_exported = None
            elif stripped.startswith("E: receiver "):
                current_element = "receiver"
                component_indent = current_indent
                current_name = None
                current_exported = None
            elif stripped.startswith("E: provider "):
                current_element = "provider"
                component_indent = current_indent
                current_name = None
                current_exported = None
                current_authorities = None
            elif stripped.startswith("E: activity "):
                current_element = "activity"
                component_indent = current_indent
                current_name = None
                info["activities"] += 1
            elif (
                stripped.startswith("E: ")
                and current_indent <= component_indent
                and current_element
            ):
                # End of component block — save what we have
                if current_element == "service" and current_name:
                    info["services"].append(
                        {"name": current_name, "exported": current_exported}
                    )
                elif current_element == "receiver" and current_name:
                    info["receivers"].append(
                        {"name": current_name, "exported": current_exported}
                    )
                elif current_element == "provider" and current_name:
                    info["providers"].append(
                        {
                            "name": current_name,
                            "exported": current_exported,
                            "authorities": current_authorities,
                        }
                    )
                current_element = (
                    stripped.split()[1] if len(stripped.split()) > 1 else None
                )
                if current_element in ("service", "receiver", "provider", "activity"):
                    component_indent = current_indent
                    current_name = None
                    current_exported = None
                    current_authorities = None
                    if current_element == "activity":
                        info["activities"] += 1
                else:
                    current_element = None

            # Extract attributes
            if current_element in ("service", "receiver", "provider", "activity"):
                if "A: http://schemas.android.com/apk/res/android:name(" in stripped:
                    # Extract name value
                    parts = stripped.split('"')
                    if len(parts) >= 2:
                        current_name = parts[1]
                elif "A: android:name(" in stripped:
                    parts = stripped.split('"')
                    if len(parts) >= 2:
                        current_name = parts[1]
                elif "exported" in stripped.lower():
                    info["has_exported"] = True
                    if "0xfffffff" in stripped or "=true" in stripped.lower():
                        current_exported = True
                    elif "0x0" in stripped:
                        current_exported = False
                elif "authorities" in stripped.lower():
                    parts = stripped.split('"')
                    if len(parts) >= 2:
                        current_authorities = parts[1]

            # Package name
            if "A: package=" in stripped or (
                "A: " in stripped and "package" in stripped
            ):
                parts = stripped.split('"')
                if len(parts) >= 2 and not info["package"]:
                    info["package"] = parts[1]

        # Save last component
        if current_element == "service" and current_name:
            info["services"].append(
                {"name": current_name, "exported": current_exported}
            )
        elif current_element == "receiver" and current_name:
            info["receivers"].append(
                {"name": current_name, "exported": current_exported}
            )
        elif current_element == "provider" and current_name:
            info["providers"].append(
                {
                    "name": current_name,
                    "exported": current_exported,
                    "authorities": current_authorities,
                }
            )

    except Exception as e:
        info["error"] = str(e)

    return info


def main():
    apks = sorted(APKS_DIR.glob("*.apk"))
    print(f"Scanning {len(apks)} APKs...\n")

    results = []
    for apk in apks:
        info = count_components_aapt(apk)
        if info["services"] or info["receivers"] or info["providers"]:
            results.append(info)

    # Sort by number of non-activity components (most interesting first)
    results.sort(
        key=lambda x: len(x["services"]) + len(x["receivers"]) + len(x["providers"]),
        reverse=True,
    )

    # Summary
    with_services = sum(1 for r in results if r["services"])
    with_receivers = sum(1 for r in results if r["receivers"])
    with_providers = sum(1 for r in results if r["providers"])
    with_all_three = sum(
        1 for r in results if r["services"] and r["receivers"] and r["providers"]
    )

    print("=== SUMMARY ===")
    print(f"APKs with Services:  {with_services}")
    print(f"APKs with Receivers: {with_receivers}")
    print(f"APKs with Providers: {with_providers}")
    print(f"APKs with ALL THREE: {with_all_three}")
    print()

    # Show best candidates (have all 3, or at least 2)
    print("=== BEST CANDIDATES (all 3 component types) ===")
    for r in results:
        if r["services"] and r["receivers"] and r["providers"]:
            print(f"\n{r['apk']} ({r['package']})")
            print(f"  Activities: {r['activities']}")
            print(
                f"  Services ({len(r['services'])}): {[s['name'] for s in r['services']]}"
            )
            print(
                f"  Receivers ({len(r['receivers'])}): {[s['name'] for s in r['receivers']]}"
            )
            print(
                f"  Providers ({len(r['providers'])}): {[s['name'] for s in r['providers']]}"
            )
            if any(p.get("authorities") for p in r["providers"]):
                print(
                    f"  Authorities: {[p.get('authorities') for p in r['providers']]}"
                )

    if not with_all_three:
        print("\nNo APK has all 3. Showing top candidates:")
        for r in results[:10]:
            print(f"\n{r['apk']} ({r['package']})")
            print(f"  Activities: {r['activities']}")
            if r["services"]:
                print(
                    f"  Services ({len(r['services'])}): {[s['name'] for s in r['services'][:5]]}"
                )
            if r["receivers"]:
                print(
                    f"  Receivers ({len(r['receivers'])}): {[s['name'] for s in r['receivers'][:5]]}"
                )
            if r["providers"]:
                print(
                    f"  Providers ({len(r['providers'])}): {[s['name'] for s in r['providers'][:5]]}"
                )


if __name__ == "__main__":
    main()
