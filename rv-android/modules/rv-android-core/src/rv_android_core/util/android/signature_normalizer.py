"""
Signature normalizer for inner class notation in Android method signatures.

Normalizes inner class notation: OuterClass.InnerClass -> OuterClass$InnerClass.
This is needed because static analysis tools (Soot) use $ notation for inner classes,
while dynamic signatures from GESDA/GATOR may use dot notation.

### Scope:

- normalize_signature(): Normalizes parameter types only, preserving method names
- normalize_class_name(): Normalizes full class names (for GESDA/GATOR class_name fields)

### Origin:

Copied from rvsec-regerar-resultados/processors/signature_normalizer.py.
The normalization logic is preserved identically.
"""

import re
from typing import Optional


class SignatureNormalizer:
    """
    Inner class normalization for method signatures and class names.

    Converts OuterClass.InnerClass -> OuterClass$InnerClass based on Java
    naming conventions (uppercase = class, lowercase = package).

    ### Scope:

    - normalize_signature(): Normalizes parameter types, not method names
    - normalize_class_name(): Normalizes full class names including inner classes
    - Soot's Type.toString() already generates proper $ notation in .methods files,
      so this normalizes dynamic/GESDA/GATOR data to match
    """

    def normalize_signature(self, signature: str) -> str:
        """
        Apply inner class corrections to method parameters.

        Process:
        1. Split signature into method part and parameters part
        2. Normalize parameter types: OuterClass.InnerClass -> OuterClass$InnerClass
        3. Preserve method names unchanged
        4. CRITICAL: Maintain parentheses balance

        Example:
        Input:  "onTabSelected(TabLayout.Tab)"
        Output: "onTabSelected(TabLayout$Tab)"

        Args:
            signature: Method signature to normalize

        Returns:
            Normalized signature with inner class corrections and balanced parentheses
        """
        if '(' not in signature:
            return signature

        # Find the opening parenthesis
        paren_start = signature.find('(')
        method_part = signature[:paren_start]

        # Extract everything between parentheses
        remaining = signature[paren_start:]
        if not remaining.endswith(')'):
            # If no closing parenthesis, return as-is
            return signature

        # Extract parameter content (without outer parentheses)
        param_content = remaining[1:-1]  # Remove '(' and ')'

        if param_content:
            normalized_params = self.normalize_parameter_list(param_content)
            return f"{method_part}({normalized_params})"
        else:
            # Empty parameters
            return f"{method_part}()"

    def normalize_class_name(self, class_name: str) -> str:
        """
        Normalize inner class notation in class names.

        Handles both simple and mixed patterns:
        - Simple: OuterClass.InnerClass -> OuterClass$InnerClass
        - Mixed: Outer.Inner$1 -> Outer$Inner$1 (anonymous inner classes)

        Examples:
        Input:  "com.example.OuterClass.InnerClass"
        Output: "com.example.OuterClass$InnerClass"
        Input:  "Map.GameFieldPosition$1"
        Output: "Map$GameFieldPosition$1"

        Args:
            class_name: Class name to normalize

        Returns:
            Normalized class name with inner class corrections
        """
        if '.' not in class_name:
            return class_name

        # Split preserving both . and $ separators
        # Use regex to split but keep separators
        parts = re.split(r'([.$])', class_name)
        # Example: 'Map.GameFieldPosition$1' -> ['Map', '.', 'GameFieldPosition', '$', '1']

        result = []
        i = 0

        while i < len(parts):
            if i == 0:
                # First part is always a component
                result.append(parts[i])
                i += 1
            elif parts[i] in ['.', '$']:
                # Found a separator
                sep = parts[i]
                i += 1

                if i < len(parts):
                    next_part = parts[i]
                    prev_part = result[-1] if result else ''

                    # Decide if this should be $ (inner class) or . (package)
                    if self._is_likely_inner_class(prev_part, next_part):
                        result.append('$')  # Force inner class separator
                    else:
                        result.append(sep)  # Keep original separator

                    result.append(next_part)
                    i += 1
            else:
                # Regular component (shouldn't happen with proper split)
                result.append(parts[i])
                i += 1

        return ''.join(result)

    def normalize_parameter_list(self, parameters: str) -> str:
        """
        Normalize parameter list for inner class corrections.

        Args:
            parameters: Parameter list (comma or semicolon separated)

        Returns:
            Normalized parameter list preserving original spacing
        """
        if not parameters or not parameters.strip():
            return parameters

        # Handle both comma and semicolon separators
        separator = ';' if ';' in parameters else ','

        param_parts = parameters.split(separator)
        normalized_parts = []

        for i, param in enumerate(param_parts):
            # Preserve leading/trailing whitespace but normalize the type
            stripped_param = param.strip()
            if stripped_param:
                # Apply inner class normalization to each parameter type
                normalized_param = self._normalize_single_parameter(stripped_param)

                # Restore original spacing pattern
                if i == 0:
                    # First parameter - keep original leading space
                    leading_space = param[:len(param) - len(param.lstrip())]
                    trailing_space = param[len(param.rstrip()):]
                    normalized_parts.append(leading_space + normalized_param + trailing_space)
                else:
                    # Subsequent parameters - preserve space after comma
                    if param.startswith(' '):
                        normalized_parts.append(' ' + normalized_param)
                    else:
                        normalized_parts.append(normalized_param)
            else:
                # Empty parameter, keep as-is
                normalized_parts.append(param)

        return separator.join(normalized_parts)

    def _normalize_single_parameter(self, param_type: str) -> str:
        """
        Normalize a single parameter type for inner classes.

        CORRECTED LOGIC: Only convert actual inner classes, not packages.
        Based on test cases from test_controlled_validation.py:
        - TabLayout.Tab -> TabLayout$Tab (both parts start with uppercase)
        - android.os.Bundle -> android.os.Bundle (os is lowercase = package)
        - java.lang.String -> java.lang.String (lang is lowercase = package)

        Examples:
        Input:  "TabLayout.Tab"              -> "TabLayout$Tab" (inner class)
        Input:  "View.OnClickListener"       -> "View$OnClickListener" (inner class)
        Input:  "android.os.Bundle"          -> "android.os.Bundle" (package - unchanged)
        Input:  "java.lang.String"           -> "java.lang.String" (package - unchanged)
        Input:  "OuterClass.InnerClass.Deep" -> "OuterClass$InnerClass$Deep" (nested inner)

        Args:
            param_type: Single parameter type

        Returns:
            Normalized parameter type with inner class corrections only
        """
        # Handle array notation
        array_suffix = ''
        while param_type.endswith('[]'):
            array_suffix += '[]'
            param_type = param_type[:-2]

        # Apply inner class normalization only if no $ already present
        if '.' in param_type and '$' not in param_type:
            parts = param_type.split('.')
            normalized_parts = []

            # Process parts to identify inner classes vs packages
            for i, part in enumerate(parts):
                if i == 0:
                    # First part is always added as-is
                    normalized_parts.append(part)
                else:
                    previous_part = parts[i-1]

                    # CRITICAL RULE: Convert to inner class ONLY if:
                    # 1. Previous part starts with UPPERCASE (it's a class, not package)
                    # 2. Current part starts with UPPERCASE (it's an inner class)
                    # 3. Previous part is not a known package name
                    if (self._is_likely_inner_class(previous_part, part)):
                        # Join with $ (inner class syntax)
                        if normalized_parts:
                            normalized_parts[-1] = normalized_parts[-1] + '$' + part
                        else:
                            normalized_parts.append(part)
                    else:
                        # Regular package/class - keep dot
                        normalized_parts.append(part)

            param_type = '.'.join(normalized_parts)

        return param_type + array_suffix

    def _is_likely_inner_class(self, outer_part: str, inner_part: str) -> bool:
        """
        Determine if outer.inner represents an inner class vs package.class.

        Based on Java conventions:
        - Inner classes: OuterClass.InnerClass (both uppercase)
        - Packages: package.Class (package lowercase, Class uppercase)

        Args:
            outer_part: The part before the dot
            inner_part: The part after the dot

        Returns:
            True if this appears to be an inner class relationship
        """
        if not outer_part or not inner_part:
            return False

        # Both parts must start with uppercase to be inner class
        outer_is_class = outer_part[0].isupper()
        inner_is_class = inner_part[0].isupper()

        if not (outer_is_class and inner_is_class):
            return False

        # Check if outer_part is a known package name (lowercase)
        # IMPORTANT: Only check if outer_part is actually lowercase!
        # "Widget" should NOT match "widget" package
        known_packages = {
            'android', 'java', 'javax', 'com', 'org', 'net', 'io',
            'os', 'lang', 'util', 'content', 'widget', 'app',
            'support', 'design', 'fragment', 'activity', 'graphics',
            'text', 'database', 'preference', 'animation', 'concurrent'
        }

        # BUG FIX: Only check known_packages if outer_part is lowercase
        # This prevents "Widget" from matching "widget" package
        if outer_part.islower() and outer_part in known_packages:
            return False

        # Additional heuristic: if outer_part is short and all lowercase,
        # it's likely a package, not a class
        if len(outer_part) <= 3 and outer_part.islower():
            return False

        # If both start with uppercase and outer is not a known package,
        # likely an inner class
        return True

    def extract_method_name(self, signature: str) -> str:
        """
        Extract method name from signature.

        Example:
        Input:  "onCreate(android.os.Bundle)"
        Output: "onCreate"

        Args:
            signature: Method signature

        Returns:
            Method name only
        """
        if '(' in signature:
            return signature.split('(')[0]
        return signature

    def extract_parameters(self, signature: str) -> str:
        """
        Extract parameters from signature.

        Example:
        Input:  "onCreate(android.os.Bundle)"
        Output: "android.os.Bundle"

        Args:
            signature: Method signature

        Returns:
            Parameters part without parentheses
        """
        if '(' not in signature:
            return ""

        # Find parameters between parentheses
        start = signature.find('(')
        end = signature.rfind(')')

        if start != -1 and end != -1 and end > start:
            return signature[start + 1:end]

        return ""

    def create_signature(self, method_name: str, parameters: str) -> str:
        """
        Create normalized signature from method name and parameters.

        Args:
            method_name: Method name
            parameters: Parameter string

        Returns:
            Complete normalized signature
        """
        normalized_params = self.normalize_parameter_list(parameters)
        return f"{method_name}({normalized_params})"
