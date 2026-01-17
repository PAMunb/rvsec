"""
UI Coverage Tracker for RVAgent - Element discovery and testing tracking.

Key Design Decisions:

1. COORDINATE-BASED ELEMENT IDs
   Problem: Same UI element may have different resource IDs across app versions,
   or no ID at all (common in custom views and games).
   Solution: Use normalized coordinates (x, y) as primary identifier.
   Format: "coords:{x},{y}" - standardized via element_id module.

2. ANNOTATION SYSTEM FOR LLM GUIDANCE
   Problem: LLM doesn't know which elements have been tested and may repeatedly
   click the same button while ignoring unexplored options.
   Solution: Annotate screen descriptions with [UNTESTED], [TESTED-Nx] tags.
   The LLM sees "[UNTESTED] Button 'Submit'" and knows to prioritize it.

3. SCREEN-ELEMENT TRACKING
   Problem: Need to know coverage per screen to detect when a screen is fully explored.
   Solution: Maintain screen_elements dict mapping screen_hash -> set of element IDs.
   This enables per-screen coverage statistics and exploration suggestions.

4. TEST COUNT THRESHOLDS
   - 0 tests: [UNTESTED] - highest priority
   - 1-2 tests: [TESTED-Nx] - medium priority (may need more testing)
   - >WELL_TESTED_THRESHOLD: [WELL-TESTED] - low priority

   WHY MULTIPLE TESTS: Some elements have state-dependent behavior (e.g., toggle
   buttons, checkboxes). Testing once may not reveal all behaviors.
"""
import time
from typing import Dict, Set, Optional, List, Any
from dataclasses import dataclass
from collections import defaultdict

from ..constants import RVAgentConstants
from .element_id import make_element_id


@dataclass
class UIElementStats:
    """
    Estatísticas de interação com elementos UI para suporte a decisões LLM.
    """
    total_elements: int = 0
    tested_elements: int = 0
    untested_elements: int = 0

    @property
    def coverage_percentage(self) -> float:
        if self.total_elements == 0:
            return 0.0
        return (self.tested_elements / self.total_elements) * 100

    @property
    def discovery_rate(self) -> float:
        """Rate of new element discovery."""
        if self.total_elements == 0:
            return 0.0
        return (self.tested_elements / self.total_elements)


class UICoverageTracker:
    """
    Tracks UI element interactions for exploration guidance and coverage metrics.

    Provides:
    - Element test count tracking (how many times each element was clicked)
    - Screen-element mapping (which elements exist on each screen)
    - Annotation generation for LLM prompts ([UNTESTED], [TESTED-Nx])
    - Coverage statistics per screen and overall
    - Exploration suggestions based on testing history

    Used by:
    - RVAgentStrategy: to prioritize untested/least-tested elements
    - ScreenProcessor: to annotate screen descriptions for LLM
    - MemoryCoordinator: to track element discovery over time
    """

    def __init__(self):
        """Initialize UI coverage tracker with basic logging."""
        import logging
        self.logger = logging.getLogger("rv_agent.memory.ui_coverage")

        # Element tracking
        self.tested_elements: Dict[str, int] = {}
        self.action_type_counts: Dict[str, int] = {}
        self.screen_elements: Dict[str, Set[str]] = {}

        # Component type tracking (element_id -> component class name)
        self.element_types: Dict[str, str] = {}

        # Temporal tracking
        self.first_interactions: Dict[str, float] = {}
        self.last_interactions: Dict[str, float] = {}

        # Discovery tracking
        self.discovery_timeline: List[Dict[str, Any]] = []

        self.logger.info("[RVAGENT_DEBUG] UICoverageTracker initialized")

    def record_interaction(self, element_id: str, action_type: str = "click",
                         screen_hash: Optional[str] = None, success: bool = True,
                         component_type: Optional[str] = None) -> None:
        """
        Registra interação com elemento com tipo de ação para guidance balanceado.

        Args:
            element_id: Unique identifier for UI element
            action_type: Type of action performed
            screen_hash: Hash of screen state
            success: Whether interaction was successful
            component_type: Component type (Button, EditText, etc.) for auto-registration
        """
        try:
            current_time = time.time()

            # Auto-register element if not in element_types (ensures coverage consistency)
            if element_id not in self.element_types and component_type:
                self.element_types[element_id] = component_type

            # Track element interaction count
            was_new_element = element_id not in self.tested_elements
            self.tested_elements[element_id] = self.tested_elements.get(element_id, 0) + 1

            # Track action types
            self.action_type_counts[action_type] = self.action_type_counts.get(action_type, 0) + 1

            # Track screen-element mapping
            if screen_hash:
                if screen_hash not in self.screen_elements:
                    self.screen_elements[screen_hash] = set()
                self.screen_elements[screen_hash].add(element_id)

            # Track temporal information
            if was_new_element:
                self.first_interactions[element_id] = current_time
                self.discovery_timeline.append({
                    'element_id': element_id,
                    'action_type': action_type,
                    'screen_hash': screen_hash,
                    'timestamp': current_time,
                    'discovery_order': len(self.first_interactions)
                })

            self.last_interactions[element_id] = current_time

            # Logging with debug prefix
            status = "NEW" if was_new_element else f"#{self.tested_elements[element_id]}"
            result = "SUCCESS" if success else "FAILED"
            self.logger.debug(f"[RVAGENT_DEBUG] UI interaction: {status} {element_id} "
                            f"({action_type}) - {result}")

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Failed to record interaction: {e}")

    def is_element_untested(self, element_id: str, screen_hash: Optional[str] = None) -> bool:
        """
        Check if element has never been tested before.

        Used for metrics: tracking LLM's ability to discover new UI elements.

        Args:
            element_id: Element to check
            screen_hash: Screen context (optional)

        Returns:
            True if element is completely untested
        """
        if not element_id:
            return False
        return element_id not in self.tested_elements

    def get_element_test_count(self, element_id: str, screen_hash: Optional[str] = None) -> int:
        """
        Get how many times an element has been tested.

        Used for metrics: identifying over-tested elements (inefficient exploration).

        Args:
            element_id: Element to check
            screen_hash: Screen context (optional)

        Returns:
            Number of times element has been tested
        """
        if not element_id:
            return 0
        return self.tested_elements.get(element_id, 0)

    def get_element_priority(self, element_id: str) -> str:
        """
        Get exploration priority for element based on testing history.

        Returns:
            Priority level: "high", "medium", "low"
        """
        test_count = self.get_element_test_count(element_id)

        if test_count == 0:
            return "high"  # Untested elements get highest priority
        elif test_count <= 2:
            return "medium"  # Lightly tested elements
        else:
            return "low"  # Well-tested elements get lower priority

    def annotate_screen_elements(self, screen_description: str, screen_hash: str) -> str:
        """
        Adiciona anotações [UNTESTED]/[TESTED] à descrição da tela.

        Tipos de anotação:
        - [UNTESTED]: Maior prioridade para seleção LLM
        - [TESTED-1x]: Testado uma vez, pode precisar de mais exploração
        - [TESTED-Nx]: Testado N vezes, prioridade moderada
        - [WELL-TESTED]: Testado extensivamente, menor prioridade

        Args:
            screen_description: Original screen description
            screen_hash: Screen state hash

        Returns:
            Annotated screen description with testing status
        """
        try:
            if screen_hash not in self.screen_elements:
                self.screen_elements[screen_hash] = set()

            # For simple string-based descriptions, add annotations
            lines = screen_description.split('\n')
            annotated_lines = []

            for line in lines:
                # Extract element info from line (format: "N. description at position (x, y)")
                if '. ' in line and 'at position' in line:
                    # Simple heuristic: use description before coordinates as element_id
                    parts = line.split(' at position')
                    if len(parts) >= 2:
                        element_desc = parts[0]
                        coords_part = parts[1]  # e.g., " (500, 170)"

                        # Generate element_id - pass FULL line to extract coordinates
                        element_id = self._generate_element_id(line)

                        # Track this element for this screen
                        self.screen_elements[screen_hash].add(element_id)

                        # Generate annotation
                        annotation = self._get_element_annotation(element_id)

                        # Insert annotation after the number
                        if '. ' in element_desc:
                            number_part, desc_part = element_desc.split('. ', 1)
                            annotated_line = f"{number_part}. {annotation} {desc_part} at position{parts[1]}"
                        else:
                            annotated_line = f"{annotation} {line}"

                        annotated_lines.append(annotated_line)
                    else:
                        annotated_lines.append(line)
                else:
                    annotated_lines.append(line)

            result = '\n'.join(annotated_lines)

            # [INSTRUMENTATION] Log tracked elements for debugging
            tracked_elements = list(self.screen_elements[screen_hash])[:3]  # First 3 for brevity
            self.logger.info(
                f"[INSTRUMENTATION] UI_ELEMENTS_TRACKED: screen={screen_hash[:8]} "
                f"count={len(self.screen_elements[screen_hash])} "
                f"sample={tracked_elements}"
            )

            return result

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Screen annotation failed: {e}")
            return screen_description

    def _generate_element_id(self, element_desc: str) -> str:
        """Generate consistent element ID from description.

        Uses coordinates as primary identifier via make_element_id()
        for consistency across all components.
        """
        import re

        # PRIMARY: Extract coordinates from "at position (x, y)" or bounds
        pos_match = re.search(r'at position\s*\((\d+),\s*(\d+)\)', element_desc)
        if pos_match:
            x, y = int(pos_match.group(1)), int(pos_match.group(2))
            return make_element_id(x, y)

        # FALLBACK: Extract ID
        id_match = re.search(r'id:(\w+)', element_desc)
        if id_match:
            return f"id:{id_match.group(1)}"

        # FALLBACK: Extract quoted text
        text_match = re.search(r'"([^"]+)"', element_desc)
        if text_match:
            return f'text:"{text_match.group(1)}"'

        # FALLBACK: Extract description
        desc_match = re.search(r'desc:"([^"]+)"', element_desc)
        if desc_match:
            return f'desc:"{desc_match.group(1)}"'

        # FALLBACK: hash of description
        import hashlib
        return f"hash:{hashlib.md5(element_desc.encode()).hexdigest()[:8]}"

    def _get_element_annotation(self, element_id: str) -> str:
        """Get annotation for element based on test count."""
        count = self.get_element_test_count(element_id)

        if count == 0:
            return "[UNTESTED]"
        elif count == 1:
            return "[TESTED-1x]"
        elif count <= RVAgentConstants.WELL_TESTED_THRESHOLD:
            return f"[TESTED-{count}x]"
        else:
            return "[WELL-TESTED]"

    def get_screen_coverage_stats(self, screen_hash: str) -> UIElementStats:
        """
        Get coverage statistics for specific screen.

        Args:
            screen_hash: Screen to analyze

        Returns:
            Coverage statistics
        """
        try:
            if screen_hash not in self.screen_elements:
                return UIElementStats()

            screen_elements = self.screen_elements[screen_hash]
            total_elements = len(screen_elements)
            tested_elements = sum(1 for elem in screen_elements if elem in self.tested_elements)
            untested_elements = total_elements - tested_elements

            return UIElementStats(
                total_elements=total_elements,
                tested_elements=tested_elements,
                untested_elements=untested_elements
            )

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Coverage stats calculation failed: {e}")
            return UIElementStats()

    def get_exploration_suggestions(self, screen_hash: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get suggestions for exploration based on coverage data.

        Args:
            screen_hash: Current screen
            limit: Maximum number of suggestions

        Returns:
            List of exploration suggestions
        """
        try:
            if screen_hash not in self.screen_elements:
                return [{"suggestion": "explore_new_screen", "reason": "No elements tracked for this screen"}]

            screen_elements = self.screen_elements[screen_hash]
            untested_elements = [elem for elem in screen_elements if elem not in self.tested_elements]

            suggestions = []

            # Prioritize untested elements
            for elem in untested_elements[:limit]:
                suggestions.append({
                    "element_id": elem,
                    "suggestion": "test_untested_element",
                    "reason": "Element has never been tested",
                    "priority": "high"
                })

            # If we have suggestions, return them
            if suggestions:
                return suggestions

            # Look for lightly tested elements
            lightly_tested = [(elem, self.tested_elements[elem])
                            for elem in screen_elements
                            if elem in self.tested_elements and self.tested_elements[elem] <= 2]

            lightly_tested.sort(key=lambda x: x[1])  # Sort by test count

            for elem, count in lightly_tested[:limit]:
                suggestions.append({
                    "element_id": elem,
                    "suggestion": "retest_lightly_tested",
                    "reason": f"Element only tested {count} times",
                    "priority": "medium",
                    "test_count": count
                })

            return suggestions if suggestions else [
                {"suggestion": "explore_different_actions", "reason": "All elements well tested"}
            ]

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Exploration suggestions failed: {e}")
            return [{"suggestion": "error", "reason": str(e)}]

    def get_overall_statistics(self) -> Dict[str, Any]:
        """Get comprehensive coverage statistics."""
        try:
            total_unique_elements = len(self.tested_elements)
            total_interactions = sum(self.tested_elements.values())

            # Action type distribution
            action_distribution = dict(self.action_type_counts)

            # Discovery rate over time
            recent_discoveries = len([d for d in self.discovery_timeline
                                   if time.time() - d['timestamp'] < 300])  # Last 5 minutes

            # Most and least tested elements
            sorted_elements = sorted(self.tested_elements.items(), key=lambda x: x[1], reverse=True)
            most_tested = sorted_elements[:3] if sorted_elements else []
            least_tested = sorted_elements[-3:] if len(sorted_elements) > 3 else []

            return {
                "total_unique_elements": total_unique_elements,
                "total_interactions": total_interactions,
                "average_interactions_per_element": (total_interactions / total_unique_elements
                                                   if total_unique_elements > 0 else 0),
                "action_distribution": action_distribution,
                "recent_discoveries": recent_discoveries,
                "total_screens": len(self.screen_elements),
                "most_tested_elements": most_tested,
                "least_tested_elements": least_tested,
                "discovery_timeline_length": len(self.discovery_timeline)
            }

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Overall statistics failed: {e}")
            return {"error": str(e)}

    def reset_coverage(self) -> None:
        """Reset all coverage data (for testing or new session)."""
        self.logger.info("[RVAGENT_DEBUG] Resetting UI coverage data...")

        cleared_elements = len(self.tested_elements)
        cleared_screens = len(self.screen_elements)

        self.tested_elements.clear()
        self.action_type_counts.clear()
        self.screen_elements.clear()
        self.element_types.clear()
        self.first_interactions.clear()
        self.last_interactions.clear()
        self.discovery_timeline.clear()

        self.logger.info(f"[RVAGENT_DEBUG] UI coverage reset complete: "
                        f"{cleared_elements} elements, {cleared_screens} screens")

    def register_screen_elements(self, screen_hash: str, screen_desc: Any) -> None:
        """
        Register all elements from a ScreenDescription with their component types.

        This enables tracking coverage by component type (Button, EditText, Spinner, etc.)
        and is called during screen parsing to capture all discoverable elements.

        Args:
            screen_hash: Hash of the screen state
            screen_desc: ScreenDescription object with items
        """
        try:
            if screen_hash not in self.screen_elements:
                self.screen_elements[screen_hash] = set()

            element_count = 0
            for item in getattr(screen_desc, 'items', []):
                view = getattr(item, 'view', {}) if hasattr(item, 'view') else item.get('view', {})

                # Get component class name
                component_class = view.get('class', 'unknown')
                # Extract simple class name (e.g., "android.widget.Button" -> "Button")
                simple_class = component_class.split('.')[-1] if component_class else 'unknown'

                # Get element coordinates for ID
                bounds = view.get('bounds', [[0, 0], [0, 0]])
                if bounds and len(bounds) == 2:
                    center_x = (bounds[0][0] + bounds[1][0]) // 2
                    center_y = (bounds[0][1] + bounds[1][1]) // 2
                    element_id = make_element_id(center_x, center_y)

                    self.screen_elements[screen_hash].add(element_id)
                    if element_id not in self.element_types:
                        self.element_types[element_id] = simple_class
                    element_count += 1

            self.logger.debug(
                f"Registered {element_count} elements for screen {screen_hash[:8]}"
            )

        except Exception as e:
            self.logger.error(f"Failed to register screen elements: {e}")

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive UI coverage metrics including component type breakdown.

        Returns:
            Dict with detailed coverage metrics:
            - total_unique_elements: Number of unique elements discovered
            - total_interactions: Total interaction count
            - element_coverage: Percentage of elements tested at least once
            - elements_by_type: Count of elements per component type
            - interactions_by_type: Count of interactions per component type
            - coverage_by_type: Coverage percentage per component type
            - screens_visited: Number of unique screens visited
            - elements_per_screen: Element counts per screen
            - coverage_per_screen: Coverage percentage per screen
        """
        try:
            # Basic counts
            # Count only elements that are properly registered
            total_elements = len(self.element_types)
            # Count tested elements as those in BOTH element_types AND tested_elements
            # This ensures coverage never exceeds 100%
            tested_elements = len(set(self.tested_elements.keys()) & set(self.element_types.keys()))
            total_interactions = sum(self.tested_elements.values())

            # Elements and interactions by component type
            elements_by_type: Dict[str, int] = {}
            interactions_by_type: Dict[str, int] = {}

            for element_id, comp_type in self.element_types.items():
                elements_by_type[comp_type] = elements_by_type.get(comp_type, 0) + 1
                if element_id in self.tested_elements:
                    interactions_by_type[comp_type] = (
                        interactions_by_type.get(comp_type, 0) +
                        self.tested_elements[element_id]
                    )

            # Coverage by component type
            coverage_by_type: Dict[str, Dict[str, Any]] = {}
            for comp_type, total_count in elements_by_type.items():
                tested_count = sum(
                    1 for eid, ct in self.element_types.items()
                    if ct == comp_type and eid in self.tested_elements
                )
                coverage_by_type[comp_type] = {
                    "total": total_count,
                    "tested": tested_count,
                    "coverage": (tested_count / total_count * 100) if total_count > 0 else 0
                }

            # Screen metrics
            elements_per_screen: Dict[str, int] = {}
            coverage_per_screen: Dict[str, float] = {}

            for screen_hash, elements in self.screen_elements.items():
                screen_key = screen_hash[:8]
                elements_per_screen[screen_key] = len(elements)
                tested = sum(1 for e in elements if e in self.tested_elements)
                coverage_per_screen[screen_key] = (
                    (tested / len(elements) * 100) if elements else 0
                )

            # Element distribution by test count (only for registered elements)
            registered_and_tested = set(self.tested_elements.keys()) & set(self.element_types.keys())
            untested = total_elements - len(registered_and_tested)
            tested_once = sum(1 for eid in registered_and_tested if self.tested_elements.get(eid, 0) == 1)
            tested_multiple = sum(1 for eid in registered_and_tested if 2 <= self.tested_elements.get(eid, 0) <= 3)
            well_tested = sum(1 for eid in registered_and_tested if self.tested_elements.get(eid, 0) > 3)

            return {
                "total_unique_elements": total_elements,
                "total_interactions": total_interactions,
                "avg_interactions_per_element": (
                    total_interactions / tested_elements if tested_elements > 0 else 0
                ),
                "element_coverage": (
                    tested_elements / total_elements * 100 if total_elements > 0 else 0
                ),
                "element_distribution": {
                    "untested": untested,
                    "tested_once": tested_once,
                    "tested_multiple": tested_multiple,
                    "well_tested": well_tested
                },
                "elements_by_type": elements_by_type,
                "interactions_by_type": interactions_by_type,
                "coverage_by_type": coverage_by_type,
                "screens_visited": len(self.screen_elements),
                "elements_per_screen": elements_per_screen,
                "coverage_per_screen": coverage_per_screen
            }

        except Exception as e:
            self.logger.error(f"Failed to get comprehensive metrics: {e}")
            return {"error": str(e)}