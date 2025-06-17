import os
from typing import Optional, Dict, Any

import rv_android_core.constants as constants
from rv_android_core.commands.command import Command
from rv_android_core.util import utils
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_monitor_generator.config import RVGeneratorConfig, ConfigurationError


class RuntimeVerificationGenerator:
    """
    Core generator for runtime verification monitoring artifacts from MOP specifications.
    
    The RuntimeVerificationGenerator serves as the central component for transforming
    Monitoring-Oriented Programming (MOP) specifications into executable monitoring 
    artifacts. It orchestrates the JavaMOP and RV-Monitor tools to produce both
    AspectJ weaving files and Java monitor classes.

    ### Architectural Decisions:
    - Implements a flexible configuration system supporting multiple deployment scenarios
    - Delegates error handling to centralized ErrorHandler for consistent behavior
    - Uses structured logging through LoggingManager for operational visibility
    - Orchestrates JavaMOP and RV-Monitor execution in a coordinated pipeline
    - Provides validation at both configuration and execution phases

    ### Role in the System:
    - Acts as the foundation component for monitor generation in the RV ecosystem
    - Transforms MOP specifications into executable monitoring artifacts
    - Generates AspectJ files required for instrumentation integration
    - Produces Java monitor classes for runtime verification execution
    - Supports both JCA-specific and generic monitored operations specifications
    - Enables rv-instrumentation module through generated monitoring artifacts
    
    ### Integration Points:
    - Consumed by rv-instrumentation for APK instrumentation workflows
    - Used by experiment orchestration systems for monitor preparation
    - Integrated with CLI tooling for standalone monitor generation
    """

    def __init__(self, config: Optional[RVGeneratorConfig] = None):
        """
        Initialize RuntimeVerificationGenerator with configuration and error handling.
        
        Args:
            config: Configuration object. If None, will be created with default settings
                   from environment variables or explicit paths.
        """
        self.config = config or RVGeneratorConfig()
        
        # Initialize structured logging through LoggingManager
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            'rv_monitor_generator.RuntimeVerificationGenerator',
            {
                CONTEXT_COMPONENT: 'RuntimeVerificationGenerator',
                'component_module': 'rv-monitor-generator'
            }
        )
        
        # Initialize centralized error handling
        self._error_handler = ErrorHandler.get_instance()
        
        self._logger.info("RuntimeVerificationGenerator initialized", extra={
            'config_summary': self.config.get_configuration_summary()
        })

    def generate_monitors(self, output_dir: str) -> bool:
        """
        Execute the complete monitor generation pipeline from MOP specifications.
        
        This method orchestrates the entire process of transforming MOP specifications
        into executable monitoring artifacts. It coordinates JavaMOP execution for
        AspectJ generation and RV-Monitor execution for monitor class creation.
        
        ### Processing Pipeline:
        1. Validates output directory accessibility and creates if necessary
        2. Resets output directory to ensure clean generation environment
        3. Executes JavaMOP to generate AspectJ files and RVM specifications
        4. Executes RV-Monitor to transform RVM files into Java monitor classes
        5. Copies custom AspectJ files from aspects directory
        6. Cleans up intermediate RVM files
        
        Args:
            output_dir: Target directory for generated monitoring artifacts.
                       Will be created if it doesn't exist.
            
        Returns:
            bool: True if the complete generation pipeline succeeded,
                  False if any step failed.
                  
        Raises:
            ConfigurationError: If output directory validation fails
            CommandException: If JavaMOP or RV-Monitor execution fails
        """
        try:
            # Critical validation point - ensure output accessibility
            self.config.validate_output_directory(output_dir)
            
            self._logger.info("Starting runtime verification monitor generation pipeline", extra={
                'output_dir': output_dir,
                'specs_count': len(self._get_mop_specs()),
                'pipeline_stage': 'initialization'
            })
            
            # Prepare clean generation environment
            utils.reset_folder(output_dir)
            self._logger.debug("Output directory prepared", extra={'output_dir': output_dir})

            # Execute coordinated generation pipeline
            self._execute_javamop(output_dir)
            self._execute_rvmonitor(output_dir)
            
            self._logger.info("Monitor generation pipeline completed successfully", extra={
                'output_dir': output_dir,
                'pipeline_stage': 'completed'
            })
            return True
            
        except Exception as e:
            # Use centralized error handling for consistent error management
            context = {
                'component': 'RuntimeVerificationGenerator',
                'operation': 'generate_monitors',
                'output_dir': output_dir,
                'mop_specs_dir': self.config.mop_specs_dir,
                'pipeline_stage': 'failed'
            }
            
            self._error_handler.handle_error(e, context)
            return False

    def _execute_javamop(self, output_dir: str) -> None:
        """
        Execute JavaMOP to generate AspectJ weaving files and RVM monitor specifications.
        
        JavaMOP processes MOP specification files to generate two critical artifacts:
        1. AspectJ (.aj) files that define pointcuts and advice for method interception
        2. RVM (.rvm) files containing monitor state machine specifications
        
        ### Implementation Details:
        - Uses merge option to combine multiple MOP specifications into unified artifacts
        - Handles JavaMOP's incomplete -d option by manually moving RVM files
        - Integrates custom AspectJ files from the aspects directory
        
        Args:
            output_dir: Target directory for generated JavaMOP artifacts
            
        Raises:
            CommandException: If JavaMOP execution fails
        """
        mop_specs = self._get_mop_specs()
        
        self._logger.info("Executing JavaMOP for monitored operations generation", extra={
            'tool': 'JavaMOP',
            'specs_directory': self.config.mop_specs_dir,
            'specs_count': len(mop_specs),
            'output_directory': output_dir
        })
        
        # Construct JavaMOP command with merge option for unified artifact generation
        mop_files_pattern = os.path.join(self.config.mop_specs_dir, '*' + constants.EXTENSION_MOP)
        javamop_cmd = Command(self.config.javamop_bin, ['-d', output_dir, '-merge', mop_files_pattern])
        
        utils.execute_command(javamop_cmd, "javamop")
        
        # Critical workaround: JavaMOP's -d option has incomplete behavior
        # It moves generated .aj files but leaves .rvm files in source directory
        utils.move_files_by_extension(constants.EXTENSION_RVM, self.config.mop_specs_dir, output_dir)
        
        # Integrate custom AspectJ files for enhanced monitoring capabilities
        utils.copy_files_by_extension(constants.EXTENSION_AJ, self.config.aspects_dir, output_dir, log_info=True)
        
        self._logger.debug("JavaMOP execution completed", extra={
            'generated_artifacts': ['AspectJ files', 'RVM specifications'],
            'custom_aspects_integrated': True
        })

    def _execute_rvmonitor(self, output_dir: str) -> None:
        """
        Execute RV-Monitor to transform RVM specifications into executable Java monitor classes.
        
        RV-Monitor processes the RVM files generated by JavaMOP to create the final
        Java monitor classes that will be integrated into instrumented applications.
        These monitors implement the runtime verification logic for monitored operations.
        
        ### Processing Details:
        - Transforms RVM state machine specifications into Java monitor implementations
        - Generates optimized monitor code for runtime execution
        - Creates monitor classes compatible with AspectJ weaving
        
        Args:
            output_dir: Directory containing RVM files and target for Java monitor classes
            
        Raises:
            CommandException: If RV-Monitor execution fails
        """
        self._logger.info("Executing RV-Monitor for monitor class generation", extra={
            'tool': 'RV-Monitor',
            'input_directory': output_dir,
            'artifact_type': 'Java monitor classes'
        })
        
        # Process all RVM files in the output directory
        rvm_files_pattern = os.path.join(output_dir, '*' + constants.EXTENSION_RVM)
        rvmonitor_cmd = Command(self.config.rvmonitor_bin, ['-d', output_dir, '-merge', rvm_files_pattern])
        
        utils.execute_command(rvmonitor_cmd, "rvmonitor")
        
        # Clean up intermediate RVM files - they're no longer needed after monitor generation
        utils.delete_files_by_extension(constants.EXTENSION_RVM, output_dir)
        
        self._logger.debug("RV-Monitor execution completed", extra={
            'generated_artifacts': ['Java monitor classes'],
            'intermediate_files_cleaned': True
        })

    def _get_mop_specs(self) -> list:
        """
        Retrieve list of MOP specification files from the configured directory.
        
        Returns:
            list: List of MOP specification file paths
        """
        import glob
        return glob.glob(os.path.join(self.config.mop_specs_dir, f'*{constants.EXTENSION_MOP}'))
    
    def get_generation_summary(self, output_dir: str) -> Dict[str, Any]:
        """
        Generate summary information about the monitoring artifacts produced.
        
        Args:
            output_dir: Directory containing generated artifacts
            
        Returns:
            Dict containing summary of generated artifacts and their purposes
        """
        import glob
        
        aspectj_files = glob.glob(os.path.join(output_dir, f'*{constants.EXTENSION_AJ}'))
        java_files = glob.glob(os.path.join(output_dir, f'*{constants.EXTENSION_JAVA}'))
        
        return {
            'output_directory': output_dir,
            'aspectj_files': {
                'count': len(aspectj_files),
                'purpose': 'Weaving specifications for monitored operations instrumentation'
            },
            'monitor_classes': {
                'count': len(java_files),
                'purpose': 'Runtime verification monitor implementations'
            },
            'specs_processed': {
                'source_directory': self.config.mop_specs_dir,
                'count': len(self._get_mop_specs())
            }
        }