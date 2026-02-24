"""
Signature normalizer for inner class corrections.

Converts OuterClass.InnerClass to OuterClass$InnerClass in method parameters.
"""

import re


class SignatureNormalizer:
    """Normalizes signatures for inner class corrections."""

    def normalize_signature(self, signature: str) -> str:
        """
        Normalize inner class notation in method parameters.

        Example:
            Input:  "onTabSelected(TabLayout.Tab)"
            Output: "onTabSelected(TabLayout$Tab)"
        """
        if "(" not in signature:
            return signature

        paren_start = signature.find("(")
        method_part = signature[:paren_start]
        remaining = signature[paren_start:]

        if not remaining.endswith(")"):
            return signature

        param_content = remaining[1:-1]

        if param_content:
            normalized_params = self._normalize_parameter_list(param_content)
            return f"{method_part}({normalized_params})"
        else:
            return f"{method_part}()"

    def normalize_class_name(self, class_name: str) -> str:
        """
        Normalize inner class notation in class names.

        Example:
            Input:  "com.example.OuterClass.InnerClass"
            Output: "com.example.OuterClass$InnerClass"
        """
        if "." not in class_name:
            return class_name

        parts = re.split(r"([.$])", class_name)
        result = []
        i = 0

        while i < len(parts):
            if i == 0:
                result.append(parts[i])
                i += 1
            elif parts[i] in [".", "$"]:
                sep = parts[i]
                i += 1
                if i < len(parts):
                    next_part = parts[i]
                    prev_part = result[-1] if result else ""
                    if self._is_likely_inner_class(prev_part, next_part):
                        result.append("$")
                    else:
                        result.append(sep)
                    result.append(next_part)
                    i += 1
            else:
                result.append(parts[i])
                i += 1

        return "".join(result)

    def _normalize_parameter_list(self, parameters: str) -> str:
        """Normalize parameter list for inner class corrections."""
        if not parameters or not parameters.strip():
            return parameters

        separator = ";" if ";" in parameters else ","
        param_parts = parameters.split(separator)
        normalized_parts = []

        for param in param_parts:
            stripped_param = param.strip()
            if stripped_param:
                normalized_param = self._normalize_single_parameter(stripped_param)
                normalized_parts.append(normalized_param)
            else:
                normalized_parts.append(param)

        return separator.join(normalized_parts)

    def _normalize_single_parameter(self, param_type: str) -> str:
        """Normalize a single parameter type for inner classes."""
        array_suffix = ""
        while param_type.endswith("[]"):
            array_suffix += "[]"
            param_type = param_type[:-2]

        if "." in param_type and "$" not in param_type:
            parts = param_type.split(".")
            normalized_parts = []

            for i, part in enumerate(parts):
                if i == 0:
                    normalized_parts.append(part)
                else:
                    previous_part = parts[i - 1]
                    if self._is_likely_inner_class(previous_part, part):
                        if normalized_parts:
                            normalized_parts[-1] = normalized_parts[-1] + "$" + part
                        else:
                            normalized_parts.append(part)
                    else:
                        normalized_parts.append(part)

            param_type = ".".join(normalized_parts)

        return param_type + array_suffix

    def _is_likely_inner_class(self, outer_part: str, inner_part: str) -> bool:
        """Determine if outer.inner represents an inner class vs package.class."""
        if not outer_part or not inner_part:
            return False

        outer_is_class = outer_part[0].isupper()
        inner_is_class = inner_part[0].isupper()

        if not (outer_is_class and inner_is_class):
            return False

        known_packages = {
            "android",
            "java",
            "javax",
            "com",
            "org",
            "net",
            "io",
            "os",
            "lang",
            "util",
            "content",
            "widget",
            "app",
            "support",
            "design",
            "fragment",
            "activity",
            "graphics",
            "text",
            "database",
            "preference",
            "animation",
            "concurrent",
        }

        if outer_part.islower() and outer_part in known_packages:
            return False

        if len(outer_part) <= 3 and outer_part.islower():
            return False

        return True
