"""
Tests for SignatureNormalizer - Android method signature normalization.

Tests cover:
- normalize_signature() with various inner class patterns
- normalize_class_name() with mixed separators
- normalize_parameter_list() with comma/semicolon separators
- _normalize_single_parameter() with array notation
- _is_likely_inner_class() heuristics
- extract_method_name(), extract_parameters(), create_signature()
"""

import pytest
from rv_android_core.util.android.signature_normalizer import SignatureNormalizer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def normalizer():
    """Create SignatureNormalizer instance."""
    return SignatureNormalizer()


# ---------------------------------------------------------------------------
# Tests: normalize_signature()
# ---------------------------------------------------------------------------


class TestNormalizeSignature:
    """Test normalize_signature() with various inner class patterns."""

    def test_simple_inner_class(self, normalizer):
        """Test simple inner class notation conversion."""
        result = normalizer.normalize_signature("onTabSelected(TabLayout.Tab)")
        assert result == "onTabSelected(TabLayout$Tab)"

    def test_nested_inner_class(self, normalizer):
        """Test nested inner class notation."""
        result = normalizer.normalize_signature("onClick(View.OnClickListener)")
        assert result == "onClick(View$OnClickListener)"

    def test_android_package_unchanged(self, normalizer):
        """Test that android package notation is unchanged."""
        result = normalizer.normalize_signature("onCreate(android.os.Bundle)")
        assert result == "onCreate(android.os.Bundle)"

    def test_java_lang_unchanged(self, normalizer):
        """Test that java.lang package is unchanged."""
        result = normalizer.normalize_signature("toString(java.lang.String)")
        assert result == "toString(java.lang.String)"

    def test_multiple_parameters(self, normalizer):
        """Test multiple parameters with mixed notation."""
        result = normalizer.normalize_signature(
            "onItemSelected(AdapterView.ParentView,View)"
        )
        assert "AdapterView$ParentView" in result

    def test_no_parameters(self, normalizer):
        """Test method with no parameters."""
        result = normalizer.normalize_signature("onCreate()")
        assert result == "onCreate()"

    def test_no_parentheses(self, normalizer):
        """Test signature without parentheses returns as-is."""
        result = normalizer.normalize_signature("someMethod")
        assert result == "someMethod"

    def test_already_normalized(self, normalizer):
        """Test signature already using $ notation."""
        result = normalizer.normalize_signature("onClick(View$OnClickListener)")
        assert result == "onClick(View$OnClickListener)"

    def test_missing_closing_paren(self, normalizer):
        """Test signature without closing parenthesis."""
        result = normalizer.normalize_signature("onCreate(android.os.Bundle")
        assert result == "onCreate(android.os.Bundle"

    def test_nested_inner_classes(self, normalizer):
        """Test deeply nested inner classes."""
        result = normalizer.normalize_signature("method(Outer.Inner.Deep)")
        assert result == "method(Outer$Inner$Deep)"


# ---------------------------------------------------------------------------
# Tests: normalize_class_name()
# ---------------------------------------------------------------------------


class TestNormalizeClassName:
    """Test normalize_class_name() with mixed separators."""

    def test_simple_inner_class(self, normalizer):
        """Test simple inner class normalization."""
        result = normalizer.normalize_class_name("com.example.OuterClass.InnerClass")
        assert result == "com.example.OuterClass$InnerClass"

    def test_mixed_separators(self, normalizer):
        """Test mixed dot and $ separators."""
        result = normalizer.normalize_class_name("Map.GameFieldPosition$1")
        assert result == "Map$GameFieldPosition$1"

    def test_no_dots_returns_unchanged(self, normalizer):
        """Test class name without dots returns unchanged."""
        result = normalizer.normalize_class_name("SimpleClass")
        assert result == "SimpleClass"

    def test_android_package_preserved(self, normalizer):
        """Test android package structure is preserved."""
        result = normalizer.normalize_class_name("android.os.Bundle")
        assert result == "android.os.Bundle"

    def test_java_package_preserved(self, normalizer):
        """Test java package structure is preserved."""
        result = normalizer.normalize_class_name("java.lang.String")
        assert result == "java.lang.String"

    def test_package_to_inner_class(self, normalizer):
        """Test package with inner class."""
        result = normalizer.normalize_class_name("android.widget.Button.OnClickListener")
        assert result == "android.widget.Button$OnClickListener"


# ---------------------------------------------------------------------------
# Tests: normalize_parameter_list()
# ---------------------------------------------------------------------------


class TestNormalizeParameterList:
    """Test normalize_parameter_list() with various separators."""

    def test_comma_separated(self, normalizer):
        """Test comma-separated parameters."""
        result = normalizer.normalize_parameter_list("TabLayout.Tab,View.OnClickListener")
        assert "TabLayout$Tab" in result
        assert "View$OnClickListener" in result

    def test_semicolon_separated(self, normalizer):
        """Test semicolon-separated parameters."""
        result = normalizer.normalize_parameter_list("TabLayout.Tab;View.OnClickListener")
        assert "TabLayout$Tab" in result
        assert "View$OnClickListener" in result

    def test_empty_parameters(self, normalizer):
        """Test empty parameter string."""
        result = normalizer.normalize_parameter_list("")
        assert result == ""

    def test_single_parameter(self, normalizer):
        """Test single parameter normalization."""
        result = normalizer.normalize_parameter_list("OuterClass.InnerClass")
        assert result == "OuterClass$InnerClass"

    def test_preserves_whitespace(self, normalizer):
        """Test that whitespace is preserved."""
        result = normalizer.normalize_parameter_list(" TabLayout.Tab , View.OnClickListener ")
        # Should preserve spaces around commas
        assert "TabLayout$Tab" in result
        assert "View$OnClickListener" in result


# ---------------------------------------------------------------------------
# Tests: _normalize_single_parameter()
# ---------------------------------------------------------------------------


class TestNormalizeSingleParameter:
    """Test _normalize_single_parameter() with array notation and packages."""

    def test_inner_class_conversion(self, normalizer):
        """Test inner class dot to $ conversion."""
        result = normalizer._normalize_single_parameter("TabLayout.Tab")
        assert result == "TabLayout$Tab"

    def test_android_package_unchanged(self, normalizer):
        """Test android package unchanged."""
        result = normalizer._normalize_single_parameter("android.os.Bundle")
        assert result == "android.os.Bundle"

    def test_java_lang_unchanged(self, normalizer):
        """Test java.lang unchanged."""
        result = normalizer._normalize_single_parameter("java.lang.String")
        assert result == "java.lang.String"

    def test_array_notation_preserved(self, normalizer):
        """Test array notation is preserved."""
        result = normalizer._normalize_single_parameter("OuterClass.InnerClass[]")
        assert result == "OuterClass$InnerClass[]"

    def test_multi_dimensional_array(self, normalizer):
        """Test multi-dimensional array notation."""
        result = normalizer._normalize_single_parameter("Outer.Inner[][]")
        assert result == "Outer$Inner[][]"

    def test_nested_inner_classes(self, normalizer):
        """Test nested inner class conversion."""
        result = normalizer._normalize_single_parameter("OuterClass.InnerClass.Deep")
        assert result == "OuterClass$InnerClass$Deep"

    def test_known_package_widget(self, normalizer):
        """Test known package 'widget' is unchanged."""
        result = normalizer._normalize_single_parameter("android.widget.TextView")
        assert result == "android.widget.TextView"

    def test_class_widget_becomes_inner(self, normalizer):
        """Test Widget.SomeClass becomes Widget$SomeClass (both uppercase)."""
        result = normalizer._normalize_single_parameter("Widget.SomeClass")
        assert result == "Widget$SomeClass"


# ---------------------------------------------------------------------------
# Tests: _is_likely_inner_class()
# ---------------------------------------------------------------------------


class TestIsLikelyInnerClass:
    """Test _is_likely_inner_class() heuristics."""

    def test_both_uppercase(self, normalizer):
        """Test both uppercase = inner class."""
        assert normalizer._is_likely_inner_class("Outer", "Inner") is True

    def test_lowercase_outer(self, normalizer):
        """Test lowercase outer = package."""
        assert normalizer._is_likely_inner_class("android", "os") is False

    def test_lowercase_inner(self, normalizer):
        """Test lowercase inner = package."""
        assert normalizer._is_likely_inner_class("Class", "method") is False

    def test_empty_parts(self, normalizer):
        """Test empty parts returns False."""
        assert normalizer._is_likely_inner_class("", "Inner") is False
        assert normalizer._is_likely_inner_class("Outer", "") is False

    def test_known_package_android(self, normalizer):
        """Test known package 'android' is not inner class."""
        assert normalizer._is_likely_inner_class("android", "os") is False

    def test_known_package_java(self, normalizer):
        """Test known package 'java' is not inner class."""
        assert normalizer._is_likely_inner_class("java", "lang") is False

    def test_short_lowercase(self, normalizer):
        """Test short lowercase strings are not inner classes."""
        assert normalizer._is_likely_inner_class("os", "Bundle") is False

    def test_class_with_inner_class(self, normalizer):
        """Test actual class with inner class."""
        assert normalizer._is_likely_inner_class("TabLayout", "Tab") is True
        assert normalizer._is_likely_inner_class("View", "OnClickListener") is True


# ---------------------------------------------------------------------------
# Tests: extract_method_name()
# ---------------------------------------------------------------------------


class TestExtractMethodName:
    """Test extract_method_name() extraction."""

    def test_simple_method(self, normalizer):
        """Test simple method name extraction."""
        result = normalizer.extract_method_name("onCreate(android.os.Bundle)")
        assert result == "onCreate"

    def test_no_parameters(self, normalizer):
        """Test method with no parameters."""
        result = normalizer.extract_method_name("onStart()")
        assert result == "onStart"

    def test_no_parentheses(self, normalizer):
        """Test string without parentheses."""
        result = normalizer.extract_method_name("methodName")
        assert result == "methodName"

    def test_complex_parameters(self, normalizer):
        """Test method with complex parameters."""
        result = normalizer.extract_method_name("onClick(View$OnClickListener,android.view.MotionEvent)")
        assert result == "onClick"


# ---------------------------------------------------------------------------
# Tests: extract_parameters()
# ---------------------------------------------------------------------------


class TestExtractParameters:
    """Test extract_parameters() extraction."""

    def test_single_parameter(self, normalizer):
        """Test single parameter extraction."""
        result = normalizer.extract_parameters("onCreate(android.os.Bundle)")
        assert result == "android.os.Bundle"

    def test_multiple_parameters(self, normalizer):
        """Test multiple parameter extraction."""
        result = normalizer.extract_parameters("method(String,int)")
        assert result == "String,int"

    def test_no_parameters(self, normalizer):
        """Test no parameters extraction."""
        result = normalizer.extract_parameters("onStart()")
        assert result == ""

    def test_no_parentheses(self, normalizer):
        """Test string without parentheses."""
        result = normalizer.extract_parameters("methodName")
        assert result == ""

    def test_nested_parentheses(self, normalizer):
        """Test nested parentheses extraction."""
        result = normalizer.extract_parameters("method(Outer$Inner)")
        assert result == "Outer$Inner"


# ---------------------------------------------------------------------------
# Tests: create_signature()
# ---------------------------------------------------------------------------


class TestCreateSignature:
    """Test create_signature() building."""

    def test_create_simple_signature(self, normalizer):
        """Test creating simple method signature."""
        result = normalizer.create_signature("onCreate", "android.os.Bundle")
        assert result == "onCreate(android.os.Bundle)"

    def test_create_with_inner_class(self, normalizer):
        """Test creating signature with inner class normalization."""
        result = normalizer.create_signature("onClick", "View.OnClickListener")
        assert result == "onClick(View$OnClickListener)"

    def test_create_multiple_parameters(self, normalizer):
        """Test creating signature with multiple parameters."""
        result = normalizer.create_signature("method", "String,int")
        assert result == "method(String,int)"

    def test_create_empty_parameters(self, normalizer):
        """Test creating signature with empty parameters."""
        result = normalizer.create_signature("onStart", "")
        assert result == "onStart()"
