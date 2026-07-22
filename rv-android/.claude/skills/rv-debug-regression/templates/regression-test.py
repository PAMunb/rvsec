"""
Regression Test Template

Use this template when adding regression tests after fixing a bug.
"""

import pytest


def test_regression_ISSUE_NAME():
    """
    Regression test for: BRIEF_DESCRIPTION

    Breaking commit: COMMIT_HASH
    Root cause: ROOT_CAUSE_SUMMARY
    Fixed in: FIX_COMMIT_HASH

    This test ensures the regression does not recur.
    """
    # Arrange
    # Setup the conditions that triggered the regression
    input_data = ...

    # Act
    # Call the function/method that was broken
    result = function_under_test(input_data)

    # Assert
    # Verify the correct behavior (that was broken before)
    assert result == expected_value, (
        "Regression: DESCRIPTION_OF_WHAT_SHOULD_HAPPEN"
    )


class TestRegressionISSUE_NAME:
    """
    Regression test suite for: BRIEF_DESCRIPTION

    Use this class if multiple related tests are needed.
    """

    @pytest.fixture
    def setup_regression_scenario(self):
        """Setup that reproduces the regression conditions."""
        # Create the specific conditions that caused the bug
        return ...

    def test_normal_case(self, setup_regression_scenario):
        """Test that normal operation works after fix."""
        result = function_under_test(setup_regression_scenario)
        assert result == expected_normal_value

    def test_edge_case_that_caused_regression(self, setup_regression_scenario):
        """Test the specific edge case that caused the regression."""
        # This is the case that was broken
        edge_input = modify_for_edge_case(setup_regression_scenario)
        result = function_under_test(edge_input)
        assert result == expected_edge_value, (
            "Regression: This specific case was broken in COMMIT_HASH"
        )

    def test_related_edge_case(self, setup_regression_scenario):
        """Test related edge cases that might have similar issues."""
        related_input = ...
        result = function_under_test(related_input)
        assert result == expected_related_value
