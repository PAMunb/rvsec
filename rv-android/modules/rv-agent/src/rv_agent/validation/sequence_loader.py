"""
Sequence loader for offline validation.

Loads pre-captured app sequences from dataset directory with screenshots,
UI dumps, and static analysis files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScreenData:
    """Data for a single screen in the sequence."""

    step: int
    screenshot_path: Path
    uiautomator_path: Path
    state_path: Path
    activity: str
    package: str
    screen_size: tuple[int, int]

    def __str__(self) -> str:
        return f"Screen(step={self.step}, activity={self.activity})"


@dataclass
class AppSequence:
    """Complete sequence of screens for an app."""

    app_name: str
    app_dir: Path
    package_name: str
    screens: List[ScreenData]
    apk_path: Optional[Path] = None
    reach_path: Optional[Path] = None
    gesda_path: Optional[Path] = None
    wtg_path: Optional[Path] = None
    methods_path: Optional[Path] = None

    def __len__(self) -> int:
        return len(self.screens)

    def __str__(self) -> str:
        return f"AppSequence({self.app_name}, {len(self.screens)} screens, package={self.package_name})"


class SequenceLoader:
    """
    Loads app sequences from dataset directory.

    Dataset structure:
    ```
    dataset/
    ├── app1.apk/
    │   ├── 001.png
    │   ├── 001.uiautomator
    │   ├── 001.state
    │   ├── 002.png
    │   ├── 002.uiautomator
    │   ├── 002.state
    │   ├── ...
    │   ├── app1.apk
    │   ├── app1.apk.reach
    │   ├── app1.apk.gesda
    │   ├── app1.apk.wtg
    │   └── app1.apk.methods
    └── app2.apk/
        └── ...
    ```
    """

    def __init__(self, dataset_dir: Path):
        """
        Initialize sequence loader.

        Args:
            dataset_dir: Root directory containing app sequences
        """
        self.dataset_dir = Path(dataset_dir)

        if not self.dataset_dir.exists():
            raise ValueError(f"Dataset directory not found: {dataset_dir}")

        logger.info(f"SequenceLoader initialized: {self.dataset_dir}")

    def list_apps(self) -> List[str]:
        """
        List all available app names in dataset.

        Returns:
            List of app directory names
        """
        apps = [d.name for d in self.dataset_dir.iterdir() if d.is_dir()]
        logger.info(f"Found {len(apps)} apps in dataset")
        return sorted(apps)

    def load_app_sequence(self, app_name: str) -> AppSequence:
        """
        Load complete sequence for an app.

        Args:
            app_name: App directory name (e.g., "cryptoapp.apk")

        Returns:
            AppSequence with all screen data

        Raises:
            ValueError: If app not found or invalid structure
        """
        app_dir = self.dataset_dir / app_name

        if not app_dir.exists():
            raise ValueError(f"App directory not found: {app_dir}")

        logger.info(f"Loading sequence for: {app_name}")

        # Find all screen files (001.png, 002.png, ...)
        screen_files = sorted(app_dir.glob("*.png"))

        if not screen_files:
            raise ValueError(f"No screenshots found in {app_dir}")

        screens = []
        package_name = None

        for screenshot_path in screen_files:
            # Extract step number from filename (e.g., "001.png" -> 1)
            step_str = screenshot_path.stem  # "001"
            try:
                step = int(step_str)
            except ValueError:
                logger.warning(f"Skipping non-sequential file: {screenshot_path.name}")
                continue

            # Corresponding files
            uiautomator_path = app_dir / f"{step_str}.uiautomator"
            state_path = app_dir / f"{step_str}.state"

            if not uiautomator_path.exists():
                logger.warning(f"Missing UIAutomator dump for step {step}: {uiautomator_path}")
                continue

            if not state_path.exists():
                logger.warning(f"Missing state file for step {step}: {state_path}")
                continue

            # Parse state file to get activity and package
            try:
                with open(state_path, 'r') as f:
                    state_data = json.load(f)

                activity = state_data.get('activity', 'unknown')
                pkg = state_data.get('view_tree', {}).get('package', 'unknown')
                screen_size_dict = state_data.get('screen_size', {})
                screen_size = (
                    screen_size_dict.get('width', 1080),
                    screen_size_dict.get('height', 1920)
                )

                if package_name is None:
                    package_name = pkg

                screen_data = ScreenData(
                    step=step,
                    screenshot_path=screenshot_path,
                    uiautomator_path=uiautomator_path,
                    state_path=state_path,
                    activity=activity,
                    package=pkg,
                    screen_size=screen_size
                )

                screens.append(screen_data)

            except Exception as e:
                logger.error(f"Failed to parse state file {state_path}: {e}")
                continue

        if not screens:
            raise ValueError(f"No valid screens loaded for {app_name}")

        # Load static analysis files
        apk_files = list(app_dir.glob("*.apk"))
        apk_path = apk_files[0] if apk_files else None

        # Find static analysis files (they use the apk filename as prefix)
        reach_files = list(app_dir.glob("*.reach"))
        gesda_files = list(app_dir.glob("*.gesda"))
        wtg_files = list(app_dir.glob("*.wtg"))
        methods_files = list(app_dir.glob("*.methods"))

        sequence = AppSequence(
            app_name=app_name,
            app_dir=app_dir,
            package_name=package_name or "unknown",
            screens=screens,
            apk_path=apk_path,
            reach_path=reach_files[0] if reach_files else None,
            gesda_path=gesda_files[0] if gesda_files else None,
            wtg_path=wtg_files[0] if wtg_files else None,
            methods_path=methods_files[0] if methods_files else None
        )

        logger.info(f"Loaded {sequence}")
        logger.info(f"  Package: {sequence.package_name}")
        logger.info(f"  Screens: {len(sequence.screens)}")
        logger.info(f"  Static analysis: reach={sequence.reach_path is not None}, "
                   f"gesda={sequence.gesda_path is not None}, wtg={sequence.wtg_path is not None}")

        return sequence

    def load_all_sequences(self) -> Dict[str, AppSequence]:
        """
        Load all app sequences in dataset.

        Returns:
            Dictionary mapping app names to AppSequence objects
        """
        apps = self.list_apps()
        sequences = {}

        for app_name in apps:
            try:
                sequence = self.load_app_sequence(app_name)
                sequences[app_name] = sequence
            except Exception as e:
                logger.error(f"Failed to load {app_name}: {e}")

        logger.info(f"Loaded {len(sequences)}/{len(apps)} app sequences")
        return sequences
