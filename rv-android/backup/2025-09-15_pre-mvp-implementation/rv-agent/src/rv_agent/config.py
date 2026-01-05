"""
RVAgent Prototype Configuration

Hardcoded configuration for Phase 0 prototype with parameter grid search.
"""
import random
from dataclasses import dataclass
from typing import List, Tuple
from pathlib import Path

@dataclass
class PrototypeConfig:
    """Phase 0 prototype configuration with hardcoded values for simplicity."""
    
    # Data Source Configuration
    SCREENSHOTS_DIR: str = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    RANDOM_SEED: int = 42  # For reproducible results
    
    # Test Parameters (configurable)
    NUM_TEST_APPS: int = 10      # Default: 10 apps from 14 available
    SCREENSHOTS_PER_APP: int = 5 # Default: 5 screenshots per app
    TIMEOUT_SECONDS: int = 30    # Per screenshot analysis timeout
    
    # Vision Model Configuration (from research findings)
    PRIMARY_MODEL: str = "qwen2.5vl:7b"  # 98.3% success rate champion
    FALLBACK_MODEL: str = "gemma2:9b"    # 96.9% success rate
    COORDINATE_TOLERANCE: int = 50       # pixels (from research)
    
    # Parameter Grid for A/B Testing
    TEMPERATURES: List[float] = None
    TOP_PS: List[float] = None 
    TOP_KS: List[int] = None
    
    # LLM Configuration
    BASE_URL: str = "http://localhost:11434"
    MAX_TOKENS: int = 1000
    
    def __post_init__(self):
        """Initialize parameter variations after dataclass creation."""
        if self.TEMPERATURES is None:
            self.TEMPERATURES = [0.1, 0.3, 0.7]  # deterministic → creative
        if self.TOP_PS is None:
            self.TOP_PS = [0.7, 0.9]             # conservative → diverse  
        if self.TOP_KS is None:
            self.TOP_KS = [20, 40]               # restricted → open
    
    @property 
    def total_tests(self) -> int:
        """Calculate total number of tests in grid search."""
        return (len(self.TEMPERATURES) * len(self.TOP_PS) * len(self.TOP_KS) * 
                self.NUM_TEST_APPS * self.SCREENSHOTS_PER_APP)
    
    @property
    def estimated_duration_hours(self) -> float:
        """Estimate total execution time in hours."""
        return (self.total_tests * self.TIMEOUT_SECONDS) / 3600
    
    def get_available_apps(self) -> List[str]:
        """Get list of available apps in screenshots directory."""
        screenshots_path = Path(self.SCREENSHOTS_DIR)
        if not screenshots_path.exists():
            raise FileNotFoundError(f"Screenshots directory not found: {self.SCREENSHOTS_DIR}")
            
        apps = []
        for app_dir in screenshots_path.iterdir():
            if app_dir.is_dir() and app_dir.name.endswith('.apk'):
                apps.append(app_dir.name)
        
        return sorted(apps)
    
    def random_select_apps(self, num_apps: int = None) -> List[str]:
        """Select random apps with reproducible seed."""
        if num_apps is None:
            num_apps = self.NUM_TEST_APPS
            
        random.seed(self.RANDOM_SEED)
        all_apps = self.get_available_apps()
        
        if len(all_apps) < num_apps:
            raise ValueError(f"Not enough apps available. Found {len(all_apps)}, need {num_apps}")
            
        return random.sample(all_apps, num_apps)
    
    def random_select_screenshots(self, app_name: str, num_screenshots: int = None) -> List[str]:
        """Select random screenshots from app with reproducible seed."""
        if num_screenshots is None:
            num_screenshots = self.SCREENSHOTS_PER_APP
            
        # App-specific seed for consistent selection per app
        random.seed(self.RANDOM_SEED + hash(app_name))
        
        app_path = Path(self.SCREENSHOTS_DIR) / app_name
        if not app_path.exists():
            raise FileNotFoundError(f"App directory not found: {app_path}")
        
        # Get all PNG files
        screenshots = []
        for file in app_path.iterdir():
            if file.suffix == '.png' and file.stem.isdigit():
                screenshots.append(file.stem)
        
        if len(screenshots) < num_screenshots:
            num_screenshots = len(screenshots)  # Use all available if fewer than requested
            
        selected = random.sample(screenshots, num_screenshots)
        return sorted(selected)  # Sort for consistent ordering
    
    def get_screenshot_files(self, app_name: str, screenshot_id: str) -> Tuple[str, str]:
        """Get paths to screenshot image and uiautomator XML files."""
        base_path = Path(self.SCREENSHOTS_DIR) / app_name / screenshot_id
        
        image_path = str(base_path.with_suffix('.png'))
        xml_path = str(base_path.with_suffix('.uiautomator'))
        
        # Verify files exist
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Screenshot image not found: {image_path}")
        if not Path(xml_path).exists():
            raise FileNotFoundError(f"UIAutomator XML not found: {xml_path}")
            
        return image_path, xml_path
    
    def print_config_summary(self):
        """Print configuration summary for validation."""
        print("=" * 60)
        print("RVAgent Phase 0 Prototype Configuration")
        print("=" * 60)
        print(f"Screenshots Directory: {self.SCREENSHOTS_DIR}")
        print(f"Available Apps: {len(self.get_available_apps())}")
        print(f"Test Apps: {self.NUM_TEST_APPS}")
        print(f"Screenshots per App: {self.SCREENSHOTS_PER_APP}")
        print(f"Primary Model: {self.PRIMARY_MODEL}")
        print(f"Random Seed: {self.RANDOM_SEED}")
        print()
        print("Parameter Grid:")
        print(f"  Temperatures: {self.TEMPERATURES}")
        print(f"  Top-P: {self.TOP_PS}")
        print(f"  Top-K: {self.TOP_KS}")
        print()
        print(f"Total Tests: {self.total_tests:,}")
        print(f"Estimated Duration: {self.estimated_duration_hours:.1f} hours")
        print(f"Timeout per Test: {self.TIMEOUT_SECONDS}s")
        print("=" * 60)