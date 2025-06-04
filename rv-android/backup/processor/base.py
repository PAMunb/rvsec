# rvandroid/experiment/processor/base.py
"""
Base phase processor implementation for the unified execution framework.

This module provides the BasePhaseProcessor class, which serves as a foundation
for all phase processor implementations. It implements common functionality and
provides hooks for customization by subclasses.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from rvandroid.experiment.core.interfaces import (
    IPhaseProcessor,
    IExecutionContext,
    ExecutionPhase
)
from rvandroid.experiment.event import EventBus, get_event_bus
from rvandroid.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rvandroid.util.logging.manager import LoggingManager


class BasePhaseProcessor(IPhaseProcessor, ABC):
    """
    Base implementation of the phase processor interface.
    
    ### Architectural Decisions:
    - Implements common functionality for all phase processors
    - Provides comprehensive error handling and logging
    - Enables consistent processor initialization and configuration
    - Facilitates clear separation of processor responsibilities
    
    ### Role in the System:
    - Serves as the foundation for all phase processor implementations
    - Provides consistent error handling and logging
    - Enables standardized processor execution and cleanup
    - Facilitates processor discovery and registration
    """
    
    def __init__(self, 
                processor_name: str,
                supported_phases: List[ExecutionPhase],
                context: IExecutionContext,
                event_bus: Optional[EventBus] = None):
        """
        Initialize the phase processor.
        
        Args:
            processor_name: Name of the processor
            supported_phases: List of phases this processor can handle
            context: Execution context
            event_bus: Optional event bus for event publishing
        """
        self._name = processor_name
        self._supported_phases = supported_phases
        self._context = context
        self._event_bus = event_bus or get_event_bus()
        
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.processor',
            {
                'experiment_id': context.experiment_id,
                CONTEXT_COMPONENT: processor_name
            }
        )
        
    @property
    def name(self) -> str:
        """
        Get the processor name.
        
        Returns:
            Processor name
        """
        return self._name
        
    @property
    def supported_phases(self) -> List[ExecutionPhase]:
        """
        Get the phases supported by this processor.
        
        Returns:
            List of supported phases
        """
        return self._supported_phases
        
    def process(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Process the specified phase with the given context.
        
        Provides common error handling and logging for all processors.
        
        Args:
            phase: Phase to process
            context: Execution context
            
        Returns:
            True if processing was successful, False otherwise
        """
        if not self.can_process(phase):
            self.logger.error(f"Cannot process phase {phase.name}")
            return False
            
        with self.logger.with_context(phase=phase.name):
            self.logger.info(LOG_START.format(operation=f"Processing phase {phase.name}"))
            
            try:
                # Process the phase using the subclass implementation
                result = self._process_phase(phase, context)
                
                if result:
                    self.logger.info(LOG_COMPLETE.format(operation=f"Processing phase {phase.name}"))
                else:
                    self.logger.error(LOG_ERROR.format(
                        operation=f"Processing phase {phase.name}",
                        error="Processing failed"
                    ))
                    
                return result
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation=f"Processing phase {phase.name}",
                    error=str(e)
                ))
                return False
                
    def can_process(self, phase: ExecutionPhase) -> bool:
        """
        Check if this processor can handle the specified phase.
        
        Args:
            phase: Phase to check
            
        Returns:
            True if this processor can handle the phase
        """
        return phase in self._supported_phases
        
    @abstractmethod
    def _process_phase(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Process the specified phase with the given context.
        
        This method must be implemented by subclasses.
        
        Args:
            phase: Phase to process
            context: Execution context
            
        Returns:
            True if processing was successful, False otherwise
        """
        pass