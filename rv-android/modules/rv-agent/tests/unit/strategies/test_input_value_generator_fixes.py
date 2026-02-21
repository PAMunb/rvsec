"""
Tests for InputValueGenerator fixes (gh26 Group 2).

Verifies:
- Faker values first for text type (no PINs)
- PINs only for password/pin types
- No empty string as first value
- MOP field extended variations (11 edge-case payloads)
- Missing input types (search, url, date, time, number, zip, verification_code)
"""

import pytest
from rv_agent.strategies.rvagent_strategy.input_value_generator import (
    InputValueGenerator,
)


class TestValueOrdering:
    """Verify value ordering fixes."""

    def test_faker_values_first_for_text(self):
        """Text type should start with Faker values, not PINs."""
        gen = InputValueGenerator(max_variations=5)
        value = gen.get_next_value("text_field", is_mop=False, input_type="text")

        assert value is not None
        # First value should NOT be a PIN
        assert value not in (
            "1234",
            "0000",
            "123456",
            "password",
            "admin",
            "test",
            "demo",
            "",
        )

    def test_pins_only_for_password(self):
        """Password type should include PINs/common passwords."""
        gen = InputValueGenerator(max_variations=5)
        value = gen.get_next_value("pass_field", is_mop=False, input_type="password")

        assert value is not None
        # First value should be a common password/PIN
        assert value in ("1234", "0000", "123456", "password", "admin", "test", "demo")

    def test_pins_only_for_pin(self):
        """PIN type should include PINs."""
        gen = InputValueGenerator(max_variations=5)
        value = gen.get_next_value("pin_field", is_mop=False, input_type="pin")

        assert value is not None
        assert value in ("1234", "0000", "123456", "password", "admin", "test", "demo")

    def test_no_empty_first_value(self):
        """No type should produce empty string as first value."""
        gen = InputValueGenerator(max_variations=5)

        for input_type in (
            "text",
            "email",
            "name",
            "phone",
            "address",
            "search",
            "url",
            "date",
            "time",
            "number",
            "zip",
            "verification_code",
            "username",
        ):
            value = gen.get_next_value(
                f"field_{input_type}", is_mop=False, input_type=input_type
            )
            assert (
                value != ""
            ), f"First value for '{input_type}' should not be empty string"
            assert (
                value is not None
            ), f"First value for '{input_type}' should not be None"


class TestMopFieldExtendedVariations:
    """Verify MOP field uses extended edge-case payloads."""

    def test_mop_field_extended_variations(self):
        """MOP fields should support 11 edge-case payloads with mop_max_input_variations=11."""
        gen = InputValueGenerator(max_variations=11)
        values = []
        for i in range(11):
            v = gen.get_next_value("mop_field", is_mop=True, input_type="text")
            if v is None:
                break
            values.append(v)

        assert len(values) == 11, f"Expected 11 values for MOP field, got {len(values)}"

        # Should include edge-case payloads
        assert "" in values, "Edge case: empty string should be in MOP values"
        assert "0" in values, "Edge case: zero should be in MOP values"
        assert "-1" in values, "Edge case: negative should be in MOP values"


class TestMissingInputTypes:
    """Verify Faker generators for missing input types."""

    def test_search_type(self):
        """Search type should produce search query values."""
        gen = InputValueGenerator(max_variations=3)
        value = gen.get_next_value("search_field", is_mop=False, input_type="search")
        assert value is not None
        assert len(value) > 0

    def test_url_type(self):
        """URL type should produce URL values."""
        gen = InputValueGenerator(max_variations=3)
        value = gen.get_next_value("url_field", is_mop=False, input_type="url")
        assert value is not None
        assert len(value) > 0

    def test_date_type(self):
        """Date type should produce date values."""
        gen = InputValueGenerator(max_variations=3)
        value = gen.get_next_value("date_field", is_mop=False, input_type="date")
        assert value is not None
        assert len(value) > 0

    def test_time_type(self):
        """Time type should produce time values."""
        gen = InputValueGenerator(max_variations=3)
        value = gen.get_next_value("time_field", is_mop=False, input_type="time")
        assert value is not None
        assert len(value) > 0

    def test_number_type(self):
        """Number type should produce numeric values."""
        gen = InputValueGenerator(max_variations=3)
        value = gen.get_next_value("number_field", is_mop=False, input_type="number")
        assert value is not None
        assert len(value) > 0

    def test_zip_type(self):
        """ZIP type should produce zipcode values."""
        gen = InputValueGenerator(max_variations=3)
        value = gen.get_next_value("zip_field", is_mop=False, input_type="zip")
        assert value is not None
        assert len(value) > 0

    def test_verification_code_type(self):
        """Verification code type should produce numeric code values."""
        gen = InputValueGenerator(max_variations=3)
        value = gen.get_next_value(
            "code_field", is_mop=False, input_type="verification_code"
        )
        assert value is not None
        assert len(value) > 0
        # Should be numeric
        assert value.isdigit(), f"Verification code should be digits, got '{value}'"
