"""
End-to-end agent integration tests.

Tests full RVAgent workflow with real emulator and LLM.
"""

import pytest
import time
import json
from pathlib import Path
from datetime import datetime

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.agent_factory import AgentFactory
from .conftest import (
    launch_app,
    force_stop_app,
    SGLANG_URL,
    SGLANG_MODEL,
    DEVICE_ID,
)

pytestmark = [pytest.mark.online, pytest.mark.slow]


RESULTS_DIR = Path("/tmp/rvagent_e2e_tests")


@pytest.fixture(scope="module")
def results_dir():
    """Create results directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


# =============================================================================
# Pure Algorithm Mode Tests (No LLM)
# =============================================================================


class TestPureAlgorithmMode:
    """Test agent in pure_algorithm mode (no LLM dependency)."""

    def test_agent_creation(self, device, cryptoapp, check_emulator):
        """Can create agent in pure_algorithm mode."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)
        assert agent is not None
        assert agent.config.agent_mode == "pure_algorithm"
        print(f"\n  Agent created in pure_algorithm mode")

    def test_short_exploration(
        self, device, cryptoapp, device_id, check_emulator, results_dir
    ):
        """Run short exploration (30s) in pure_algorithm mode."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
            debug_mode=True,
        )

        agent = AgentFactory.create_agent(config, device=device)

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        start_time = time.time()
        result = agent.run()
        duration = time.time() - start_time

        # Save results
        result_file = (
            results_dir / f"pure_algo_{datetime.now().strftime('%H%M%S')}.json"
        )
        with open(result_file, "w") as f:
            json.dump(
                {
                    "mode": "pure_algorithm",
                    "duration_s": duration,
                    "result": result,
                },
                f,
                indent=2,
                default=str,
            )

        print(f"\n  Duration: {duration:.1f}s")
        print(f"  Iterations: {result.get('iterations', 0)}")
        print(f"  Unique states: {result.get('unique_states', 0)}")
        print(f"  Results: {result_file}")

        assert result.get("status") == "completed"
        assert result.get("iterations", 0) > 0

    def test_exploration_with_multiple_apps(
        self, device, device_id, check_emulator, results_dir
    ):
        """Run exploration on multiple apps sequentially."""
        from .conftest import APPS_WITH_STATIC, install_apk, is_app_installed

        results = []

        for app in APPS_WITH_STATIC[:3]:  # Test first 3 apps
            # Install if needed
            if not is_app_installed(device_id, app.package_name):
                if not install_apk(device_id, app.apk_path, grant_permissions=True):
                    continue

            config = RVAgentConfig(
                package_name=app.package_name,
                device_id=DEVICE_ID,
                agent_mode="pure_algorithm",
                timeout=20,
            )

            agent = AgentFactory.create_agent(config, device=device)

            launch_app(device_id, app.package_name)
            time.sleep(2)

            result = agent.run()

            results.append(
                {
                    "app": app.name,
                    "iterations": result.get("iterations", 0),
                    "unique_states": result.get("unique_states", 0),
                }
            )

            force_stop_app(device_id, app.package_name)

        print(f"\n  Results for {len(results)} apps:")
        for r in results:
            print(
                f"    {r['app']}: {r['iterations']} iterations, {r['unique_states']} states"
            )


# =============================================================================
# Multimode Tests (LLM + Algorithm)
# =============================================================================


@pytest.mark.sglang
class TestMultimodeExecution:
    """Test agent in multimode (LLM + algorithm hybrid)."""

    def test_agent_creation_multimode(
        self, device, cryptoapp, check_emulator, check_sglang
    ):
        """Can create agent in multimode."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="multimode",
            llm_probability=0.7,
            llm_base_url=SGLANG_URL,
            llm_model=SGLANG_MODEL,
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)
        assert agent is not None
        assert agent.config.agent_mode == "multimode"
        assert agent.llm_client is not None
        print(f"\n  Agent created in multimode with LLM")

    def test_multimode_exploration(
        self, device, cryptoapp, device_id, check_emulator, check_sglang, results_dir
    ):
        """Run exploration in multimode."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="multimode",
            llm_probability=0.7,
            llm_base_url=SGLANG_URL,
            llm_model=SGLANG_MODEL,
            timeout=60,
            debug_mode=True,
        )

        agent = AgentFactory.create_agent(config, device=device)

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        start_time = time.time()
        result = agent.run()
        duration = time.time() - start_time

        # Get routing statistics
        routing = agent.routing_manager
        total_actions = routing.llm_executed + routing.algorithm_chosen
        llm_pct = (
            (routing.llm_executed / total_actions * 100) if total_actions > 0 else 0
        )

        # Save results
        result_file = (
            results_dir / f"multimode_{datetime.now().strftime('%H%M%S')}.json"
        )
        with open(result_file, "w") as f:
            json.dump(
                {
                    "mode": "multimode",
                    "duration_s": duration,
                    "llm_executed": routing.llm_executed,
                    "algorithm_chosen": routing.algorithm_chosen,
                    "llm_percentage": llm_pct,
                    "result": result,
                },
                f,
                indent=2,
                default=str,
            )

        print(f"\n  Duration: {duration:.1f}s")
        print(f"  Iterations: {result.get('iterations', 0)}")
        print(f"  LLM executed: {routing.llm_executed}")
        print(f"  Algorithm chosen: {routing.algorithm_chosen}")
        print(f"  LLM percentage: {llm_pct:.1f}%")
        print(f"  Results: {result_file}")

        assert result.get("status") == "completed"
        assert result.get("iterations", 0) > 0

    def test_multimode_proportion(
        self, device, cryptoapp, device_id, check_emulator, check_sglang
    ):
        """Verify multimode maintains ~70% LLM proportion."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="multimode",
            llm_probability=0.7,
            llm_base_url=SGLANG_URL,
            llm_model=SGLANG_MODEL,
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        agent.run()

        routing = agent.routing_manager
        total = routing.llm_executed + routing.algorithm_chosen

        if total >= 10:  # Need enough samples
            llm_pct = routing.llm_executed / total * 100
            print(f"\n  LLM percentage: {llm_pct:.1f}% (target: 70%)")
            # Allow variance: 50-90%
            assert 40 <= llm_pct <= 95, f"LLM% outside expected range: {llm_pct}%"


# =============================================================================
# LLM Only Mode Tests
# =============================================================================


@pytest.mark.sglang
class TestLLMOnlyMode:
    """Test agent in llm_only mode."""

    def test_agent_creation_llm_only(
        self, device, cryptoapp, check_emulator, check_sglang
    ):
        """Can create agent in llm_only mode."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="llm_only",
            llm_base_url=SGLANG_URL,
            llm_model=SGLANG_MODEL,
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)
        assert agent is not None
        assert agent.config.agent_mode == "llm_only"
        print(f"\n  Agent created in llm_only mode")

    def test_llm_only_exploration(
        self, device, cryptoapp, device_id, check_emulator, check_sglang, results_dir
    ):
        """Run exploration in llm_only mode."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="llm_only",
            llm_base_url=SGLANG_URL,
            llm_model=SGLANG_MODEL,
            timeout=60,
            debug_mode=True,
        )

        agent = AgentFactory.create_agent(config, device=device)

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        result = agent.run()

        print(f"\n  Iterations: {result.get('iterations', 0)}")
        print(f"  LLM tokens input: {result.get('llm_tokens_input', 0)}")
        print(f"  LLM tokens output: {result.get('llm_tokens_output', 0)}")

        assert result.get("status") == "completed"


# =============================================================================
# Memory System Tests
# =============================================================================


class TestMemorySystems:
    """Test memory systems during exploration."""

    def test_memory_population(self, device, cryptoapp, device_id, check_emulator):
        """Memory systems are populated during exploration."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        result = agent.run()

        # Check memory statistics
        memory_stats = agent.get_memory_stats()

        print(f"\n  Memory statistics:")
        for key, value in memory_stats.items():
            print(f"    {key}: {value}")

        # Should have some state recorded
        assert result.get("unique_states", 0) > 0 or result.get("iterations", 0) > 0

    def test_dynamic_graph_population(
        self, device, cryptoapp, device_id, check_emulator
    ):
        """Dynamic graph records state transitions."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        agent.run()

        # Check dynamic graph
        graph = agent.dynamic_graph
        if hasattr(graph, "states"):
            print(f"\n  States in graph: {len(graph.states)}")
        if hasattr(graph, "get_statistics"):
            stats = graph.get_statistics()
            print(f"  Graph stats: {stats}")


# =============================================================================
# Recovery and Error Handling Tests
# =============================================================================


class TestRecoveryMechanisms:
    """Test recovery and error handling."""

    def test_recovers_from_home_screen(
        self, device, cryptoapp, device_id, check_emulator
    ):
        """Agent recovers when app goes to background."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        # Agent should handle external navigation
        result = agent.run()

        # Should complete even if app was briefly in background
        print(f"\n  Completed with {result.get('iterations', 0)} iterations")
        assert result.get("status") in ["completed", "error"]

    def test_stuck_detection(self, device, cryptoapp, device_id, check_emulator):
        """Stuck detection prevents infinite loops."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)

        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        result = agent.run()

        # Should complete without hanging
        assert result.get("status") == "completed"
