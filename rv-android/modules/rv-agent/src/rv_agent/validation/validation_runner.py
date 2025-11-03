"""
Validation runner for offline validation.

Orchestrates the complete validation workflow: loading sequences, running
agent with mock device, collecting metrics, and generating reports.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent
from rv_agent.validation.sequence_loader import SequenceLoader, AppSequence
from rv_agent.validation.mock_device import MockDeviceInterface
from rv_agent.validation.metrics_collector import MetricsCollector
from rv_android_core.domain.static import StaticAnalysisData

logger = logging.getLogger(__name__)


class ValidationRunner:
    """
    Orchestrates offline validation workflow.

    Workflow:
    1. Load app sequence from dataset
    2. Initialize RVAgent with configuration
    3. Replace DeviceInterface with MockDeviceInterface
    4. Run agent for N iterations
    5. Collect metrics at each step
    6. Generate validation report

    This allows testing agent behavior without emulator using pre-captured
    screenshots and UI dumps.
    """

    def __init__(
        self,
        dataset_dir: Path,
        max_iterations: int = 25,
        device_dimensions: tuple[int, int] = (1080, 1920),
        optimized_dimensions: tuple[int, int] = (728, 1288)
    ):
        """
        Initialize validation runner.

        Args:
            dataset_dir: Directory containing app sequences
            max_iterations: Maximum iterations to run
            device_dimensions: Device screen dimensions
            optimized_dimensions: Optimized screenshot dimensions
        """
        self.dataset_dir = Path(dataset_dir)
        self.max_iterations = max_iterations
        self.device_dimensions = device_dimensions
        self.optimized_dimensions = optimized_dimensions

        # Load dataset
        self.loader = SequenceLoader(dataset_dir)

        logger.info(f"ValidationRunner initialized")
        logger.info(f"  Dataset: {dataset_dir}")
        logger.info(f"  Max iterations: {max_iterations}")

    def validate_app(
        self,
        app_name: str,
        strategy: str = "dfs",
        static_data: Optional[StaticAnalysisData] = None,
        output_path: Optional[Path] = None
    ) -> dict:
        """
        Run validation for a single app.

        Args:
            app_name: App name (directory name in dataset)
            strategy: Exploration strategy (dfs or bfs)
            static_data: Optional static analysis data
            output_path: Optional path to save results JSON

        Returns:
            Validation metrics as dictionary

        Raises:
            ValueError: If app not found or validation fails
        """
        logger.info("=" * 80)
        logger.info(f"🧪 VALIDATION: {app_name}")
        logger.info("=" * 80)

        # Load app sequence
        try:
            sequence = self.loader.load_app_sequence(app_name)
        except Exception as e:
            logger.error(f"Failed to load app sequence: {e}")
            raise

        # Create mock device
        mock_device = MockDeviceInterface(sequence, device_id="validation_mock")

        # Create metrics collector
        metrics_collector = MetricsCollector(app_name)

        # Create RVAgent configuration
        config = RVAgentConfig(
            package_name=sequence.package_name,
            device_id="validation_mock",
            strategy=strategy,
            timeout=9999,  # No timeout for validation
            device_dimensions=self.device_dimensions,
            optimized_dimensions=self.optimized_dimensions
        )

        # Initialize RVAgent with mock device injected
        try:
            agent = RVAgent(config, static_data=static_data, device=mock_device)

            # Update tool references to use mock device
            from rv_agent.llm.tools.android_tools import set_device_interface
            set_device_interface(mock_device)

            logger.info(f"✅ RVAgent initialized with mock device")

        except Exception as e:
            logger.error(f"Failed to initialize RVAgent: {e}", exc_info=True)
            raise

        # Run validation iterations
        try:
            self._run_validation_iterations(
                agent=agent,
                mock_device=mock_device,
                metrics_collector=metrics_collector,
                max_iterations=min(self.max_iterations, len(sequence.screens))
            )
        except Exception as e:
            logger.error(f"Validation run failed: {e}", exc_info=True)
            raise

        # Finalize metrics
        metrics_collector.finalize()

        # Collect memory/graph stats from agent
        metrics_collector.record_memory_stats(
            graph_states=len(agent.dynamic_graph.states),
            graph_transitions=len(agent.dynamic_graph.transitions),
            long_term_patterns=0,  # TODO: Extract from long_term memory
            short_term_iterations=len(agent.short_term.iterations)
        )

        # Get final metrics
        validation_metrics = metrics_collector.get_metrics().to_dict()

        # Add device action summary
        action_summary = mock_device.get_action_summary()
        validation_metrics['device_actions'] = action_summary

        # Save to file if requested
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(validation_metrics, f, indent=2)

            logger.info(f"📄 Validation report saved: {output_path}")

        # Print summary
        self._print_summary(validation_metrics)

        return validation_metrics

    def _run_validation_iterations(
        self,
        agent: RVAgent,
        mock_device: MockDeviceInterface,
        metrics_collector: MetricsCollector,
        max_iterations: int
    ):
        """
        Run validation iterations manually.

        Instead of calling agent.run(), we manually invoke the graph for each
        iteration so we can collect detailed metrics.

        Args:
            agent: RVAgent instance
            mock_device: Mock device interface
            metrics_collector: Metrics collector
            max_iterations: Maximum iterations to run
        """
        logger.info(f"🚀 Starting validation iterations (max: {max_iterations})")

        # Initialize persistent state across iterations
        visited_states = set()
        state_transitions = {}

        # Initial summaries (will be updated after each iteration)
        action_history_summary = "No previous actions."
        exploration_summary = "Starting exploration."
        memory_insights = "No insights yet."
        navigation_path = "Starting navigation."

        for iteration in range(max_iterations):
            logger.info(f"\n{'='*60}")
            logger.info(f"ITERATION {iteration + 1}/{max_iterations}")
            logger.info(f"Step: {mock_device.get_current_step()}/{mock_device.get_sequence_length()}")
            logger.info(f"{'='*60}")

            try:
                # Create state for this iteration (STATELESS - summaries from previous iteration)
                state = {
                    # LangChain messages for tool calling (V5 - fresh each iteration)
                    "messages": [],

                    # Memory summaries (pre-formatted strings from previous iteration)
                    "action_history_summary": action_history_summary,
                    "exploration_summary": exploration_summary,
                    "memory_insights": memory_insights,
                    "navigation_path": navigation_path,

                    # Screen observation state (will be updated by observe node)
                    "screenshot_b64": "",
                    "current_screen_hash": "",
                    "current_activity": "",
                    "screen_description": None,

                    # Exploration state (accumulated across iterations)
                    "strategy_name": agent.config.strategy,
                    "iteration": iteration,
                    "should_continue": True,
                    "visited_states": visited_states,
                    "state_transitions": state_transitions,

                    # Timing and termination
                    "start_time": metrics_collector.metrics.start_time,
                    "timeout": 9999,

                    # Coordinate conversion
                    "device_dimensions": self.device_dimensions,
                    "optimized_dimensions": self.optimized_dimensions,

                    # App retention tracking
                    "external_navigation_count": 0,
                    "is_external": False,

                    # LLM usage tracking (will be updated by assistant node)
                    "llm_tokens_input": 0,
                    "llm_tokens_output": 0,
                    "llm_time_ms": 0.0,

                    # V7 Retry Mechanism Parameters
                    "retry_count": 0,
                    "max_retries": 2,
                    "last_action_success": True,
                    "retry_reason": "",

                    # V7 Sampling Parameters (progressive sampling on retry)
                    "sampling_temperature": 0.1,
                    "sampling_top_p": 0.9,
                    "sampling_top_k": 40,

                    # Transient action (will be set by assistant node)
                    "current_action": None,

                    # Injected dependencies
                    "_device": mock_device,
                    "_parser": agent.parser,
                    "_static_data": agent.static_data,
                    "_strategy": agent.strategy,
                    "_long_term": agent.long_term,
                    "_short_term": agent.short_term,
                    "_ui_coverage": agent.ui_coverage,
                    "_graph": agent.dynamic_graph,
                    "_converter": agent.converter,
                    "_package_name": agent.config.package_name
                }

                # Log MockDevice state BEFORE graph invocation
                actions_before = len(mock_device.actions_executed)
                logger.debug(f"🔍 BEFORE graph invocation:")
                logger.debug(f"   MockDevice.actions_executed: {actions_before}")

                # Invoke graph for ONE iteration
                final_state = agent.graph.invoke(state)

                # Log MockDevice state AFTER graph invocation
                actions_after = len(mock_device.actions_executed)
                logger.debug(f"🔍 AFTER graph invocation:")
                logger.debug(f"   MockDevice.actions_executed: {actions_after}")
                logger.debug(f"   New actions: {actions_after - actions_before}")

                # Update summaries for next iteration (stateless - extract from final_state)
                action_history_summary = final_state.get("action_history_summary", action_history_summary)
                exploration_summary = final_state.get("exploration_summary", exploration_summary)
                memory_insights = final_state.get("memory_insights", memory_insights)
                navigation_path = final_state.get("navigation_path", navigation_path)

                # Update persistent exploration state
                visited_states = final_state.get("visited_states", visited_states)
                state_transitions = final_state.get("state_transitions", state_transitions)

                # Extract metrics from final state
                screen_hash = final_state.get('current_screen_hash', 'unknown')
                activity = final_state.get('current_activity', 'unknown')

                # Get element types from validator
                element_types = mock_device.validator.get_element_type_distribution()
                element_count = len(mock_device.validator.current_elements)

                # Get action info from mock device
                action_summary = mock_device.get_action_summary()
                last_action = action_summary['actions'][-1] if action_summary['actions'] else None

                action_type = last_action['action_type'] if last_action else 'UNKNOWN'
                valid_action = last_action['valid'] if last_action else False

                # Log action_type determination for debugging
                logger.debug(f"🎯 ACTION_TYPE DETERMINATION:")
                logger.debug(f"   last_action exists: {last_action is not None}")
                logger.debug(f"   action_type: {action_type}")
                logger.debug(f"   valid_action: {valid_action}")
                if last_action:
                    logger.debug(f"   last_action details: step={last_action.get('step')}, "
                               f"reason={last_action.get('reason')}")

                # Extract token metrics from state (stateless architecture)
                tokens_input = final_state.get('llm_tokens_input', 0)
                tokens_output = final_state.get('llm_tokens_output', 0)
                llm_time_ms = final_state.get('llm_time_ms', 0.0)

                # Record iteration metrics
                metrics_collector.record_iteration(
                    iteration=iteration + 1,
                    action_type=action_type,
                    valid_action=valid_action,
                    screen_hash=screen_hash,
                    activity=activity,
                    element_count=element_count,
                    element_types=element_types,
                    message_count=1,  # Always 1 in stateless mode (fresh message each time)
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    llm_time_ms=llm_time_ms
                )

                logger.info(f"✅ Iteration {iteration + 1} completed")

            except Exception as e:
                logger.error(f"❌ Iteration {iteration + 1} failed: {e}", exc_info=True)
                # Continue to next iteration on error
                continue

        logger.info(f"\n🏁 Validation completed: {max_iterations} iterations")

    def _print_summary(self, metrics: dict):
        """
        Print validation summary.

        Args:
            metrics: Validation metrics dictionary
        """
        logger.info("\n" + "=" * 80)
        logger.info("📊 VALIDATION SUMMARY")
        logger.info("=" * 80)

        logger.info(f"\n🎯 Execution:")
        logger.info(f"  Duration: {metrics['execution_time_s']:.1f}s")
        logger.info(f"  Iterations: {metrics['total_iterations']}")

        logger.info(f"\n⚡ Actions:")
        logger.info(f"  Valid: {metrics['actions']['valid']}")
        logger.info(f"  Invalid: {metrics['actions']['invalid']}")
        logger.info(f"  Valid rate: {metrics['actions']['valid_rate'] * 100:.1f}%")
        logger.info(f"  By type:")
        for action, count in metrics['actions']['by_type'].items():
            logger.info(f"    {action}: {count}")

        logger.info(f"\n🎨 Element Coverage:")
        logger.info(f"  Types seen: {len(metrics['element_coverage']['types_seen'])}")
        logger.info(f"  Types: {', '.join(metrics['element_coverage']['types_seen'])}")

        logger.info(f"\n🗺️  Exploration:")
        logger.info(f"  Unique screens: {metrics['exploration']['unique_screens']}")
        logger.info(f"  Activities: {len(metrics['exploration']['activities'])}")
        logger.info(f"  Revisit rate: {metrics['exploration']['revisit_rate'] * 100:.1f}%")

        logger.info(f"\n🧠 Memory/Graph:")
        logger.info(f"  Graph states: {metrics['memory_graph']['graph_states']}")
        logger.info(f"  Graph transitions: {metrics['memory_graph']['graph_transitions']}")
        logger.info(f"  Short-term iterations: {metrics['memory_graph']['short_term_iterations']}")

        logger.info(f"\n🤖 LLM:")
        logger.info(f"  Total tokens: {metrics['llm']['total_tokens']}")
        logger.info(f"  Avg tokens/iteration: {metrics['llm']['avg_tokens_per_iteration']:.1f}")
        logger.info(f"  Max messages: {metrics['llm']['max_message_count']}")

        logger.info("=" * 80 + "\n")

    def validate_all_apps(
        self,
        strategy: str = "dfs",
        output_dir: Optional[Path] = None
    ) -> dict:
        """
        Run validation for all apps in dataset.

        Args:
            strategy: Exploration strategy
            output_dir: Optional directory to save individual reports

        Returns:
            Dictionary mapping app names to validation metrics
        """
        apps = self.loader.list_apps()
        results = {}

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        for app_name in apps:
            try:
                output_path = output_dir / f"{app_name}_validation.json" if output_dir else None
                metrics = self.validate_app(app_name, strategy=strategy, output_path=output_path)
                results[app_name] = metrics
            except Exception as e:
                logger.error(f"Failed to validate {app_name}: {e}")
                results[app_name] = {'error': str(e)}

        logger.info(f"\n🎉 Validated {len(results)} apps")

        return results
