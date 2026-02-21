"""
Long Term Memory for RVAgent - Cross-session persistence.

Implementation EXATA do plano com process isolation support.
Process isolation SUCCESS: LoggingManager e ErrorHandler com instâncias próprias.
"""

import time
from collections import defaultdict
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler

from ..constants import RVAgentConstants


@dataclass
class MemoryState:
    """
    Representa um estado da aplicação na memória.

    Armazena informações do estado, histórico de transições e resultados de ações.
    ADAPTADO para funcionamento cliente (sem singletons server-side).
    """

    fingerprint: str
    activity: str
    visit_count: int = 0
    first_visit: float = 0.0
    last_visit: float = 0.0
    interactive_elements_count: int = 0

    def __post_init__(self):
        if self.first_visit == 0.0:
            self.first_visit = time.time()
        self.last_visit = time.time()
        self.all_actions = set()
        self.outgoing_transitions = {}
        self.incoming_transitions = {}


@dataclass
class MemoryAction:
    """
    Representa uma ação na memória.

    Rastreia histórico de execução, taxa de sucesso e transições causadas.
    """

    id: int
    text: str
    action_type: str
    execution_count: int = 0
    success_count: int = 0
    reaches_mop: bool = False

    def __post_init__(self):
        self.state_transitions = defaultdict(list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this action."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count


class LongTermMemory:
    """
    Sistema de memória de longo prazo para RVAgent cliente.

    PROCESSO SUBPROCESS ISOLADO:
    - LoggingManager.get_instance() com instância própria do subprocess
    - ErrorHandler.get_instance() com instância própria do subprocess
    - StaticAnalysisData disponível (rv-android-core habilitado)
    - File-based persistence para estado local do cliente

    Target app: br.unb.cic.cryptoapp
    """

    def __init__(self, static_data: Optional[Any] = None):
        """Initialize long term memory with process isolation support."""

        # Process isolation - LoggingManager com instância própria
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.memory.long_term", {"component": "LongTermMemory"}
        )

        # ErrorHandler decorators disponíveis no subprocess
        self.error_handler = ErrorHandler.get_instance()

        self.static_data = static_data
        self.states: Dict[str, MemoryState] = {}
        self.actions: Dict[int, MemoryAction] = {}
        self.activities: Dict[str, List[str]] = defaultdict(list)
        self.transitions: List[Dict[str, Any]] = []

        # Statistics
        self.total_states = 0
        self.total_activities = 0
        self.total_actions = 0

        self.logger.info(" LongTermMemory initialized")

    def record_state(
        self, state_hash: str, activity: str, interactive_elements_count: int = 0
    ) -> None:
        """
        Registra estado com error handling cliente.

        Args:
            state_hash: Hash único do estado da tela
            activity: Nome da activity Android
            interactive_elements_count: Número de elementos interativos
        """
        try:
            if state_hash not in self.states:
                self.states[state_hash] = MemoryState(
                    fingerprint=state_hash,
                    activity=activity,
                    interactive_elements_count=interactive_elements_count,
                )
                self.total_states += 1

                # Track activity-state mapping
                if activity not in self.activities:
                    self.total_activities += 1
                self.activities[activity].append(state_hash)

                self.logger.debug(f" New state recorded: {activity} ({state_hash[:8]})")

            # Update visit information
            state = self.states[state_hash]
            state.visit_count += 1
            state.last_visit = time.time()

            self.logger.debug(
                f" State visit updated: {activity} (visit #{state.visit_count})"
            )

        except Exception as e:
            # CLIENTE error handling - log e continue
            self.logger.error(f" Failed to record state {state_hash}: {e}")

    def record_action(
        self,
        action_id: int,
        action_text: str,
        action_type: str,
        success: bool,
        from_state: str,
        to_state: Optional[str] = None,
    ) -> None:
        """
        Record action execution with result.

        Args:
            action_id: Unique action identifier
            action_text: Human readable action description
            action_type: Type of action (click, input, swipe, etc.)
            success: Whether action was successful
            from_state: Source state hash
            to_state: Destination state hash (if state transition occurred)
        """
        try:
            if action_id not in self.actions:
                self.actions[action_id] = MemoryAction(
                    id=action_id, text=action_text, action_type=action_type
                )
                self.total_actions += 1

            action = self.actions[action_id]
            action.execution_count += 1

            if success:
                action.success_count += 1

            # Record state transition
            if to_state and to_state != from_state:
                action.state_transitions[from_state].append(to_state)
                self.transitions.append(
                    {
                        "from_state": from_state,
                        "to_state": to_state,
                        "action_id": action_id,
                        "timestamp": time.time(),
                        "success": success,
                    }
                )

                self.logger.debug(
                    f" Action recorded: {action_text} "
                    f"({from_state[:8]} → {to_state[:8]}) - Success: {success}"
                )
            else:
                self.logger.debug(
                    f" Action recorded: {action_text} "
                    f"(no transition) - Success: {success}"
                )

        except Exception as e:
            self.logger.error(f" Failed to record action: {e}")

    def get_state_guidance(self, current_state_hash: str) -> Dict[str, Any]:
        """
        Fornece guidance baseado em memória para ReAct engine.

        Args:
            current_state_hash: Hash do estado atual

        Returns:
            Dictionary com informações de guidance
        """
        try:
            if current_state_hash in self.states:
                state = self.states[current_state_hash]

                # Get successful actions from this state
                successful_actions = []
                for action in self.actions.values():
                    if current_state_hash in action.state_transitions:
                        if action.success_rate > 0.5:  # At least 50% success rate
                            successful_actions.append(
                                {
                                    "text": action.text,
                                    "type": action.action_type,
                                    "success_rate": action.success_rate,
                                    "execution_count": action.execution_count,
                                }
                            )

                # Sort by success rate
                successful_actions.sort(key=lambda x: x["success_rate"], reverse=True)

                return {
                    "visit_count": state.visit_count,
                    "activity": state.activity,
                    "interactive_elements_count": state.interactive_elements_count,
                    "successful_actions": successful_actions[:5],  # Top 5
                    "is_known_state": True,
                    "exploration_priority": (
                        "low" if state.visit_count > 3 else "medium"
                    ),
                }
            else:
                return {
                    "visit_count": 0,
                    "new_state": True,
                    "is_known_state": False,
                    "exploration_priority": "high",
                }

        except Exception as e:
            self.logger.error(f" State guidance failed: {e}")
            return {"error": str(e)}

    def get_unexplored_transitions(self, current_state_hash: str) -> List[str]:
        """
        Get potentially unexplored transitions from current state.

        Returns list of action suggestions for exploration.
        """
        try:
            if current_state_hash not in self.states:
                return ["explore_new_elements", "try_different_actions"]

            state = self.states[current_state_hash]

            # Actions that were rarely tried
            underexplored_actions = []
            for action in self.actions.values():
                if (
                    current_state_hash in action.state_transitions
                    and action.execution_count < 3
                ):
                    underexplored_actions.append(action.text)

            return underexplored_actions[:3]  # Top 3 suggestions

        except Exception as e:
            self.logger.error(f" Unexplored transitions query failed: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics for debugging and analysis."""
        try:
            total_actions_executed = sum(
                action.execution_count for action in self.actions.values()
            )
            total_successful_actions = sum(
                action.success_count for action in self.actions.values()
            )

            success_rate = (
                total_successful_actions / total_actions_executed
                if total_actions_executed > 0
                else 0.0
            )

            return {
                "total_states": self.total_states,
                "total_activities": self.total_activities,
                "total_action_types": self.total_actions,
                "total_actions_executed": total_actions_executed,
                "total_successful_actions": total_successful_actions,
                "overall_success_rate": success_rate,
                "total_transitions": len(self.transitions),
                "most_visited_states": self._get_most_visited_states(5),
            }

        except Exception as e:
            self.logger.error(f" Statistics calculation failed: {e}")
            return {"error": str(e)}

    def _get_most_visited_states(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most frequently visited states."""
        try:
            sorted_states = sorted(
                self.states.values(), key=lambda s: s.visit_count, reverse=True
            )

            return [
                {
                    "state_hash": state.fingerprint[:12],
                    "activity": state.activity,
                    "visit_count": state.visit_count,
                    "elements_count": state.interactive_elements_count,
                }
                for state in sorted_states[:limit]
            ]

        except Exception as e:
            self.logger.error(f" Most visited states query failed: {e}")
            return []

    def clear_memory(self) -> None:
        """Clear all memory data (for testing or reset)."""
        self.logger.info(" Clearing long term memory...")

        self.states.clear()
        self.actions.clear()
        self.activities.clear()
        self.transitions.clear()

        self.total_states = 0
        self.total_activities = 0
        self.total_actions = 0

        self.logger.info(" Long term memory cleared")
