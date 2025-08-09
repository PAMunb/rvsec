# rv_evaluator/evaluator.py
"""
Provides the main LLM evaluation engine.

This module contains the LLMEvaluator class, which orchestrates the systematic
testing of different LLM configurations (models, parameters, prompts). It manages
the evaluation lifecycle, from configuration generation to results collection
and summary reporting.
"""

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Dict, List, Any, Optional, Tuple

from anyio import sleep

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
    Coordinates the systematic evaluation of LLM configurations.

    This class manages the entire evaluation process, including setting up test
    runs, executing them, collecting performance and success metrics, and
    generating final reports.
    """

    def __init__(self, prompts_dir: str = "./prompts", output_dir: str = "."):
        """
        Initializes the LLMEvaluator.

        Args:
            prompts_dir: The directory where prompt files are located.
            output_dir: The directory where results and reports will be saved.
        """
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.evaluator",
            {CONTEXT_COMPONENT: "LLMEvaluator"}
        )

        self.prompts_dir = prompts_dir
        self.output_dir = output_dir

        self.metrics_collector = MetricsCollector()
        self.statistics_calculator = StatisticsCalculator()
        self.results_exporter = ResultsExporter(output_dir)

        try:
            self.prompt_pairs = get_prompt_pairs(prompts_dir)
            self.logger.info(f"Loaded {len(self.prompt_pairs)} prompt pairs.")
        except Exception as e:
            self.logger.error(f"Failed to load prompts: {e}", exc_info=True)
            raise

        self.detailed_results: List[Dict[str, Any]] = []
        self.summary_results: List[Dict[str, Any]] = []
        self.llm: Optional[LanguageModel] = None
        self.current_response_processor = None

        self.logger.info("LLM Evaluator initialized successfully.")

    def run_evaluation(self) -> Tuple[str, str, str]:
        """
        Runs the complete evaluation across all configured models and prompts.

        Returns:
            A tuple containing the file paths for the detailed results,
            summary results, and the analysis report.
        """
        self.logger.info("Starting comprehensive LLM evaluation.")
        start_time = time.time()

        try:
            configurations = generate_all_configurations()
            total_configs = len(configurations)
            total_runs = total_configs * len(self.prompt_pairs) * REPETITIONS_PER_CONFIG

            self.logger.info("Evaluation Plan:")
            self.logger.info(f"  - Models: {len(MODELS_TO_TEST)}")
            self.logger.info(f"  - Total Configurations: {total_configs}")
            self.logger.info(f"  - Prompt Pairs: {len(self.prompt_pairs)}")
            self.logger.info(f"  - Repetitions per Config: {REPETITIONS_PER_CONFIG}")
            self.logger.info(f"  - Total Runs: {total_runs} (excluding warm-up)")

            model_groups = self._group_configurations_by_model(configurations)

            for model_name, model_configs in model_groups.items():
                self._evaluate_model_group(model_name, model_configs)

            self._calculate_summary_statistics()

            file_paths = self.results_exporter.export_all_results(
                self.detailed_results, self.summary_results
            )

            elapsed_time = time.time() - start_time
            self.logger.info(f"Evaluation completed in {elapsed_time:.1f} seconds.")
            self.logger.info(f"Generated {len(self.detailed_results)} detailed results.")
            self.logger.info(f"Generated {len(self.summary_results)} summary results.")

            return file_paths

        except Exception as e:
            self.logger.error(f"Evaluation failed: {e}", exc_info=True)
            raise
        finally:
            self._cleanup_current_model()

    def _group_configurations_by_model(self, configurations: List[LLMConfig]) -> Dict[str, List[LLMConfig]]:
        """Groups configurations by model to minimize model loading overhead."""
        model_groups = {}
        for config in configurations:
            model = config.model
            if model not in model_groups:
                model_groups[model] = []
            model_groups[model].append(config)
        return model_groups

    def _evaluate_model_group(self, model_name: str, configurations: List[LLMConfig]) -> None:
        """
        Evaluates all configurations for a single model.

        Args:
            model_name: The name of the model to evaluate.
            configurations: The list of configurations for this model.
        """
        self.logger.info(f"Starting evaluation for model: {model_name}")
        self.logger.info(f"  - {len(configurations)} configurations to test.")

        try:
            self._initialize_model(model_name)
            self._perform_warmup(configurations[0])
            print("************* dormindo 5sec ...")
            time.sleep(5.0)
            print("************* acordou!!!")


            for i, config in enumerate(configurations, 1):
                self.logger.info(f"Evaluating configuration {i}/{len(configurations)}: {self._format_config(config)}")
                self._evaluate_configuration(config)

        except Exception as e:
            self.logger.error(f"Error evaluating model {model_name}: {e}", exc_info=True)
        finally:
            self._cleanup_current_model()
            print("************* dormindo 40sec ...")
            time.sleep(40.0)
            print("************* acordou!!!")

    def _initialize_model(self, model_name: str) -> None:
        """
        Initializes the language model and associated components.

        Args:
            model_name: The name of the model to initialize.
        """
        self.logger.info(f"Initializing model: {model_name}")
        try:
            config = LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=model_name,
                temperature=0.2, # Default, will be overridden by specific config
                max_tokens=800 # Default, will be overridden
            )
            self.llm = LLMComponentFactory.create_llm(config)

            from rvandroid_tool.llm.service.response_processor import ResponseProcessor
            self.current_response_processor = ResponseProcessor(config=config)
            self.logger.info(f"Model {model_name} initialized successfully.")

        except Exception as e:
            self.logger.error(f"Failed to initialize model {model_name}: {e}", exc_info=True)
            raise

    def _perform_warmup(self, sample_config: LLMConfig) -> None:
        """
        Performs warm-up runs to stabilize model performance measurements.

        Args:
            sample_config: A sample configuration to use for the warm-up.
        """
        self.logger.info(f"Performing {WARMUP_RUNS} warm-up runs.")
        if not self.prompt_pairs:
            self.logger.warning("No prompts available for warm-up, skipping.")
            return

        prompt_id, system_file, user_file, image_file = self.prompt_pairs[0]

        for i in range(WARMUP_RUNS):
            try:
                self._execute_single_run(sample_config, prompt_id, system_file, user_file, image_file, is_warmup=True)
                self.logger.debug(f"Warm-up run {i + 1}/{WARMUP_RUNS} completed.")
            except Exception as e:
                self.logger.warning(f"Warm-up run {i + 1} failed: {e}")

    def _evaluate_configuration(self, config: LLMConfig) -> None:
        """
        Evaluates a single configuration across all prompts and repetitions.

        Args:
            config: The LLM configuration to evaluate.
        """
        for prompt_id, system_file, user_file, image_file in self.prompt_pairs:
            self.logger.debug(f"Testing prompt {prompt_id} with config: {self._format_config(config)}")

            for run_number in range(1, REPETITIONS_PER_CONFIG + 1):
                try:
                    result = self._execute_single_run(config, prompt_id, system_file, user_file, image_file, run_number)
                    if result:
                        self.detailed_results.append(result)
                except Exception as e:
                    self.logger.error(
                        f"Run failed for config {self._format_config(config)}, prompt {prompt_id}, run {run_number}: {e}",
                        exc_info=True
                    )
                    error_result = self._create_error_result(config, prompt_id, run_number, str(e))
                    self.detailed_results.append(error_result)

    def _execute_single_run(self,
                            config: LLMConfig,
                            prompt_id: str,
                            system_file: str,
                            user_file: str,
                            image_file: Optional[str],
                            run_number: int = 1,
                            is_warmup: bool = False) -> Optional[Dict[str, Any]]:
        """
        Executes a single evaluation run and collects metrics.

        Args:
            config: The configuration to test.
            prompt_id: The identifier for the prompt being used.
            system_file: Path to the system prompt file.
            user_file: Path to the user prompt file.
            image_file: Path to the image file (optional).
            run_number: The repetition number for this run.
            is_warmup: Flag indicating if this is a warm-up run.

        Returns:
            A dictionary with the results, or None for warm-up runs.
        """
        start_time = time.time()
        self.logger.debug(f"Starting single run for prompt {prompt_id}")
        response, parsed_actions, parsing_errors, error_info = None, [], [], None

        try:
            system_prompt, user_prompt, image_prompt = self._load_prompts(system_file, user_file, image_file)

            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=[LLMTextContent(text=system_prompt)]),
                LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text=user_prompt)])
            ]
            if config.vision and image_prompt:
                messages = [
                    LLMMessage(role=LLMRole.SYSTEM, content=[LLMTextContent(text=system_prompt)]),
                    LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text=user_prompt),
                                                           LLMImageContent(url=image_file, encoded_string=image_prompt)])
                ]

            response, parsed_actions, parsing_errors, error_info = self._execute_with_timeout(messages, config)

            if response:
                self.logger.debug(f"LLM response received: tokens_in={response.input_tokens}, tokens_out={response.output_tokens}, total_duration={response.total_duration}")

        except Exception as e:
            self.logger.error(f"Single run execution failed: {e}", exc_info=True)
            error_info = {"type": "execution_error", "timeout": False, "message": str(e)}

        execution_time = time.time() - start_time
        self.logger.debug(f"Single run completed in {execution_time:.3f}s")

        if is_warmup:
            return None

        metrics = self.metrics_collector.collect_run_metrics(
            response=response,
            parsed_actions=parsed_actions,
            parsing_errors=parsing_errors,
            error_info=error_info,
            execution_time=execution_time
        )

        result = {
            **config.to_dict(),
            'prompt_id': prompt_id,
            'run_number': run_number,
            **metrics
        }
        return result

    def _load_prompts(self, system_file: str, user_file: str, image_file: Optional[str]) -> Tuple[str, str, Optional[str]]:
        """
        Loads prompt content from files.

        Args:
            system_file: Path to the system prompt file.
            user_file: Path to the user prompt file.
            image_file: Path to the image file (optional).

        Returns:
            A tuple of (system_prompt, user_prompt, image_data).
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
            self.logger.error(f"Failed to load prompts: {e}", exc_info=True)
            raise

    def _execute_with_timeout(self, messages: List[LLMMessage], config: LLMConfig) -> Tuple[
        Optional[LLMResponse], List[Dict[str, Any]], List[str], Optional[Dict[str, Any]]]:
        """
        Executes the LLM generation and parsing with a timeout.

        Args:
            messages: The list of messages to send to the LLM.
            config: The LLM configuration for this run.

        Returns:
            A tuple of (response, parsed_actions, parsing_errors, error_info).
        """
        def _generate_and_process():
            response = self.llm.generate(messages, config)
            parsed_actions, parsing_errors = self.current_response_processor.process_response(
                response.content, {}
            )
            return response, parsed_actions, parsing_errors, None

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_generate_and_process)
            try:
                return future.result(timeout=GENERATION_TIMEOUT)
            except TimeoutError:
                msg = f"Generation timed out after {GENERATION_TIMEOUT} seconds."
                self.logger.warning(msg)
                error_info = {"type": "timeout", "timeout": True, "message": msg}
                return None, [], [msg], error_info
            except Exception as e:
                self.logger.error(f"Generation or parsing failed: {e}", exc_info=True)
                error_info = {"type": "generation_error", "timeout": False, "message": str(e)}
                return None, [], [str(e)], error_info

    def _create_error_result(self,
                             config: LLMConfig,
                             prompt_id: str,
                             run_number: int,
                             error_message: str,
                             execution_time: float = 0.0) -> Dict[str, Any]:
        """
        Creates a result dictionary for a failed run.

        Args:
            config: The configuration that failed.
            prompt_id: The prompt identifier.
            run_number: The repetition number.
            error_message: The captured error message.
            execution_time: The time elapsed before the failure.

        Returns:
            A dictionary representing the error result.
        """
        error_type = "unknown"
        if "timeout" in error_message.lower():
            error_type = "timeout"

        error_info = {
            "type": error_type,
            "timeout": error_type == "timeout",
            "message": error_message
        }

        metrics = self.metrics_collector.collect_run_metrics(
            response=None,
            parsed_actions=[],
            parsing_errors=[error_message],
            error_info=error_info,
            execution_time=execution_time
        )

        return {
            **config.to_dict(),
            'prompt_id': prompt_id,
            'run_number': run_number,
            **metrics
        }

    def _calculate_summary_statistics(self) -> None:
        """Calculates summary statistics for each unique configuration."""
        self.logger.info("Calculating summary statistics.")
        config_groups = {}

        # Define the keys that identify a unique configuration
        config_keys = ['model', 'temperature', 'top_p', 'max_tokens', 'top_k', 'prompt_id']

        for result in self.detailed_results:
            # Create a tuple of configuration values as the key
            # Use .get() to handle cases where a key might be missing
            config_values = tuple(result.get(key) for key in config_keys)

            if config_values not in config_groups:
                config_groups[config_values] = []
            config_groups[config_values].append(result)

        for config_values, runs in config_groups.items():
            summary = self.statistics_calculator.calculate_summary_statistics(runs)

            # Add configuration information back to the summary
            config_dict = dict(zip(config_keys, config_values))
            summary.update(config_dict)
            summary['total_runs'] = len(runs)

            self.summary_results.append(summary)

        self.logger.info(f"Generated {len(self.summary_results)} configuration summaries.")

    def _cleanup_current_model(self) -> None:
        """Cleans up resources used by the current language model."""
        if self.llm:
            try:
                self.llm.cleanup()
                self.logger.info(f"Model {self.llm.config.model} cleaned up.")
            except Exception as e:
                self.logger.warning(f"Error cleaning up model: {e}")
        self.llm = None
        self.current_response_processor = None

    def _format_config(self, config: LLMConfig) -> str:
        """Formats a configuration dictionary for readable logging."""
        return f"{config.model}|T={config.temperature}|p={config.top_p}|max={config.max_tokens}"
