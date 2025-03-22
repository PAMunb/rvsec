#!/usr/bin/env python3
"""
code_cleanup_pipeline.py - Automated Python Code Cleanup Pipeline

This script runs a series of tools to detect and clean unused code
in Python projects, including:
1. Dead code detection with Vulture
2. Unused imports removal with Autoflake
3. Import organization with isort
4. Formatting with Black
5. Static analysis with Pylint
6. Code coverage analysis with Coverage

Usage:
    python code_cleanup_pipeline.py --path /path/to/project [--aggressive] [--report-only]
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_tools():
    """Check if all required tools are installed."""
    tools = [
        "vulture", "autoflake", "isort", "black", "pylint", "coverage", "pytest"
    ]
    missing = []

    for tool in tools:
        if shutil.which(tool) is None:
            missing.append(tool)

    if missing:
        print(f"{RED}Missing tools: {', '.join(missing)}{RESET}")
        print(f"\nInstall the required tools with:")
        print(f"{BLUE}pip install {' '.join(missing)}{RESET}")
        return False

    return True


def run_command(command, description, capture_output=False):
    """Run a command and return the result."""
    print(f"{BLUE}=== {description} ==={RESET}")

    try:
        if capture_output:
            result = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            return result
        else:
            result = subprocess.run(command, check=False)
            print()  # Blank line to separate outputs
            return result.returncode == 0
    except Exception as e:
        print(f"{RED}Error running {description}: {e}{RESET}")
        return None if capture_output else False


def create_backup(project_path):
    """Create a backup of the project before making modifications."""
    temp_dir = tempfile.mkdtemp()
    backup_path = os.path.join(temp_dir, "backup")

    print(f"{BLUE}Creating backup at: {backup_path}{RESET}")
    shutil.copytree(project_path, backup_path)

    return backup_path


def restore_backup(backup_path, project_path):
    """Restore the project from a backup."""
    print(f"{YELLOW}Restoring project from backup...{RESET}")

    # Remove current directory
    shutil.rmtree(project_path)

    # Restore from backup
    shutil.copytree(backup_path, project_path)

    print(f"{GREEN}Restoration completed!{RESET}")


def detect_dead_code(project_path):
    """Detect dead code with Vulture."""
    result = run_command(
        ["vulture", project_path, "--min-confidence", "80"],
        "Detecting dead code with Vulture",
        capture_output=True
    )

    if result and result.stdout:
        print(f"{YELLOW}Potentially unused code found:{RESET}")
        print(result.stdout)
        return result.stdout
    else:
        print(f"{GREEN}No obvious dead code found.{RESET}")
        return ""


def run_tests(project_path):
    """Run tests with coverage."""
    # Move to the project directory to run tests
    cwd = os.getcwd()
    os.chdir(project_path)

    # Run tests with coverage
    success = run_command(
        ["coverage", "run", "-m", "pytest"],
        "Running tests with Coverage"
    )

    if success:
        # Generate coverage report
        result = run_command(
            ["coverage", "report", "-m"],
            "Code coverage report",
            capture_output=True
        )

        # Also save as HTML for detailed analysis
        run_command(
            ["coverage", "html"],
            "Generating HTML coverage report"
        )

        print(f"{GREEN}HTML coverage report generated at 'htmlcov/index.html'{RESET}")

    # Return to original directory
    os.chdir(cwd)

    return success


def remove_unused_imports(project_path, aggressive_mode=False):
    """Remove unused imports with Autoflake."""
    cmd = [
        "autoflake", "--in-place", "--remove-all-unused-imports",
        "--remove-unused-variables", "--recursive"
    ]

    if aggressive_mode:
        cmd.append("--expand-star-imports")
        cmd.append("--remove-duplicate-keys")

    cmd.append(project_path)

    return run_command(
        cmd,
        "Removing unused imports with Autoflake"
    )


def organize_imports(project_path):
    """Organize imports with isort."""
    return run_command(
        ["isort", project_path],
        "Organizing imports with isort"
    )


def format_code(project_path):
    """Format code with Black."""
    return run_command(
        ["black", project_path],
        "Formatting code with Black"
    )


def lint_code(project_path):
    """Lint code with Pylint."""
    result = run_command(
        ["pylint", project_path],
        "Linting code with Pylint",
        capture_output=True
    )

    if result:
        print(result.stdout)
        print(result.stderr)

    return result


def main():
    parser = argparse.ArgumentParser(description="Python Code Cleanup Pipeline")
    parser.add_argument("--path", required=True, help="Path to the Python project")
    parser.add_argument("--aggressive", action="store_true", help="Use aggressive cleanup options")
    parser.add_argument("--report-only", action="store_true", help="Only report issues without making changes")

    args = parser.parse_args()

    project_path = args.path

    print(f"{BOLD}{BLUE}Starting Python Code Cleanup Pipeline{RESET}")
    print(f"Project path: {project_path}")
    print(f"Mode: {'Report Only' if args.report_only else 'Cleanup'}")
    print(f"Aggressive: {'Yes' if args.aggressive else 'No'}")
    print()

    # Check if all required tools are installed
    if not check_tools():
        return 1

    # Create backup if we're making changes
    backup_path = None
    if not args.report_only:
        backup_path = create_backup(project_path)

    try:
        # Analysis steps (always run)
        dead_code = detect_dead_code(project_path)

        # Run tests if available
        has_tests = os.path.exists(os.path.join(project_path, "tests"))
        if has_tests:
            run_tests(project_path)
        else:
            print(f"{YELLOW}No tests directory found. Skipping test coverage.{RESET}")

        # If report only, stop here
        if args.report_only:
            print(f"{BLUE}Report-only mode. No changes made to the code.{RESET}")
            return 0

        # Cleanup steps
        remove_unused_imports(project_path, args.aggressive)
        organize_imports(project_path)
        format_code(project_path)

        # Final linting to check the result
        lint_result = lint_code(project_path)

        print(f"{GREEN}{BOLD}Cleanup pipeline completed successfully!{RESET}")
        print(f"{BLUE}You may want to review the changes and run your tests before committing.{RESET}")

    except Exception as e:
        print(f"{RED}Error during cleanup: {e}{RESET}")

        # Restore from backup if there was an error
        if backup_path:
            restore_backup(backup_path, project_path)

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())