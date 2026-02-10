# rvandroid/analysis/patterns/dialog_detector.py
"""
Dialog pattern detector implementation.

This module provides a specialized detector for dialog patterns in Android applications.
It identifies dialogs, alerts, modals, and confirmation windows to enable appropriate
dialog interaction strategies.
"""

from typing import List, Optional, Tuple

from rvandroid.analysis.patterns.pattern_data import PatternType, PatternData, PatternResult
from rvandroid.analysis.patterns.pattern_detector import BasePatternDetector
from rvandroid.parser.screen.visitor.model import ScreenItem, ScreenDescription
from rvandroid.util.error.error_handler import ErrorHandler


class DialogDetector(BasePatternDetector):
    """
    Detector for dialog patterns in UI.

    ### Architectural Decisions:
    - Implements specialized detection for dialogs, alerts, and modal windows
    - Uses visual characteristics and component analysis for dialog identification
    - Differentiates between dialog types (alert, confirmation, input, etc.)
    - Identifies dialog components (title, message, buttons) for structured interaction

    ### Role in the System:
    - Provides reliable dialog pattern detection for batch action generation
    - Identifies dialog components for appropriate interaction sequences
    - Enables systematic testing of dialog responses
    - Supports comprehensive coverage of dialog-based functionality
    """

    def __init__(self):
        """Initialize the dialog detector."""
        super().__init__()
        self.error_handler = ErrorHandler.get_instance()

    @property
    def pattern_type(self) -> PatternType:
        """Get the pattern type."""
        return PatternType.DIALOG

    def detect(self, screen: ScreenDescription) -> PatternResult:
        """
        Detect dialog patterns in a screen.

        Args:
            screen: Parsed screen description

        Returns:
            PatternResult with detection results
        """
        self.logger.debug(f"Detecting dialog patterns in screen with {len(screen.items)} items")

        # Initialize pattern result
        result = self.create_base_result(PatternType.DIALOG)

        # Check if there are enough items to form a pattern
        if len(screen.items) < 2:
            self.logger.debug("Not enough items for a dialog pattern")
            return result

        # Look for dialog containers
        dialog_container = self._find_dialog_container(screen)

        if not dialog_container:
            self.logger.debug("No dialog container found")
            return result

        # Calculate confidence based on dialog characteristics
        dialog_confidence = self._calculate_dialog_confidence(dialog_container, screen)

        if dialog_confidence < 0.6:
            self.logger.debug(f"Low confidence in dialog pattern: {dialog_confidence:.2f}")
            return result

        # Identify dialog components
        dialog_title = self._find_dialog_title(dialog_container, screen)
        dialog_message = self._find_dialog_message(dialog_container, screen)
        dialog_buttons = self._find_dialog_buttons(dialog_container, screen)
        dialog_inputs = self._find_dialog_inputs(dialog_container, screen)

        # Set pattern confidence and elements count
        result.confidence = dialog_confidence
        result.elements_count = 1  # Container
        if dialog_title:
            result.elements_count += 1
        if dialog_message:
            result.elements_count += 1
        result.elements_count += len(dialog_buttons) + len(dialog_inputs)

        # Determine dialog type
        dialog_type = self._determine_dialog_type(
            dialog_container, dialog_title, dialog_message, dialog_buttons, dialog_inputs)

        result.properties["dialog_type"] = dialog_type
        result.properties["has_title"] = dialog_title is not None
        result.properties["has_message"] = dialog_message is not None
        result.properties["button_count"] = len(dialog_buttons)
        result.properties["has_inputs"] = len(dialog_inputs) > 0
        result.properties["input_count"] = len(dialog_inputs)

        # Add container with pattern data
        container_pattern = self.create_pattern_data(
            dialog_container,
            role="container",
            confidence=dialog_confidence,
            properties={
                "dialog_type": dialog_type,
                "has_title": dialog_title is not None,
                "has_message": dialog_message is not None,
                "button_count": len(dialog_buttons),
                "has_inputs": len(dialog_inputs) > 0
            }
        )
        self.apply_pattern_to_item(dialog_container, container_pattern)

        # Add title if found
        if dialog_title:
            title_pattern = self.create_pattern_data(
                dialog_title,
                role="title",
                confidence=dialog_confidence,
                properties={
                    "text": dialog_title.view.get("text", "")
                }
            )
            self.apply_pattern_to_item(dialog_title, title_pattern)

        # Add message if found
        if dialog_message:
            message_pattern = self.create_pattern_data(
                dialog_message,
                role="message",
                confidence=dialog_confidence,
                properties={
                    "text": dialog_message.view.get("text", "")
                }
            )
            self.apply_pattern_to_item(dialog_message, message_pattern)

        # Add buttons
        for i, button in enumerate(dialog_buttons):
            # Determine button role (positive, negative, neutral)
            button_role = self._determine_button_role(button, i, len(dialog_buttons))

            button_pattern = self.create_pattern_data(
                button,
                role=button_role,
                confidence=dialog_confidence,
                properties={
                    "button_index": i,
                    "button_text": button.view.get("text", ""),
                    "clickable": button.view.get("clickable", False),
                    "has_click_action": any(a.event == "click" for a in button.actions)
                }
            )
            self.apply_pattern_to_item(button, button_pattern)

        # Add inputs
        for i, input_field in enumerate(dialog_inputs):
            input_type = self._infer_input_type(input_field)

            input_pattern = self.create_pattern_data(
                input_field,
                role="input",
                confidence=dialog_confidence,
                properties={
                    "input_index": i,
                    "input_type": input_type,
                    "editable": input_field.view.get("editable", False),
                    "hint": input_field.view.get("hint", ""),
                    "has_set_text_action": any(a.event == "set_text" for a in input_field.actions)
                }
            )
            self.apply_pattern_to_item(input_field, input_pattern)

        self.logger.debug(f"Detected {dialog_type} dialog with confidence {dialog_confidence:.2f}, "
                          f"{len(dialog_buttons)} buttons, {len(dialog_inputs)} inputs")

        return result

    def _find_dialog_container(self, screen: ScreenDescription) -> Optional[ScreenItem]:
        """
        Find a dialog container element.

        Args:
            screen: Parsed screen description

        Returns:
            Dialog container item or None
        """
        # Look for elements with dialog-related classes or resource IDs
        for item in screen.items:
            view = item.view

            # Skip invisible elements
            if not self.is_visible(item):
                continue

            # Check class name for dialog indicators
            class_name = view.get("class", "").lower()

            # Direct dialog classes
            if any(dialog_cls in class_name for dialog_cls in [
                "dialog", "alertdialog", "popupwindow", "dialogfragment", "bottomsheetdialog",
                "datepickerdialog", "timepickerdialog", "progressdialog"
            ]):
                return item

            # Check resource ID for dialog indicators
            resource_id = self.get_resource_id(view)
            if any(dialog_id in resource_id for dialog_id in [
                "dialog", "alert", "popup", "modal", "sheet", "bottomsheet", "snackbar"
            ]):
                return item

        # If no direct match, look for visual characteristics of dialogs
        return self._find_dialog_by_visual_characteristics(screen)

    def _find_dialog_by_visual_characteristics(self, screen: ScreenDescription) -> Optional[ScreenItem]:
        """
        Find a dialog by its visual characteristics.

        Args:
            screen: Parsed screen description

        Returns:
            Dialog container item or None
        """
        # Estimate screen dimensions
        screen_width, screen_height = self.estimate_screen_dimensions(screen)

        # Dialog candidates - look for medium sized containers with specific characteristics
        candidates = []

        for item in screen.items:
            view = item.view

            # Skip invisible elements or small elements
            if not self.is_visible(item):
                continue

            # Get bounds
            bounds = view.get("bounds", {})
            width = bounds[1][0] - bounds[0][0]
            height = bounds[1][1] - bounds[0][1]

            # Skip very small elements
            if width < 100 or height < 100:
                continue

            # Calculate size relative to screen
            width_ratio = width / screen_width
            height_ratio = height / screen_height

            # Most dialogs are smaller than the full screen
            # but large enough to be noticeable
            if 0.3 <= width_ratio <= 0.95 and 0.2 <= height_ratio <= 0.8:
                # Check for dialog-like contents
                score = 0.0

                # Check if it has buttons at the bottom
                children = self.get_direct_children(item, screen)
                button_count = sum(1 for child in children if self._looks_like_button(child))

                if button_count >= 1:
                    # More buttons = more likely a dialog
                    score += min(0.4, button_count * 0.15)

                # Check if it has a title-like element
                has_title = any(self._looks_like_title(child) for child in children)
                if has_title:
                    score += 0.3

                # Check if it seems to float over the UI (centered)
                center_x = (bounds[0][0] + bounds[1][0]) / 2
                center_y = (bounds[0][1] + bounds[1][1]) / 2

                # Is it near the center of the screen?
                x_centering = 1.0 - (abs(center_x - screen_width / 2) / (screen_width / 2))
                y_centering = 1.0 - (abs(center_y - screen_height / 2) / (screen_height / 2))

                centering_score = (x_centering + y_centering) / 2
                score += centering_score * 0.3

                # Add to candidates if score is high enough
                if score >= 0.4:
                    candidates.append((item, score))

        # Return the highest scoring candidate if any
        if candidates:
            return max(candidates, key=lambda x: x[1])[0]

        return None

    def _calculate_dialog_confidence(self, container: ScreenItem, screen: ScreenDescription) -> float:
        """
        Calculate confidence that the container is a dialog.

        Args:
            container: Potential dialog container
            screen: Screen description

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.0

        # Check class name
        class_name = container.view.get("class", "").lower()

        # Direct dialog classes get high confidence
        if "alertdialog" in class_name:
            confidence += 0.7
        elif "dialog" in class_name:
            confidence += 0.6
        elif "popupwindow" in class_name or "bottomsheetdialog" in class_name:
            confidence += 0.5
        elif "dialogfragment" in class_name:
            confidence += 0.5

        # Check resource ID
        resource_id = container.view.get("resource_id", "").lower()
        if "dialog" in resource_id or "alert" in resource_id:
            confidence += 0.3
        elif "popup" in resource_id or "modal" in resource_id:
            confidence += 0.2

        # Check children
        children = self.get_direct_children(container, screen)

        # Dialogs typically have buttons
        button_count = sum(1 for child in children if self._looks_like_button(child))
        if button_count >= 1:
            confidence += min(0.3, button_count * 0.1)

        # Dialogs often have a title
        if any(self._looks_like_title(child) for child in children):
            confidence += 0.2

        # Dialogs usually have a message or content
        if any(self._looks_like_message(child) for child in children):
            confidence += 0.2

        # Check size and position (dialogs are typically centered and not full screen)
        bounds = container.view.get("bounds", {})
        if bounds:
            # Estimate screen dimensions
            screen_width, screen_height = self.estimate_screen_dimensions(screen)

            width = bounds[1][0] - bounds[0][0]
            height = bounds[1][1] - bounds[0][1]

            # Calculate size relative to screen
            width_ratio = width / screen_width
            height_ratio = height / screen_height

            # Most dialogs are smaller than the full screen
            if width_ratio < 0.95 and height_ratio < 0.9:
                confidence += 0.2 * (1 - max(width_ratio, height_ratio))

            # Check if centered
            center_x = (bounds[0][0] + bounds[1][0]) / 2
            center_y = (bounds[0][1] + bounds[1][1]) / 2

            # Calculate distance from screen center
            x_centering = 1.0 - (abs(center_x - screen_width / 2) / (screen_width / 2))
            y_centering = 1.0 - (abs(center_y - screen_height / 2) / (screen_height / 2))

            centering_score = (x_centering + y_centering) / 2
            confidence += centering_score * 0.2

        # Limit to valid range
        return min(1.0, confidence)

    def _looks_like_button(self, item: ScreenItem) -> bool:
        """
        Check if an item looks like a button.

        Args:
            item: Screen item to check

        Returns:
            True if the item looks like a button
        """
        view = item.view

        # Buttons should be visible and clickable
        if not self.is_visible(item) or not view.get("clickable", False):
            return False

        # Check class name
        class_name = view.get("class", "").lower()
        if "button" in class_name:
            return True

        # Check resource ID
        resource_id = self.get_resource_id(view)
        if "button" in resource_id:
            return True

        # Check for common dialog button texts
        text = self.get_view_property("text", view)
        if text in ["ok", "cancel", "yes", "no", "accept", "decline", "confirm", "skip", "close"]:
            return True

        # Check if item has click actions
        return any(a.event == "click" for a in item.actions)

    def _looks_like_title(self, item: ScreenItem) -> bool:
        """
        Check if an item looks like a dialog title.

        Args:
            item: Screen item to check

        Returns:
            True if the item looks like a title
        """
        view = item.view

        # Title should be visible and have text
        if not self.is_visible(item) or not view.get("text", ""):
            return False

        # Check class name
        class_name = view.get("class", "").lower()
        if "title" in class_name:
            return True

        # Check resource ID
        resource_id = self.get_resource_id(view)
        if "title" in resource_id or "header" in resource_id:
            return True

        # Check text style - titles often have larger or bold text
        text_size = view.get("text_size", 0)
        if text_size and text_size > 18:  # Larger text is more likely to be a title
            return True

        text_style = view.get("text_style", "")
        if text_style and "bold" in str(text_style).lower():
            return True

        # Check position - titles are typically at the top
        parent_bounds = item.view.get("parent_bounds", {})
        bounds = view.get("bounds", {})

        if parent_bounds and bounds:
            parent_top = parent_bounds[0][1]
            item_top = bounds[0][1]

            # Near the top of the parent
            if abs(item_top - parent_top) < 50:
                return True

        # Short text might be a title
        text = view.get("text", "")
        return len(text) < 40  # Titles are typically short

    def _looks_like_message(self, item: ScreenItem) -> bool:
        """
        Check if an item looks like a dialog message.

        Args:
            item: Screen item to check

        Returns:
            True if the item looks like a message
        """
        view = item.view

        # Message should be visible and have text
        if not self.is_visible(item) or not view.get("text", ""):
            return False

        # Check class name
        class_name = view.get("class", "").lower()
        if "textview" in class_name and "title" not in class_name:
            return True

        # Check resource ID
        resource_id = self.get_resource_id(view)
        if "message" in resource_id or "content" in resource_id or "text" in resource_id:
            return True

        # Check if it's in the middle of the dialog (not at the top or bottom)
        parent_bounds = item.view.get("parent_bounds", {})
        bounds = view.get("bounds", {})

        if parent_bounds and bounds:
            parent_top = parent_bounds[0][1]
            parent_bottom = parent_bounds[1][1]
            parent_height = parent_bottom - parent_top

            item_top = bounds[0][1]
            item_bottom = bounds[1][1]

            # In the middle section of the parent
            top_ratio = (item_top - parent_top) / parent_height
            bottom_ratio = (item_bottom - parent_top) / parent_height

            if 0.1 <= top_ratio <= 0.7 and 0.2 <= bottom_ratio <= 0.8:
                return True

        # Longer text might be a message
        text = view.get("text", "")
        return len(text) > 20  # Messages are typically longer than titles

    def _find_dialog_title(self, container: ScreenItem, screen: ScreenDescription) -> Optional[ScreenItem]:
        """
        Find the title element of a dialog.

        Args:
            container: Dialog container
            screen: Screen description

        Returns:
            Title item or None
        """
        # Get direct children first
        children = self.get_direct_children(container, screen)

        # Look for title among direct children
        for child in children:
            if self._looks_like_title(child):
                return child

        # If not found, look for title in grandchildren
        for child in children:
            grandchildren = self.get_direct_children(child, screen)
            for grandchild in grandchildren:
                if self._looks_like_title(grandchild):
                    return grandchild

        # If still not found, look for the first text element at the top
        sorted_children = sorted(
            [c for c in children if self.is_visible(c) and c.view.get("text", "")],
            key=lambda x: x.view.get("bounds", {})[0][1]
        )

        if sorted_children:
            return sorted_children[0]

        return None

    def _find_dialog_message(self, container: ScreenItem, screen: ScreenDescription) -> Optional[ScreenItem]:
        """
        Find the message/content element of a dialog.

        Args:
            container: Dialog container
            screen: Screen description

        Returns:
            Message item or None
        """
        # Get direct children first
        children = self.get_direct_children(container, screen)

        # Look for message among direct children
        for child in children:
            if self._looks_like_message(child):
                return child

        # If not found, look for message in grandchildren
        for child in children:
            grandchildren = self.get_direct_children(child, screen)
            for grandchild in grandchildren:
                if self._looks_like_message(grandchild):
                    return grandchild

        # If still not found, look for the longest text element
        text_elements = [
            c for c in children if self.is_visible(c) and c.view.get("text", "")
        ]

        if text_elements:
            # Return the element with the longest text
            return max(text_elements, key=lambda x: len(x.view.get("text", "")))

        return None

    def _find_dialog_buttons(self, container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Find button elements in a dialog.

        Args:
            container: Dialog container
            screen: Screen description

        Returns:
            List of button items
        """
        buttons = []

        # Get direct children first
        children = self.get_direct_children(container, screen)

        # Look for buttons among direct children
        for child in children:
            if self._looks_like_button(child):
                buttons.append(child)

        # If not enough buttons found, look in grandchildren
        if len(buttons) < 1:
            for child in children:
                grandchildren = self.get_direct_children(child, screen)
                for grandchild in grandchildren:
                    if self._looks_like_button(grandchild) and grandchild not in buttons:
                        buttons.append(grandchild)

        # Try to sort buttons horizontally (left to right)
        if buttons:
            buttons.sort(key=lambda x: x.view.get("bounds", {})[0][0])

        return buttons

    def _find_dialog_inputs(self, container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Find input elements in a dialog.

        Args:
            container: Dialog container
            screen: Screen description

        Returns:
            List of input items
        """
        inputs = []

        # Get all descendants recursively
        descendants = self._get_all_descendants(container, screen)

        # Look for input fields among descendants
        for item in descendants:
            if self._looks_like_input(item):
                inputs.append(item)

        return inputs

    def _get_all_descendants(self, container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Get all descendants of a container recursively.

        Args:
            container: Container element
            screen: Screen description

        Returns:
            List of all descendant items
        """
        descendants = []

        # Get direct children
        children = self.get_direct_children(container, screen)
        descendants.extend(children)

        # Get children of children recursively
        for child in children:
            descendants.extend(self._get_all_descendants(child, screen))

        return descendants

    def _looks_like_input(self, item: ScreenItem) -> bool:
        """
        Check if an item looks like an input field.

        Args:
            item: Screen item to check

        Returns:
            True if the item looks like an input field
        """
        view = item.view

        # Input fields should be visible
        if not self.is_visible(item):
            return False

        # Check class name
        class_name = view.get("class", "").lower()
        if any(input_cls in class_name for input_cls in [
            "edittext", "textfield", "textinputlayout", "textinputedittext"
        ]):
            return True

        # Check if it's editable
        if view.get("editable", False):
            return True

        # Check resource ID
        resource_id = self.get_resource_id(view)
        if any(input_hint in resource_id for input_hint in [
            "edit", "input", "field", "text"
        ]):
            return True

        # Check for hint text
        if view.get("hint", ""):
            return True

        # Check for input methods
        return any(a.event == "set_text" for a in item.actions)

    def _determine_dialog_type(self, container: ScreenItem, title: Optional[ScreenItem],
                               message: Optional[ScreenItem], buttons: List[ScreenItem],
                               inputs: List[ScreenItem]) -> str:
        """
        Determine the type of dialog.

        Args:
            container: Dialog container
            title: Dialog title element
            message: Dialog message element
            buttons: List of dialog buttons
            inputs: List of dialog inputs

        Returns:
            Dialog type string
        """
        # Check class name for specific dialog types
        class_name = container.view.get("class", "").lower()

        if "datepicker" in class_name:
            return "date_picker"
        elif "timepicker" in class_name:
            return "time_picker"
        elif "progress" in class_name:
            return "progress"
        elif "bottomsheet" in class_name:
            return "bottom_sheet"

        # Check resource ID for specific dialog types
        resource_id = container.view.get("resource_id", "").lower()
        if "datepicker" in resource_id:
            return "date_picker"
        elif "timepicker" in resource_id:
            return "time_picker"
        elif "progress" in resource_id:
            return "progress"
        elif "bottomsheet" in resource_id:
            return "bottom_sheet"

        # Check button count and content
        if len(buttons) == 0:
            return "custom_dialog"  # No buttons, probably custom dialog

        # Check for inputs
        if inputs:
            return "input_dialog"

        # Check message content and buttons for dialog type
        if message:
            message_text = message.view.get("text", "").lower()

            # Check for common alert messages
            if "error" in message_text or "warning" in message_text or "alert" in message_text:
                return "alert_dialog"

            # Check for confirmation patterns
            if "?" in message_text or any(confirm_term in message_text for confirm_term in
                                          ["confirm", "sure", "want to", "proceed"]):
                return "confirmation_dialog"

        # Check button text for dialog type
        if buttons:
            button_texts = [b.view.get("text", "").lower() for b in buttons]

            # Yes/No pattern suggests confirmation
            if "yes" in button_texts and "no" in button_texts:
                return "confirmation_dialog"

            # OK/Cancel pattern suggests alert or notification
            if "ok" in button_texts and "cancel" in button_texts:
                return "alert_dialog"

            # Single "OK" button suggests information
            if len(buttons) == 1 and button_texts[0] in ["ok", "got it", "dismiss", "close"]:
                return "information_dialog"

        # Default to simple dialog
        return "simple_dialog"

    def _determine_button_role(self, button: ScreenItem, index: int, total_buttons: int) -> str:
        """
        Determine the role of a dialog button.

        Args:
            button: Button element
            index: Button index
            total_buttons: Total number of buttons

        Returns:
            Button role string
        """
        # Check button text
        text = button.view.get("text", "").lower()

        # Check for positive actions
        if text in ["ok", "yes", "accept", "agree", "confirm", "done", "save", "submit"]:
            return "positive_button"

        # Check for negative actions
        if text in ["no", "cancel", "decline", "disagree", "dismiss", "back", "close", "reject"]:
            return "negative_button"

        # Check for neutral actions
        if text in ["maybe", "remind me later", "skip", "not now", "later"]:
            return "neutral_button"

        # If only one button, it's likely positive
        if total_buttons == 1:
            return "positive_button"

        # In 2-button dialogs, typically right button is positive, left is negative
        if total_buttons == 2:
            return "positive_button" if index == 1 else "negative_button"

        # In 3-button dialogs, typically:
        # - Left button is negative
        # - Middle button is neutral
        # - Right button is positive
        if total_buttons == 3:
            if index == 0:
                return "negative_button"
            elif index == 1:
                return "neutral_button"
            else:
                return "positive_button"

        # Generic button role
        return "button"

    def _infer_input_type(self, item: ScreenItem) -> str:
        """
        Infer the input type for a field.

        Args:
            item: Screen item

        Returns:
            Input type string
        """
        view = item.view

        # Check explicit input type
        input_type = view.get("input_type", "").lower()
        if input_type:
            if "password" in input_type:
                return "password"
            elif "email" in input_type:
                return "email"
            elif "phone" in input_type:
                return "phone"
            elif "number" in input_type:
                return "number"
            elif "date" in input_type:
                return "date"

        # Check resource ID
        resource_id = self.get_resource_id(view)

        if "password" in resource_id:
            return "password"
        elif "email" in resource_id:
            return "email"
        elif "phone" in resource_id or "mobile" in resource_id:
            return "phone"
        elif "username" in resource_id or "login" in resource_id:
            return "username"
        elif "search" in resource_id:
            return "search"
        elif "address" in resource_id:
            return "address"
        elif "name" in resource_id:
            if "first" in resource_id or "given" in resource_id:
                return "first_name"
            elif "last" in resource_id or "family" in resource_id:
                return "last_name"
            return "name"
        elif "zip" in resource_id or "postal" in resource_id:
            return "postal_code"
        elif "city" in resource_id:
            return "city"
        elif "state" in resource_id or "province" in resource_id:
            return "state"
        elif "country" in resource_id:
            return "country"
        elif "number" in resource_id or "amount" in resource_id or "price" in resource_id:
            return "number"
        elif "date" in resource_id:
            return "date"
        elif "time" in resource_id:
            return "time"

        # Check hint text
        hint = view.get("hint", "").lower()

        if hint:
            if "password" in hint:
                return "password"
            elif "email" in hint:
                return "email"
            elif "phone" in hint or "mobile" in hint:
                return "phone"
            elif "username" in hint or "user name" in hint:
                return "username"
            elif "search" in hint:
                return "search"

        # Default to text
        return "text"