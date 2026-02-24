#!/usr/bin/env python3
"""Script to select 60 apps stratified by category with priority for Security."""

import csv
import random
from collections import defaultdict
from pathlib import Path

# Configuration
FDROID_CSV = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/apks/fdroid.csv"
APKS_DIR = "/home/pedro/desenvolvimento/RV_ANDROID/apks"
TARGET_APPS = 60
SEED = 42

# Category quotas (prioritizing Security)
CATEGORY_QUOTAS = {
    "Security": 10,  # Priority
    "System": 7,
    "Internet": 6,
    "Games": 5,
    "Multimedia": 5,
    "Science & Education": 4,
    "Writing": 3,
    "Navigation": 3,
    "Time": 3,
    "Connectivity": 2,
    "Money": 3,
    "Reading": 3,
    "Development": 2,
    "Sports & Health": 2,
    "Theming": 1,
    "Graphics": 1,
}


def find_apk_path(apk_filename: str, apks_dir: str) -> str | None:
    """Find APK file in subdirectories."""
    for subdir in Path(apks_dir).iterdir():
        if subdir.is_dir():
            apk_path = subdir / apk_filename
            if apk_path.exists():
                return str(apk_path)
    # Also check root
    root_path = Path(apks_dir) / apk_filename
    if root_path.exists():
        return str(root_path)
    return None


def parse_categories(cat_str: str) -> list[str]:
    """Parse category string like "['Security', 'Internet']" to list."""
    # Remove brackets and quotes
    cat_str = cat_str.strip("[]'\"")
    if not cat_str:
        return []
    # Split by ', ' and clean each category
    cats = []
    for c in cat_str.split("', '"):
        c = c.strip().strip("'\"")
        if c:
            cats.append(c)
    return cats


def main():
    random.seed(SEED)

    # Read fdroid.csv and organize by category
    apps_by_category = defaultdict(list)
    all_apps = {}

    with open(FDROID_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            apk_file = row.get("file", "")
            if not apk_file:
                continue

            # Check if APK exists
            apk_path = find_apk_path(apk_file, APKS_DIR)
            if not apk_path:
                continue

            categories = parse_categories(row.get("categories", ""))
            package = row.get("package", "")
            name = row.get("name", "")

            app_info = {
                "name": name,
                "package": package,
                "file": apk_file,
                "path": apk_path,
                "categories": categories,
                "mop": row.get("mop", "No") == "Yes",
            }

            all_apps[apk_file] = app_info

            # Add to each category
            for cat in categories:
                apps_by_category[cat].append(app_info)

    print(f"Total apps with APKs available: {len(all_apps)}")
    print(f"\nApps by category:")
    for cat in sorted(
        apps_by_category.keys(), key=lambda x: len(apps_by_category[x]), reverse=True
    ):
        print(f"  {cat}: {len(apps_by_category[cat])}")

    # Select apps stratified by category
    selected = {}

    for category, quota in CATEGORY_QUOTAS.items():
        available = [
            a for a in apps_by_category.get(category, []) if a["file"] not in selected
        ]

        # Prioritize MOP apps (they use crypto)
        mop_apps = [a for a in available if a["mop"]]
        non_mop_apps = [a for a in available if not a["mop"]]

        # Shuffle
        random.shuffle(mop_apps)
        random.shuffle(non_mop_apps)

        # Select MOP first, then non-MOP
        to_select = min(quota, len(available))
        candidates = mop_apps + non_mop_apps

        for app in candidates[:to_select]:
            if app["file"] not in selected:
                selected[app["file"]] = app

    # Fill remaining quota if needed
    remaining = TARGET_APPS - len(selected)
    if remaining > 0:
        unselected = [a for a in all_apps.values() if a["file"] not in selected]
        random.shuffle(unselected)
        for app in unselected[:remaining]:
            selected[app["file"]] = app

    print(f"\n{'='*60}")
    print(f"SELECTED {len(selected)} APPS")
    print(f"{'='*60}\n")

    # Print by category
    selected_by_cat = defaultdict(list)
    for app in selected.values():
        for cat in app["categories"]:
            selected_by_cat[cat].append(app)

    print("Selected by category:")
    for cat in sorted(selected_by_cat.keys()):
        apps = selected_by_cat[cat]
        print(f"\n{cat} ({len(apps)}):")
        for app in apps:
            mop_marker = " [MOP]" if app["mop"] else ""
            print(f"  - {app['name']}: {app['package']}{mop_marker}")

    # Output list of APK paths
    print(f"\n{'='*60}")
    print("APK PATHS FOR VALIDATION:")
    print(f"{'='*60}\n")

    for app in sorted(selected.values(), key=lambda x: x["path"]):
        print(app["path"])

    # Save to file
    output_file = Path(__file__).parent / "selected_apps_60.txt"
    with open(output_file, "w") as f:
        f.write(f"# Selected 60 apps for overnight validation\n")
        f.write(f"# Generated with seed={SEED}\n")
        f.write(f"# Categories stratified with Security priority\n\n")

        for app in sorted(
            selected.values(),
            key=lambda x: x["categories"][0] if x["categories"] else "ZZZ",
        ):
            cats = ", ".join(app["categories"])
            mop = " [MOP]" if app["mop"] else ""
            f.write(f"{app['path']}\t{app['package']}\t{cats}{mop}\n")

    print(f"\nSaved to: {output_file}")

    # Summary
    mop_count = sum(1 for a in selected.values() if a["mop"])
    print(f"\nSummary:")
    print(f"  Total apps: {len(selected)}")
    print(f"  MOP apps (use crypto): {mop_count}")
    print(f"  Non-MOP apps: {len(selected) - mop_count}")


if __name__ == "__main__":
    main()
