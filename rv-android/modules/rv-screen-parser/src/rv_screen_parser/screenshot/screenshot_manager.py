# rvandroid/analysis/screenshot/screenshot_manager.py
"""
Screenshot Manager for RVDroid.

This module provides functionality to capture, store, and manage
screenshots during test execution, with capabilities for caching
and optimizing disk usage.
"""

import os
import shutil
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from rv_android_core.analysis.base_analyzer import BaseRepository


class ScreenshotManager(BaseRepository):
    """
    Manages the capture and storage of screenshots during testing.

    ### Architectural Decisions:
    - Centralizes screenshot management to reduce redundancy
    - Implements an efficient caching strategy to avoid excessive I/O
    - Provides cleanup functionality to manage disk usage
    - Supports structured organization of screenshots by test session
    - Extends BaseRepository for consistent interface

    ### Role in the System:
    - Handles screenshot capture requests from different components
    - Manages screenshot storage and organization
    - Implements caching for performance optimization
    - Handles cleanup to avoid excessive disk usage
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        max_screenshots: int = 100,
        retention_time: int = 3600,
    ):  # Default 1 hour retention
        """
        Initialize the screenshot manager.

        Args:
            base_dir: Base directory for storing screenshots
            max_screenshots: Maximum number of screenshots to keep
            retention_time: Time in seconds to retain screenshots
        """
        super().__init__(repository_name="screenshot")

        # Set base directory
        self.base_dir = base_dir or os.path.join(
            os.path.dirname(__file__), "screenshots"
        )
        os.makedirs(self.base_dir, exist_ok=True)

        # Set session directory (with timestamp)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.base_dir, f"session_{timestamp}")
        os.makedirs(self.session_dir, exist_ok=True)

        # Set configuration
        self.max_screenshots = max_screenshots
        self.retention_time = retention_time

        # Initialize tracking
        self.screenshot_paths: List[str] = []
        self.screenshot_count = 0

        self.logger.info(
            f"Initialized screenshot manager with session dir: {self.session_dir}"
        )

        # Clean up old screenshots
        self._cleanup_old_screenshots()

    def save_screenshot(
        self, screenshot_data, activity_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Save a screenshot to disk.

        Args:
            screenshot_data: Raw screenshot data (bytes or PIL Image)
            activity_name: Optional activity name for file naming

        Returns:
            Path to saved screenshot or None if failed
        """
        try:
            # Generate filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            activity_prefix = f"{activity_name}_" if activity_name else ""
            filename = f"{activity_prefix}{timestamp}.png"

            # Full path
            save_path = os.path.join(self.session_dir, filename)

            # Save based on data type
            if isinstance(screenshot_data, bytes):
                with open(save_path, "wb") as f:
                    f.write(screenshot_data)
            elif hasattr(screenshot_data, "save"):  # PIL Image
                screenshot_data.save(save_path)
            else:
                self.logger.error(
                    f"Unsupported screenshot data type: {type(screenshot_data)}"
                )
                return None

            # Track this screenshot
            self.screenshot_paths.append(save_path)
            self.screenshot_count += 1

            # Log storage
            self.log_storage_summary("screenshot", 1)

            # Check if we need to clean up
            if self.screenshot_count > self.max_screenshots:
                self._cleanup_excess_screenshots()

            return save_path

        except Exception as e:
            self.logger.error(f"Error saving screenshot: {e}")
            return None

    def rename_with_state(
        self, screenshot_path: str, state_fingerprint: str
    ) -> Optional[str]:
        """
        Rename a screenshot file to include state fingerprint.

        Args:
            screenshot_path: Original screenshot path
            state_fingerprint: State fingerprint to add to filename

        Returns:
            New path after renaming or None if failed
        """
        try:
            if not os.path.exists(screenshot_path):
                self.logger.error(f"Screenshot not found: {screenshot_path}")
                return None

            # Get directory and filename parts
            directory = os.path.dirname(screenshot_path)
            filename = os.path.basename(screenshot_path)

            # Add state fingerprint to filename (before extension)
            name_parts = filename.split(".")
            if len(name_parts) > 1:
                # Take the first 8 chars of fingerprint for brevity
                short_fingerprint = state_fingerprint[:8]
                new_filename = f"{name_parts[0]}_{short_fingerprint}.{name_parts[1]}"
            else:
                new_filename = f"{filename}_{state_fingerprint[:8]}"

            new_path = os.path.join(directory, new_filename)

            # Rename the file
            os.rename(screenshot_path, new_path)

            # Update path in tracking list
            if screenshot_path in self.screenshot_paths:
                index = self.screenshot_paths.index(screenshot_path)
                self.screenshot_paths[index] = new_path

            return new_path

        except Exception as e:
            self.logger.error(f"Error renaming screenshot: {e}")
            return None

    def get_screenshot_for_state(self, state_fingerprint: str) -> Optional[str]:
        """
        Find a screenshot for a specific state.

        Args:
            state_fingerprint: State fingerprint to search for

        Returns:
            Path to screenshot for the state or None if not found
        """
        # Convert fingerprint to the shortened version used in filenames
        short_fingerprint = state_fingerprint[:8]

        # Search for matching filenames
        for path in self.screenshot_paths:
            filename = os.path.basename(path)
            if short_fingerprint in filename:
                return path

        return None

    def _cleanup_excess_screenshots(self) -> None:
        """
        Clean up excess screenshots beyond max_screenshots limit.
        Removes oldest screenshots first.
        """
        if len(self.screenshot_paths) <= self.max_screenshots:
            return

        # Calculate how many to remove
        excess_count = len(self.screenshot_paths) - self.max_screenshots

        # Get oldest screenshots to remove
        screenshots_to_remove = self.screenshot_paths[:excess_count]

        # Remove screenshots
        for path in screenshots_to_remove:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    self.logger.debug(f"Removed excess screenshot: {path}")
            except Exception as e:
                self.logger.error(f"Error removing screenshot {path}: {e}")

        # Update tracking list
        self.screenshot_paths = self.screenshot_paths[excess_count:]

        # Log cleanup
        self.log_storage_summary("removed screenshots", excess_count)

    def _cleanup_old_screenshots(self) -> None:
        """
        Clean up screenshots older than retention_time.
        Removes screenshots from past sessions.
        """
        try:
            # Get current time
            current_time = time.time()
            removed_count = 0

            # Look for session directories
            for item in os.listdir(self.base_dir):
                item_path = os.path.join(self.base_dir, item)

                # Skip current session directory
                if item_path == self.session_dir:
                    continue

                # If it's a directory that looks like a session dir
                if os.path.isdir(item_path) and item.startswith("session_"):
                    # Check directory age
                    dir_stat = os.stat(item_path)
                    dir_age = current_time - dir_stat.st_mtime

                    # Remove if older than retention time
                    if dir_age > self.retention_time:
                        shutil.rmtree(item_path)
                        removed_count += 1
                        self.logger.info(
                            f"Removed old screenshot directory: {item_path}"
                        )

            if removed_count > 0:
                self.log_storage_summary("old screenshot directories", removed_count)

        except Exception as e:
            self.logger.error(f"Error cleaning up old screenshots: {e}")

    def get_latest_screenshot(self) -> Optional[str]:
        """
        Get the most recent screenshot path.

        Returns:
            Path to the latest screenshot or None if no screenshots
        """
        if not self.screenshot_paths:
            return None

        return self.screenshot_paths[-1]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the screenshot repository.

        Returns:
            Dictionary with metrics
        """
        return {
            "total_screenshots": self.screenshot_count,
            "active_screenshots": len(self.screenshot_paths),
            "session_directory": self.session_dir,
            "max_screenshots": self.max_screenshots,
            "retention_time_seconds": self.retention_time,
        }
