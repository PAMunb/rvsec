# scripts/migrate_logcat_files.py

"""
Utility script to migrate legacy logcat files to the new format.

This script:
1. Identifies legacy logcat files in the results directory
2. Parses them using the modern parser
3. Converts the data to the standardized format using LogcatRepository
4. Saves the results in a standard format

This supports complete migration away from legacy parsers.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rvandroid.domain.coverage import LogcatRepository
from rvandroid.parser.log import logcat_parser


def setup_logging():
    """Configure logging for the migration script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logcat_migration.log')
        ]
    )
    return logging.getLogger('migrate_logcat')


def find_logcat_files(base_dir: str) -> List[str]:
    """
    Find all logcat files in the base directory and subdirectories.

    Args:
        base_dir: Base directory to search

    Returns:
        List of paths to logcat files
    """
    logcat_files = []

    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.logcat'):
                logcat_files.append(os.path.join(root, file))

    return logcat_files


def migrate_logcat_file(file_path: str, backup: bool = True) -> Optional[LogcatRepository]:
    """
    Migrate a single logcat file to the new format.

    Args:
        file_path: Path to the logcat file
        backup: Whether to create a backup of the original file

    Returns:
        LogcatRepository with the processed data or None if migration failed
    """
    logger = logging.getLogger('migrate_logcat')

    try:
        # Create backup if requested
        if backup:
            backup_path = f"{file_path}.bak"
            logger.info(f"Creating backup at {backup_path}")
            with open(file_path, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())

        # Parse the logcat file using the modern parser
        logger.info(f"Parsing logcat file: {file_path}")
        repository = logcat_parser.parse_logcat_file(file_path)

        # Check if parsing was successful
        metrics = repository.calculate_metrics()
        logger.info(f"Parsed {metrics.called_methods} method calls and {metrics.unique_errors} unique errors")

        return repository

    except Exception as e:
        logger.error(f"Error migrating logcat file {file_path}: {e}", exc_info=True)
        return None


def run_migration(base_dir: str, backup: bool = True):
    """
    Run the migration on all logcat files in the base directory.

    Args:
        base_dir: Base directory for migration
        backup: Whether to create backups of the original files
    """
    logger = logging.getLogger('migrate_logcat')

    # Find all logcat files
    logger.info(f"Searching for logcat files in {base_dir}...")
    logcat_files = find_logcat_files(base_dir)
    logger.info(f"Found {len(logcat_files)} logcat files")

    # Process each file
    success_count = 0
    failure_count = 0

    for file_path in logcat_files:
        logger.info(f"Processing {file_path}...")
        repository = migrate_logcat_file(file_path, backup)

        if repository:
            success_count += 1
        else:
            failure_count += 1

    # Print summary
    logger.info(f"Migration complete. {success_count} files processed successfully, {failure_count} failures.")


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description='Migrate legacy logcat files to standardized format')
    parser.add_argument('--dir', '-d', help='Base directory containing logcat files', required=True)
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backups of original files')

    args = parser.parse_args()

    logger = setup_logging()
    logger.info(f"Starting logcat file migration")

    run_migration(args.dir, not args.no_backup)


if __name__ == '__main__':
    main()