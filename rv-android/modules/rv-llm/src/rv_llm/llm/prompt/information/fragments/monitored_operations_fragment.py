"""Monitored operations information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting monitored
operations information (previously called security operations) from the application state.
"""

from typing import Any, Dict, List, Optional

from rv_llm.llm.prompt.information.base_fragment import InformationFragment


class MonitoredOperationsFragment(InformationFragment):
    """Fragment for extracting and formatting monitored operations information.
    
    This fragment processes information about monitored operations (e.g., cryptographic
    operations, file access, network calls) that have been detected in the application.
    """

    def __init__(self, name: str = "monitored_operations", priority: int = 300):
        """Initialize the monitored operations fragment.
        
        Args:
            name: The name of the fragment (default: "monitored_operations").
            priority: The priority of the fragment (default: 300).
        """
        super().__init__(name, priority)

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate monitored operations information from the application state.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            A dictionary containing information about monitored operations.
        """
        if not state:
            return {}

        # Extract monitored operations from state
        monitored_ops = state.get("monitored_operations", [])

        if not monitored_ops:
            self.logger.debug("No monitored operations found in state")
            return {}

        # TODO implementar
        # Group operations by type
        # grouped_ops = self._group_operations_by_type(monitored_ops)
        grouped_ops = ""

        # Generate summary
        # summary = self._generate_summary(grouped_ops)
        summary = ""

        result = {
            "operations": monitored_ops,
            "grouped": grouped_ops,
            "summary": summary
        }

        self.logger.debug(f"Generated information about {len(monitored_ops)} monitored operations")
        return result

    def _group_operations_by_type(self, operations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group operations by their type.
        
        Args:
            operations: List of monitored operations.
            
        Returns:
            Dictionary mapping operation types to lists of operations.
        """
        grouped = {}

        for op in operations:
            op_type = op.get("type", "unknown")

            if op_type not in grouped:
                grouped[op_type] = []

            grouped[op_type].append(op)

        return grouped

    def _generate_summary(self, grouped_ops: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate a human-readable summary of monitored operations.
        
        Args:
            grouped_ops: Operations grouped by type.
            
        Returns:
            A human-readable summary string.
        """
        if not grouped_ops:
            return "No monitored operations detected."

        summary_parts = []

        # Map of operation types to human-readable descriptions
        type_descriptions = {
            "crypto": "cryptographic operations",
            "file": "file operations",
            "network": "network operations",
            "permission": "permission-sensitive operations",
            "database": "database operations"
        }

        for op_type, ops in grouped_ops.items():
            description = type_descriptions.get(op_type, f"{op_type} operations")
            summary_parts.append(f"{len(ops)} {description}")

        return "Detected " + ", ".join(summary_parts) + "."

    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if monitored operations information should be included.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            True if monitored operations information should be included, False otherwise.
        """
        # Include if there are any monitored operations in the state
        return bool(state and state.get("monitored_operations"))
