# rvandroid/core/patterns/list_detector.py
"""
List pattern detector implementation.

This module provides a specialized detector for list patterns in Android applications.
It identifies scrollable lists, grid layouts, and recycler views to enable batch list exploration.
"""

from typing import Dict, Any, List, Optional, Set, Tuple

from rvandroid.core.patterns.ui_pattern_detector import (
    IPatternDetector, PatternType, PatternResult, PatternElement, PatternDetectorFactory
)
from rvandroid.parser.screen.visitor.model import ScreenItem, ScreenDescription
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ListDetector(IPatternDetector):
    """
    Detector for list patterns in UI.
    
    ### Architectural Decisions:
    - Implements specialized list detection using multi-factor heuristics
    - Uses DOM-based analysis with normalized node structure
    - Identifies list components based on view properties and hierarchical relationships
    - Applies confidence scoring based on repeating elements, scrollability, and layout
    
    ### Role in the System:
    - Provides reliable list pattern detection for batch action generation
    - Identifies list item relationships and structural patterns
    - Enables coherent list exploration sequences
    - Enhances testing effectiveness by supporting systematic list testing
    """
    
    def __init__(self):
        """Initialize the list detector."""
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "core.patterns.list_detector",
            {CONTEXT_COMPONENT: "ListDetector"}
        )
    
    @property
    def pattern_type(self) -> PatternType:
        """Get the pattern type."""
        return PatternType.LIST
    
    def detect(self, screen: ScreenDescription) -> PatternResult:
        """
        Detect list patterns in a screen.
        
        Args:
            screen: Parsed screen description
            
        Returns:
            PatternResult with detection results
        """
        self.logger.debug(f"Detecting list patterns in screen with {len(screen.items)} items")
        
        # Initialize pattern result
        result = PatternResult(
            type=PatternType.LIST,
            confidence=0.0,
            elements=[],
            properties={}
        )
        
        # Check if there are enough items to form a pattern
        if len(screen.items) < 3:
            self.logger.debug("Not enough items for a list pattern")
            return result
        
        # Look for list containers
        list_containers = self._find_list_containers(screen)
        
        # If no list containers found, try to detect repeating items
        if not list_containers:
            list_items, confidence = self._detect_repeating_items(screen)
            
            if confidence >= 0.7:
                result.confidence = confidence
                result.properties["list_type"] = "implicit"
                result.properties["item_count"] = len(list_items)
                
                # Add list items as elements
                for i, item in enumerate(list_items):
                    element = self._create_pattern_element(item, f"item_{i}", "list_item")
                    result.elements.append(element)
                
                self.logger.debug(f"Detected implicit list with {len(list_items)} items, "
                                 f"confidence {confidence:.2f}")
                
                return result
        
        # Process list containers
        if list_containers:
            # Find the most likely list container
            container, container_confidence = self._get_best_list_container(list_containers, screen)
            
            if container and container_confidence >= 0.7:
                # Extract list items from container
                list_items = self._get_list_items(container, screen)
                
                # Calculate confidence based on items
                item_confidence = min(1.0, len(list_items) / 10)  # Max confidence at 10+ items
                
                # Combined confidence
                confidence = (container_confidence * 0.7) + (item_confidence * 0.3)
                
                result.confidence = confidence
                
                # Determine list type
                list_type = self._determine_list_type(container)
                result.properties["list_type"] = list_type
                result.properties["item_count"] = len(list_items)
                result.properties["scrollable"] = container.view.get("scrollable", False)
                
                # Add container as an element
                container_element = self._create_pattern_element(container, "list_container", "container")
                result.elements.append(container_element)
                
                # Add list items
                for i, item in enumerate(list_items):
                    element = self._create_pattern_element(item, f"item_{i}", "list_item")
                    result.elements.append(element)
                
                # Check if we can scroll the list
                scroll_actions = [a for a in container.actions if "scroll" in a.event.lower()]
                if scroll_actions:
                    result.properties["has_scroll_actions"] = True
                    
                    # Add scroll directions available
                    directions = [
                        a.event.replace("scroll_", "") for a in scroll_actions 
                        if a.event.startswith("scroll_")
                    ]
                    if directions:
                        result.properties["scroll_directions"] = directions
                
                self.logger.debug(f"Detected {list_type} list with {len(list_items)} items, "
                                 f"confidence {confidence:.2f}")
        
        return result
    
    def _find_list_containers(self, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Find potential list container elements.
        
        Args:
            screen: Parsed screen description
            
        Returns:
            List of potential list container items
        """
        containers = []
        
        for item in screen.items:
            # Skip invisible elements
            if not self._is_visible(item):
                continue
            
            # Check for list container classes
            view = item.view
            class_name = view.get("class", "").lower()
            
            # Direct list container classes
            if any(container_cls in class_name for container_cls in [
                "listview", "recyclerview", "gridview", "expandablelistview", "scrollview",
                "horizontalscrollview", "nestedscrollview", "viewpager"
            ]):
                containers.append(item)
                continue
            
            # Check resource ID hints
            resource_id = view.get("resource_id", "").lower()
            if any(id_hint in resource_id for id_hint in [
                "list", "recycler", "grid", "scroll"
            ]):
                containers.append(item)
                continue
            
            # Check scrollability
            if view.get("scrollable", False):
                containers.append(item)
                continue
            
            # Check if it has many children with similar structure
            if self._has_repeating_children(item, screen):
                containers.append(item)
        
        return containers
    
    def _is_visible(self, item: ScreenItem) -> bool:
        """
        Check if an element is visible.
        
        Args:
            item: Screen item to check
            
        Returns:
            True if the element is visible
        """
        view = item.view
        
        # Check visibility
        if view.get("visibility") == "gone" or view.get("visibility") == "invisible":
            return False
        
        # Check bounds
        bounds = view.get("bounds", {})
        if not bounds:
            return False
            
        width = bounds.get("right", 0) - bounds.get("left", 0)
        height = bounds.get("bottom", 0) - bounds.get("top", 0)
        
        # Ensure minimum size
        if width <= 0 or height <= 0:
            return False
        
        return True
    
    def _has_repeating_children(self, item: ScreenItem, screen: ScreenDescription) -> bool:
        """
        Check if an item has repeating children with similar structure.
        
        Args:
            item: Screen item to check
            screen: Screen description
            
        Returns:
            True if the item has repeating children
        """
        # Get the children IDs
        children_ids = item.view.get("children", [])
        
        if len(children_ids) < 3:
            return False
        
        # Find the actual child items
        children = []
        for child_id in children_ids:
            for screen_item in screen.items:
                if screen_item.view.get("id") == child_id:
                    children.append(screen_item)
                    break
        
        # Need at least 3 children for a list
        if len(children) < 3:
            return False
        
        # Check if children have similar classes and structure
        classes = {}
        for child in children:
            class_name = child.view.get("class", "")
            classes[class_name] = classes.get(class_name, 0) + 1
        
        # If one class represents majority of children, likely a list
        most_common_class = max(classes.items(), key=lambda x: x[1])
        ratio = most_common_class[1] / len(children)
        
        return ratio >= 0.7  # If 70% of children are the same class, probably a list
    
    def _detect_repeating_items(self, screen: ScreenDescription) -> Tuple[List[ScreenItem], float]:
        """
        Detect repeating items that might form an implicit list.
        
        Args:
            screen: Parsed screen description
            
        Returns:
            Tuple of (list of items, confidence)
        """
        # Group items by class
        class_groups = {}
        
        for item in screen.items:
            if not self._is_visible(item):
                continue
                
            class_name = item.view.get("class", "")
            if class_name not in class_groups:
                class_groups[class_name] = []
            class_groups[class_name].append(item)
        
        # Find the largest group with at least 3 items
        largest_group = []
        for group in class_groups.values():
            if len(group) >= 3 and len(group) > len(largest_group):
                largest_group = group
        
        if not largest_group:
            return [], 0.0
        
        # Check if items in the group have similar structure
        if self._have_similar_structure(largest_group):
            # Check if they're vertically or horizontally aligned
            alignment_score = self._check_alignment(largest_group)
            
            # Calculate confidence based on group size and alignment
            size_confidence = min(1.0, len(largest_group) / 10)  # Max confidence at 10+ items
            confidence = (size_confidence * 0.7) + (alignment_score * 0.3)
            
            return largest_group, confidence
        
        return [], 0.0
    
    def _have_similar_structure(self, items: List[ScreenItem]) -> bool:
        """
        Check if items have similar structure.
        
        Args:
            items: List of screen items
            
        Returns:
            True if items have similar structure
        """
        if not items:
            return False
            
        # Count action types
        action_counts = {}
        for item in items:
            action_types = set(a.event for a in item.actions)
            action_types_str = ','.join(sorted(action_types))
            
            action_counts[action_types_str] = action_counts.get(action_types_str, 0) + 1
        
        # If one action pattern represents majority of items, they're similar
        most_common = max(action_counts.values())
        ratio = most_common / len(items)
        
        return ratio >= 0.7  # If 70% have same action pattern, they're similar
    
    def _check_alignment(self, items: List[ScreenItem]) -> float:
        """
        Check if items are aligned vertically or horizontally.
        
        Args:
            items: List of screen items
            
        Returns:
            Alignment score (0.0-1.0)
        """
        if not items:
            return 0.0
            
        # Extract bounds
        lefts = []
        rights = []
        tops = []
        bottoms = []
        
        for item in items:
            bounds = item.view.get("bounds", {})
            if bounds:
                lefts.append(bounds.get("left", 0))
                rights.append(bounds.get("right", 0))
                tops.append(bounds.get("top", 0))
                bottoms.append(bounds.get("bottom", 0))
        
        if not lefts:
            return 0.0
            
        # Calculate standard deviations
        def std_dev(values):
            if not values:
                return 0
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            return variance ** 0.5
        
        # For horizontal alignment, left positions should be similar
        left_std = std_dev(lefts)
        left_mean = sum(lefts) / len(lefts)
        horizontal_alignment = 1.0 - min(1.0, left_std / max(1, left_mean))
        
        # For vertical alignment, check if tops form a pattern
        vertical_alignment = 0.0
        if len(tops) >= 3:
            # Sort by top position
            sorted_tops = sorted(tops)
            
            # Check for consistent spacing
            diffs = [sorted_tops[i+1] - sorted_tops[i] for i in range(len(sorted_tops)-1)]
            
            if diffs:
                diff_std = std_dev(diffs)
                diff_mean = sum(diffs) / len(diffs)
                
                if diff_mean > 0:
                    diff_consistency = 1.0 - min(1.0, diff_std / diff_mean)
                    vertical_alignment = diff_consistency
        
        # Return the better of the two alignments
        return max(horizontal_alignment, vertical_alignment)
    
    def _get_best_list_container(self, containers: List[ScreenItem], 
                              screen: ScreenDescription) -> Tuple[Optional[ScreenItem], float]:
        """
        Get the best list container from candidates.
        
        Args:
            containers: List of container candidates
            screen: Screen description
            
        Returns:
            Tuple of (best container, confidence)
        """
        if not containers:
            return None, 0.0
            
        # Score each container
        scored_containers = []
        
        for container in containers:
            score = 0.0
            
            # Check class name
            class_name = container.view.get("class", "").lower()
            
            # Direct list classes get high scores
            if "listview" in class_name or "recyclerview" in class_name:
                score += 0.6
            elif "gridview" in class_name:
                score += 0.5
            elif "scrollview" in class_name:
                score += 0.4
            
            # Check scrollability
            if container.view.get("scrollable", True):
                score += 0.2
            
            # Check resource ID
            resource_id = container.view.get("resource_id", "").lower()
            if "list" in resource_id or "recycler" in resource_id:
                score += 0.1
            
            # Check children count - more children = more likely a list
            children_count = len(container.view.get("children", []))
            children_score = min(0.3, children_count / 30)  # Max 0.3 at 30+ children
            score += children_score
            
            # Check if has scroll actions
            has_scroll = any("scroll" in a.event.lower() for a in container.actions)
            if has_scroll:
                score += 0.1
            
            # Add to scored containers
            scored_containers.append((container, min(1.0, score)))
        
        # Return the highest scoring container
        if not scored_containers:
            return None, 0.0
            
        return max(scored_containers, key=lambda x: x[1])
    
    def _get_list_items(self, container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Get the list items from a container.
        
        Args:
            container: List container
            screen: Screen description
            
        Returns:
            List of list items
        """
        # Get the children IDs
        children_ids = container.view.get("children", [])
        
        # Find the actual child items
        children = []
        for child_id in children_ids:
            for screen_item in screen.items:
                if screen_item.view.get("id") == child_id:
                    children.append(screen_item)
                    break
        
        # If container has direct children, those are the list items
        if children:
            return children
        
        # Otherwise, try to infer list items from layout
        return self._infer_list_items(container, screen)
    
    def _infer_list_items(self, container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Infer list items based on layout when direct children are not available.
        
        Args:
            container: List container
            screen: Screen description
            
        Returns:
            List of inferred list items
        """
        # Get container bounds
        container_bounds = container.view.get("bounds", {})
        if not container_bounds:
            return []
            
        c_left = container_bounds.get("left", 0)
        c_right = container_bounds.get("right", 0)
        c_top = container_bounds.get("top", 0)
        c_bottom = container_bounds.get("bottom", 0)
        
        # Find items that are visually contained within the container
        contained_items = []
        
        for item in screen.items:
            # Skip the container itself
            if item.view.get("id") == container.view.get("id"):
                continue
                
            # Skip invisible items
            if not self._is_visible(item):
                continue
            
            # Get item bounds
            item_bounds = item.view.get("bounds", {})
            if not item_bounds:
                continue
                
            i_left = item_bounds.get("left", 0)
            i_right = item_bounds.get("right", 0)
            i_top = item_bounds.get("top", 0)
            i_bottom = item_bounds.get("bottom", 0)
            
            # Check if item is contained within container
            if (i_left >= c_left and i_right <= c_right and
                i_top >= c_top and i_bottom <= c_bottom):
                contained_items.append(item)
        
        # Group by class to find the most common type (likely list items)
        class_groups = {}
        
        for item in contained_items:
            class_name = item.view.get("class", "")
            if class_name not in class_groups:
                class_groups[class_name] = []
            class_groups[class_name].append(item)
        
        # Find the largest group with at least 2 items
        largest_group = []
        for group in class_groups.values():
            if len(group) >= 2 and len(group) > len(largest_group):
                largest_group = group
        
        return largest_group
    
    def _determine_list_type(self, container: ScreenItem) -> str:
        """
        Determine the type of list.
        
        Args:
            container: List container
            
        Returns:
            List type string
        """
        class_name = container.view.get("class", "").lower()
        
        if "gridview" in class_name or "grid" in class_name:
            return "grid"
        elif "horizontalscrollview" in class_name or "horizontal" in class_name:
            return "horizontal"
        elif "recyclerview" in class_name:
            # Determine orientation from bounds
            bounds = container.view.get("bounds", {})
            if bounds:
                width = bounds.get("right", 0) - bounds.get("left", 0)
                height = bounds.get("bottom", 0) - bounds.get("top", 0)
                
                if width > height * 2:  # Much wider than tall
                    return "horizontal"
            
            return "vertical"  # Default for RecyclerView
        else:
            return "vertical"  # Default for most lists
    
    def _create_pattern_element(self, item: ScreenItem, id_suffix: str, role: str) -> PatternElement:
        """
        Create a pattern element from a screen item.
        
        Args:
            item: Screen item
            id_suffix: Suffix to add to the element ID
            role: Role of the element in the pattern
            
        Returns:
            PatternElement instance
        """
        # Use resource ID if available, otherwise generate one
        resource_id = item.view.get("resource_id", "")
        if resource_id:
            element_id = resource_id
        else:
            element_id = f"generated_{id_suffix}"
        
        # Create pattern element
        element = PatternElement(
            id=element_id,
            role=role,
            view=item.view,
            actions=item.actions
        )
        
        # Add properties based on view
        if "text" in item.view:
            element.properties["text"] = item.view["text"]
            
        if "bounds" in item.view:
            element.properties["bounds"] = item.view["bounds"]
            
        if "class" in item.view:
            element.properties["class"] = item.view["class"]
            
        # For list items, note if they're clickable
        if role == "list_item":
            element.properties["clickable"] = item.view.get("clickable", False)
            
            # Note if the item has direct click actions
            element.properties["has_click_action"] = any(
                a.event == "click" for a in item.actions
            )
        
        # For container, note if it's scrollable
        if role == "container":
            element.properties["scrollable"] = item.view.get("scrollable", False)
        
        return element


# Register the detector with the factory
PatternDetectorFactory.register(ListDetector)