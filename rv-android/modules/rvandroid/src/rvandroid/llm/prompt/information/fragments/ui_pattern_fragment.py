"""UI Pattern information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting UI pattern
information from the application state.
"""

from typing import Any, Dict, Optional

from rv_android_core.llm.prompt.information.base_fragment import InformationFragment


# TODO deprecated
class UIPatternFragment(InformationFragment):
    """Fragment for extracting and formatting UI pattern information.
    
    This fragment identifies common UI patterns like login forms, settings pages,
    navigation menus, etc. from the application state.
    """

    def __init__(self, name: str = "ui_patterns", priority: int = 200):
        """Initialize the UI pattern fragment.
        
        Args:
            name: The name of the fragment (default: "ui_patterns").
            priority: The priority of the fragment (default: 200).
        """
        super().__init__(name, priority)

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate UI pattern information from the application state.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            A dictionary containing identified UI patterns and their properties.
        """
        if not state or "screen" not in state:
            self.logger.debug("No screen information available in state")
            return {}

        patterns = {}
        screen = state.get("screen", {})

        # Extract UI components from the screen
        components = screen.get("components", [])

        # Detect login form
        login_components = self._detect_login_form(components)
        if login_components:
            patterns["login_form"] = login_components

        # Detect settings page
        settings_components = self._detect_settings_page(components, screen.get("title", ""))
        if settings_components:
            patterns["settings_page"] = settings_components

        # Detect navigation menu
        navigation_components = self._detect_navigation_menu(components)
        if navigation_components:
            patterns["navigation_menu"] = navigation_components

        # Detect form fields (input, dropdown, checkbox, etc.)
        form_fields = self._detect_form_fields(components)
        if form_fields:
            patterns["form_fields"] = form_fields

        self.logger.debug(f"Detected {len(patterns)} UI patterns")
        return patterns

    def _detect_login_form(self, components: list) -> Dict[str, Any]:
        """Detect if the current screen contains a login form.
        
        Args:
            components: List of UI components.
            
        Returns:
            Dictionary with login form details if detected, empty dict otherwise.
        """
        username_field = None
        password_field = None
        login_button = None

        for component in components:
            # Handle different component formats safely
            if not component:
                continue

            # Get component properties with appropriate null/type checking
            component_type = component.get("type", "")
            component_type = component_type.lower() if component_type else ""

            component_text = component.get("text", "")
            component_text = component_text.lower() if component_text else ""

            component_hint = component.get("hint", "")
            component_hint = component_hint.lower() if component_hint else ""

            component_id = component.get("resource_id", "")
            component_id = component_id.lower() if component_id else ""

            # Check for username field
            if component_type == "edittext" and any(kw in component_hint or kw in component_text or kw in component_id
                                                    for kw in ["username", "email", "login", "user"]):
                username_field = component

            # Check for password field
            if component_type == "edittext" and any(kw in component_hint or kw in component_text or kw in component_id
                                                    for kw in ["password", "passwd"]):
                password_field = component

            # Check for login button
            if component_type in ["button", "textview"] and any(kw in component_text
                                                                for kw in ["login", "sign in", "entrar"]):
                login_button = component

        if username_field and password_field:
            return {
                "username_field": self._extract_component_info(username_field),
                "password_field": self._extract_component_info(password_field),
                "login_button": self._extract_component_info(login_button) if login_button else None
            }

        return {}

    def _detect_settings_page(self, components: list, title: str) -> Dict[str, Any]:
        """Detect if the current screen is a settings page.
        
        Args:
            components: List of UI components.
            title: Screen title.
            
        Returns:
            Dictionary with settings details if detected, empty dict otherwise.
        """
        # Handle null title
        if not title:
            title = ""

        if "settings" in title.lower() or "configurações" in title.lower():
            settings_items = []

            for component in components:
                if not component:
                    continue

                clickable = component.get("clickable", False)
                component_type = component.get("type", "")
                if isinstance(component_type, str):
                    component_type = component_type.lower()

                if clickable and component_type in ["textview", "switch", "checkbox"]:
                    settings_items.append(self._extract_component_info(component))

            if settings_items:
                return {"title": title, "settings_items": settings_items}

        return {}

    def _detect_navigation_menu(self, components: list) -> Dict[str, Any]:
        """Detect if the current screen contains a navigation menu.
        
        Args:
            components: List of UI components.
            
        Returns:
            Dictionary with navigation menu details if detected, empty dict otherwise.
        """
        menu_items = []

        # Look for components that might be part of a navigation menu
        for component in components:
            if not component:
                continue

            # Get component type with null checks
            component_type = component.get("type", "")
            if component_type and isinstance(component_type, str):
                component_type = component_type.lower()
            else:
                component_type = ""

            if component_type in ["textview", "imageview"] and component.get("clickable", False):
                # Check if it's positioned like a menu item (at the edge of the screen)
                bounds = component.get("bounds", None)
                if bounds:
                    # Handle different bounds formats
                    if isinstance(bounds, dict):
                        # Dictionary format
                        left = bounds.get("left", 100)
                        right = bounds.get("right", 0)
                        if left < 50 or right > 1000:
                            menu_items.append(self._extract_component_info(component))
                    elif isinstance(bounds, list) and len(bounds) >= 2:
                        # List format [[left,top], [right,bottom]]
                        try:
                            left = bounds[0][0]
                            right = bounds[1][0]
                            if left < 50 or right > 1000:
                                menu_items.append(self._extract_component_info(component))
                        except (IndexError, TypeError):
                            # Skip if bounds are malformed
                            pass

        if len(menu_items) >= 3:  # Assume it's a menu if there are at least 3 items
            return {"menu_items": menu_items}

        return {}

    def _detect_form_fields(self, components: list) -> Dict[str, Any]:
        """Detect form fields in the current screen.
        
        Args:
            components: List of UI components.
            
        Returns:
            Dictionary with form field details if detected, empty dict otherwise.
        """
        form_fields = []

        for component in components:
            if not component:
                continue

            # Get component type with null checks
            component_type = component.get("type", "")
            if component_type and isinstance(component_type, str):
                component_type = component_type.lower()
            else:
                component_type = ""

            if component_type in ["edittext", "checkbox", "radiobutton", "spinner", "switch"]:
                form_fields.append(self._extract_component_info(component))

        if form_fields:
            return {"fields": form_fields}

        return {}

    def _extract_component_info(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant information from a UI component.
        
        Args:
            component: The UI component data.
            
        Returns:
            Dictionary with relevant component information.
        """
        if not component:
            return {}

        # Process bounds to ensure consistent format
        bounds = component.get("bounds", None)
        bounds_info = {}

        if bounds:
            if isinstance(bounds, dict):
                # Dictionary format
                bounds_info = bounds
            elif isinstance(bounds, list) and len(bounds) >= 2:
                # List format [[left,top], [right,bottom]]
                try:
                    left, top = bounds[0]
                    right, bottom = bounds[1]
                    bounds_info = {
                        "left": left,
                        "top": top,
                        "right": right,
                        "bottom": bottom
                    }
                except (IndexError, TypeError):
                    # Use empty dict for malformed bounds
                    pass

        return {
            "type": component.get("type", ""),
            "text": component.get("text", ""),
            "hint": component.get("hint", ""),
            "resource_id": component.get("resource_id", ""),
            "clickable": component.get("clickable", False),
            "enabled": component.get("enabled", True),
            "bounds": bounds_info
        }
