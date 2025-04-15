# rvandroid/core/patterns/tab_detector.py
"""
Tab pattern detector implementation.

This module provides a specialized detector for tab patterns in Android applications.
It identifies tab layouts, tab elements, and associated content to enable systematic tab navigation.
"""

from typing import Dict, Any, List, Optional, Set, Tuple

from rvandroid.core.patterns.ui_pattern_detector import (
    IPatternDetector, PatternType, PatternResult, PatternElement, PatternDetectorFactory
)
from rvandroid.parser.screen.visitor.model import ScreenItem, ScreenDescription
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class TabDetector(IPatternDetector):
    """
    Detector for tab patterns in UI.
    
    ### Architectural Decisions:
    - Implements specialized tab detection using multi-factor heuristics
    - Uses DOM-based analysis with normalized Node structure
    - Identifies tab components based on view properties and hierarchical relationships
    - Applies confidence scoring based on tab layout recognition and structural patterns
    
    ### Role in the System:
    - Provides reliable tab pattern detection for batch action generation
    - Identifies tab navigation components and related content areas
    - Enables coherent tab exploration sequences
    - Enhances testing effectiveness by supporting systematic tab testing
    """
    
    def __init__(self):
        """Initialize the tab detector."""
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "core.patterns.tab_detector",
            {CONTEXT_COMPONENT: "TabDetector"}
        )
    
    @property
    def pattern_type(self) -> PatternType:
        """Get the pattern type."""
        return PatternType.TABS
    
    def detect(self, screen: ScreenDescription, state_data: Dict[str, Any]) -> PatternResult:
        """
        Detect tab patterns in a screen.
        
        Args:
            screen: Parsed screen description
            state_data: Additional state data
            
        Returns:
            PatternResult with detection results
        """
        self.logger.debug(f"Detecting tab patterns in screen with {len(screen.items)} items")
        
        # Initialize pattern result
        result = PatternResult(
            type=PatternType.TABS,
            confidence=0.0,
            elements=[],
            properties={}
        )
        
        # Check if there are enough items to form a pattern
        if len(screen.items) < 2:
            self.logger.debug("Not enough items for a tab pattern")
            return result
        
        # Find potential tab containers
        tab_containers = self._find_tab_containers(screen)
        
        if not tab_containers:
            self.logger.debug("No tab containers found")
            return result
        
        # Find the best tab container
        best_container, container_confidence = self._get_best_tab_container(tab_containers, screen)
        
        if not best_container or container_confidence < 0.6:
            self.logger.debug(f"No strong tab container candidate (confidence: {container_confidence:.2f})")
            return result
        
        # Extract tab items from container
        tab_items = self._get_tab_items(best_container, screen)
        
        # Calculate confidence based on tabs found
        if not tab_items:
            self.logger.debug("No tab items found in container")
            return result
        
        # Better confidence with more tab items (up to 5)
        item_confidence = min(0.9, 0.5 + (len(tab_items) * 0.1))
        
        # Identify active tab
        active_tab, active_tab_confidence = self._identify_active_tab(tab_items)
        
        # Combine confidence scores
        confidence = (container_confidence * 0.5) + (item_confidence * 0.4) + (active_tab_confidence * 0.1)
        result.confidence = confidence
        
        # Add container to result
        container_element = self._create_pattern_element(best_container, "tab_container", "container")
        result.elements.append(container_element)
        
        # Add tab items to result
        for i, tab in enumerate(tab_items):
            role = "active_tab" if active_tab and tab.view.get("id") == active_tab.view.get("id") else "tab"
            element = self._create_pattern_element(tab, f"tab_{i}", role)
            result.elements.append(element)
        
        # Try to identify content area
        content_area = self._identify_content_area(best_container, active_tab, screen)
        if content_area:
            content_element = self._create_pattern_element(content_area, "content_area", "content")
            result.elements.append(content_element)
            result.properties["has_content_area"] = True
        
        # Set additional properties
        result.properties["tab_count"] = len(tab_items)
        result.properties["has_active_tab"] = active_tab is not None
        result.properties["tab_layout_type"] = self._determine_tab_layout_type(best_container, tab_items)
        
        self.logger.debug(f"Detected tab pattern with confidence {confidence:.2f}, "
                        f"{len(tab_items)} tabs, active tab: {active_tab is not None}")
        
        return result
    
    def _find_tab_containers(self, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Find potential tab container elements.
        
        Args:
            screen: Parsed screen description
            
        Returns:
            List of potential tab container items
        """
        containers = []
        
        for item in screen.items:
            view = item.view
            
            # Skip invisible elements
            if not self._is_visible(item):
                continue
            
            # Check class name for tab indicators
            class_name = view.get("class", "").lower()
            
            # Direct tab container classes
            if any(tab_cls in class_name for tab_cls in [
                "tablayout", "tabhost", "tabwidget", "viewpager", "pagerstrip",
                "pagerindicator", "slidingtablayout", "tabcontainer"
            ]):
                containers.append(item)
                continue
            
            # Check resource ID for tab indicators
            resource_id = view.get("resource_id", "").lower()
            if any(id_hint in resource_id for id_hint in [
                "tab", "tabbar", "tabs", "tablayout", "viewpager", "pager"
            ]):
                containers.append(item)
                continue
            
            # Check layout characteristics - horizontal layout with several clickable children
            if self._has_tab_layout_characteristics(item, screen):
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
    
    def _has_tab_layout_characteristics(self, item: ScreenItem, screen: ScreenDescription) -> bool:
        """
        Check if an item has characteristics typical of a tab layout.
        
        Args:
            item: Screen item to check
            screen: Screen description
            
        Returns:
            True if the item has tab layout characteristics
        """
        # Get child IDs
        child_ids = item.view.get("children", [])
        
        # Tabs typically have at least 2 children
        if len(child_ids) < 2:
            return False
        
        # Find the children
        children = []
        for child_id in child_ids:
            for screen_item in screen.items:
                if screen_item.view.get("id") == child_id:
                    children.append(screen_item)
                    break
        
        # Count clickable children - tabs are typically clickable
        clickable_count = sum(1 for child in children if child.view.get("clickable", False))
        
        # If most children are clickable, it might be a tab layout
        if clickable_count >= len(children) * 0.7:
            # Check if children are arranged horizontally
            return self._is_horizontal_arrangement(children)
        
        return False
    
    def _is_horizontal_arrangement(self, items: List[ScreenItem]) -> bool:
        """
        Check if items are arranged horizontally.
        
        Args:
            items: List of screen items
            
        Returns:
            True if items are arranged horizontally
        """
        if not items or len(items) < 2:
            return False
        
        # Extract bounds
        bounds_list = []
        for item in items:
            bounds = item.view.get("bounds", {})
            if bounds:
                bounds_list.append((
                    bounds.get("left", 0),
                    bounds.get("top", 0),
                    bounds.get("right", 0),
                    bounds.get("bottom", 0)
                ))
        
        if len(bounds_list) < 2:
            return False
        
        # Check if items are mostly at the same vertical position
        # but different horizontal positions
        tops = [b[1] for b in bounds_list]
        lefts = [b[0] for b in bounds_list]
        
        # Calculate average top position
        avg_top = sum(tops) / len(tops)
        
        # Check if tops are similar (within 20% of height)
        heights = [b[3] - b[1] for b in bounds_list]
        avg_height = sum(heights) / len(heights) if heights else 1
        height_threshold = max(20, avg_height * 0.2)  # 20px or 20% of average height
        
        vertical_alignment = all(abs(top - avg_top) <= height_threshold for top in tops)
        
        # Check if lefts are distributed (not all in the same place)
        lefts_variation = max(lefts) - min(lefts)
        screen_width = max([b[2] for b in bounds_list], default=1000)  # Estimate screen width
        
        horizontal_distribution = lefts_variation > (screen_width * 0.3)  # Items span at least 30% of width
        
        return vertical_alignment and horizontal_distribution
    
    def _get_best_tab_container(self, containers: List[ScreenItem], 
                           screen: ScreenDescription) -> Tuple[Optional[ScreenItem], float]:
        """
        Get the best tab container from candidates.
        
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
            
            # Direct tab classes get high scores
            if "tablayout" in class_name:
                score += 0.7
            elif "tabhost" in class_name or "tabwidget" in class_name:
                score += 0.6
            elif "viewpager" in class_name:
                score += 0.5
            elif "pagerindicator" in class_name or "pagerstrip" in class_name:
                score += 0.5
            
            # Check resource ID
            resource_id = container.view.get("resource_id", "").lower()
            if "tab" in resource_id:
                score += 0.2
            elif "pager" in resource_id:
                score += 0.15
            
            # Check position - tabs often at top of screen
            bounds = container.view.get("bounds", {})
            if bounds:
                top = bounds.get("top", 0)
                # Near top of screen but not at the very top (allowing for toolbar)
                if 50 <= top <= 200:
                    score += 0.1
            
            # Check children count - tab bars typically have 2-5 tabs
            children = self._get_direct_children(container, screen)
            children_count = len(children)
            
            if 2 <= children_count <= 5:
                score += 0.1
            elif children_count > 5:
                score += 0.05
            
            # Check if children are clickable (tabs should be clickable)
            clickable_children = sum(1 for child in children if child.view.get("clickable", False))
            if clickable_children >= children_count * 0.7:
                score += 0.1
            
            # Add to scored containers
            scored_containers.append((container, min(1.0, score)))
        
        # Return the highest scoring container
        if not scored_containers:
            return None, 0.0
        
        return max(scored_containers, key=lambda x: x[1])
    
    def _get_direct_children(self, container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Get direct children of a container.
        
        Args:
            container: Container element
            screen: Screen description
            
        Returns:
            List of direct children
        """
        child_ids = container.view.get("children", [])
        
        children = []
        for child_id in child_ids:
            for item in screen.items:
                if item.view.get("id") == child_id:
                    children.append(item)
                    break
        
        return children
    
    def _get_tab_items(self, container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Get the tab items from a container.
        
        Args:
            container: Tab container
            screen: Screen description
            
        Returns:
            List of tab items
        """
        # Get direct children first
        children = self._get_direct_children(container, screen)
        
        # If children exist and seem to be tabs, return them
        if children and self._items_look_like_tabs(children):
            return children
        
        # If direct children don't look like tabs, they might be layout containers
        # Try to find tab items within these containers
        if children:
            potential_tabs = []
            for child in children:
                grandchildren = self._get_direct_children(child, screen)
                if grandchildren and self._items_look_like_tabs(grandchildren):
                    potential_tabs.extend(grandchildren)
            
            if potential_tabs:
                return potential_tabs
        
        # If container has no children or they don't look like tabs,
        # try to infer tabs visually
        return self._infer_tab_items(container, screen)
    
    def _items_look_like_tabs(self, items: List[ScreenItem]) -> bool:
        """
        Check if items look like tabs.
        
        Args:
            items: List of items to check
            
        Returns:
            True if items look like tabs
        """
        if not items:
            return False
        
        # Count items with tab-like properties
        tab_like_count = 0
        
        for item in items:
            # Most tabs are clickable
            if not item.view.get("clickable", False):
                continue
            
            # Check class name
            class_name = item.view.get("class", "").lower()
            if "tab" in class_name:
                tab_like_count += 1
                continue
            
            # Check resource ID
            resource_id = item.view.get("resource_id", "").lower()
            if "tab" in resource_id:
                tab_like_count += 1
                continue
            
            # Check if small-ish and width similar to others
            bounds = item.view.get("bounds", {})
            if bounds:
                width = bounds.get("right", 0) - bounds.get("left", 0)
                height = bounds.get("bottom", 0) - bounds.get("top", 0)
                
                # Tabs are typically wider than tall
                if width > height and height < 150:
                    tab_like_count += 1
                    continue
        
        # If most items look like tabs, return true
        return tab_like_count >= len(items) * 0.7
    
    def _infer_tab_items(self, container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Infer tab items when direct children don't work.
        
        Args:
            container: Tab container
            screen: Screen description
            
        Returns:
            List of inferred tab items
        """
        # Get container bounds
        container_bounds = container.view.get("bounds", {})
        if not container_bounds:
            return []
        
        c_left = container_bounds.get("left", 0)
        c_right = container_bounds.get("right", 0)
        c_top = container_bounds.get("top", 0)
        c_bottom = container_bounds.get("bottom", 0)
        
        # Find items contained within container bounds
        contained_items = []
        for item in screen.items:
            # Skip container itself
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
                
                # Tabs are typically clickable
                if item.view.get("clickable", False):
                    contained_items.append(item)
        
        # Try to identify tabs among contained items
        tab_candidates = []
        for item in contained_items:
            # Check class name
            class_name = item.view.get("class", "").lower()
            if "tab" in class_name:
                tab_candidates.append(item)
                continue
            
            # Check resource ID
            resource_id = item.view.get("resource_id", "").lower()
            if "tab" in resource_id:
                tab_candidates.append(item)
                continue
            
            # Check if it has text and is clickable
            text = item.view.get("text", "")
            if text and item.view.get("clickable", False):
                tab_candidates.append(item)
        
        # If we have at least 2 candidates, it might be tabs
        if len(tab_candidates) >= 2:
            # Check if they're arranged horizontally
            if self._is_horizontal_arrangement(tab_candidates):
                return tab_candidates
        
        # If we still don't have tabs, look for horizontally arranged text views
        if not tab_candidates:
            text_views = []
            for item in contained_items:
                if (item.view.get("text", "") and 
                    ("textview" in item.view.get("class", "").lower() or 
                     item.view.get("clickable", False))):
                    text_views.append(item)
            
            # If text views are arranged horizontally, they might be tabs
            if len(text_views) >= 2 and self._is_horizontal_arrangement(text_views):
                return text_views
        
        return tab_candidates
    
    def _identify_active_tab(self, tab_items: List[ScreenItem]) -> Tuple[Optional[ScreenItem], float]:
        """
        Identify which tab is currently active.
        
        Args:
            tab_items: List of tab items
            
        Returns:
            Tuple of (active tab, confidence)
        """
        if not tab_items:
            return None, 0.0
        
        candidates = []
        
        for item in tab_items:
            score = 0.0
            view = item.view
            
            # Check for "selected" or "checked" state
            if view.get("selected", False):
                score += 0.5
            
            if view.get("checked", False):
                score += 0.4
            
            # Check text style - active tabs often have different text style
            text_color = view.get("text_color")
            if text_color:
                score += 0.2
            
            text_style = view.get("text_style")
            if text_style:
                if "bold" in str(text_style).lower():
                    score += 0.2
            
            # Check background - active tabs often have different background
            background = view.get("background")
            if background:
                score += 0.2
            
            # Check content description
            content_desc = view.get("content_description", "").lower()
            if "selected" in content_desc or "active" in content_desc:
                score += 0.3
            
            # Check class name for indicators
            class_name = view.get("class", "").lower()
            if "selected" in class_name or "active" in class_name:
                score += 0.3
            
            # Check resource ID for indicators
            resource_id = view.get("resource_id", "").lower()
            if "selected" in resource_id or "active" in resource_id:
                score += 0.3
            
            candidates.append((item, min(1.0, score)))
        
        # Return the item with highest score if it's high enough
        if candidates:
            best_candidate = max(candidates, key=lambda x: x[1])
            if best_candidate[1] >= 0.3:  # Minimum confidence threshold
                return best_candidate
        
        # If no clear active tab, just return the first one with low confidence
        return (tab_items[0], 0.1) if tab_items else (None, 0.0)
    
    def _identify_content_area(self, container: ScreenItem, active_tab: Optional[ScreenItem], 
                           screen: ScreenDescription) -> Optional[ScreenItem]:
        """
        Try to identify the content area associated with tabs.
        
        Args:
            container: Tab container
            active_tab: Currently active tab
            screen: Screen description
            
        Returns:
            Content area item or None
        """
        # Get container bounds
        container_bounds = container.view.get("bounds", {})
        if not container_bounds:
            return None
        
        container_bottom = container_bounds.get("bottom", 0)
        
        # Look for large containers below the tab bar
        candidates = []
        
        for item in screen.items:
            # Skip small items and invisible items
            if not self._is_visible(item) or item.view.get("id") == container.view.get("id"):
                continue
            
            # Get item bounds
            bounds = item.view.get("bounds", {})
            if not bounds:
                continue
            
            item_top = bounds.get("top", 0)
            
            # Check if item is below tab container
            if item_top < container_bottom:
                continue
            
            # Calculate size
            width = bounds.get("right", 0) - bounds.get("left", 0)
            height = bounds.get("bottom", 0) - bounds.get("top", 0)
            
            # Content areas are typically large
            item_size = width * height
            
            # Check for content area indicators
            score = 0.0
            
            # Size score - larger items more likely to be content areas
            size_score = min(0.5, item_size / 500000)  # Cap at 0.5 for very large items
            score += size_score
            
            # Check class name for content indicators
            class_name = item.view.get("class", "").lower()
            if "viewpager" in class_name:
                score += 0.5
            elif "content" in class_name or "container" in class_name:
                score += 0.3
            elif "framelayout" in class_name or "relativelayout" in class_name:
                score += 0.2
            
            # Check resource ID
            resource_id = item.view.get("resource_id", "").lower()
            if "content" in resource_id or "container" in resource_id:
                score += 0.3
            elif "pager" in resource_id:
                score += 0.4
            
            # Check proximity to tab bar
            proximity = 1.0 - min(1.0, (item_top - container_bottom) / 300)  # Closer is better
            score += proximity * 0.2
            
            candidates.append((item, score))
        
        # Return the highest scoring candidate if it's good enough
        if candidates:
            best_candidate = max(candidates, key=lambda x: x[1])
            if best_candidate[1] >= 0.5:  # Minimum confidence threshold
                return best_candidate[0]
        
        return None
    
    def _determine_tab_layout_type(self, container: ScreenItem, tab_items: List[ScreenItem]) -> str:
        """
        Determine the type of tab layout.
        
        Args:
            container: Tab container
            tab_items: List of tab items
            
        Returns:
            Tab layout type string
        """
        # Check container class name first
        class_name = container.view.get("class", "").lower()
        
        if "tablayout" in class_name:
            return "material_tabs"
        elif "tabhost" in class_name or "tabwidget" in class_name:
            return "classic_tabs"
        elif "viewpager" in class_name:
            return "viewpager_tabs"
        
        # Check container bounds for positioning clues
        bounds = container.view.get("bounds", {})
        if bounds:
            top = bounds.get("top", 0)
            if top <= 80:  # Near top of screen
                return "top_tabs"
            
            width = bounds.get("right", 0) - bounds.get("left", 0)
            height = bounds.get("bottom", 0) - bounds.get("top", 0)
            
            # If tab container is taller than wide, might be side tabs
            if height > width:
                return "side_tabs"
        
        # Default to standard tabs
        return "standard_tabs"
    
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
            
        if "content_description" in item.view:
            element.properties["content_description"] = item.view["content_description"]
            
        if "bounds" in item.view:
            element.properties["bounds"] = item.view["bounds"]
            
        if "class" in item.view:
            element.properties["class"] = item.view["class"]
        
        # For tab items, note if they're selected
        if role == "tab" or role == "active_tab":
            element.properties["selected"] = item.view.get("selected", False)
            element.properties["checked"] = item.view.get("checked", False)
            element.properties["clickable"] = item.view.get("clickable", False)
            
            # Note if the tab has direct click actions
            element.properties["has_click_action"] = any(
                a.event == "click" for a in item.actions
            )
        
        # For content areas, note size and position
        if role == "content":
            bounds = item.view.get("bounds", {})
            if bounds:
                width = bounds.get("right", 0) - bounds.get("left", 0)
                height = bounds.get("bottom", 0) - bounds.get("top", 0)
                element.properties["width"] = width
                element.properties["height"] = height
        
        return element


# Register the detector with the factory
PatternDetectorFactory.register(TabDetector)