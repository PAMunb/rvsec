"""
Checkpoint management for experiment resume capability.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Set, Optional

from .config import RunConfig

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages experiment checkpoints for resume capability.

    Tracks completed runs and allows resuming interrupted experiments.
    """

    def __init__(self, checkpoint_file: Path):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_file: Path to checkpoint JSON file.
        """
        self.checkpoint_file = checkpoint_file
        self._completed_runs: Set[str] = set()
        self._failed_runs: Set[str] = set()
        self._start_time: Optional[str] = None
        self._last_update: Optional[str] = None

        self._load()

    def _load(self):
        """Load checkpoint from file if exists."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    self._completed_runs = set(data.get("completed_runs", []))
                    self._failed_runs = set(data.get("failed_runs", []))
                    self._start_time = data.get("start_time")
                    self._last_update = data.get("last_update")
                    logger.info(f"Loaded checkpoint: {len(self._completed_runs)} completed, {len(self._failed_runs)} failed")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
                self._completed_runs = set()
                self._failed_runs = set()

    def _save(self):
        """Save checkpoint to file."""
        self._last_update = datetime.now().isoformat()

        data = {
            "completed_runs": sorted(list(self._completed_runs)),
            "failed_runs": sorted(list(self._failed_runs)),
            "start_time": self._start_time,
            "last_update": self._last_update,
            "total_completed": len(self._completed_runs),
            "total_failed": len(self._failed_runs),
        }

        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)

    def start_experiment(self):
        """Mark experiment start time."""
        if not self._start_time:
            self._start_time = datetime.now().isoformat()
            self._save()

    def mark_completed(self, run: RunConfig):
        """
        Mark a run as completed.

        Args:
            run: Completed run configuration.
        """
        self._completed_runs.add(run.run_id)
        self._failed_runs.discard(run.run_id)
        self._save()
        logger.debug(f"Marked completed: {run.run_id}")

    def mark_failed(self, run: RunConfig, error: str = ""):
        """
        Mark a run as failed.

        Args:
            run: Failed run configuration.
            error: Error message.
        """
        self._failed_runs.add(run.run_id)
        self._save()
        logger.warning(f"Marked failed: {run.run_id} - {error}")

    def is_completed(self, run: RunConfig) -> bool:
        """
        Check if a run is already completed.

        Args:
            run: Run configuration to check.

        Returns:
            True if run is completed.
        """
        return run.run_id in self._completed_runs

    def get_pending_runs(self, all_runs: List[RunConfig]) -> List[RunConfig]:
        """
        Get runs that haven't been completed yet.

        Args:
            all_runs: All run configurations.

        Returns:
            List of pending runs.
        """
        pending = [r for r in all_runs if r.run_id not in self._completed_runs]
        logger.info(f"Pending runs: {len(pending)} of {len(all_runs)}")
        return pending

    def get_progress(self, total_runs: int) -> dict:
        """
        Get experiment progress.

        Args:
            total_runs: Total number of runs.

        Returns:
            Progress dictionary.
        """
        completed = len(self._completed_runs)
        failed = len(self._failed_runs)
        pending = total_runs - completed

        return {
            "total": total_runs,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "progress_percent": round(completed / total_runs * 100, 1) if total_runs > 0 else 0,
            "start_time": self._start_time,
            "last_update": self._last_update,
        }

    def reset(self):
        """Reset checkpoint (clear all progress)."""
        self._completed_runs = set()
        self._failed_runs = set()
        self._start_time = None
        self._last_update = None

        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

        logger.info("Checkpoint reset")
