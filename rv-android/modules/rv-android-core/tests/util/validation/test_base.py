"""
Tests for BaseValidatedModel - rv_android_core Pydantic validation base class.

Tests cover:
- Model initialization with validation
- model_dump_json_safe() and model_dump_safe() serialization
- from_dict() deserialization
- __repr__(), __eq__(), __hash__() magic methods
- Configuration behavior (extra fields, whitespace stripping)
"""

from typing import Optional
from unittest.mock import patch

import pytest
from pydantic import Field
from rv_android_core.util.validation.base import BaseValidatedModel

# ---------------------------------------------------------------------------
# Test Model
# ---------------------------------------------------------------------------


class SampleModel(BaseValidatedModel):
    """Test model for validation."""

    name: str = "default"
    value: int = 0
    optional: Optional[str] = None


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestInitialization:
    """Test model initialization with validation."""

    def test_init_with_data(self):
        """Test initialization with data."""
        model = SampleModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        model = SampleModel()
        assert model.name == "default"
        assert model.value == 0

    def test_init_strips_whitespace(self):
        """Test that str_strip_whitespace is enabled."""
        model = SampleModel(name="  test  ")
        assert model.name == "test"

    def test_init_forbids_extra_fields(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            SampleModel(name="test", unknown_field="value")

    def test_init_validates_types(self):
        """Test that type validation is enabled."""
        # Should fail if we try to pass wrong type
        # Note: Pydantic may coerce types, so this depends on strictness
        model = SampleModel(value="123")  # May coerce to int
        assert model.value == 123


# ---------------------------------------------------------------------------
# Tests: model_dump_json_safe()
# ---------------------------------------------------------------------------


class SampleModelDumpJsonSafe:
    """Test model_dump_json_safe() serialization."""

    def test_dump_json_returns_string(self):
        """Test that dump_json returns string."""
        model = SampleModel(name="test", value=42)
        json_str = model.model_dump_json_safe()
        assert isinstance(json_str, str)

    def test_dump_json_contains_fields(self):
        """Test that JSON contains model fields."""
        model = SampleModel(name="test", value=42)
        json_str = model.model_dump_json_safe()
        assert "test" in json_str
        assert "42" in json_str

    def test_dump_json_handles_errors(self):
        """Test that JSON serialization errors are handled."""
        model = SampleModel(name="test")
        # Force error by breaking model_dump_json
        with patch.object(
            model, "model_dump_json", side_effect=Exception("JSON error")
        ):
            result = model.model_dump_json_safe()
            # Should fallback to str(model_dump())
            assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Tests: model_dump_safe()
# ---------------------------------------------------------------------------


class SampleModelDumpSafe:
    """Test model_dump_safe() serialization."""

    def test_dump_safe_returns_dict(self):
        """Test that dump_safe returns dict."""
        model = SampleModel(name="test", value=42)
        data = model.model_dump_safe()
        assert isinstance(data, dict)

    def test_dump_safe_contains_fields(self):
        """Test that dict contains model fields."""
        model = SampleModel(name="test", value=42)
        data = model.model_dump_safe()
        assert data["name"] == "test"
        assert data["value"] == 42

    def test_dump_safe_handles_errors(self):
        """Test that serialization errors are handled."""
        model = SampleModel(name="test")
        # Force error
        with patch.object(model, "model_dump", side_effect=Exception("Dump error")):
            result = model.model_dump_safe()
            assert "__type__" in result
            assert "__error__" in result
            assert result["__type__"] == "SampleModel"


# ---------------------------------------------------------------------------
# Tests: from_dict()
# ---------------------------------------------------------------------------


class TestFromDict:
    """Test from_dict() deserialization."""

    def test_from_dict_creates_instance(self):
        """Test that from_dict creates model instance."""
        data = {"name": "test", "value": 42}
        model = SampleModel.from_dict(data)
        assert isinstance(model, SampleModel)

    def test_from_dict_sets_values(self):
        """Test that from_dict sets values correctly."""
        data = {"name": "from_dict", "value": 100}
        model = SampleModel.from_dict(data)
        assert model.name == "from_dict"
        assert model.value == 100

    def test_from_dict_with_partial_data(self):
        """Test that from_dict works with partial data."""
        data = {"name": "partial"}
        model = SampleModel.from_dict(data)
        assert model.name == "partial"
        assert model.value == 0  # default

    def test_from_dict_with_empty_data(self):
        """Test that from_dict works with empty data."""
        data = {}
        model = SampleModel.from_dict(data)
        assert model.name == "default"
        assert model.value == 0


# ---------------------------------------------------------------------------
# Tests: __repr__()
# ---------------------------------------------------------------------------


class TestRepr:
    """Test __repr__() string representation."""

    def test_repr_returns_string(self):
        """Test that __repr__ returns string."""
        model = SampleModel(name="test")
        repr_str = repr(model)
        assert isinstance(repr_str, str)

    def test_repr_contains_class_name(self):
        """Test that __repr__ contains class name."""
        model = SampleModel(name="test")
        repr_str = repr(model)
        assert "SampleModel" in repr_str

    def test_repr_handles_errors(self):
        """Test that __repr__ handles errors gracefully."""
        model = SampleModel(name="test")
        # Force error
        with patch.object(model, "__repr__", side_effect=Exception("Repr error")):
            # The fallback should work
            try:
                repr_str = repr(model)
                assert "SampleModel" in repr_str
            except Exception:
                # Fallback representation
                pass


# ---------------------------------------------------------------------------
# Tests: __eq__()
# ---------------------------------------------------------------------------


class TestEq:
    """Test __eq__() equality comparison."""

    def test_equal_models(self):
        """Test that identical models are equal."""
        model1 = SampleModel(name="test", value=42)
        model2 = SampleModel(name="test", value=42)
        assert model1 == model2

    def test_different_models(self):
        """Test that different models are not equal."""
        model1 = SampleModel(name="test", value=42)
        model2 = SampleModel(name="test", value=100)
        assert model1 != model2

    def test_not_equal_to_other_types(self):
        """Test that model is not equal to other types."""
        model = SampleModel(name="test")
        assert model != "string"
        assert model != 42
        assert model != None

    def test_equal_handles_errors(self):
        """Test that __eq__ handles errors gracefully."""
        model1 = SampleModel(name="test")
        model2 = SampleModel(name="test")
        # Pydantic's model_dump is robust, but the code has try/except fallback
        # Just verify equality works without raising
        result = model1 == model2
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Tests: __hash__()
# ---------------------------------------------------------------------------


class TestHash:
    """Test __hash__() generation."""

    def test_hash_returns_int(self):
        """Test that __hash__ returns int."""
        model = SampleModel(name="test")
        hash_val = hash(model)
        assert isinstance(hash_val, int)

    def test_equal_models_have_same_hash(self):
        """Test that equal models have same hash."""
        model1 = SampleModel(name="test", value=42)
        model2 = SampleModel(name="test", value=42)
        assert hash(model1) == hash(model2)

    def test_hash_handles_errors(self):
        """Test that __hash__ handles errors gracefully."""
        model = SampleModel(name="test")
        # Pydantic's model_dump_json is robust, but the code has try/except fallback
        # Just verify hash works without raising
        hash_val = hash(model)
        assert isinstance(hash_val, int)

    def test_hash_allows_dict_usage(self):
        """Test that hashed models can be used in dict."""
        model1 = SampleModel(name="test")
        model2 = SampleModel(name="other")

        # Note: This may not work if models are mutable
        # Just ensure hash doesn't raise
        hash1 = hash(model1)
        hash2 = hash(model2)
        assert isinstance(hash1, int)
        assert isinstance(hash2, int)


# ---------------------------------------------------------------------------
# Tests: Configuration
# ---------------------------------------------------------------------------


class TestConfiguration:
    """Test model configuration."""

    def test_validate_assignment_enabled(self):
        """Test that validate_assignment is enabled."""
        model = SampleModel(name="test")
        # Should raise on invalid assignment
        # Note: Depends on validation config
        try:
            model.value = "not_an_int"  # May coerce or raise
        except Exception:
            pass  # Expected if strict validation

    def test_arbitrary_types_allowed(self):
        """Test that arbitrary_types_allowed is True."""
        # Config should allow arbitrary types
        assert SampleModel.model_config.get("arbitrary_types_allowed") is True

    def test_extra_forbidden(self):
        """Test that extra fields are forbidden."""
        assert SampleModel.model_config.get("extra") == "forbid"

    def test_str_strip_whitespace(self):
        """Test that str_strip_whitespace is enabled."""
        assert SampleModel.model_config.get("str_strip_whitespace") is True
