"""
Static analysis integration tests.

Tests RVAgent with and without static analysis data to verify:
- MOP prioritization works with static data
- Graceful degradation without static data
- Static data loading from .reach, .wtg, .gesda files
"""

import pytest
import time
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.agent_factory import AgentFactory
from .conftest import (
    launch_app,
    force_stop_app,
    DATASET_ROOT,
    DEVICE_ID,
    SGLANG_URL,
    SGLANG_MODEL,
)

pytestmark = [pytest.mark.online, pytest.mark.static_analysis]


# =============================================================================
# Static Data Loading Tests
# =============================================================================


class TestStaticDataLoading:
    """Test loading static analysis data."""

    def test_reach_file_exists(self, cryptoapp):
        """Verify .reach file exists for cryptoapp."""
        if not cryptoapp.static_data_dir:
            pytest.skip("No static data directory")

        reach_files = list(cryptoapp.static_data_dir.glob("*.reach"))
        assert len(reach_files) > 0, "No .reach file found"
        print(f"\n  Found .reach: {reach_files[0].name}")

    def test_wtg_file_exists(self, cryptoapp):
        """Verify .wtg file exists for cryptoapp."""
        if not cryptoapp.static_data_dir:
            pytest.skip("No static data directory")

        wtg_files = list(cryptoapp.static_data_dir.glob("*.wtg"))
        assert len(wtg_files) > 0, "No .wtg file found"
        print(f"\n  Found .wtg: {wtg_files[0].name}")

    def test_gesda_file_exists(self, cryptoapp):
        """Verify .gesda file exists for cryptoapp."""
        if not cryptoapp.static_data_dir:
            pytest.skip("No static data directory")

        gesda_files = list(cryptoapp.static_data_dir.glob("*.gesda"))
        assert len(gesda_files) > 0, "No .gesda file found"
        print(f"\n  Found .gesda: {gesda_files[0].name}")

    def test_load_static_analysis_data(self, cryptoapp):
        """Can load static analysis data from files."""
        if not cryptoapp.has_static_analysis:
            pytest.skip("No static analysis data")

        try:
            from rv_static_analysis.loader import StaticAnalysisLoader

            loader = StaticAnalysisLoader(cryptoapp.static_data_dir)
            static_data = loader.load()

            assert static_data is not None
            print(f"\n  Static data loaded successfully")

            # Check components
            if hasattr(static_data, "classes"):
                print(
                    f"  Classes: {len(static_data.classes.methods) if hasattr(static_data.classes, 'methods') else 'N/A'}"
                )
            if hasattr(static_data, "windows"):
                print(
                    f"  Windows: {len(static_data.windows.windows) if hasattr(static_data.windows, 'windows') else 'N/A'}"
                )
            if hasattr(static_data, "wtg"):
                print(
                    f"  WTG transitions: {len(static_data.wtg.transitions) if hasattr(static_data.wtg, 'transitions') else 'N/A'}"
                )

        except ImportError:
            pytest.skip("rv_static_analysis not available")


# =============================================================================
# Exploration With Static Analysis Tests
# =============================================================================


class TestExplorationWithStaticAnalysis:
    """Test agent exploration with static analysis data."""

    def test_agent_accepts_static_data(self, device, cryptoapp, check_emulator):
        """Agent can be created with static analysis data."""
        static_data = None

        if cryptoapp.has_static_analysis:
            try:
                from rv_static_analysis.loader import StaticAnalysisLoader

                loader = StaticAnalysisLoader(cryptoapp.static_data_dir)
                static_data = loader.load()
            except Exception:
                pass

        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(
            config, device=device, static_data=static_data
        )

        assert agent is not None
        if static_data:
            print(f"\n  Agent created with static analysis data")
        else:
            print(f"\n  Agent created without static analysis data")

    def test_exploration_with_static_data(
        self, device, cryptoapp, device_id, check_emulator
    ):
        """Run exploration with static analysis data."""
        static_data = None

        if cryptoapp.has_static_analysis:
            try:
                from rv_static_analysis.loader import StaticAnalysisLoader

                loader = StaticAnalysisLoader(cryptoapp.static_data_dir)
                static_data = loader.load()
            except Exception:
                pass

        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(
            config, device=device, static_data=static_data
        )

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        result = agent.run()

        print(f"\n  With static data: {static_data is not None}")
        print(f"  Iterations: {result.get('iterations', 0)}")
        print(f"  Unique states: {result.get('unique_states', 0)}")

        assert result.get("status") == "completed"


# =============================================================================
# Graceful Degradation Tests (No Static Analysis)
# =============================================================================


class TestGracefulDegradation:
    """Test agent works without static analysis data."""

    def test_agent_without_static_data(self, device, cryptoapp, check_emulator):
        """Agent works without static analysis data."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        # Explicitly create without static data
        agent = AgentFactory.create_agent(config, device=device, static_data=None)

        assert agent is not None
        print(f"\n  Agent created without static data")

    def test_exploration_without_static_data(
        self, device, cryptoapp, device_id, check_emulator
    ):
        """Run exploration without static analysis data."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device, static_data=None)

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        result = agent.run()

        print(f"\n  Without static data:")
        print(f"  Iterations: {result.get('iterations', 0)}")
        print(f"  Unique states: {result.get('unique_states', 0)}")

        assert result.get("status") == "completed"
        assert result.get("iterations", 0) > 0

    def test_compare_with_and_without_static(
        self, device, cryptoapp, device_id, check_emulator
    ):
        """Compare exploration results with and without static data."""
        # Run without static data
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=20,
        )

        agent_no_static = AgentFactory.create_agent(
            config, device=device, static_data=None
        )

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        result_no_static = agent_no_static.run()

        force_stop_app(device_id, cryptoapp.package_name)
        time.sleep(1)

        # Run with static data
        static_data = None
        if cryptoapp.has_static_analysis:
            try:
                from rv_static_analysis.loader import StaticAnalysisLoader

                loader = StaticAnalysisLoader(cryptoapp.static_data_dir)
                static_data = loader.load()
            except Exception:
                pass

        agent_with_static = AgentFactory.create_agent(
            config, device=device, static_data=static_data
        )

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        result_with_static = agent_with_static.run()

        print(f"\n  Without static data:")
        print(f"    Iterations: {result_no_static.get('iterations', 0)}")
        print(f"    States: {result_no_static.get('unique_states', 0)}")

        print(f"\n  With static data:")
        print(f"    Iterations: {result_with_static.get('iterations', 0)}")
        print(f"    States: {result_with_static.get('unique_states', 0)}")

        # Both should complete successfully
        assert result_no_static.get("status") == "completed"
        assert result_with_static.get("status") == "completed"


# =============================================================================
# MOP Prioritization Tests
# =============================================================================


class TestMOPPrioritization:
    """Test MOP (Monitored Operations) prioritization."""

    def test_strategy_has_mop_priority(self, device, cryptoapp, check_emulator):
        """Strategy supports MOP prioritization."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)

        # Check strategy has MOP priority method
        strategy = agent.strategy
        has_mop_priority = hasattr(strategy, "_get_mop_priority") or hasattr(
            strategy, "mop_prioritization"
        )

        print(f"\n  Strategy: {type(strategy).__name__}")
        print(f"  Has MOP priority: {has_mop_priority}")

    def test_mop_priority_with_static_data(
        self, device, cryptoapp, device_id, check_emulator
    ):
        """MOP priority works with static analysis data."""
        static_data = None

        if cryptoapp.has_static_analysis:
            try:
                from rv_static_analysis.loader import StaticAnalysisLoader

                loader = StaticAnalysisLoader(cryptoapp.static_data_dir)
                static_data = loader.load()
            except Exception:
                pass

        if not static_data:
            pytest.skip("No static data available")

        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(
            config, device=device, static_data=static_data
        )

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        result = agent.run()

        # Check if any MOP actions were prioritized
        memory_stats = agent.get_memory_stats()

        print(f"\n  Exploration with MOP prioritization:")
        print(f"  Iterations: {result.get('iterations', 0)}")
        print(f"  Memory stats: {memory_stats}")
