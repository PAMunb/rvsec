#!/usr/bin/env python3
"""
Component Score Calibration Script.

Analyzes UI dumps from the screenshot dataset to:
1. Count distribution of component types across apps
2. Identify components that are frequently interactive
3. Generate calibrated scores for the ranking system

Usage:
    python calibrate_scores.py --dataset /path/to/screenshots
    python calibrate_scores.py --dataset /path/to/screenshots --output scores_config.json
"""

import argparse
import json
import logging
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ComponentStats:
    """Statistics for a component type."""
    total_count: int = 0
    clickable_count: int = 0
    apps_with_component: Set[str] = field(default_factory=set)
    screens_with_component: int = 0

    @property
    def clickable_ratio(self) -> float:
        return self.clickable_count / self.total_count if self.total_count > 0 else 0.0

    @property
    def app_coverage(self) -> float:
        return len(self.apps_with_component)


def parse_ui_dump(xml_path: Path) -> List[Dict]:
    """Parse UIAutomator XML dump and extract component info."""
    elements = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for node in root.iter('node'):
            class_name = node.get('class', '')
            clickable = node.get('clickable', 'false') == 'true'
            long_clickable = node.get('long-clickable', 'false') == 'true'
            checkable = node.get('checkable', 'false') == 'true'
            scrollable = node.get('scrollable', 'false') == 'true'
            focusable = node.get('focusable', 'false') == 'true'
            enabled = node.get('enabled', 'false') == 'true'

            # Extract simple class name
            simple_class = class_name.split('.')[-1] if class_name else 'unknown'

            elements.append({
                'class': class_name,
                'simple_class': simple_class,
                'clickable': clickable,
                'long_clickable': long_clickable,
                'checkable': checkable,
                'scrollable': scrollable,
                'focusable': focusable,
                'enabled': enabled,
                'interactive': clickable or long_clickable or checkable or scrollable,
            })
    except Exception as e:
        logger.warning(f"Failed to parse {xml_path}: {e}")

    return elements


def analyze_dataset(dataset_path: Path) -> Dict[str, ComponentStats]:
    """Analyze all UI dumps in the dataset."""
    stats: Dict[str, ComponentStats] = defaultdict(ComponentStats)

    total_screens = 0
    total_apps = 0

    # Iterate through all app directories
    for app_dir in sorted(dataset_path.iterdir()):
        if not app_dir.is_dir():
            continue

        app_name = app_dir.name
        total_apps += 1

        # Find all UI dump files
        xml_files = sorted(app_dir.glob('*.uiautomator.xml'))

        for xml_file in xml_files:
            total_screens += 1
            elements = parse_ui_dump(xml_file)

            # Track which components appear in this screen
            screen_components: Set[str] = set()

            for elem in elements:
                simple_class = elem['simple_class']

                stats[simple_class].total_count += 1
                stats[simple_class].apps_with_component.add(app_name)

                if elem['interactive']:
                    stats[simple_class].clickable_count += 1

                screen_components.add(simple_class)

            # Update screen counts
            for comp in screen_components:
                stats[comp].screens_with_component += 1

    logger.info(f"\nDataset Analysis:")
    logger.info(f"  Apps: {total_apps}")
    logger.info(f"  Screens: {total_screens}")
    logger.info(f"  Component types: {len(stats)}")

    return dict(stats)


def calculate_priority_scores(stats: Dict[str, ComponentStats]) -> Dict[str, float]:
    """
    Calculate priority scores based on component analysis.

    Heuristics:
    1. Components that reveal options (Spinner, Menu) get high scores
    2. Components that are frequently interactive get moderate scores
    3. Components that appear in many apps are more important
    4. Layout containers get low/no scores
    """
    scores = {}

    # Categorize components by their typical role
    DROPDOWN_TYPES = {'Spinner', 'AppCompatSpinner', 'MaterialSpinner', 'AutoCompleteTextView'}
    MENU_TYPES = {'PopupMenu', 'MenuView', 'ActionMenuView', 'NavigationMenuView', 'DrawerLayout'}
    BUTTON_TYPES = {'Button', 'AppCompatButton', 'MaterialButton', 'ImageButton', 'FloatingActionButton', 'FAB'}
    INPUT_TYPES = {'EditText', 'AppCompatEditText', 'TextInputEditText', 'SearchView'}
    TOGGLE_TYPES = {'Switch', 'SwitchCompat', 'CheckBox', 'AppCompatCheckBox', 'RadioButton', 'ToggleButton'}
    LIST_TYPES = {'RecyclerView', 'ListView', 'GridView', 'ViewPager', 'ViewPager2'}
    TAB_TYPES = {'TabLayout', 'TabHost', 'BottomNavigationView', 'NavigationView'}
    CONTAINER_TYPES = {'LinearLayout', 'RelativeLayout', 'FrameLayout', 'ConstraintLayout', 'CoordinatorLayout', 'CardView', 'ScrollView', 'NestedScrollView'}

    for comp, stat in stats.items():
        # Base score based on interactivity ratio
        base_score = stat.clickable_ratio * 20

        # Bonus for appearing across many apps (universal components)
        app_bonus = min(stat.app_coverage * 2, 10)

        # Category-specific bonuses
        category_bonus = 0

        if comp in DROPDOWN_TYPES:
            category_bonus = 50  # Dropdowns reveal hidden options
        elif comp in MENU_TYPES:
            category_bonus = 40  # Menus provide navigation
        elif comp in TAB_TYPES:
            category_bonus = 35  # Tabs lead to different sections
        elif comp in BUTTON_TYPES:
            category_bonus = 25  # Buttons are primary actions
        elif comp in INPUT_TYPES:
            category_bonus = 20  # Inputs are important for forms
        elif comp in TOGGLE_TYPES:
            category_bonus = 15  # Toggles change state
        elif comp in LIST_TYPES:
            category_bonus = 10  # Lists contain content
        elif comp in CONTAINER_TYPES:
            category_bonus = 0   # Containers are not interactive themselves

        # Calculate final score
        final_score = base_score + app_bonus + category_bonus

        # Only include if score > 0
        if final_score > 0:
            scores[comp] = round(final_score, 1)

    return scores


def generate_config(scores: Dict[str, float], output_path: Path) -> None:
    """Generate a JSON config file with calibrated scores."""
    # Sort by score descending
    sorted_scores = dict(sorted(scores.items(), key=lambda x: -x[1]))

    config = {
        "description": "Auto-calibrated component priority scores",
        "generated_from": "UI dump analysis of screenshot dataset",
        "usage": "Higher scores = higher priority in action selection",
        "score_ranges": {
            "high_priority": "50+ (dropdowns, menus, tabs)",
            "medium_priority": "25-50 (buttons, inputs)",
            "low_priority": "10-25 (toggles, lists)",
            "no_priority": "0 (containers, layouts)"
        },
        "component_scores": sorted_scores,
    }

    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    logger.info(f"\nConfig saved to: {output_path}")


def print_analysis(stats: Dict[str, ComponentStats], scores: Dict[str, float]) -> None:
    """Print detailed analysis results."""
    logger.info("\n" + "=" * 80)
    logger.info("COMPONENT ANALYSIS RESULTS")
    logger.info("=" * 80)

    # Sort by total count
    sorted_stats = sorted(stats.items(), key=lambda x: -x[1].total_count)

    logger.info(f"\n{'Component':<35} {'Count':>8} {'Click%':>8} {'Apps':>6} {'Score':>8}")
    logger.info("-" * 80)

    for comp, stat in sorted_stats[:40]:  # Top 40
        score = scores.get(comp, 0)
        logger.info(f"{comp:<35} {stat.total_count:>8} {stat.clickable_ratio:>7.1%} {stat.app_coverage:>6} {score:>8.1f}")

    # Summary by category
    logger.info("\n" + "=" * 80)
    logger.info("RECOMMENDED SCORER CATEGORIES")
    logger.info("=" * 80)

    high_priority = [(c, s) for c, s in scores.items() if s >= 50]
    medium_priority = [(c, s) for c, s in scores.items() if 25 <= s < 50]
    low_priority = [(c, s) for c, s in scores.items() if 10 <= s < 25]

    logger.info(f"\nHigh Priority (score >= 50):")
    for comp, score in sorted(high_priority, key=lambda x: -x[1]):
        logger.info(f"  {comp}: {score}")

    logger.info(f"\nMedium Priority (25 <= score < 50):")
    for comp, score in sorted(medium_priority, key=lambda x: -x[1]):
        logger.info(f"  {comp}: {score}")

    logger.info(f"\nLow Priority (10 <= score < 25):")
    for comp, score in sorted(low_priority, key=lambda x: -x[1])[:15]:
        logger.info(f"  {comp}: {score}")


def generate_scorer_code(scores: Dict[str, float]) -> str:
    """Generate Python code for the ComponentPriorityScorer."""
    high_priority = {c: s for c, s in scores.items() if s >= 50}
    medium_priority = {c: s for c, s in scores.items() if 25 <= s < 50}

    code = '''
class ComponentPriorityScorer(Scorer):
    """
    Scores actions based on component type priority.

    Auto-calibrated from UI dump analysis.
    """

    # High priority components (reveal options, provide navigation)
    HIGH_PRIORITY = {
'''
    for comp, score in sorted(high_priority.items(), key=lambda x: -x[1]):
        code += f'        "{comp}": {score},\n'

    code += '''    }

    # Medium priority components (primary actions, inputs)
    MEDIUM_PRIORITY = {
'''
    for comp, score in sorted(medium_priority.items(), key=lambda x: -x[1]):
        code += f'        "{comp}": {score},\n'

    code += '''    }

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        target_class = action.target_view.get('class', '') if action.target_view else ''
        simple_class = target_class.split('.')[-1] if target_class else ''

        # Check high priority first
        if simple_class in self.HIGH_PRIORITY:
            return self.HIGH_PRIORITY[simple_class]
        if target_class in self.HIGH_PRIORITY:
            return self.HIGH_PRIORITY[target_class]

        # Then medium priority
        if simple_class in self.MEDIUM_PRIORITY:
            return self.MEDIUM_PRIORITY[simple_class]
        if target_class in self.MEDIUM_PRIORITY:
            return self.MEDIUM_PRIORITY[target_class]

        return 0.0
'''
    return code


def main():
    parser = argparse.ArgumentParser(description='Calibrate component priority scores')
    parser.add_argument('--dataset', type=str, required=True,
                        help='Path to screenshot dataset directory')
    parser.add_argument('--output', type=str, default='scores_config.json',
                        help='Output config file path')
    parser.add_argument('--generate-code', action='store_true',
                        help='Generate Python scorer code')

    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error(f"Dataset path not found: {dataset_path}")
        return

    # Analyze dataset
    stats = analyze_dataset(dataset_path)

    # Calculate priority scores
    scores = calculate_priority_scores(stats)

    # Print analysis
    print_analysis(stats, scores)

    # Generate config
    output_path = Path(args.output)
    generate_config(scores, output_path)

    # Optionally generate code
    if args.generate_code:
        code = generate_scorer_code(scores)
        code_path = output_path.with_suffix('.py')
        with open(code_path, 'w') as f:
            f.write(code)
        logger.info(f"Scorer code saved to: {code_path}")


if __name__ == '__main__':
    main()
