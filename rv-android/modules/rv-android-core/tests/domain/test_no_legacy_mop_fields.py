"""INV-CORE-33 — no `_mop` / `mop_*` *fields* on the renamed Pydantic models.

The G_no_legacy_mop scanner (`scripts/check_no_legacy_mop.py`) flags any
*occurrence* of legacy tokens in source text. This complementary AST test
goes one level deeper: it instantiates the Pydantic models gh60 renamed
and asserts the `model_fields` dict (Pydantic v2's authoritative
declaration registry) contains zero field whose name still uses the MOP
nomenclature.

Why both gates exist
--------------------
Scanner pros / cons
    + Catches *any* mention: method names, dict keys, comments, identifiers.
    - Cannot tell a planned legacy reference (e.g. an upstream type import
      at the adapter boundary) from a forgotten field declaration.

AST test pros / cons
    + Authoritative for field declarations — directly inspects the live
      Pydantic schema after every model load.
    - Says nothing about method names, helper functions, or string literals.

Together they bracket the contract: the scanner is broad, the AST test is
deep. A drift in either direction breaks one of them.

Scope (per design.md INV-CORE-33)
---------------------------------
    Method            (rv_android_core.domain.classes)
    Widget            (rv_android_core.domain.widget)
    WidgetEvent       (rv_android_core.domain.widget)
    ComponentInfo     (rv_android_core.domain.components)
    WindowTransition  (rv_android_core.domain.wtg)

The forbidden field-name fragments below are matched against each model's
field names with a case-insensitive `in`/`endswith` check — a `class
Method` that grows `reaches_mop` again would fail the assertion.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from rv_android_core.domain.classes import Method
from rv_android_core.domain.components import ComponentInfo
from rv_android_core.domain.widget import Widget, WidgetEvent
from rv_android_core.domain.wtg import WindowTransition

# Field-name fragments that the C1f rename must have eliminated. Listed as
# `(needle, semantics)` so the assertion message names *why* it failed.
FORBIDDEN_FIELD_FRAGMENTS = [
    ("reaches_mop", "renamed to reaches_target"),
    ("directly_reaches_mop", "renamed to directly_reaches_target"),
    ("mop_methods", "renamed to target_methods"),
    ("target_reaches_mop", "renamed to target_reaches_target"),
]

MODELS_UNDER_TEST: list[type[BaseModel]] = [
    Method,
    Widget,
    WidgetEvent,
    ComponentInfo,
    WindowTransition,
]


@pytest.mark.parametrize(
    "model",
    MODELS_UNDER_TEST,
    ids=[m.__name__ for m in MODELS_UNDER_TEST],
)
def test_no_legacy_mop_field_names(model: type[BaseModel]) -> None:
    """Every Pydantic field name on the renamed models is MOP-free.

    Uses Pydantic v2's `model_fields` (the authoritative registry) — a
    subclass that *re-declares* a forbidden field would override the
    parent and surface here even if the parent moved on.
    """
    field_names = list(model.model_fields.keys())
    violations: list[tuple[str, str]] = []
    for name in field_names:
        for needle, rename in FORBIDDEN_FIELD_FRAGMENTS:
            if needle in name:
                violations.append((name, rename))
                break
    assert not violations, (
        f"{model.__name__} still declares legacy MOP field(s): "
        + ", ".join(f"{name!r} (should be: {rename})" for name, rename in violations)
        + f"\n  observed fields: {field_names}"
    )


def test_renamed_fields_actually_exist_with_target_names() -> None:
    """Positive control — the renamed fields landed under the new names.

    Without this assertion, a regression that DELETED `reaches_target`
    entirely (no field at all) would still pass `test_no_legacy_mop_field_names`
    because there's nothing to flag. This test pins down the new schema.
    """
    expected_target_fields = {
        Method: {"reaches_target", "directly_reaches_target"},
        Widget: {"reaches_target", "directly_reaches_target"},
        ComponentInfo: {"reaches_target"},
    }
    for model, expected in expected_target_fields.items():
        present = set(model.model_fields.keys())
        missing = expected - present
        assert not missing, (
            f"{model.__name__} is missing renamed field(s) {missing}; "
            f"observed fields: {sorted(present)}"
        )


def test_widget_event_does_not_carry_reaches_field() -> None:
    """WidgetEvent is a pure event descriptor — no reachability flag.

    Tripwire against an inadvertent rename that adds `reaches_*` to
    WidgetEvent during refactoring. The reachability state lives on the
    *handler method* (Method.reaches_target), not on the event record.
    """
    forbidden = {"reaches_mop", "reaches_target", "directly_reaches_mop", "directly_reaches_target"}
    present = set(WidgetEvent.model_fields.keys())
    leak = forbidden & present
    assert not leak, f"WidgetEvent unexpectedly carries reachability field(s) {leak}"
