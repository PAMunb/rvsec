"""Tests for shared instrumentation result Pydantic models.

Verifies round-trip serialization for both variants and confirms that legacy
JSON without ``variant`` field deserializes with default ``"ajc"`` (retrocompat
mechanism inherited from gh52 — `Field(default="ajc")`).
"""

import json

from rv_instrumentation_core import InstrumentationError, InstrumentationResults


def test_round_trip_ajc_variant():
    results = InstrumentationResults(
        success_count=3,
        total_count=5,
        variant="ajc",
        errors={
            "fail.apk": InstrumentationError(
                code=1, tool="dex2jar", message="boom", phase="decompilation"
            )
        },
    )
    payload = results.model_dump_json(exclude={"success_rate"})
    revived = InstrumentationResults.model_validate_json(payload)
    assert revived.variant == "ajc"
    assert revived.success_count == 3
    assert revived.total_count == 5
    assert revived.success_rate == 60.0
    assert "fail.apk" in revived.errors
    assert revived.errors["fail.apk"].phase == "decompilation"


def test_round_trip_dexlib2_variant():
    results = InstrumentationResults(
        success_count=10, total_count=10, variant="dexlib2"
    )
    revived = InstrumentationResults.model_validate_json(
        results.model_dump_json(exclude={"success_rate"})
    )
    assert revived.variant == "dexlib2"
    assert revived.success_rate == 100.0


def test_legacy_json_without_variant_defaults_to_ajc():
    legacy_payload = json.dumps({"success_count": 1, "total_count": 2, "errors": {}})
    revived = InstrumentationResults.model_validate_json(legacy_payload)
    assert revived.variant == "ajc"
    assert revived.success_rate == 50.0


def test_success_rate_zero_total():
    assert InstrumentationResults(success_count=0, total_count=0).success_rate == 0.0
