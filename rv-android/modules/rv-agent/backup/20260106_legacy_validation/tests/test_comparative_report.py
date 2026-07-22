"""
Unit tests for ComparativeReportGenerator and related dataclasses.
"""

import json
import csv
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from rv_agent.validation.comparative_report import (
    AppElementCoverage,
    ComparativeMetrics,
    ComparativeReportGenerator
)


# =============================================================================
# AppElementCoverage Dataclass Tests
# =============================================================================

class TestAppElementCoverage:
    """Tests for AppElementCoverage dataclass."""

    def test_creation(self):
        """Test creating AppElementCoverage."""
        coverage = AppElementCoverage(
            app_name="test.apk",
            element_types=["Button", "TextView", "EditText"],
            element_counts={"Button": 5, "TextView": 10, "EditText": 2}
        )

        assert coverage.app_name == "test.apk"
        assert len(coverage.element_types) == 3
        assert coverage.element_counts["Button"] == 5


# =============================================================================
# ComparativeMetrics Dataclass Tests
# =============================================================================

class TestComparativeMetrics:
    """Tests for ComparativeMetrics dataclass."""

    def test_creation_defaults(self):
        """Test ComparativeMetrics has correct defaults."""
        metrics = ComparativeMetrics()

        assert metrics.total_apps == 0
        assert metrics.app_names == []
        assert metrics.all_element_types == set()
        assert metrics.element_frequency == {}
        assert metrics.app_coverages == []
        assert metrics.total_actions == 0
        assert metrics.action_distribution == {}
        assert metrics.total_valid_actions == 0
        assert metrics.total_invalid_actions == 0
        assert metrics.total_tokens == 0
        assert metrics.total_llm_time_ms == 0.0
        assert metrics.total_screens == 0
        assert metrics.total_activities == 0

    def test_mutable_collections_independent(self):
        """Test that mutable collections are independent between instances."""
        metrics1 = ComparativeMetrics()
        metrics2 = ComparativeMetrics()

        metrics1.app_names.append("app1")
        metrics1.all_element_types.add("Button")

        assert metrics2.app_names == []
        assert metrics2.all_element_types == set()


# =============================================================================
# ComparativeReportGenerator Initialization Tests
# =============================================================================

class TestComparativeReportGeneratorInit:
    """Tests for ComparativeReportGenerator initialization."""

    def test_init_creates_empty_results(self, tmp_path):
        """Test initialization creates empty results dict."""
        generator = ComparativeReportGenerator(tmp_path)

        assert generator.results_dir == tmp_path
        assert generator.app_results == {}

    def test_init_accepts_string_path(self, tmp_path):
        """Test initialization with string path."""
        generator = ComparativeReportGenerator(str(tmp_path))

        assert generator.results_dir == tmp_path


# =============================================================================
# Load Results Tests
# =============================================================================

class TestComparativeReportGeneratorLoadResults:
    """Tests for ComparativeReportGenerator.load_results()."""

    def _create_validation_result(self, tmp_path: Path, app_name: str, data: dict) -> Path:
        """Helper to create a validation result file."""
        file_path = tmp_path / f"{app_name}_validation.json"
        data['app_name'] = app_name
        file_path.write_text(json.dumps(data))
        return file_path

    def test_load_results_empty_directory(self, tmp_path):
        """Test loading from empty directory."""
        generator = ComparativeReportGenerator(tmp_path)

        count = generator.load_results()

        assert count == 0
        assert generator.app_results == {}

    def test_load_results_single_file(self, tmp_path):
        """Test loading a single result file."""
        self._create_validation_result(tmp_path, "app1", {"total_iterations": 25})

        generator = ComparativeReportGenerator(tmp_path)
        count = generator.load_results()

        assert count == 1
        assert "app1" in generator.app_results
        assert generator.app_results["app1"]["total_iterations"] == 25

    def test_load_results_multiple_files(self, tmp_path):
        """Test loading multiple result files."""
        self._create_validation_result(tmp_path, "app1", {"total_iterations": 25})
        self._create_validation_result(tmp_path, "app2", {"total_iterations": 30})
        self._create_validation_result(tmp_path, "app3", {"total_iterations": 20})

        generator = ComparativeReportGenerator(tmp_path)
        count = generator.load_results()

        assert count == 3
        assert "app1" in generator.app_results
        assert "app2" in generator.app_results
        assert "app3" in generator.app_results

    def test_load_results_custom_pattern(self, tmp_path):
        """Test loading with custom pattern."""
        # Create files with different patterns
        (tmp_path / "app1_results.json").write_text('{"app_name": "app1"}')
        (tmp_path / "app2_results.json").write_text('{"app_name": "app2"}')
        (tmp_path / "app3_validation.json").write_text('{"app_name": "app3"}')

        generator = ComparativeReportGenerator(tmp_path)
        count = generator.load_results(pattern="*_results.json")

        assert count == 2
        assert "app1" in generator.app_results
        assert "app2" in generator.app_results
        assert "app3" not in generator.app_results

    def test_load_results_invalid_json(self, tmp_path):
        """Test handling of invalid JSON files."""
        (tmp_path / "good_validation.json").write_text('{"app_name": "good"}')
        (tmp_path / "bad_validation.json").write_text('not valid json')

        generator = ComparativeReportGenerator(tmp_path)
        count = generator.load_results()

        assert count == 1
        assert "good" in generator.app_results

    def test_load_results_uses_filename_if_no_app_name(self, tmp_path):
        """Test that filename is used if app_name not in data."""
        (tmp_path / "myapp_validation.json").write_text('{"total_iterations": 10}')

        generator = ComparativeReportGenerator(tmp_path)
        generator.load_results()

        # Should use filename stem
        assert "myapp_validation" in generator.app_results


# =============================================================================
# Aggregate Metrics Tests
# =============================================================================

class TestComparativeReportGeneratorAggregateMetrics:
    """Tests for ComparativeReportGenerator.aggregate_metrics()."""

    def test_aggregate_empty_results(self, tmp_path):
        """Test aggregating with no results."""
        generator = ComparativeReportGenerator(tmp_path)

        metrics = generator.aggregate_metrics()

        assert metrics.total_apps == 0
        assert metrics.app_names == []

    def test_aggregate_basic_metrics(self, tmp_path):
        """Test aggregating basic metrics."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": ["Button", "TextView"], "type_counts": {"Button": 5}},
                "actions": {"by_type": {"CLICK": 10}, "valid": 8, "invalid": 2},
                "llm": {"total_tokens": 1000, "total_time_ms": 500},
                "exploration": {"unique_screens": 3, "activities": ["Main", "Settings"]}
            },
            "app2": {
                "element_coverage": {"types_seen": ["Button", "EditText"], "type_counts": {"Button": 3}},
                "actions": {"by_type": {"CLICK": 8, "BACK": 2}, "valid": 9, "invalid": 1},
                "llm": {"total_tokens": 1500, "total_time_ms": 600},
                "exploration": {"unique_screens": 4, "activities": ["Main"]}
            }
        }

        metrics = generator.aggregate_metrics()

        assert metrics.total_apps == 2
        assert set(metrics.app_names) == {"app1", "app2"}
        assert metrics.all_element_types == {"Button", "TextView", "EditText"}
        assert metrics.element_frequency["Button"] == 2  # Both apps have Button
        assert metrics.element_frequency["TextView"] == 1
        assert metrics.element_frequency["EditText"] == 1

    def test_aggregate_action_metrics(self, tmp_path):
        """Test aggregating action metrics."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {"CLICK": 10, "BACK": 5}, "valid": 12, "invalid": 3},
                "llm": {},
                "exploration": {}
            },
            "app2": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {"CLICK": 8, "HOME": 2}, "valid": 9, "invalid": 1},
                "llm": {},
                "exploration": {}
            }
        }

        metrics = generator.aggregate_metrics()

        assert metrics.total_actions == 25
        assert metrics.action_distribution["CLICK"] == 18
        assert metrics.action_distribution["BACK"] == 5
        assert metrics.action_distribution["HOME"] == 2
        assert metrics.total_valid_actions == 21
        assert metrics.total_invalid_actions == 4

    def test_aggregate_llm_metrics(self, tmp_path):
        """Test aggregating LLM metrics."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0},
                "llm": {"total_tokens": 1000, "total_time_ms": 500.0},
                "exploration": {}
            },
            "app2": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0},
                "llm": {"total_tokens": 2000, "total_time_ms": 800.0},
                "exploration": {}
            }
        }

        metrics = generator.aggregate_metrics()

        assert metrics.total_tokens == 3000
        assert metrics.total_llm_time_ms == 1300.0

    def test_aggregate_exploration_metrics(self, tmp_path):
        """Test aggregating exploration metrics."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0},
                "llm": {},
                "exploration": {"unique_screens": 5, "activities": ["A", "B", "C"]}
            },
            "app2": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0},
                "llm": {},
                "exploration": {"unique_screens": 3, "activities": ["X", "Y"]}
            }
        }

        metrics = generator.aggregate_metrics()

        assert metrics.total_screens == 8
        assert metrics.total_activities == 5

    def test_aggregate_creates_app_coverages(self, tmp_path):
        """Test that aggregate creates per-app coverage data."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": ["Button"], "type_counts": {"Button": 5}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0},
                "llm": {},
                "exploration": {}
            }
        }

        metrics = generator.aggregate_metrics()

        assert len(metrics.app_coverages) == 1
        assert metrics.app_coverages[0].app_name == "app1"
        assert metrics.app_coverages[0].element_types == ["Button"]


# =============================================================================
# Generate Markdown Report Tests
# =============================================================================

class TestComparativeReportGeneratorMarkdownReport:
    """Tests for ComparativeReportGenerator.generate_markdown_report()."""

    def test_generate_markdown_creates_file(self, tmp_path):
        """Test that markdown report is created."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": ["Button"], "type_counts": {}},
                "actions": {"by_type": {"CLICK": 10}, "valid": 8, "invalid": 2},
                "llm": {"total_tokens": 1000, "total_time_ms": 500},
                "exploration": {"unique_screens": 3, "activities": ["Main"]}
            }
        }

        metrics = generator.aggregate_metrics()
        output_path = tmp_path / "report.md"
        generator.generate_markdown_report(output_path, metrics)

        assert output_path.exists()

    def test_generate_markdown_contains_header(self, tmp_path):
        """Test that markdown contains header."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0},
                "llm": {},
                "exploration": {}
            }
        }

        metrics = generator.aggregate_metrics()
        output_path = tmp_path / "report.md"
        generator.generate_markdown_report(output_path, metrics)

        content = output_path.read_text()
        assert "# RVAgent Multi-App Validation Report" in content
        assert "**Total Apps**" in content

    def test_generate_markdown_contains_element_coverage(self, tmp_path):
        """Test that markdown contains element coverage section."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": ["Button", "TextView"], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0},
                "llm": {},
                "exploration": {}
            }
        }

        metrics = generator.aggregate_metrics()
        output_path = tmp_path / "report.md"
        generator.generate_markdown_report(output_path, metrics)

        content = output_path.read_text()
        assert "Element Type Coverage" in content
        assert "Button" in content

    def test_generate_markdown_contains_action_distribution(self, tmp_path):
        """Test that markdown contains action distribution section."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {"CLICK": 10, "BACK": 5}, "valid": 12, "invalid": 3},
                "llm": {},
                "exploration": {}
            }
        }

        metrics = generator.aggregate_metrics()
        output_path = tmp_path / "report.md"
        generator.generate_markdown_report(output_path, metrics)

        content = output_path.read_text()
        assert "Action Distribution" in content
        assert "CLICK" in content
        assert "BACK" in content

    def test_generate_markdown_contains_llm_metrics(self, tmp_path):
        """Test that markdown contains LLM metrics section."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0},
                "llm": {"total_tokens": 5000, "total_time_ms": 2000},
                "exploration": {}
            }
        }

        metrics = generator.aggregate_metrics()
        output_path = tmp_path / "report.md"
        generator.generate_markdown_report(output_path, metrics)

        content = output_path.read_text()
        assert "LLM Usage Metrics" in content
        assert "5,000" in content or "5000" in content

    def test_generate_markdown_contains_exploration_metrics(self, tmp_path):
        """Test that markdown contains exploration metrics section."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0},
                "llm": {},
                "exploration": {"unique_screens": 5, "activities": ["A", "B"]}
            }
        }

        metrics = generator.aggregate_metrics()
        output_path = tmp_path / "report.md"
        generator.generate_markdown_report(output_path, metrics)

        content = output_path.read_text()
        assert "Exploration Metrics" in content
        assert "unique screens" in content.lower()

    def test_generate_markdown_detects_low_type_text(self, tmp_path):
        """Test that markdown detects low SET_TEXT usage."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "element_coverage": {"types_seen": ["EditText"], "type_counts": {}},
                "actions": {"by_type": {"CLICK": 100, "SET_TEXT": 1}, "valid": 100, "invalid": 1},
                "llm": {},
                "exploration": {}
            }
        }

        metrics = generator.aggregate_metrics()
        output_path = tmp_path / "report.md"
        generator.generate_markdown_report(output_path, metrics)

        content = output_path.read_text()
        assert "SET_TEXT usage very low" in content or "Fix SET_TEXT usage" in content


# =============================================================================
# Generate CSV Report Tests
# =============================================================================

class TestComparativeReportGeneratorCSVReport:
    """Tests for ComparativeReportGenerator.generate_csv_report()."""

    def test_generate_csv_creates_file(self, tmp_path):
        """Test that CSV report is created."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "total_iterations": 25,
                "execution_time_s": 180.0,
                "element_coverage": {"types_seen": ["Button"], "type_counts": {}},
                "actions": {"by_type": {"CLICK": 10}, "valid": 8, "invalid": 2, "valid_rate": 0.8},
                "llm": {"total_tokens": 1000, "avg_tokens_per_iteration": 40, "avg_time_per_iteration_ms": 50},
                "exploration": {"unique_screens": 3, "activities": ["Main"]}
            }
        }

        output_path = tmp_path / "report.csv"
        generator.generate_csv_report(output_path)

        assert output_path.exists()

    def test_generate_csv_contains_headers(self, tmp_path):
        """Test that CSV contains correct headers."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "total_iterations": 25,
                "execution_time_s": 180.0,
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0, "valid_rate": 0},
                "llm": {},
                "exploration": {"unique_screens": 0, "activities": []}
            }
        }

        output_path = tmp_path / "report.csv"
        generator.generate_csv_report(output_path)

        with open(output_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)

        assert "app_name" in headers
        assert "total_iterations" in headers
        assert "valid_actions" in headers
        assert "click_count" in headers

    def test_generate_csv_contains_data(self, tmp_path):
        """Test that CSV contains correct data."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "total_iterations": 25,
                "execution_time_s": 180.0,
                "element_coverage": {"types_seen": ["Button", "EditText"], "type_counts": {}},
                "actions": {"by_type": {"CLICK": 15, "SET_TEXT": 5}, "valid": 18, "invalid": 2, "valid_rate": 0.9},
                "llm": {"total_tokens": 5000, "avg_tokens_per_iteration": 200, "avg_time_per_iteration_ms": 100},
                "exploration": {"unique_screens": 5, "activities": ["A", "B", "C"]}
            }
        }

        output_path = tmp_path / "report.csv"
        generator.generate_csv_report(output_path)

        with open(output_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["app_name"] == "app1"
        assert rows[0]["total_iterations"] == "25"
        assert rows[0]["click_count"] == "15"
        assert rows[0]["type_text_count"] == "5"
        assert rows[0]["has_edittext"] == "True"

    def test_generate_csv_multiple_apps(self, tmp_path):
        """Test CSV with multiple apps."""
        generator = ComparativeReportGenerator(tmp_path)
        generator.app_results = {
            "app1": {
                "total_iterations": 25,
                "execution_time_s": 180.0,
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0, "valid_rate": 0},
                "llm": {},
                "exploration": {"unique_screens": 0, "activities": []}
            },
            "app2": {
                "total_iterations": 30,
                "execution_time_s": 200.0,
                "element_coverage": {"types_seen": [], "type_counts": {}},
                "actions": {"by_type": {}, "valid": 0, "invalid": 0, "valid_rate": 0},
                "llm": {},
                "exploration": {"unique_screens": 0, "activities": []}
            }
        }

        output_path = tmp_path / "report.csv"
        generator.generate_csv_report(output_path)

        with open(output_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
