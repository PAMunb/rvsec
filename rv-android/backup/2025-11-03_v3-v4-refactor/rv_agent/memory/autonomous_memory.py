"""
Autonomous Memory Management for LangGraph RVAgent

Enhanced memory system with reasoning tracking, UI coverage analysis,
and persistent learning capabilities for autonomous Android testing.

Features:
- Short-term memory: Recent actions and discoveries
- Long-term memory: Persistent patterns and learned strategies
- UI Coverage memory: Track tested/untested elements
- Reasoning log: Detailed decision tracking for debugging
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

from rv_android_core.util.logging.manager import LoggingManager


@dataclass
class MemoryEntry:
    """Individual memory entry with reasoning"""
    timestamp: float
    entry_type: str
    content: str
    reasoning: str
    priority: str
    metadata: Dict[str, Any]


@dataclass
class UIElement:
    """UI element information for coverage tracking"""
    coordinates: str  # "x,y" format
    element_type: str
    description: str
    activity: str
    first_seen: float
    last_tested: Optional[float] = None
    test_count: int = 0
    successful_tests: int = 0
    reasoning_history: List[str] = None

    def __post_init__(self):
        if self.reasoning_history is None:
            self.reasoning_history = []


@dataclass
class ReasoningEntry:
    """Detailed reasoning tracking for debugging"""
    timestamp: float
    iteration: int
    decision_type: str  # "action", "analysis", "strategy"
    reasoning: str
    context: Dict[str, Any]
    outcome: Optional[str] = None


class AutonomousMemoryManager:
    """Comprehensive memory management for autonomous Android testing"""

    def __init__(self, memory_dir: Optional[Path] = None):
        """Initialize autonomous memory manager"""

        # Logging setup
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.memory.autonomous_memory",
            {"component": "AutonomousMemoryManager"}
        )

        # Memory storage
        self.memory_dir = memory_dir or Path.home() / ".rvagent" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Memory containers
        self.short_term_memory: deque = deque(maxlen=100)  # Recent 100 entries
        self.long_term_memory: List[MemoryEntry] = []
        self.ui_elements: Dict[str, UIElement] = {}  # coordinates -> UIElement
        self.reasoning_log: List[ReasoningEntry] = []

        # Coverage tracking
        self.tested_coordinates: Set[str] = set()
        self.successful_coordinates: Set[str] = set()
        self.failed_coordinates: Set[str] = set()

        # Learning patterns
        self.successful_patterns: Dict[str, int] = defaultdict(int)
        self.failed_patterns: Dict[str, int] = defaultdict(int)

        # Session tracking
        self.current_session: Optional[str] = None
        self.session_start_time: Optional[float] = None

        # Load persistent data
        self._load_persistent_memory()

        self.logger.info("Autonomous memory manager initialized")


    def start_session(self, session_id: str, app_package: str):
        """Start new testing session"""
        self.current_session = session_id
        self.session_start_time = time.time()

        # Clear short-term memory for fresh session
        self.short_term_memory.clear()

        # Add session start to memory
        self.add_short_term_memory(
            entry_type="session_start",
            content=f"Started session {session_id} for {app_package}",
            reasoning=f"Beginning autonomous testing of {app_package}",
            priority="high"
        )

        self.logger.info(f"Started memory session: {session_id} for {app_package}")


    def add_short_term_memory(self, entry_type: str, content: str, reasoning: str,
                             priority: str = "normal", metadata: Optional[Dict[str, Any]] = None):
        """Add entry to short-term memory"""

        entry = MemoryEntry(
            timestamp=time.time(),
            entry_type=entry_type,
            content=content,
            reasoning=reasoning,
            priority=priority,
            metadata=metadata or {}
        )

        self.short_term_memory.append(entry)

        # Promote high-priority entries to long-term memory
        if priority == "high":
            self.long_term_memory.append(entry)

        self.logger.debug(f"Added short-term memory: {entry_type} - {reasoning}")


    def add_reasoning_entry(self, iteration: int, decision_type: str, reasoning: str,
                           context: Dict[str, Any], outcome: Optional[str] = None):
        """Add detailed reasoning entry for debugging"""

        entry = ReasoningEntry(
            timestamp=time.time(),
            iteration=iteration,
            decision_type=decision_type,
            reasoning=reasoning,
            context=context,
            outcome=outcome
        )

        self.reasoning_log.append(entry)

        # Keep only last 200 reasoning entries
        if len(self.reasoning_log) > 200:
            self.reasoning_log = self.reasoning_log[-200:]

        self.logger.debug(f"Added reasoning entry: {decision_type} - {reasoning[:50]}...")


    def track_ui_element(self, coordinates: str, element_type: str, description: str,
                        activity: str, reasoning: str = ""):
        """Track discovered UI element"""

        if coordinates not in self.ui_elements:
            element = UIElement(
                coordinates=coordinates,
                element_type=element_type,
                description=description,
                activity=activity,
                first_seen=time.time(),
                reasoning_history=[reasoning] if reasoning else []
            )
            self.ui_elements[coordinates] = element

            self.add_short_term_memory(
                entry_type="ui_discovery",
                content=f"Discovered {element_type}: {description} at {coordinates}",
                reasoning=f"New UI element found in {activity}: {reasoning}",
                priority="normal",
                metadata={"coordinates": coordinates, "element_type": element_type}
            )

            self.logger.debug(f"Tracked new UI element: {element_type} at {coordinates}")
        else:
            # Update existing element
            element = self.ui_elements[coordinates]
            if reasoning and reasoning not in element.reasoning_history:
                element.reasoning_history.append(reasoning)


    def record_action_attempt(self, coordinates: str, action_type: str, reasoning: str,
                             success: bool, outcome: str):
        """Record action attempt on UI element"""

        # Track coordinates in sets
        self.tested_coordinates.add(coordinates)
        if success:
            self.successful_coordinates.add(coordinates)
        else:
            self.failed_coordinates.add(coordinates)

        # Update UI element if exists
        if coordinates in self.ui_elements:
            element = self.ui_elements[coordinates]
            element.last_tested = time.time()
            element.test_count += 1
            if success:
                element.successful_tests += 1
            element.reasoning_history.append(f"{action_type}: {reasoning} -> {outcome}")

        # Learn patterns
        pattern_key = f"{action_type}_{self._extract_element_pattern(coordinates)}"
        if success:
            self.successful_patterns[pattern_key] += 1
        else:
            self.failed_patterns[pattern_key] += 1

        # Add to memory
        priority = "high" if not success else "normal"  # Failed attempts are more important to remember
        self.add_short_term_memory(
            entry_type="action_attempt",
            content=f"{action_type} at {coordinates}: {'✅' if success else '❌'} - {outcome}",
            reasoning=reasoning,
            priority=priority,
            metadata={
                "coordinates": coordinates,
                "action_type": action_type,
                "success": success,
                "outcome": outcome
            }
        )

        self.logger.debug(f"Recorded action: {action_type} at {coordinates} - {'✅' if success else '❌'}")


    def _extract_element_pattern(self, coordinates: str) -> str:
        """Extract pattern from coordinates for learning"""
        try:
            x, y = map(int, coordinates.split(','))
            # Categorize by screen regions
            if y < 300:
                return "top_region"
            elif y < 600:
                return "upper_middle"
            elif y < 1200:
                return "middle_region"
            elif y < 1500:
                return "lower_middle"
            elif y < 1800:
                return "bottom_content"
            else:
                return "system_navigation"
        except:
            return "unknown_region"


    def get_forbidden_coordinates(self) -> List[str]:
        """Get coordinates that should not be clicked again"""
        # Return coordinates that were successfully tested
        return list(self.successful_coordinates)


    def get_untested_elements(self) -> List[Dict[str, Any]]:
        """Get UI elements that haven't been tested yet"""
        untested = []
        for coords, element in self.ui_elements.items():
            if element.last_tested is None:
                untested.append({
                    "coordinates": coords,
                    "element_type": element.element_type,
                    "description": element.description,
                    "activity": element.activity,
                    "age_seconds": time.time() - element.first_seen
                })

        # Sort by priority (newer discoveries first, then by element type)
        untested.sort(key=lambda x: (-x["age_seconds"], x["element_type"]))
        return untested


    def get_exploration_suggestions(self) -> List[Dict[str, str]]:
        """Generate exploration suggestions based on memory"""
        suggestions = []

        # Suggest untested elements
        untested = self.get_untested_elements()
        for element in untested[:3]:  # Top 3 untested
            suggestions.append({
                "suggestion": f"Test {element['element_type']} at {element['coordinates']}",
                "reason": f"Untested element: {element['description']}",
                "priority": "high" if element['element_type'] in ['Button', 'EditText'] else "normal"
            })

        # Suggest based on successful patterns
        if self.successful_patterns:
            most_successful_pattern = max(self.successful_patterns.items(), key=lambda x: x[1])
            suggestions.append({
                "suggestion": f"Focus on {most_successful_pattern[0]} elements",
                "reason": f"Pattern has {most_successful_pattern[1]} successful interactions",
                "priority": "normal"
            })

        # Suggest avoiding failed patterns
        if self.failed_patterns:
            most_failed_pattern = max(self.failed_patterns.items(), key=lambda x: x[1])
            suggestions.append({
                "suggestion": f"Avoid {most_failed_pattern[0]} actions",
                "reason": f"Pattern has {most_failed_pattern[1]} failures",
                "priority": "low"
            })

        return suggestions


    def get_coverage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive coverage statistics"""

        total_elements = len(self.ui_elements)
        tested_elements = len(self.tested_coordinates)
        untested_elements = total_elements - tested_elements

        success_rate = (
            len(self.successful_coordinates) / len(self.tested_coordinates) * 100
            if self.tested_coordinates else 0
        )

        return {
            "total_elements_discovered": total_elements,
            "tested_elements": tested_elements,
            "untested_elements": untested_elements,
            "coverage_percentage": (tested_elements / total_elements * 100) if total_elements > 0 else 0,
            "success_rate": success_rate,
            "successful_coordinates": len(self.successful_coordinates),
            "failed_coordinates": len(self.failed_coordinates),
            "total_test_attempts": len(self.tested_coordinates)
        }


    def get_memory_context_for_llm(self) -> str:
        """Generate formatted memory context for LLM"""

        context_parts = []

        # Recent actions (forbidden coordinates)
        forbidden = self.get_forbidden_coordinates()
        if forbidden:
            context_parts.append(f"🚫 FORBIDDEN COORDINATES (already tested successfully): {', '.join(forbidden)}")

        # Coverage status
        stats = self.get_coverage_statistics()
        context_parts.append(
            f"📊 COVERAGE: {stats['tested_elements']}/{stats['total_elements_discovered']} elements tested "
            f"({stats['coverage_percentage']:.1f}%)"
        )

        # Recent memory entries
        recent_entries = list(self.short_term_memory)[-5:]  # Last 5 entries
        if recent_entries:
            context_parts.append("📝 RECENT ACTIONS:")
            for entry in recent_entries:
                status = "✅" if "✅" in entry.content else ("❌" if "❌" in entry.content else "📝")
                context_parts.append(f"  {status} {entry.content}")

        # Exploration suggestions
        suggestions = self.get_exploration_suggestions()
        if suggestions:
            context_parts.append("💡 EXPLORATION SUGGESTIONS:")
            for suggestion in suggestions[:3]:
                context_parts.append(f"  • {suggestion['suggestion']}: {suggestion['reason']}")

        return "\n".join(context_parts)


    def get_reasoning_summary(self) -> List[Dict[str, Any]]:
        """Get summary of recent reasoning for debugging"""

        recent_reasoning = self.reasoning_log[-10:]  # Last 10 entries

        return [
            {
                "iteration": entry.iteration,
                "decision_type": entry.decision_type,
                "reasoning": entry.reasoning,
                "outcome": entry.outcome,
                "timestamp": entry.timestamp
            }
            for entry in recent_reasoning
        ]


    def save_session_summary(self) -> Dict[str, Any]:
        """Save and return session summary"""

        if not self.current_session:
            return {"error": "No active session"}

        session_duration = time.time() - (self.session_start_time or time.time())

        summary = {
            "session_id": self.current_session,
            "duration_seconds": session_duration,
            "coverage_stats": self.get_coverage_statistics(),
            "short_term_entries": len(self.short_term_memory),
            "long_term_entries": len(self.long_term_memory),
            "reasoning_entries": len(self.reasoning_log),
            "ui_elements_discovered": len(self.ui_elements),
            "successful_patterns": dict(self.successful_patterns),
            "failed_patterns": dict(self.failed_patterns),
            "exploration_suggestions": self.get_exploration_suggestions()
        }

        # Save to file
        session_file = self.memory_dir / f"session_{self.current_session}_{int(time.time())}.json"
        try:
            with open(session_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            self.logger.info(f"Session summary saved: {session_file}")
        except Exception as e:
            self.logger.error(f"Failed to save session summary: {e}")

        return summary


    def _load_persistent_memory(self):
        """Load persistent memory from storage"""

        try:
            persistent_file = self.memory_dir / "persistent_memory.json"
            if persistent_file.exists():
                with open(persistent_file, 'r') as f:
                    data = json.load(f)

                # Load patterns
                self.successful_patterns.update(data.get("successful_patterns", {}))
                self.failed_patterns.update(data.get("failed_patterns", {}))

                # Load long-term memory
                for entry_data in data.get("long_term_memory", []):
                    entry = MemoryEntry(**entry_data)
                    self.long_term_memory.append(entry)

                self.logger.info(f"Loaded persistent memory: {len(self.long_term_memory)} entries")

        except Exception as e:
            self.logger.warning(f"Failed to load persistent memory: {e}")


    def _save_persistent_memory(self):
        """Save persistent memory to storage"""

        try:
            persistent_data = {
                "successful_patterns": dict(self.successful_patterns),
                "failed_patterns": dict(self.failed_patterns),
                "long_term_memory": [asdict(entry) for entry in self.long_term_memory[-50:]]  # Last 50 entries
            }

            persistent_file = self.memory_dir / "persistent_memory.json"
            with open(persistent_file, 'w') as f:
                json.dump(persistent_data, f, indent=2, default=str)

            self.logger.debug("Persistent memory saved")

        except Exception as e:
            self.logger.error(f"Failed to save persistent memory: {e}")


    def clear_memory(self, memory_type: str = "short_term"):
        """Clear specified memory type"""

        if memory_type == "short_term":
            self.short_term_memory.clear()
        elif memory_type == "long_term":
            self.long_term_memory.clear()
        elif memory_type == "reasoning":
            self.reasoning_log.clear()
        elif memory_type == "ui_elements":
            self.ui_elements.clear()
            self.tested_coordinates.clear()
            self.successful_coordinates.clear()
            self.failed_coordinates.clear()
        elif memory_type == "all":
            self.short_term_memory.clear()
            self.long_term_memory.clear()
            self.reasoning_log.clear()
            self.ui_elements.clear()
            self.tested_coordinates.clear()
            self.successful_coordinates.clear()
            self.failed_coordinates.clear()
            self.successful_patterns.clear()
            self.failed_patterns.clear()

        self.logger.info(f"Cleared {memory_type} memory")


    def __del__(self):
        """Save persistent memory on destruction"""
        try:
            self._save_persistent_memory()
        except:
            pass  # Don't raise exceptions in destructor