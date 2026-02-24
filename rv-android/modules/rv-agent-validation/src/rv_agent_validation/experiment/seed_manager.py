"""
Seed management for reproducible experiments.
"""

import hashlib


class SeedManager:
    """
    Manages deterministic seeds for experiment reproducibility.

    Each (app, strategy, repetition) combination receives a unique,
    deterministic seed derived from a base seed.
    """

    def __init__(self, base_seed: int = 42):
        """
        Initialize seed manager.

        Args:
            base_seed: Base seed for deterministic generation.
        """
        self.base_seed = base_seed
        self._cache: dict = {}

    def get_seed(self, app: str, strategy: str, repetition: int) -> int:
        """
        Get deterministic seed for a specific run configuration.

        Args:
            app: Application package name.
            strategy: Strategy name.
            repetition: Repetition number (1-indexed).

        Returns:
            Deterministic seed value.
        """
        key = (app, strategy, repetition)

        if key not in self._cache:
            seed_string = f"{self.base_seed}_{app}_{strategy}_{repetition}"
            hash_value = hashlib.md5(seed_string.encode()).hexdigest()
            self._cache[key] = int(hash_value, 16) % (2**31)

        return self._cache[key]

    def get_all_seeds(self, apps: list, strategies: list, repetitions: int) -> dict:
        """
        Generate all seeds for an experiment.

        Args:
            apps: List of app package names.
            strategies: List of strategy names.
            repetitions: Number of repetitions.

        Returns:
            Dictionary mapping (app, strategy, rep) to seed.
        """
        seeds = {}
        for app in apps:
            for strategy in strategies:
                for rep in range(1, repetitions + 1):
                    seeds[(app, strategy, rep)] = self.get_seed(app, strategy, rep)
        return seeds

    def verify_reproducibility(self, app: str, strategy: str, repetition: int) -> bool:
        """
        Verify that seed generation is deterministic.

        Args:
            app: Application package name.
            strategy: Strategy name.
            repetition: Repetition number.

        Returns:
            True if seeds are reproducible.
        """
        seed1 = self.get_seed(app, strategy, repetition)

        # Clear cache and regenerate
        key = (app, strategy, repetition)
        if key in self._cache:
            del self._cache[key]

        seed2 = self.get_seed(app, strategy, repetition)

        return seed1 == seed2
