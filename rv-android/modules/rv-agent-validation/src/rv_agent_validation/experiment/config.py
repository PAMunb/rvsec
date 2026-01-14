"""
Experiment configuration for strategy validation.

Supports:
- Multiple strategies: rvagent, dfs, bfs, greedy
- Static analysis integration for MOP prioritization
- Configurable repetitions and timeouts
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


# =============================================================================
# Apps with Complete Static Analysis Data
# =============================================================================

# Default location for static analysis files (.reach, .wtg, .gesda)
DEFAULT_STATIC_ANALYSIS_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

# Apps with complete static analysis (14 total)
APPS_WITH_STATIC_ANALYSIS: List[Dict[str, Any]] = [
    {
        "name": "cryptoapp.apk",
        "package": "br.unb.cic.cryptoapp",
        "dir": "cryptoapp.apk",
        "category": "Security",
    },
    {
        "name": "byrne.utilities.hashpass_2.apk",
        "package": "byrne.utilities.hashpass",
        "dir": "byrne.utilities.hashpass_2.apk",
        "category": "Security",
    },
    {
        "name": "com.sam.hex_16.apk",
        "package": "com.sam.hex",
        "dir": "com.sam.hex_16.apk",
        "category": "Games",
    },
    {
        "name": "org.secuso.privacyfriendlyludo_5.apk",
        "package": "org.secuso.privacyfriendlyludo",
        "dir": "org.secuso.privacyfriendlyludo_5.apk",
        "category": "Games",
    },
    {
        "name": "org.secuso.privacyfriendlydicer_8.apk",
        "package": "org.secuso.privacyfriendlydicer",
        "dir": "org.secuso.privacyfriendlydicer_8.apk",
        "category": "Games",
    },
    {
        "name": "ca.farrelltonsolar.classic_314.apk",
        "package": "ca.farrelltonsolar.classic",
        "dir": "ca.farrelltonsolar.classic_314.apk",
        "category": "System",
    },
    {
        "name": "com.gianlu.dnshero_40.apk",
        "package": "com.gianlu.dnshero",
        "dir": "com.gianlu.dnshero_40.apk",
        "category": "Internet",
    },
    {
        "name": "com.github.axet.hourlyreminder_476.apk",
        "package": "com.github.axet.hourlyreminder",
        "dir": "com.github.axet.hourlyreminder_476.apk",
        "category": "Time",
    },
    {
        "name": "com.hwloc.lstopo_271.apk",
        "package": "com.hwloc.lstopo",
        "dir": "com.hwloc.lstopo_271.apk",
        "category": "System",
    },
    {
        "name": "info.zamojski.soft.towercollector_2140302.apk",
        "package": "info.zamojski.soft.towercollector",
        "dir": "info.zamojski.soft.towercollector_2140302.apk",
        "category": "Navigation",
    },
    {
        "name": "livio.rssreader_101.apk",
        "package": "livio.rssreader",
        "dir": "livio.rssreader_101.apk",
        "category": "Reading",
    },
    {
        "name": "org.emunix.insteadlauncher_80601.apk",
        "package": "org.emunix.insteadlauncher",
        "dir": "org.emunix.insteadlauncher_80601.apk",
        "category": "Games",
    },
    {
        "name": "org.pulpdust.lesserpad_42.apk",
        "package": "org.pulpdust.lesserpad",
        "dir": "org.pulpdust.lesserpad_42.apk",
        "category": "Writing",
    },
    {
        "name": "t20kdc.offlinepuzzlesolver_4.apk",
        "package": "t20kdc.offlinepuzzlesolver",
        "dir": "t20kdc.offlinepuzzlesolver_4.apk",
        "category": "Games",
    },
]


def get_apps_with_static_analysis(
    static_dir: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Get list of apps with complete static analysis data.

    Verifies that .reach, .wtg, .gesda files exist.

    Args:
        static_dir: Base directory for static analysis files.

    Returns:
        List of app info dicts with verified paths.
    """
    base_dir = static_dir or DEFAULT_STATIC_ANALYSIS_DIR
    verified_apps = []

    for app in APPS_WITH_STATIC_ANALYSIS:
        app_dir = base_dir / app["dir"]

        # Check for required files
        reach_files = list(app_dir.glob("*.reach"))
        wtg_files = list(app_dir.glob("*.wtg"))
        gesda_files = list(app_dir.glob("*.gesda"))

        if reach_files and wtg_files and gesda_files:
            verified_apps.append({
                **app,
                "static_dir": str(app_dir),
                "reach_file": str(reach_files[0]),
                "wtg_file": str(wtg_files[0]),
                "gesda_file": str(gesda_files[0]),
            })

    return verified_apps


@dataclass
class RunConfig:
    """Configuration for a single experiment run."""

    apk_path: str  # Path to APK file
    package_name: str  # Package name extracted from APK
    strategy: str
    repetition: int
    seed: int
    run_id: str = field(default="")

    def __post_init__(self):
        if not self.run_id:
            # Use package name for run_id (more readable)
            pkg_short = self.package_name.split(".")[-1]  # e.g., "cryptoapp"
            self.run_id = f"{pkg_short}_{self.strategy}_rep{self.repetition}"


@dataclass
class ExperimentConfig:
    """Configuration for the validation experiment."""

    experiment_id: str
    experiment_name: str

    # APK paths to test (Androguard extracts package names)
    apk_paths: List[str]

    # Strategies to compare
    strategies: List[str] = field(default_factory=lambda: [
        "rvagent", "dfs", "bfs", "greedy"
    ])

    # Execution parameters
    repetitions: int = 3
    timeout_seconds: int = 300
    agent_mode: str = "pure_algorithm"

    # Reproducibility
    base_seed: int = 42

    # Paths (configurable)
    results_dir: Path = field(default_factory=lambda: Path("results"))

    # Device
    device_serial: str = "emulator-5554"

    # Static analysis
    enable_static_analysis: bool = True
    static_analysis_dir: Path = field(default_factory=lambda: DEFAULT_STATIC_ANALYSIS_DIR)

    @classmethod
    def create_default(cls, apk_paths: List[str]) -> "ExperimentConfig":
        """Create default experiment configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return cls(
            experiment_id=f"strategy_validation_{timestamp}",
            experiment_name="Strategy Validation Experiment",
            apk_paths=apk_paths,
        )

    def generate_runs(self, app_info_cache: dict = None) -> List[RunConfig]:
        """
        Generate all run configurations for the experiment.

        Args:
            app_info_cache: Optional dict mapping apk_path -> package_name
                           (to avoid re-parsing APKs multiple times)

        Returns:
            List of RunConfig instances.
        """
        from .seed_manager import SeedManager

        seed_manager = SeedManager(self.base_seed)
        runs = []

        for rep in range(1, self.repetitions + 1):
            for apk_path in self.apk_paths:
                # Get package name from cache or placeholder
                package_name = ""
                if app_info_cache and apk_path in app_info_cache:
                    package_name = app_info_cache[apk_path]

                for strategy in self.strategies:
                    seed = seed_manager.get_seed(apk_path, strategy, rep)
                    runs.append(RunConfig(
                        apk_path=apk_path,
                        package_name=package_name,
                        strategy=strategy,
                        repetition=rep,
                        seed=seed,
                    ))

        return runs

    @property
    def total_runs(self) -> int:
        """Total number of runs in the experiment."""
        return len(self.apk_paths) * len(self.strategies) * self.repetitions

    @property
    def estimated_time_hours(self) -> float:
        """Estimated execution time in hours."""
        # timeout + 30s overhead per run
        time_per_run_seconds = self.timeout_seconds + 30
        total_seconds = self.total_runs * time_per_run_seconds
        return total_seconds / 3600

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "apk_paths": self.apk_paths,
            "strategies": self.strategies,
            "repetitions": self.repetitions,
            "timeout_seconds": self.timeout_seconds,
            "agent_mode": self.agent_mode,
            "base_seed": self.base_seed,
            "results_dir": str(self.results_dir),
            "device_serial": self.device_serial,
            "enable_static_analysis": self.enable_static_analysis,
            "static_analysis_dir": str(self.static_analysis_dir),
            "total_runs": self.total_runs,
            "estimated_time_hours": round(self.estimated_time_hours, 2),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentConfig":
        """Create from dictionary."""
        return cls(
            experiment_id=data["experiment_id"],
            experiment_name=data["experiment_name"],
            apk_paths=data["apk_paths"],
            strategies=data.get("strategies", ["rvagent", "dfs", "bfs", "greedy"]),
            repetitions=data.get("repetitions", 3),
            timeout_seconds=data.get("timeout_seconds", 300),
            agent_mode=data.get("agent_mode", "pure_algorithm"),
            base_seed=data.get("base_seed", 42),
            results_dir=Path(data.get("results_dir", "results")),
            device_serial=data.get("device_serial", "emulator-5554"),
            enable_static_analysis=data.get("enable_static_analysis", True),
            static_analysis_dir=Path(data.get("static_analysis_dir", str(DEFAULT_STATIC_ANALYSIS_DIR))),
        )

    @classmethod
    def create_with_static_apps(
        cls,
        timeout_seconds: int = 180,
        repetitions: int = 3,
        strategies: Optional[List[str]] = None,
    ) -> "ExperimentConfig":
        """
        Create experiment config using apps with static analysis.

        Args:
            timeout_seconds: Timeout per run (default 180s = 3 min).
            repetitions: Number of repetitions per app/strategy.
            strategies: List of strategies to test.

        Returns:
            ExperimentConfig with verified static analysis apps.
        """
        verified_apps = get_apps_with_static_analysis()

        if not verified_apps:
            raise ValueError("No apps with complete static analysis found")

        # Build APK paths from verified apps
        apk_paths = []
        for app in verified_apps:
            # Look for APK in static_dir or common locations
            static_dir = Path(app["static_dir"])
            apk_candidates = [
                static_dir / app["name"],
                static_dir.parent / app["name"],
            ]
            for apk_path in apk_candidates:
                if apk_path.exists():
                    apk_paths.append(str(apk_path))
                    break

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return cls(
            experiment_id=f"static_analysis_validation_{timestamp}",
            experiment_name="Strategy Validation with Static Analysis",
            apk_paths=apk_paths,
            strategies=strategies or ["rvagent", "dfs", "bfs", "greedy"],
            repetitions=repetitions,
            timeout_seconds=timeout_seconds,
            enable_static_analysis=True,
        )
