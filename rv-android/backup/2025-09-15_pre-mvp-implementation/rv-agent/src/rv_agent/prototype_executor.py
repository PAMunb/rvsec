"""
RVAgent Phase 0 Prototype Executor

Implements parameter grid search execution logic for vision model testing.
"""
import time
import signal
import sys
from datetime import datetime
from typing import List, Tuple, Iterator
from pathlib import Path

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

from rv_agent.config import PrototypeConfig
from rv_agent.data_structures import (
    TestResult, ParameterCombination, PrototypeReport
)
from rv_agent.llm_integration import create_vision_client, VisionModelClient
from rv_agent.coordinate_validator import create_coordinate_validator, CoordinateValidator


class PrototypeExecutor:
    """
    Executes Phase 0 prototype with parameter grid search.
    
    Implements the nested loop structure requested:
    for temperature in temperatures:
        for top_p in top_ps:
            for top_k in top_ks:
                execute(screenshot, temperature, top_p, top_k)
    """
    
    def __init__(self, config: PrototypeConfig):
        """
        Initialize prototype executor.
        
        Args:
            config: Prototype configuration
        """
        self.config = config
        self.vision_client = create_vision_client(config)
        self.validator = create_coordinate_validator(config)
        
        # Setup logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.prototype_executor",
            {CONTEXT_COMPONENT: "PrototypeExecutor"}
        )
        
        # Execution state
        self.report = PrototypeReport(start_time=datetime.now())
        self.current_test_index = 0
        self.interrupted = False
        
        # Setup interrupt handler for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_interrupt)
        
    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C interrupt gracefully."""
        self.logger.info("Interrupt received. Finishing current test and saving results...")
        self.interrupted = True
        
    def run(self) -> PrototypeReport:
        """
        Execute complete parameter grid search prototype.
        
        Returns:
            Comprehensive prototype report with results
        """
        self.logger.info("Starting RVAgent Phase 0 Prototype Execution")
        self.config.print_config_summary()
        
        # Store configuration in report
        self.report.config_summary = {
            'screenshots_dir': self.config.SCREENSHOTS_DIR,
            'num_test_apps': self.config.NUM_TEST_APPS,
            'screenshots_per_app': self.config.SCREENSHOTS_PER_APP,
            'primary_model': self.config.PRIMARY_MODEL,
            'temperatures': self.config.TEMPERATURES,
            'top_ps': self.config.TOP_PS,
            'top_ks': self.config.TOP_KS,
            'total_tests': self.config.total_tests,
            'timeout_seconds': self.config.TIMEOUT_SECONDS,
            'coordinate_tolerance': self.config.COORDINATE_TOLERANCE,
            'random_seed': self.config.RANDOM_SEED
        }
        
        try:
            # Select apps and screenshots with reproducible randomization
            selected_apps = self.config.random_select_apps()
            self.logger.info(f"Selected {len(selected_apps)} apps for testing: {selected_apps}")
            
            # Execute grid search
            for test_data in self._generate_test_cases(selected_apps):
                if self.interrupted:
                    self.logger.info("Execution interrupted by user")
                    break
                
                result = self._execute_single_test(test_data)
                self.report.add_result(result)
                
                # Log progress periodically
                if self.current_test_index % 50 == 0:
                    self._log_progress()
                    
                # Save intermediate results periodically
                if self.current_test_index % 100 == 0:
                    self._save_intermediate_results()
            
            # Finalize report
            self.report.finalize()
            self.logger.info("Prototype execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"Prototype execution failed: {e}")
            self.report.finalize()
            raise
        
        return self.report
    
    def _generate_test_cases(self, selected_apps: List[str]) -> Iterator[dict]:
        """
        Generate test cases for grid search execution.
        
        Implements the nested loop structure:
        for temperature in temperatures:
            for top_p in top_ps:
                for top_k in top_ks:
                    for app in apps:
                        for screenshot in screenshots:
                            yield test_case
        
        Args:
            selected_apps: List of app names to test
            
        Yields:
            Test case dictionaries with all necessary parameters
        """
        self.current_test_index = 0
        
        # Parameter grid search loops (as requested)
        for temperature in self.config.TEMPERATURES:
            for top_p in self.config.TOP_PS:
                for top_k in self.config.TOP_KS:
                    for app_name in selected_apps:
                        # Get random screenshots for this app
                        screenshot_ids = self.config.random_select_screenshots(app_name)
                        
                        for screenshot_id in screenshot_ids:
                            self.current_test_index += 1
                            
                            yield {
                                'test_index': self.current_test_index,
                                'app_name': app_name,
                                'screenshot_id': screenshot_id,
                                'temperature': temperature,
                                'top_p': top_p,
                                'top_k': top_k
                            }
    
    def _execute_single_test(self, test_data: dict) -> TestResult:
        """
        Execute a single coordinate generation and validation test.
        
        Args:
            test_data: Test parameters dictionary
            
        Returns:
            TestResult with execution metrics
        """
        start_time = time.time()
        
        # Initialize result object
        result = TestResult(
            app_name=test_data['app_name'],
            screenshot_id=test_data['screenshot_id'],
            test_index=test_data['test_index'],
            model_name=self.config.PRIMARY_MODEL,
            temperature=test_data['temperature'],
            top_p=test_data['top_p'],
            top_k=test_data['top_k'],
            timestamp=datetime.now()
        )
        
        try:
            # Get file paths
            image_path, xml_path = self.config.get_screenshot_files(
                test_data['app_name'], 
                test_data['screenshot_id']
            )
            
            self.logger.debug(
                f"Test {test_data['test_index']}: {test_data['app_name']}/{test_data['screenshot_id']} "
                f"temp={test_data['temperature']} top_p={test_data['top_p']} top_k={test_data['top_k']}"
            )
            
            # Generate coordinates using vision model
            coordinates, error = self.vision_client.generate_coordinates(
                image_path=image_path,
                temperature=test_data['temperature'],
                top_p=test_data['top_p'],
                top_k=test_data['top_k']
            )
            
            if error:
                result.error = error
                result.success = False
            elif coordinates:
                result.generated_coordinates = coordinates
                
                # Validate coordinates against ground truth
                validation_result = self.validator.validate_coordinates(coordinates, xml_path)
                
                result.success = validation_result['success']
                result.distance_to_closest = validation_result['distance']
                result.closest_ground_truth = validation_result['closest_element']
                result.ground_truth_count = validation_result['ground_truth_count']
                result.tolerance = validation_result['tolerance']
                
                if 'error' in validation_result:
                    result.error = validation_result['error']
                    
            else:
                result.error = "Failed to generate coordinates"
                result.success = False
            
            # Collect LLM metrics
            result.llm_metrics = self.vision_client.get_latest_metrics()
            
        except TimeoutError:
            result.timeout_occurred = True
            result.error = f"Timeout after {self.config.TIMEOUT_SECONDS}s"
            result.success = False
            
        except Exception as e:
            result.error = str(e)
            result.success = False
            self.logger.error(f"Test {test_data['test_index']} failed: {e}")
        
        finally:
            result.execution_time = time.time() - start_time
        
        return result
    
    def _log_progress(self):
        """Log current execution progress."""
        if self.report.total_tests > 0:
            success_rate = (self.report.successful_tests / self.report.total_tests) * 100
            self.logger.info(
                f"Progress: {self.current_test_index}/{self.config.total_tests} tests "
                f"({success_rate:.1f}% success rate so far)"
            )
    
    def _save_intermediate_results(self):
        """Save intermediate results to prevent data loss."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rv_agent_prototype_intermediate_{timestamp}.json"
            self.report.save_to_json(filename)
            self.logger.info(f"Saved intermediate results to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save intermediate results: {e}")
    
    def save_final_results(self, output_path: str = None):
        """
        Save final results to JSON file.
        
        Args:
            output_path: Custom output file path (optional)
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"rv_agent_prototype_results_{timestamp}.json"
        
        try:
            self.report.save_to_json(output_path)
            self.logger.info(f"Final results saved to {output_path}")
            
            # Also save a summary report
            summary_path = output_path.replace('.json', '_summary.txt')
            with open(summary_path, 'w') as f:
                f.write("RVAgent Phase 0 Prototype - Results Summary\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Total Tests: {self.report.total_tests}\n")
                f.write(f"Successful Tests: {self.report.successful_tests}\n")
                f.write(f"Success Rate: {self.report.success_rate:.1f}%\n")
                f.write(f"Total Duration: {self.report.total_duration/3600:.1f} hours\n")
                f.write(f"Avg Execution Time: {self.report.avg_execution_time:.2f}s\n")
                f.write(f"Total Tokens Used: {self.report.total_tokens_used:,}\n")
                
                if self.report.best_parameters:
                    f.write(f"\nBest Parameters: {self.report.best_parameters}\n")
                    best_perf = max(self.report.parameter_performance.values(), 
                                  key=lambda x: x.success_rate)
                    f.write(f"Best Success Rate: {best_perf.success_rate:.1f}%\n")
            
            self.logger.info(f"Summary saved to {summary_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save final results: {e}")
            raise


def create_prototype_executor(config: PrototypeConfig) -> PrototypeExecutor:
    """Factory function to create prototype executor."""
    return PrototypeExecutor(config)