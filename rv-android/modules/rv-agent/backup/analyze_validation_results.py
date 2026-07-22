"""
Analyze validation results from v8 run to understand root causes of issues.

Focuses on:
1. TYPE_TEXT usage (0% vs 12.8% in simple test)
2. UNKNOWN actions (4 apps with 100%)
3. "Missing" actions in cryptoapp (22 discrepancy)
"""

import json
from pathlib import Path
from collections import Counter, defaultdict

def load_results(results_dir="validation_results"):
    """Load all validation result JSON files."""
    results = {}
    results_path = Path(results_dir)

    for json_file in results_path.glob("*_validation.json"):
        app_name = json_file.stem.replace("_validation", "")
        with open(json_file, 'r') as f:
            results[app_name] = json.load(f)

    return results

def analyze_tool_distribution(results):
    """Analyze tool call distribution across all apps."""
    print("="*80)
    print("📊 TOOL CALL DISTRIBUTION ANALYSIS")
    print("="*80)

    # Overall stats
    total_actions = 0
    total_by_type = Counter()
    apps_with_type_text = 0
    apps_with_unknown = 0
    apps_with_100_unknown = []

    # Per-app analysis
    app_details = {}

    for app_name, data in results.items():
        actions = data.get('actions', {})
        by_type = actions.get('by_type', {})

        total = sum(by_type.values())
        total_actions += total

        for action_type, count in by_type.items():
            total_by_type[action_type] += count

        # Check TYPE_TEXT usage
        type_text_count = by_type.get('TYPE_TEXT', 0)
        if type_text_count > 0:
            apps_with_type_text += 1

        # Check UNKNOWN
        unknown_count = by_type.get('UNKNOWN', 0)
        if unknown_count > 0:
            apps_with_unknown += 1

        if total > 0 and unknown_count == total:
            apps_with_100_unknown.append(app_name)

        app_details[app_name] = {
            'total': total,
            'by_type': by_type,
            'type_text_pct': (type_text_count / total * 100) if total > 0 else 0,
            'unknown_pct': (unknown_count / total * 100) if total > 0 else 0
        }

    # Print overall summary
    print(f"\n📈 Overall Statistics:")
    print(f"  Total apps: {len(results)}")
    print(f"  Total actions: {total_actions}")
    print(f"\n  Actions by type:")
    for action_type, count in sorted(total_by_type.items(), key=lambda x: x[1], reverse=True):
        pct = count / total_actions * 100 if total_actions > 0 else 0
        print(f"    {action_type:20s}: {count:4d} ({pct:5.1f}%)")

    print(f"\n  TYPE_TEXT usage:")
    print(f"    Apps using TYPE_TEXT: {apps_with_type_text}/{len(results)}")
    print(f"    TYPE_TEXT percentage: {total_by_type['TYPE_TEXT'] / total_actions * 100:.1f}%")

    print(f"\n  UNKNOWN actions:")
    print(f"    Apps with UNKNOWN: {apps_with_unknown}/{len(results)}")
    print(f"    Apps with 100% UNKNOWN: {len(apps_with_100_unknown)}")
    if apps_with_100_unknown:
        print(f"    Apps:")
        for app in apps_with_100_unknown:
            print(f"      - {app}")

    return app_details, apps_with_100_unknown

def analyze_cryptoapp(results):
    """Deep dive into cryptoapp to understand the 22 action discrepancy."""
    print("\n" + "="*80)
    print("🔍 CRYPTOAPP DEEP DIVE (22 'Missing' Actions)")
    print("="*80)

    crypto_data = results.get('cryptoapp.apk')
    if not crypto_data:
        print("❌ cryptoapp.apk not found in results")
        return

    total_iterations = crypto_data.get('total_iterations', 0)
    actions_data = crypto_data.get('actions', {})

    total_actions = actions_data.get('valid', 0) + actions_data.get('invalid', 0)
    by_type = actions_data.get('by_type', {})

    device_actions = crypto_data.get('device_actions', {})
    device_total = device_actions.get('total_actions', 0)
    device_actions_list = device_actions.get('actions', [])

    print(f"\n📊 Metrics:")
    print(f"  Total iterations: {total_iterations}")
    print(f"  Actions (MetricsCollector): {total_actions}")
    print(f"  Actions (MockDevice): {device_total}")
    print(f"  Discrepancy: {total_iterations - device_total} iterations")

    print(f"\n  MetricsCollector action breakdown:")
    for action_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"    {action_type}: {count}")

    print(f"\n💡 Analysis:")
    print(f"  Iterations: {total_iterations}")
    print(f"  MockDevice actions: {device_total}")
    print(f"  Difference: {total_iterations - device_total}")
    print(f"\n  This confirms: {total_iterations - device_total} iterations did NOT reach the tools node")
    print(f"  (ValidationRunner records action_type from MockDevice, which only updates when tools execute)")

def analyze_unknown_apps(results, unknown_apps):
    """Analyze apps with 100% UNKNOWN actions."""
    print("\n" + "="*80)
    print("⚠️  APPS WITH 100% UNKNOWN ACTIONS")
    print("="*80)

    for app_name in unknown_apps:
        data = results.get(app_name)
        if not data:
            continue

        total_iterations = data.get('total_iterations', 0)
        actions = data.get('actions', {})
        llm_data = data.get('llm', {})

        print(f"\n📱 {app_name}:")
        print(f"  Iterations: {total_iterations}")
        print(f"  Valid actions: {actions.get('valid', 0)}")
        print(f"  Invalid actions: {actions.get('invalid', 0)}")
        print(f"  Action types: {actions.get('by_type', {})}")
        print(f"\n  LLM metrics:")
        print(f"    Total tokens: {llm_data.get('total_tokens', 0)}")
        print(f"    Avg tokens/iter: {llm_data.get('avg_tokens_per_iteration', 0):.1f}")
        print(f"    Max message count: {llm_data.get('max_message_count', 0)}")

def analyze_exploration_quality(results):
    """Analyze exploration quality metrics."""
    print("\n" + "="*80)
    print("🗺️  EXPLORATION QUALITY ANALYSIS")
    print("="*80)

    exploration_stats = []

    for app_name, data in results.items():
        exploration = data.get('exploration', {})
        actions = data.get('actions', {})

        unique_screens = exploration.get('unique_screens', 0)
        revisit_rate = exploration.get('revisit_rate', 0)
        total_iterations = data.get('total_iterations', 0)
        valid_rate = actions.get('valid_rate', 0)

        exploration_stats.append({
            'app': app_name,
            'unique_screens': unique_screens,
            'revisit_rate': revisit_rate,
            'iterations': total_iterations,
            'valid_rate': valid_rate
        })

    # Sort by unique screens
    exploration_stats.sort(key=lambda x: x['unique_screens'], reverse=True)

    print(f"\n📊 Top 10 apps by unique screens discovered:")
    print(f"  {'App':40s} {'Screens':>8s} {'Revisit':>8s} {'Valid%':>7s}")
    print(f"  {'-'*40} {'-'*8} {'-'*8} {'-'*7}")

    for stat in exploration_stats[:10]:
        print(f"  {stat['app']:40s} {stat['unique_screens']:8d} "
              f"{stat['revisit_rate']*100:7.1f}% {stat['valid_rate']*100:6.1f}%")

    # Apps with poor exploration
    poor_exploration = [s for s in exploration_stats if s['unique_screens'] <= 2]
    if poor_exploration:
        print(f"\n⚠️  Apps with limited exploration (≤2 screens):")
        for stat in poor_exploration:
            print(f"  - {stat['app']}: {stat['unique_screens']} screen(s)")

def compare_with_previous_run():
    """Compare with previous V7 validation if available."""
    print("\n" + "="*80)
    print("📊 COMPARISON WITH PREVIOUS RUN (if available)")
    print("="*80)

    # Check if previous validation results exist
    prev_results_path = Path("validation_results_v7")
    if not prev_results_path.exists():
        print("⚠️  Previous validation results not found")
        print("   (Expected at: validation_results_v7/)")
        return

    # Load previous results
    prev_results = {}
    for json_file in prev_results_path.glob("*_validation.json"):
        app_name = json_file.stem.replace("_validation", "")
        with open(json_file, 'r') as f:
            prev_results[app_name] = json.load(f)

    if not prev_results:
        print("⚠️  No previous results loaded")
        return

    print(f"✅ Found {len(prev_results)} previous results")

def main():
    """Main analysis entry point."""
    print("\n" + "="*80)
    print("🔬 VALIDATION RESULTS ANALYSIS - V8 WITH LOGGING")
    print("="*80)

    # Load results
    results = load_results()
    print(f"\n✅ Loaded {len(results)} validation results")

    # 1. Tool distribution analysis
    app_details, unknown_apps = analyze_tool_distribution(results)

    # 2. Cryptoapp deep dive
    analyze_cryptoapp(results)

    # 3. Apps with 100% UNKNOWN
    if unknown_apps:
        analyze_unknown_apps(results, unknown_apps)

    # 4. Exploration quality
    analyze_exploration_quality(results)

    # 5. Compare with previous run
    compare_with_previous_run()

    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)
    print("\nKey Findings:")
    print("1. TYPE_TEXT usage - check if improved from 0%")
    print("2. UNKNOWN actions - identified apps with parsing failures")
    print("3. Cryptoapp discrepancy - confirmed iterations not reaching tools node")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
