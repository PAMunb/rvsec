"""
Unit tests for rv_agent.llm.tools.tool_call_parser.

This module is pure parsing logic (json/re only), so tests exercise the full
public surface without mocks: coordinate normalization, Qwen3-VL coordinate
denormalization, the five text-parsing strategies (each with its own strategy
name), the malformed-JSON repair heuristics, and the ParserStats accumulator.

Test design notes:
- Equivalence partitioning drives normalize_tool_args (each coordinate-carrying
  format is a distinct input class) and the parse strategies (each format is a
  class that must resolve to a specific strategy name).
- Boundary value analysis drives denormalize_qwen_coords (the [0, 1000)
  normalized-vs-pixel threshold) and the failure-reason branches (length < 10).
- The global parser_stats singleton is reset before every test via an autouse
  fixture so stats-affecting tests stay independent of collection order.
"""

import pytest

from rv_agent.llm.tools.tool_call_parser import (
    ParserStats,
    _fix_malformed_json,
    denormalize_qwen_coords,
    normalize_tool_args,
    parse_tool_calls_from_text_with_strategy,
    parse_tool_calls_with_strategy,
    parser_stats,
)


@pytest.fixture(autouse=True)
def _reset_global_stats():
    """Reset the module-global parser_stats before each test.

    parse_tool_calls_from_text_with_strategy mutates this singleton whenever
    track_stats is True. Resetting keeps stats assertions independent of the
    order tests run in.
    """
    parser_stats.reset()
    yield
    parser_stats.reset()


# =============================================================================
# normalize_tool_args
# =============================================================================


class TestNormalizeToolArgs:
    """Covers every coordinate format normalize_tool_args recognizes."""

    def test_none_input_returns_empty_dict(self):
        """None input is the degenerate class: it yields an empty dict, not a crash."""
        assert normalize_tool_args(None) == {}

    def test_nested_arguments_extracts_coords_and_type(self):
        """Nested Fara-7B format: coords come from the inner coordinate array and
        the action name is taken from the inner 'type', overriding the outer name."""
        args = {
            "name": "Deny",
            "arguments": {"type": "left_click", "coordinate": [464, 487]},
        }
        result = normalize_tool_args(args)
        assert result == {"x": 464, "y": 487, "name": "left_click"}

    def test_nested_arguments_copies_extra_outer_keys(self):
        """Outer keys other than 'arguments' that are not already set are copied through."""
        args = {
            "arguments": {"type": "left_click", "coordinate": [10, 20]},
            "confidence": 0.9,
        }
        result = normalize_tool_args(args)
        assert result["x"] == 10
        assert result["y"] == 20
        assert result["confidence"] == 0.9

    def test_x_as_list_without_y_extracts_both(self):
        """Qwen3-VL packs both coords into x as [x, y]; y is derived from index 1."""
        result = normalize_tool_args({"x": [499, 510]})
        assert result["x"] == 499
        assert result["y"] == 510

    def test_x_as_list_with_y_present_keeps_existing_y(self):
        """When y is already provided, the array's second element must NOT clobber it."""
        result = normalize_tool_args({"x": [875, 235], "y": 999})
        assert result["x"] == 875
        assert result["y"] == 999

    @pytest.mark.parametrize(
        "coord_key",
        [
            "coordinate",
            "coordinates",
            "bbox",
            "bbox_2d",
            "bounds",
            "bndbox",
            "center",
        ],
    )
    def test_each_coordinate_array_key_extracts_xy(self, coord_key):
        """Every accepted coordinate-array key maps [a, b] -> x=a, y=b."""
        result = normalize_tool_args({coord_key: [464, 487], "name": "tap"})
        assert result["x"] == 464
        assert result["y"] == 487
        # Non-coordinate keys pass through untouched.
        assert result["name"] == "tap"

    def test_coordinate_priority_over_coordinates(self):
        """'coordinate' outranks 'coordinates' when both are present."""
        result = normalize_tool_args({"coordinate": [1, 2], "coordinates": [3, 4]})
        assert result["x"] == 1
        assert result["y"] == 2

    def test_string_coords_converted_to_int(self):
        """String numeric coords ('681') are coerced to int 681."""
        result = normalize_tool_args({"x": "681", "y": "777"})
        assert result == {"x": 681, "y": 777}

    def test_float_coords_truncated_to_int(self):
        """Float coords are truncated (int(499.7) == 499), not rounded."""
        result = normalize_tool_args({"x": 499.7, "y": 510.2})
        assert result == {"x": 499, "y": 510}

    def test_non_convertible_string_kept_as_is(self):
        """A non-numeric coordinate string is preserved rather than dropped."""
        result = normalize_tool_args({"x": "abc", "y": 200})
        assert result["x"] == "abc"
        assert result["y"] == 200

    def test_other_keys_pass_through(self):
        """Keys unrelated to coordinates are copied verbatim."""
        result = normalize_tool_args({"name": "click", "text": "hello"})
        assert result == {"name": "click", "text": "hello"}


# =============================================================================
# denormalize_qwen_coords
# =============================================================================


class TestDenormalizeQwenCoords:
    """Boundary-focused tests around the [0, 1000) normalized-vs-pixel threshold."""

    def test_in_range_scaled_to_pixels(self):
        """A mid-range normalized point (500, 500) scales to device pixels."""
        # 500/1000 * 1080 = 540 ; 500/1000 * 1920 = 960
        assert denormalize_qwen_coords(500, 500) == (540, 960)

    def test_already_pixel_values_pass_through(self):
        """Values >= 1000 are treated as already-pixel and returned unchanged."""
        assert denormalize_qwen_coords(1080, 1920) == (1080, 1920)

    def test_list_input_uses_first_element(self):
        """List coords (LLM may emit [x]) collapse to their first element, then scale."""
        assert denormalize_qwen_coords([500], [500]) == (540, 960)

    def test_tuple_input_uses_first_element(self):
        """Tuple coords behave the same as lists."""
        assert denormalize_qwen_coords((500,), (500,)) == (540, 960)

    def test_string_input_converted(self):
        """Numeric strings are parsed before the range check."""
        assert denormalize_qwen_coords("500", "500") == (540, 960)

    def test_empty_list_defaults_to_zero(self):
        """An empty list falls back to 0, which is in-range and scales to (0, 0)."""
        assert denormalize_qwen_coords([], []) == (0, 0)


# =============================================================================
# parse_tool_calls_from_text_with_strategy - strategy detection
# =============================================================================


class TestParseStrategies:
    """Each format must resolve to its own strategy label."""

    def test_empty_string_returns_none_strategy(self):
        """Empty input short-circuits to ([], 'none')."""
        calls, strategy = parse_tool_calls_from_text_with_strategy("")
        assert calls == []
        assert strategy == "none"

    def test_none_input_returns_none_strategy(self):
        """Non-string (None) input is also the 'none' class."""
        calls, strategy = parse_tool_calls_from_text_with_strategy(None)
        assert calls == []
        assert strategy == "none"

    def test_xml_tool_call(self):
        """<tool_call> tags resolve to the 'xml' strategy."""
        text = '<tool_call>{"name": "android_click", "arguments": {"x": 100, "y": 200}}</tool_call>'
        calls, strategy = parse_tool_calls_from_text_with_strategy(text)
        assert strategy == "xml"
        assert calls[0]["name"] == "android_click"
        assert calls[0]["args"] == {"x": 100, "y": 200}

    def test_json_array(self):
        """A bare JSON array of tool objects resolves to 'json_array'."""
        text = '[{"name": "android_click", "parameters": {"x": 100, "y": 200}}]'
        calls, strategy = parse_tool_calls_from_text_with_strategy(text)
        assert strategy == "json_array"
        assert calls[0]["name"] == "android_click"

    def test_json_object(self):
        """A single {name, parameters} object resolves to 'json_object'."""
        text = 'Action: {"name": "android_click", "parameters": {"x": 100, "y": 200}}'
        calls, strategy = parse_tool_calls_from_text_with_strategy(text)
        assert strategy == "json_object"
        assert calls[0]["name"] == "android_click"

    def test_markdown_code_block(self):
        """A fenced object lacking parameters/arguments (so earlier strategies miss it)
        resolves to 'markdown'."""
        text = '```json\n{"name": "android_click", "x": 100, "y": 200}\n```'
        calls, strategy = parse_tool_calls_from_text_with_strategy(text)
        assert strategy == "markdown"
        assert calls[0]["name"] == "android_click"

    def test_gemma_action_key(self):
        """A fenced {action, x, y} object (Gemma format) resolves to 'gemma'."""
        text = '```json\n{"action": "android_click", "x": 480, "y": 1600}\n```'
        calls, strategy = parse_tool_calls_from_text_with_strategy(text)
        assert strategy == "gemma"
        assert calls[0]["name"] == "android_click"
        assert calls[0]["args"]["x"] == 480

    def test_pythonic_function_call(self):
        """A pythonic android_*(...) call resolves to 'pythonic'."""
        text = "I will android_click(x=540, y=1054) now."
        calls, strategy = parse_tool_calls_from_text_with_strategy(text)
        assert strategy == "pythonic"
        assert calls[0]["name"] == "android_click"
        assert calls[0]["args"]["x"] == 540
        assert calls[0]["args"]["y"] == 1054

    def test_pythonic_keeps_non_numeric_arg(self):
        """Pythonic string args that are not numeric are kept as strings."""
        text = 'android_type_text(text="hello", x=10, y=20)'
        calls, strategy = parse_tool_calls_from_text_with_strategy(text)
        assert strategy == "pythonic"
        assert calls[0]["args"]["text"] == "hello"

    def test_malformed_json_repaired_via_fix(self):
        """XML strategy repairs '"x": 352, 782' into '"x": 352, "y": 782' before parsing."""
        text = '<tool_call>{"name": "android_click", "arguments": {"x": 352, 782}}</tool_call>'
        calls, strategy = parse_tool_calls_from_text_with_strategy(text)
        assert strategy == "xml"
        assert calls[0]["args"] == {"x": 352, "y": 782}


# =============================================================================
# parse_tool_calls_from_text_with_strategy - failure reasons & stats tracking
# =============================================================================


class TestParseFailureReasons:
    """The four distinct failure-reason branches at the end of the parser."""

    def test_response_too_short(self):
        """Input shorter than 10 chars records 'response_too_short'."""
        parse_tool_calls_from_text_with_strategy("hi")
        assert parser_stats.failure_reasons.get("response_too_short") == 1

    def test_refusal(self):
        """A refusal phrase ('I cannot') records 'refusal'."""
        parse_tool_calls_from_text_with_strategy("I cannot help with that action")
        assert parser_stats.failure_reasons.get("refusal") == 1

    def test_no_tool_mention(self):
        """Text with no click/tool mention records 'no_tool_mention'."""
        parse_tool_calls_from_text_with_strategy("the weather is nice today outside")
        assert parser_stats.failure_reasons.get("no_tool_mention") == 1

    def test_parse_failed(self):
        """Text that mentions 'click' but produces no call records 'parse_failed'."""
        parse_tool_calls_from_text_with_strategy("I want to click the blue button")
        assert parser_stats.failure_reasons.get("parse_failed") == 1

    def test_track_stats_false_on_success_records_nothing(self):
        """track_stats=False must not touch the global stats on success."""
        text = '<tool_call>{"name": "android_click", "arguments": {"x": 1, "y": 2}}</tool_call>'
        calls, strategy = parse_tool_calls_from_text_with_strategy(
            text, track_stats=False
        )
        assert strategy == "xml"
        assert parser_stats.total_calls == 0
        assert parser_stats.successful_parses == 0

    def test_track_stats_false_on_failure_records_nothing(self):
        """track_stats=False must not record a failure either."""
        parse_tool_calls_from_text_with_strategy("hi", track_stats=False)
        assert parser_stats.failure_reasons == {}
        assert parser_stats.total_calls == 0

    def test_success_records_strategy(self):
        """A successful parse increments the matching strategy success count."""
        text = '<tool_call>{"name": "android_click", "arguments": {"x": 1, "y": 2}}</tool_call>'
        parse_tool_calls_from_text_with_strategy(text)
        assert parser_stats.successful_parses == 1
        assert parser_stats.strategy_success_counts["xml_tool_call"] == 1


# =============================================================================
# _fix_malformed_json
# =============================================================================


class TestFixMalformedJson:
    """One case per numbered repair pattern, plus the unchanged/None case."""

    def test_pattern0_leading_zero(self):
        """Pattern 0: '.91' gains its leading zero -> '0.91'."""
        assert _fix_malformed_json('{"x": .91}') == '{"x": 0.91}'

    def test_pattern0b_double_colon(self):
        """Pattern 0b: '"x":": 541' collapses to '"x": 541'."""
        assert _fix_malformed_json('{"x":": 541}') == '{"x": 541}'

    def test_pattern0c_trailing_quote(self):
        """Pattern 0c: an errant trailing quote after an int is stripped."""
        assert _fix_malformed_json('{"y": 473"}') == '{"y": 473}'

    def test_pattern0d_two_numbers_with_space(self):
        """Pattern 0d: '867 335' keeps only the first number."""
        assert _fix_malformed_json('{"x": 867 335}') == '{"x": 867}'

    def test_pattern1_two_numbers_comma(self):
        """Pattern 1: '"x": 352, 782' becomes an x/y pair."""
        assert _fix_malformed_json('{"x": 352, 782}') == '{"x": 352, "y": 782}'

    def test_pattern2_array(self):
        """Pattern 2: '"x": [352, 782]' is split into x and y."""
        assert _fix_malformed_json('{"x": [352, 782]}') == '{"x": 352, "y": 782}'

    def test_pattern3_quoted_array(self):
        """Pattern 3: a quote-polluted array '[499", "499"]' is split into x and y."""
        assert _fix_malformed_json('{"x": [499", "499"]}') == '{"x": 499, "y": 499}'

    def test_pattern4_equals_sign(self):
        """Pattern 4: an '=' used instead of ':' is corrected."""
        assert _fix_malformed_json('{"x": = 100}') == '{"x": 100}'

    def test_pattern5_truncated_brace_balanced(self):
        """Pattern 5: an unclosed object gains its missing closing brace."""
        assert _fix_malformed_json('{"name": "foo"') == '{"name": "foo"}'

    def test_unchanged_returns_none(self):
        """Well-formed input triggers no pattern and returns None."""
        assert _fix_malformed_json('{"x": 100}') is None


# =============================================================================
# ParserStats
# =============================================================================


class TestParserStats:
    """The stats accumulator: reset, record_*, and get_stats snapshots."""

    @pytest.fixture
    def stats(self):
        """A fresh, isolated ParserStats instance (not the global singleton)."""
        return ParserStats()

    def test_reset_zeroes_counters(self, stats):
        """reset() returns every counter to its initial zero state."""
        stats.record_success("xml_tool_call")
        stats.record_failure("boom")
        stats.reset()
        assert stats.total_calls == 0
        assert stats.successful_parses == 0
        assert stats.failed_parses == 0
        assert stats.failure_reasons == {}

    def test_record_success_known_strategy(self, stats):
        """A known strategy increments both totals and its own success count."""
        stats.record_success("json_array")
        assert stats.total_calls == 1
        assert stats.successful_parses == 1
        assert stats.strategy_success_counts["json_array"] == 1

    def test_record_success_with_json_fix(self, stats):
        """json_fix_applied=True bumps the json_fixes_applied counter."""
        stats.record_success("xml_tool_call", json_fix_applied=True)
        assert stats.json_fixes_applied == 1

    def test_record_success_unknown_strategy_is_noop_on_counts(self, stats):
        """An unknown strategy still counts as success but adds no new count key."""
        stats.record_success("mystery")
        assert stats.successful_parses == 1
        assert "mystery" not in stats.strategy_success_counts

    def test_record_failure(self, stats):
        """record_failure increments totals and tallies the reason."""
        stats.record_failure("refusal")
        assert stats.total_calls == 1
        assert stats.failed_parses == 1
        assert stats.failure_reasons["refusal"] == 1

    def test_record_attempt(self, stats):
        """record_attempt increments the per-strategy attempt count."""
        stats.record_attempt("json_object")
        assert stats.strategy_attempt_counts["json_object"] == 1

    def test_record_attempt_unknown_strategy_is_noop(self, stats):
        """An unknown attempt strategy is ignored (no KeyError, no new key)."""
        stats.record_attempt("mystery")
        assert "mystery" not in stats.strategy_attempt_counts

    def test_get_stats_zero_total_success_rate(self, stats):
        """success_rate is 0.0 (not a division error) when no calls happened."""
        snapshot = stats.get_stats()
        assert snapshot["total_calls"] == 0
        assert snapshot["success_rate"] == 0.0

    def test_get_stats_success_rate_computed(self, stats):
        """success_rate reflects successes over total calls."""
        stats.record_success("xml_tool_call")
        stats.record_failure("parse_failed")
        snapshot = stats.get_stats()
        assert snapshot["total_calls"] == 2
        assert snapshot["success_rate"] == 0.5


# =============================================================================
# Backwards-compatibility alias
# =============================================================================


def test_alias_is_same_function():
    """parse_tool_calls_with_strategy is the same callable as the primary name."""
    assert parse_tool_calls_with_strategy is parse_tool_calls_from_text_with_strategy
