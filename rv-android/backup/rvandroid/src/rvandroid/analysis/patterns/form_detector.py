# rvandroid/analysis/patterns/form_detector.py
"""
Form pattern detector implementation.

This module provides a specialized detector for form patterns in Android applications.
It identifies input fields, required fields, and submit buttons to enable batch form-filling actions.
"""

from typing import List, Optional

from rv_android_core.analysis.patterns.pattern_data import PatternType, PatternResult
from rv_android_core.analysis.patterns.pattern_detector import BasePatternDetector
from rv_screen_parser.parser.screen.visitor.model import ScreenItem, ScreenDescription
from rv_android_core.util.error.error_handler import ErrorHandler


class FormDetector(BasePatternDetector):
    """
    Detector for form patterns in UI.

    ### Architectural Decisions:
    - Implements specialized form detection using multi-factor heuristics
    - Uses DOM-based analysis with normalized node structure
    - Identifies form components based on view properties and hierarchical relationships
    - Applies confidence scoring based on input field count, submit button presence, and layout

    ### Role in the System:
    - Provides reliable form pattern detection for batch action generation
    - Identifies form field relationships and dependencies
    - Enables coherent form-filling sequences
    - Enhances testing effectiveness by supporting complete form submissions
    """

    def __init__(self):
        """Initialize the form detector."""
        super().__init__()
        self.error_handler = ErrorHandler.get_instance()

    @property
    def pattern_type(self) -> PatternType:
        """Get the pattern type."""
        return PatternType.FORM

    def detect(self, screen: ScreenDescription) -> PatternResult:
        """
        Detect form patterns in a screen.

        Args:
            screen: Parsed screen description

        Returns:
            PatternResult with detection results
        """
        self.logger.debug(f"Detecting form patterns in screen with {len(screen.items)} items")

        # Initialize pattern result
        result = self.create_base_result(PatternType.FORM)

        # Check if there are enough items to form a pattern
        if len(screen.items) < 2:
            self.logger.debug("Not enough items for a form pattern")
            return result

        # Identify potential form elements
        input_fields = self.find_elements_by_property(screen, self._is_input_field)
        submit_buttons = self.find_elements_by_property(screen, self._is_submit_button)
        checkboxes = self.find_elements_by_property(screen, self._is_checkbox)
        radio_buttons = self.find_elements_by_property(screen, self._is_radio_button)

        # Calculate form confidence based on components
        input_field_count = len(input_fields)
        submit_button_count = len(submit_buttons)
        checkbox_count = len(checkboxes)
        radio_button_count = len(radio_buttons)

        total_form_elements = input_field_count + checkbox_count + radio_button_count

        # Need at least one input field and one submit button for a form
        if input_field_count == 0 or submit_button_count == 0:
            self.logger.debug(f"Not a form pattern: {input_field_count} inputs, {submit_button_count} submit buttons")
            return result

        # Calculate base confidence score
        # More inputs and a submit button = higher confidence
        base_confidence = min(0.5 + (total_form_elements * 0.1), 0.9)

        # Adjust confidence based on layout
        layout_confidence = self._analyze_form_layout(
            screen, input_fields, submit_buttons, checkboxes, radio_buttons)

        # Combine scores with layout having more weight
        confidence = (base_confidence * 0.4) + (layout_confidence * 0.6)

        result.confidence = confidence
        result.elements_count = total_form_elements + submit_button_count

        # If confidence is high enough, enrich screen items with form information
        if confidence >= 0.5:
            # Process input fields
            for item in input_fields:
                # Determine if field is required
                required = self._is_required_field(item)

                # Create pattern data
                input_properties = {
                    "input_type": self._infer_input_type(item),
                    "required": required
                }

                # Add hint if available
                if "hint" in item.view:
                    input_properties["hint"] = item.view["hint"]

                pattern_data = self.create_pattern_data(
                    item,
                    role="input_field",
                    confidence=confidence,
                    properties=input_properties
                )

                # Apply pattern to item
                self.apply_pattern_to_item(item, pattern_data)

            # Process checkboxes
            for item in checkboxes:
                pattern_data = self.create_pattern_data(
                    item,
                    role="checkbox",
                    confidence=confidence,
                    properties={
                        "checked": item.view.get("checked", False)
                    }
                )
                self.apply_pattern_to_item(item, pattern_data)

            # Process radio buttons
            for item in radio_buttons:
                pattern_data = self.create_pattern_data(
                    item,
                    role="radio_button",
                    confidence=confidence,
                    properties={
                        "checked": item.view.get("checked", False)
                    }
                )
                self.apply_pattern_to_item(item, pattern_data)

            # Process submit buttons
            for item in submit_buttons:
                pattern_data = self.create_pattern_data(
                    item,
                    role="submit",
                    confidence=confidence,
                    properties={}
                )
                self.apply_pattern_to_item(item, pattern_data)

            # Add form properties to result
            result.properties["input_count"] = input_field_count
            result.properties["checkbox_count"] = checkbox_count
            result.properties["radio_count"] = radio_button_count
            result.properties["submit_count"] = submit_button_count

            # Detect form purpose based on field types and content
            form_purpose = self._infer_form_purpose(input_fields)
            if form_purpose:
                result.properties["form_purpose"] = form_purpose

            self.logger.debug(f"Detected form pattern with confidence {confidence:.2f}, "
                              f"{input_field_count} inputs, {submit_button_count} submit buttons")

        return result

    def _is_active_element(self, item: ScreenItem) -> bool:
        """
        Check if an element is active (visible and enabled).

        Args:
            item: Screen item to check

        Returns:
            True if the element is active
        """
        view = item.view

        # Check visibility
        if not self.is_visible(item):
            return False

        # Check if enabled
        if view.get("enabled") is False:
            return False

        return True

    def _is_input_field(self, item: ScreenItem) -> bool:
        """
        Check if an element is an input field.

        Args:
            item: Screen item to check

        Returns:
            True if the element is an input field
        """
        if not self._is_active_element(item):
            return False

        view = item.view

        # Check class name
        class_name = view.get("class", "").lower()

        # Direct input field classes
        if any(input_type in class_name for input_type in [
            "edittext", "textfield", "textedit", "textinputlayout", "textinputedittext"
        ]):
            return True

        # Check content type
        if view.get("input_type") is not None:
            return True

        # Check if editable
        if view.get("editable", False):
            return True

        # Check resource ID hints
        resource_id = self.get_resource_id(view)
        if resource_id and any(input_hint in resource_id for input_hint in [
            "edit", "input", "text", "field", "username", "password", "email", "address", "phone"
        ]):
            return True

        # Check if focusable with no children
        if view.get("focusable", False) and not view.get("children", []):
            # Also check if it has click actions
            if len([a for a in item.actions if a.event == "click"]) > 0:
                return False  # Clickable focusable elements are likely not text fields

            return True

        return False

    def _is_submit_button(self, item: ScreenItem) -> bool:
        """
        Check if an element is a submit button.

        Args:
            item: Screen item to check

        Returns:
            True if the element is a submit button
        """
        if not self._is_active_element(item):
            return False

        view = item.view

        # Must be clickable
        if not view.get("clickable", False):
            return False

        # Check class name
        class_name = view.get("class", "").lower()
        if "button" not in class_name and "imagebutton" not in class_name:
            # Not a button class but might still be a button
            # Only consider it a button if it has strong button indicators

            resource_id = self.get_resource_id(view)
            text = self.get_view_property("text", view)

            if not any(submit_hint in resource_id or submit_hint in text for submit_hint in [
                "submit", "save", "login", "signup", "register", "ok", "next", "continue", "send", "generate"
            ]):
                return False

        # Check for submit button indicators in text or resource ID
        resource_id = self.get_resource_id(view)
        text = self.get_view_property("text", view)

        return any(submit_hint in resource_id or submit_hint in text for submit_hint in [
            "submit", "save", "login", "signin", "signup", "register", "ok", "next", "continue",
            "send", "search", "apply", "update", "create", "complete", "confirm", "generate"
        ])

    def _is_checkbox(self, item: ScreenItem) -> bool:
        """
        Check if an element is a checkbox.

        Args:
            item: Screen item to check

        Returns:
            True if the element is a checkbox
        """
        if not self._is_active_element(item):
            return False

        view = item.view

        # Check class name
        class_name = view.get("class", "").lower()

        if "checkbox" in class_name:
            return True

        # Check for switch classes
        if "switch" in class_name or "toggle" in class_name:
            return True

        # Check resource ID
        resource_id = self.get_resource_id(view)

        if any(cb_hint in resource_id for cb_hint in ["checkbox", "check", "switch", "toggle"]):
            return True

        # Check if checkable
        if view.get("checkable", False):
            return True

        return False

    def _is_radio_button(self, item: ScreenItem) -> bool:
        """
        Check if an element is a radio button.

        Args:
            item: Screen item to check

        Returns:
            True if the element is a radio button
        """
        if not self._is_active_element(item):
            return False

        view = item.view

        # Check class name
        class_name = view.get("class", "").lower()

        if "radiobutton" in class_name:
            return True

        # Check resource ID
        resource_id = self.get_resource_id(view)

        if "radio" in resource_id:
            return True

        # In some cases, a checkable element that's in a RadioGroup is a radio button
        parent_class = view.get("parent_class", "").lower()

        if "radiogroup" in parent_class and view.get("checkable", False):
            return True

        return False

    def _is_required_field(self, item: ScreenItem) -> bool:
        """
        Check if an input field is required.

        Args:
            item: Screen item to check

        Returns:
            True if the field is likely required
        """
        view = item.view

        # Check hint text for required indicators
        hint = view.get("hint", "").lower()
        if hint and any(req in hint for req in ["*", "required"]):
            return True

        # Check content description for required indicators
        content_desc = self.get_view_property("content_description", view)
        if content_desc and any(req in content_desc for req in ["*", "required"]):
            return True

        # Check resource ID for required indicators
        resource_id = self.get_resource_id(view)
        if resource_id and "required" in resource_id:
            return True

        # Check resource ID for common required fields
        if resource_id and any(field in resource_id for field in [
            "username", "email", "password", "first_name", "last_name", "phone"
        ]):
            return True

        return False

    def _analyze_form_layout(self, screen: ScreenDescription,
                             input_fields: List[ScreenItem],
                             submit_buttons: List[ScreenItem],
                             checkboxes: List[ScreenItem],
                             radio_buttons: List[ScreenItem]) -> float:
        """
        Analyze the layout to determine if it resembles a form.

        Args:
            screen: Screen description
            input_fields: List of input fields
            submit_buttons: List of submit buttons
            checkboxes: List of checkboxes
            radio_buttons: List of radio buttons

        Returns:
            Confidence score for form layout (0.0-1.0)
        """
        # No input fields = no form
        if not input_fields:
            return 0.0

        # Start with moderate confidence
        confidence = 0.5

        # Check if submit button is at the bottom of the form
        if submit_buttons:
            submit_y = max(button.view.get("bounds", [])[1][1] for button in submit_buttons)
            input_bottoms = [field.view.get("bounds", [])[1][1] for field in input_fields]

            # If at least half of input fields are above the submit button
            if sum(1 for y in input_bottoms if y < submit_y) >= len(input_bottoms) / 2:
                confidence += 0.2

        # Check if inputs are vertically aligned
        input_lefts = [field.view.get("bounds", [])[0][0] for field in input_fields]

        if input_lefts:
            # Calculate standard deviation as a percentage of average left position
            avg_left = sum(input_lefts) / len(input_lefts)
            if avg_left > 0:
                std_dev = (sum((x - avg_left) ** 2 for x in input_lefts) / len(input_lefts)) ** 0.5
                alignment_score = max(0.0, 1.0 - (std_dev / avg_left))

                # Reward good vertical alignment
                confidence += alignment_score * 0.2

        # Check vertical arrangement
        input_tops = sorted([field.view.get("bounds", [])[0][1] for field in input_fields])
        if len(input_tops) >= 2:
            is_vertical = True
            for i in range(1, len(input_tops)):
                # If gap between inputs is too small, they might be horizontally arranged
                if input_tops[i] - input_tops[i - 1] < 20:  # Small threshold for vertical separation
                    is_vertical = False
                    break

            if is_vertical:
                confidence += 0.1

        # Presence of form-specific elements increases confidence
        if checkboxes:
            confidence += 0.05 * min(len(checkboxes), 2)  # Max bonus for 2+ checkboxes

        if radio_buttons:
            confidence += 0.05 * min(len(radio_buttons), 2)  # Max bonus for 2+ radio buttons

        # Limit to valid range
        return max(0.0, min(confidence, 1.0))

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
        resource_id = view.get("resource_id", "").lower()

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

    def _infer_form_purpose(self, input_fields: List[ScreenItem]) -> Optional[str]:
        """
        Infer the purpose of the form based on its fields.

        Args:
            input_fields: List of input fields

        Returns:
            Form purpose or None if unknown
        """
        # Count field types
        field_types = {}

        for item in input_fields:
            input_type = self._infer_input_type(item)
            field_types[input_type] = field_types.get(input_type, 0) + 1

        # Login form detection
        if (field_types.get("username", 0) > 0 or field_types.get("email", 0) > 0) and field_types.get("password",
                                                                                                       0) > 0:
            if len(input_fields) <= 3:  # Login forms are typically simple
                return "login"

        # Registration form detection
        if (field_types.get("username", 0) > 0 or field_types.get("email", 0) > 0) and field_types.get("password",
                                                                                                       0) > 0:
            if len(input_fields) >= 4:  # Registration forms typically have more fields
                return "registration"

        # Contact form detection
        if field_types.get("name", 0) > 0 and (field_types.get("email", 0) > 0 or field_types.get("phone", 0) > 0):
            return "contact"

        # Search form detection
        if field_types.get("search", 0) > 0 and len(input_fields) <= 2:
            return "search"

        # Address form detection
        address_fields = (
                field_types.get("address", 0) +
                field_types.get("city", 0) +
                field_types.get("state", 0) +
                field_types.get("postal_code", 0) +
                field_types.get("country", 0)
        )
        if address_fields >= 2:
            return "address"

        # Payment form detection
        if field_types.get("credit_card", 0) > 0 or field_types.get("card_number", 0) > 0:
            return "payment"

        # Unknown purpose
        return None
