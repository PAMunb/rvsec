# rvandroid/llm/evaluator/evaluator.py
"""
Main LLM evaluation system for comparing model configurations.

This module provides the core evaluation engine for systematically testing
different LLM models, strategies, and parameters using fixed prompts.

### Architectural Decisions:
- Implements a systematic evaluation framework for LLM configuration comparison
- Leverages existing RV-Android components (OllamaLLM, ComponentConfigurator, ResponseProcessor)
- Provides isolated testing environment independent of full testing framework
- Uses hardcoded configuration for simplicity and reproducibility
- Groups execution by model to minimize GPU memory management overhead
- Implements comprehensive error handling and timeout mechanisms

### Role in the System:
- Acts as the primary evaluation engine for LLM configuration optimization
- Provides systematic comparison of models, strategies, and parameters
- Generates comprehensive metrics for performance and quality analysis
- Serves as a preliminary screening tool before full framework evaluation
- Enables data-driven selection of optimal LLM configurations

### Key Considerations:
- GPU memory constraint (8GB) requires careful model sequencing
- Statistical significance achieved through multiple repetitions per configuration
- Warm-up runs ensure consistent performance measurement
- Timeout mechanisms prevent hanging on problematic configurations
- Comprehensive error tracking enables debugging of configuration issues
- Results exported for detailed analysis and decision making
"""

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Dict, List, Any, Optional, Tuple

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm import LLMTextContent, LLMRole, LLMMessage, LLMConfig, LLMResponse, LanguageModel, LLMImageContent
from rv_llm.factories import LLMComponentFactory
from rv_llm.llm.constants import LLMType
from .config import (
    MODELS_TO_TEST, REPETITIONS_PER_CONFIG, WARMUP_RUNS,
    GENERATION_TIMEOUT, get_prompt_pairs, generate_all_configurations
)
from .export import ResultsExporter
from .metrics import MetricsCollector, StatisticsCalculator


class LLMEvaluator:
    """
    Main LLM evaluation system for comprehensive configuration testing.

    Coordinates the systematic evaluation of different LLM configurations
    including models, strategies, parameters, and prompts. Provides statistical
    analysis and comprehensive reporting of results.
    """

    def __init__(self, prompts_dir: str = "./prompts", output_dir: str = "."):
        """
        Initialize the LLM evaluator.

        Args:
            prompts_dir: Directory containing prompt files (optional)
            output_dir: Directory for output files
        """
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.evaluator",
            {CONTEXT_COMPONENT: "LLMEvaluator"}
        )

        # Initialize configuration
        self.prompts_dir = prompts_dir
        self.output_dir = output_dir

        # Initialize components
        self.metrics_collector = MetricsCollector()
        self.statistics_calculator = StatisticsCalculator()
        self.results_exporter = ResultsExporter(output_dir)

        # Load prompt pairs
        try:
            self.prompt_pairs = get_prompt_pairs(prompts_dir)
            self.logger.info(f"Loaded {len(self.prompt_pairs)} prompt pairs")
        except Exception as e:
            self.logger.error(f"Failed to load prompts: {e}")
            raise

        # Storage for results
        self.detailed_results: List[Dict[str, Any]] = []
        self.summary_results: List[Dict[str, Any]] = []

        # Current model state
        # self.current_model = None
        self.llm: LanguageModel = None
        # self.config = None
        # self.current_response_processor = None

        self.logger.info("LLM Evaluator initialized successfully")

    def run_evaluation(self) -> Tuple[str, str, str]:
        """
        Run the complete evaluation process.

        Executes systematic evaluation of all configurations and generates
        comprehensive results including detailed data, summaries, and analysis.

        Returns:
            Tuple of (detailed_file_path, summary_file_path, analysis_file_path)
        """
        self.logger.info("Starting comprehensive LLM evaluation")
        start_time = time.time()

        try:
            # Generate all configurations to test
            configurations = generate_all_configurations()
            print(f"configurations={configurations}")
            total_configs = len(configurations)
            total_runs = total_configs * len(self.prompt_pairs) * REPETITIONS_PER_CONFIG

            self.logger.info(f"Evaluation plan:")
            self.logger.info(f"  - {len(MODELS_TO_TEST)} models")
            self.logger.info(f"  - {total_configs} total configurations")
            self.logger.info(f"  - {len(self.prompt_pairs)} prompt pairs")
            self.logger.info(f"  - {REPETITIONS_PER_CONFIG} repetitions per config")
            self.logger.info(f"  - {total_runs} total runs (excluding warm-up)")

            # Group configurations by model for efficient execution
            model_groups = self._group_configurations_by_model(configurations)

            # Execute evaluation by model groups
            for model_name, model_configs in model_groups.items():
                self._evaluate_model_group(model_name, model_configs)

            # Calculate summary statistics
            self._calculate_summary_statistics()

            # Export results
            file_paths = self.results_exporter.export_all_results(
                self.detailed_results, self.summary_results
            )

            # Log completion
            elapsed_time = time.time() - start_time
            self.logger.info(f"Evaluation completed in {elapsed_time:.1f} seconds")
            self.logger.info(f"Generated {len(self.detailed_results)} detailed results")
            self.logger.info(f"Generated {len(self.summary_results)} summary results")

            return file_paths

        except Exception as e:
            self.logger.error(f"Evaluation failed: {e}", exc_info=True)
            raise
        finally:
            # Clean up current model if loaded
            self._cleanup_current_model()

    def _group_configurations_by_model(self, configurations: List[LLMConfig]) -> Dict[str, List[LLMConfig]]:
        """
        Group configurations by model to minimize model loading overhead.

        Args:
            configurations: List of all configurations

        Returns:
            Dictionary mapping model names to their configurations
        """
        model_groups = {}

        for config in configurations:
            model = config.model
            if model not in model_groups:
                model_groups[model] = []
            model_groups[model].append(config)

        return model_groups

    def _evaluate_model_group(self, model_name: str, configurations: List[LLMConfig]) -> None:
        """
        Evaluate all configurations for a specific model.

        Args:
            model_name: Name of the model to evaluate
            configurations: List of configurations for this model
        """
        self.logger.info(f"Starting evaluation for model: {model_name}")
        self.logger.info(f"  - {len(configurations)} configurations to test")

        try:
            # Initialize model and components
            self._initialize_model(model_name)

            # Perform warm-up runs
            self._perform_warmup(configurations[0])

            # Evaluate each configuration
            for i, config in enumerate(configurations, 1):
                self.logger.info(f"Evaluating configuration {i}/{len(configurations)}: {self._format_config(config)}")
                self._evaluate_configuration(config)

        except Exception as e:
            self.logger.error(f"Error evaluating model {model_name}: {e}", exc_info=True)
        finally:
            # Clean up model resources
            self._cleanup_current_model()

    def _initialize_model(self, model_name: str) -> None:
        """
        Initialize model and associated components.

        Args:
            model_name: Name of the model to initialize
        """
        self.logger.info(f"Initializing model: {model_name}")

        try:
            # Create config for this model
            config = LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=model_name,
                temperature=0.2,
                max_tokens=800
            )

            self.llm = LLMComponentFactory.create_llm(config)

            # # Create response processor
            # self.current_response_processor = ResponseProcessor(self.current_configurator)
            #
            # self.current_model = model_name
            self.logger.info(f"Model {model_name} initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize model {model_name}: {e}")
            raise

    def _perform_warmup(self, sample_config: LLMConfig) -> None:
        """
        Perform warm-up runs to stabilize model performance.

        Args:
            sample_config: Sample configuration for warm-up
        """
        self.logger.info(f"Performing {WARMUP_RUNS} warm-up runs")

        if not self.prompt_pairs:
            self.logger.warning("No prompts available for warm-up")
            return

        # Use first prompt pair for warm-up
        prompt_id, system_file, user_file, image_file = self.prompt_pairs[0]

        for i in range(WARMUP_RUNS):
            try:
                self._execute_single_run(sample_config, prompt_id, system_file, user_file, image_file, is_warmup=True)
                self.logger.debug(f"Warm-up run {i + 1}/{WARMUP_RUNS} completed")
            except Exception as e:
                self.logger.warning(f"Warm-up run {i + 1} failed: {e}")

    def _evaluate_configuration(self, config: LLMConfig) -> None:
        """
        Evaluate a single configuration across all prompts and repetitions.

        Args:
            config: Configuration dictionary to evaluate
        """
        config_results = []

        # Test each prompt pair
        for prompt_id, system_file, user_file, image_file in self.prompt_pairs:
            self.logger.debug(f"Testing prompt {prompt_id}")

            # Run multiple repetitions for statistical significance
            for run_number in range(1, REPETITIONS_PER_CONFIG + 1):
                try:
                    result = self._execute_single_run(config, prompt_id, system_file, user_file, image_file, run_number)
                    config_results.append(result)
                    self.detailed_results.append(result)

                except Exception as e:
                    self.logger.error(
                        f"Run failed for config {self._format_config(config)}, prompt {prompt_id}, run {run_number}: {e}")

                    # Create error result
                    error_result = self._create_error_result(config, prompt_id, run_number, str(e))
                    config_results.append(error_result)
                    self.detailed_results.append(error_result)

        self.logger.debug(f"Configuration completed: {len(config_results)} results collected")

    def _execute_single_run(self,
                            config: LLMConfig,
                            prompt_id: str,
                            system_file: str,
                            user_file: str,
                            image_file: str,
                            run_number: int = 1,
                            is_warmup: bool = False) -> Optional[Dict[str, Any]]:
        """
        Execute a single evaluation run.

        Args:
            config: Configuration to test
            prompt_id: Prompt identifier
            system_file: Path to system prompt file
            user_file: Path to user prompt file
            run_number: Run number for this configuration
            is_warmup: Whether this is a warm-up run

        Returns:
            Result dictionary or None for warm-up runs
        """
        start_time = time.time()

        try:
            # Load prompts
            system_prompt, user_prompt, image_prompt = self._load_prompts(system_file, user_file, image_file)

            # Create messages
            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=[LLMTextContent(text=system_prompt)]),
                LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text=user_prompt)])
            ]

            if config.vision:
                messages.append(LLMMessage(role=LLMRole.USER, content=[LLMImageContent(url=image_file, encoded_string=image_prompt)]))

            # Execute with timeout
            response, parsed_actions, parsing_errors = self._execute_with_timeout(messages, config)

            execution_time = time.time() - start_time

            # Don't collect metrics for warm-up runs
            if is_warmup:
                return None

            # Collect metrics
            metrics = self.metrics_collector.collect_run_metrics(
                response=response,
                parsed_actions=parsed_actions,
                parsing_errors=parsing_errors,
                execution_time=execution_time
            )

            # Add configuration information
            result = {
                **config,
                'prompt_id': prompt_id,
                'run_number': run_number,
                **metrics
            }

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Single run execution failed: {e}")

            if is_warmup:
                return None

            # Return error result for non-warm-up runs
            return self._create_error_result(config, prompt_id, run_number, str(e), execution_time)

    def _load_prompts(self, system_file: str, user_file: str, image_file: str) -> Tuple[str, str, str]:
        """
        Load system and user prompts from files.

        Args:
            system_file: Path to system prompt file
            user_file: Path to user prompt file

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        try:
            with open(system_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read().strip()

            with open(user_file, 'r', encoding='utf-8') as f:
                user_prompt = f.read().strip()

            with open(image_file, 'r', encoding='utf-8') as f:
                image_prompt = f.read().strip()

            return system_prompt, user_prompt, image_prompt

        except Exception as e:
            self.logger.error(f"Failed to load prompts from {system_file}, {user_file}: {e}")
            raise

    def _execute_with_timeout(self, messages: List[LLMMessage], config: LLMConfig) -> Tuple[
        Optional[LLMResponse], List[Dict[str, Any]], List[str]]:
        """
        Execute LLM generation with timeout protection.

        Args:
            messages: List of messages to send to LLM

        Returns:
            Tuple of (response, parsed_actions, parsing_errors)
        """

        def _generate():
            try:
                # Create LLM instance and generate response
                response = self.llm.generate(messages, config)

                # Process response
                parsed_actions, parsing_errors = self.current_response_processor.process_response(
                    response.content, {}  # Empty state for parsing
                )

                return response, parsed_actions, parsing_errors

            except Exception as e:
                self.logger.error(f"Generation error: {e}")
                raise

        # Execute with timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_generate)

            try:
                result = future.result(timeout=GENERATION_TIMEOUT)
                return result

            except TimeoutError:
                self.logger.warning(f"Generation timed out after {GENERATION_TIMEOUT} seconds")

                # Create timeout error info
                error_info = {"type": "timeout", "timeout": True}
                return None, [], [f"Generation timed out after {GENERATION_TIMEOUT} seconds"]

            except Exception as e:
                self.logger.error(f"Generation failed: {e}")
                return None, [], [f"Generation failed: {str(e)}"]

    def _create_error_result(self,
                             config: LLMConfig,
                             prompt_id: str,
                             run_number: int,
                             error_message: str,
                             execution_time: float = 0.0) -> Dict[str, Any]:
        """
        Create a result dictionary for failed runs.

        Args:
            config: Configuration that failed
            prompt_id: Prompt identifier
            run_number: Run number
            error_message: Error message
            execution_time: Time taken before failure

        Returns:
            Error result dictionary
        """
        # Determine error type
        error_type = "unknown"
        timeout_occurred = False

        if "timeout" in error_message.lower():
            error_type = "timeout"
            timeout_occurred = True
        elif "memory" in error_message.lower():
            error_type = "memory"
        elif "model" in error_message.lower():
            error_type = "model_error"
        elif "parsing" in error_message.lower():
            errr_type = "parsing"

        # Create error info
        error_info = {
            "type": error_type,
            "timeout": timeout_occurred,
            "message": error_message
        }

        # Collect metrics for error case
        metrics = self.metrics_collector.collect_run_metrics(
            response=None,
            parsed_actions=[],
            parsing_errors=[error_message],
            error_info=error_info,
            execution_time=execution_time
        )

        # Create result
        result = {
            **config.to_dict(),
            'prompt_id': prompt_id,
            'run_number': run_number,
            **metrics
        }

        return result

    def _calculate_summary_statistics(self) -> None:
        """Calculate summary statistics for each unique configuration."""
        self.logger.info("Calculating summary statistics")

        # Group results by configuration
        config_groups = {}

        for result in self.detailed_results:
            # Create configuration key
            config_key = (
                result['model'],
                result['prompt_id'],
                result['temperature'],
                result['top_p'],
                result['max_tokens'],
                result['top_k']
            )

            if config_key not in config_groups:
                config_groups[config_key] = []
            config_groups[config_key].append(result)

        # Calculate statistics for each group
        for config_key, runs in config_groups.items():
            summary = self.statistics_calculator.calculate_summary_statistics(runs)

            # Add configuration information
            summary.update({
                'model': config_key[0],
                'prompt_id': config_key[1],
                'temperature': config_key[2],
                'top_p': config_key[3],
                'max_tokens': config_key[4],
                'top_k': config_key[5],
                'total_runs': len(runs)
            })

            self.summary_results.append(summary)

        self.logger.info(f"Generated {len(self.summary_results)} configuration summaries")

    def _cleanup_current_model(self) -> None:
        """Clean up current model resources."""
        if self.llm:
            try:
                self.llm.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up model: {e}")

        self.current_model = None
        self.config = None
        # self.current_response_processor = None

    def _format_config(self, config: LLMConfig) -> str:
        """
        Format configuration for logging.

        Args:
            config: Configuration dictionary

        Returns:
            Formatted configuration string
        """
        return f"{config['model']}|{config['strategy']}|T={config['temperature']}|p={config['top_p']}|max={config['max_tokens']}"

    def get_evaluation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the evaluation results.

        Returns:
            Summary dictionary with key statistics
        """
        if not self.summary_results:
            return {"status": "no_results"}

        # Sort by overall score
        sorted_results = sorted(self.summary_results,
                                key=lambda x: x.get('overall_score', 0),
                                reverse=True)

        best_config = sorted_results[0]

        return {
            "status": "completed",
            "total_configurations": len(self.summary_results),
            "total_runs": len(self.detailed_results),
            "best_configuration": {
                "model": best_config.get('model'),
                "strategy": best_config.get('strategy'),
                "temperature": best_config.get('temperature'),
                "overall_score": best_config.get('overall_score', 0),
                "success_rate": best_config.get('overall_success_rate', 0)
            },
            "average_success_rate": sum(r.get('overall_success_rate', 0) for r in self.summary_results) / len(
                self.summary_results),
            "models_tested": list(set(r.get('model') for r in self.summary_results)),
            "strategies_tested": list(set(r.get('strategy') for r in self.summary_results))
        }
