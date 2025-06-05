"""
Module Usage Tracker for Python Projects

This decorator tracks which modules are actually used during execution by comparing
sys.modules before and after running the main function. It generates reports showing
used and unused files, helping identify dead code for cleanup.

USAGE:
1. Import the decorator in your main.py:
   from main_tracker import track_modules

2. Apply decorator to your main function:
   @track_modules()
   def main():
       # your code here
       pass

3. Run your application normally. Reports will be generated automatically.

4. To disable tracking, just comment out the decorator:
   # @track_modules()
   def main():
       # your code here
       pass

OUTPUTS:
- used_files.txt: Simple list of used files (one per line)
- module_usage_report.txt: Detailed analysis with used/unused breakdown

CONFIGURATION:
@track_modules(
    project_root=".",
    main_package="rvandroid",
    output_dir=".",
    exclude_patterns=["test_*", "__pycache__", "rvandroid/tools/qtesting/src"]
)
"""

import sys
import functools
from pathlib import Path
from datetime import datetime
import fnmatch


def track_modules(
        project_root=".",
        main_package="rvandroid",
        output_dir=".",
        exclude_patterns=None
):
    """
    Decorator to track module usage during function execution.

    Args:
        project_root (str): Root directory of the project
        main_package (str): Main package name to analyze
        output_dir (str): Directory to save output files
        exclude_patterns (list): Patterns to exclude from analysis
    """
    if exclude_patterns is None:
        exclude_patterns = [
            "test_*",
            "__pycache__",
            "*.pyc",
            "backup",
            "rvandroid/tools/qtesting/src",
            "rvandroid/rv_evaluator",
            "rvandroid/rvdroid",
            "rvandroid/test_framework"
        ]

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracker = ModuleTracker(project_root, main_package, output_dir, exclude_patterns)
            tracker.start_tracking()

            try:
                result = func(*args, **kwargs)
            finally:
                tracker.stop_tracking_and_report()

            return result

        return wrapper

    return decorator


class ModuleTracker:
    def __init__(self, project_root, main_package, output_dir, exclude_patterns):
        self.project_root = Path(project_root).resolve()
        self.main_package = main_package
        self.output_dir = Path(output_dir)
        self.exclude_patterns = exclude_patterns
        self.initial_modules = set()
        self.used_files = set()

    def start_tracking(self):
        """Capture initial state of loaded modules"""
        self.initial_modules = set(sys.modules.keys())

    def stop_tracking_and_report(self):
        """Analyze modules and generate reports"""
        # Find newly loaded modules
        final_modules = set(sys.modules.keys())
        new_modules = final_modules - self.initial_modules

        # Extract project files from new modules
        self._extract_project_files(new_modules)

        # Find all project files
        all_project_files = self._find_all_project_files()

        # Calculate unused files
        unused_files = all_project_files - self.used_files

        # Generate reports
        self._save_used_files_list()
        self._save_detailed_report(all_project_files, unused_files)

    def _extract_project_files(self, module_names):
        """Extract project files from module names"""
        for module_name in module_names:
            module = sys.modules.get(module_name)

            if not module or not hasattr(module, '__file__') or not module.__file__:
                continue

            try:
                file_path = Path(module.__file__).resolve()
                relative_path = file_path.relative_to(self.project_root)

                # Check if it's in our main package
                if str(relative_path).startswith(self.main_package):
                    # Apply exclude patterns
                    if not self._should_exclude(str(relative_path)):
                        self.used_files.add(file_path)

            except (ValueError, AttributeError):
                # Not in project root or other issues
                continue

    def _find_all_project_files(self):
        """Find all Python files in the main package"""
        all_files = set()
        package_path = self.project_root / self.main_package

        if not package_path.exists():
            return all_files

        for py_file in package_path.rglob("*.py"):
            try:
                relative_path = py_file.relative_to(self.project_root)
                if not self._should_exclude(str(relative_path)):
                    all_files.add(py_file.resolve())
            except ValueError:
                continue

        return all_files

    def _should_exclude(self, file_path):
        """Check if file should be excluded based on patterns"""
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path, pattern) or pattern in file_path:
                return True
        return False

    def _save_used_files_list(self):
        """Save simple list of used files"""
        output_file = self.output_dir / "used_files.txt"

        with open(output_file, 'w', encoding='utf-8') as f:
            for file_path in sorted(self.used_files):
                # Write relative path from project root
                try:
                    relative_path = file_path.relative_to(self.project_root)
                    f.write(f"{relative_path}\n")
                except ValueError:
                    f.write(f"{file_path}\n")

    def _save_detailed_report(self, all_files, unused_files):
        """Save detailed analysis report"""
        output_file = self.output_dir / "module_usage_report.txt"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# MODULE USAGE ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Project: {self.project_root}\n")
            f.write(f"Package: {self.main_package}\n")
            f.write("\n")

            # Summary
            f.write("## SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Python files found: {len(all_files)}\n")
            f.write(f"Files used during execution: {len(self.used_files)}\n")
            f.write(f"Files NOT used: {len(unused_files)}\n")
            if all_files:
                coverage = (len(self.used_files) / len(all_files)) * 100
                f.write(f"Code coverage: {coverage:.1f}%\n")
            f.write("\n")

            # Used files section
            f.write("## USED FILES\n")
            f.write("-" * 20 + "\n")
            if self.used_files:
                for file_path in sorted(self.used_files):
                    try:
                        relative_path = file_path.relative_to(self.project_root)
                        f.write(f"{relative_path}\n")
                    except ValueError:
                        f.write(f"{file_path}\n")
            else:
                f.write("No files detected as used.\n")
            f.write("\n")

            # Unused files section
            f.write("## UNUSED FILES (candidates for removal)\n")
            f.write("-" * 20 + "\n")
            if unused_files:
                for file_path in sorted(unused_files):
                    try:
                        relative_path = file_path.relative_to(self.project_root)
                        f.write(f"{relative_path}\n")
                    except ValueError:
                        f.write(f"{file_path}\n")
            else:
                f.write("All files are being used.\n")
            f.write("\n")

            # Exclusions section
            f.write("## EXCLUDED PATTERNS\n")
            f.write("-" * 20 + "\n")
            for pattern in self.exclude_patterns:
                f.write(f"{pattern}\n")
