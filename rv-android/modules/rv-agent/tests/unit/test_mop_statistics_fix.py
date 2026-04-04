"""
Unit tests for Group 44: MOP statistics fix (D16).

Design ref: D16 (N-20 LOW)

Verifies that get_statistics() uses mop_max_variations threshold for MOP
elements and max_variations for non-MOP elements, preventing premature
exhaustion reporting for MOP fields.
"""

import pytest
from rv_agent.strategies.rvagent_strategy.input_value_generator import (
    InputValueGenerator,
)


@pytest.fixture
def generator():
    """InputValueGenerator with max_variations=5, mop_max_variations=11."""
    return InputValueGenerator(max_variations=5, mop_max_variations=11)


class TestMopStatisticsFix:
    """D16: MOP statistics use correct threshold per element type."""

    def test_n20_s1_mop_element_not_counted_as_exhausted(self, generator):
        """
        N-20-S1: MOP element with 6 tested values is NOT counted as exhausted.

        A MOP element has mop_max_variations=11, so 6 values tested means
        it is still active (6 < 11).
        """
        # Register element as MOP via get_next_value
        generator.get_next_value("mop_field", is_mop=True)

        # Manually set 6 tested values (simulating multiple calls)
        generator.tested_values["mop_field"] = [f"val_{i}" for i in range(6)]

        stats = generator.get_statistics()

        assert stats["total_elements_tested"] == 1
        assert stats["exhausted_elements"] == 0, (
            "MOP element with 6 tested values should NOT be exhausted "
            "(threshold is mop_max_variations=11)"
        )
        assert stats["active_elements"] == 1
        assert stats["total_values_tested"] == 6

    def test_n20_s2_non_mop_element_counted_as_exhausted(self, generator):
        """
        N-20-S2: Non-MOP element with 6 tested values IS counted as exhausted.

        A non-MOP element has max_variations=5, so 6 values tested means
        it is exhausted (6 >= 5).
        """
        # Call with is_mop=False so element is NOT in mop_elements
        generator.get_next_value("regular_field", is_mop=False)

        # Manually set 6 tested values
        generator.tested_values["regular_field"] = [f"val_{i}" for i in range(6)]

        stats = generator.get_statistics()

        assert stats["total_elements_tested"] == 1
        assert stats["exhausted_elements"] == 1, (
            "Non-MOP element with 6 tested values should be exhausted "
            "(threshold is max_variations=5)"
        )
        assert stats["active_elements"] == 0
        assert stats["total_values_tested"] == 6

    def test_n20_s3_mop_elements_populated_via_get_next_value(self, generator):
        """
        N-20-S3: mop_elements set is populated when get_next_value(is_mop=True).

        Calling get_next_value with is_mop=True adds the element_id to the
        mop_elements set automatically.
        """
        assert len(generator.mop_elements) == 0

        generator.get_next_value("field_a", is_mop=True)
        assert "field_a" in generator.mop_elements

        generator.get_next_value("field_b", is_mop=False)
        assert "field_b" not in generator.mop_elements

        generator.get_next_value("field_c", is_mop=True)
        assert "field_c" in generator.mop_elements

        assert generator.mop_elements == {"field_a", "field_c"}

    def test_mixed_elements_correct_statistics(self, generator):
        """
        Mixed scenario: both MOP and non-MOP elements with the same number
        of tested values produce different exhaustion results.
        """
        # Register MOP element
        generator.get_next_value("mop_input", is_mop=True)
        # Register non-MOP element
        generator.get_next_value("regular_input", is_mop=False)

        # Both get 6 tested values
        generator.tested_values["mop_input"] = [f"mop_{i}" for i in range(6)]
        generator.tested_values["regular_input"] = [f"reg_{i}" for i in range(6)]

        stats = generator.get_statistics()

        assert stats["total_elements_tested"] == 2
        # Only regular_input is exhausted (6 >= 5), mop_input is not (6 < 11)
        assert stats["exhausted_elements"] == 1
        assert stats["active_elements"] == 1
        assert stats["total_values_tested"] == 12

    def test_mop_element_exhausted_at_threshold(self, generator):
        """
        MOP element becomes exhausted only when reaching mop_max_variations.
        """
        generator.get_next_value("mop_field", is_mop=True)

        # At 10 values: still active (10 < 11)
        generator.tested_values["mop_field"] = [f"val_{i}" for i in range(10)]
        stats = generator.get_statistics()
        assert stats["exhausted_elements"] == 0
        assert stats["active_elements"] == 1

        # At 11 values: exhausted (11 >= 11)
        generator.tested_values["mop_field"] = [f"val_{i}" for i in range(11)]
        stats = generator.get_statistics()
        assert stats["exhausted_elements"] == 1
        assert stats["active_elements"] == 0

    def test_non_mop_element_exhausted_at_threshold(self, generator):
        """
        Non-MOP element becomes exhausted at max_variations threshold.
        """
        generator.get_next_value("regular_field", is_mop=False)

        # At 4 values: still active (4 < 5)
        generator.tested_values["regular_field"] = [f"val_{i}" for i in range(4)]
        stats = generator.get_statistics()
        assert stats["exhausted_elements"] == 0

        # At 5 values: exhausted (5 >= 5)
        generator.tested_values["regular_field"] = [f"val_{i}" for i in range(5)]
        stats = generator.get_statistics()
        assert stats["exhausted_elements"] == 1

    def test_reset_clears_mop_elements(self, generator):
        """
        reset() clears both tested_values and mop_elements.
        """
        generator.get_next_value("mop_field", is_mop=True)
        generator.get_next_value("regular_field", is_mop=False)

        assert len(generator.mop_elements) == 1
        assert len(generator.tested_values) == 2

        generator.reset()

        assert len(generator.mop_elements) == 0
        assert len(generator.tested_values) == 0
