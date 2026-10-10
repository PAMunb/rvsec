"""
Tests for the host-side MOP artifact derivation.

Each relocated parse-time rule gets a named test on a synthetic fragment, so a
regression names the rule that broke rather than diffing a large fixture. The
cryptoapp ground truth covers the projection as a whole.
"""

import hashlib
import json
import os
import random
import re
import subprocess
import sys

import pytest
from rv_android_core.util.analysis_document import (
    PairPolicy,
    digest_of_file,
    read_analysis_document,
)

from aperv_tool.tools.aperv.derive_mop_artifact import (
    DIST_K,
    DIST_WEIGHED_MAX,
    DerivationError,
    _base_activity,
    _cut_nearest,
    _cut_weighed,
    _index_reachability,
    _merge_minima,
    _normalize_event_type,
    _read_pairs,
    derive,
    serialize_canonical,
)


def _document(**overrides) -> dict:
    """Minimal derivable document; overrides replace whole top-level sections."""
    document = {
        "complete": True,
        "package": "com.example",
        "mainActivity": "com.example.MainActivity",
        "reachability": [],
        "windows": [],
        "transitions": [],
        "components": {},
    }
    document.update(overrides)
    return document


def _method(
    signature, *, name=None, reaches=False, direct=False, distances=None
) -> dict:
    method = {
        "name": name if name is not None else signature,
        "signature": signature,
        "reachable": True,
        "reachesTarget": reaches,
        "directlyReachesTarget": direct,
    }
    if distances is not None:
        method["targetDistances"] = distances
    return method


def _distance_targets(count) -> list[dict]:
    """A `distanceTargets` section of `count` entries; only its length is read."""
    return [
        {"signature": f"<com.example.T: void t{index}()>", "kind": "direct"}
        for index in range(count)
    ]


def _listener(event_type, handler, *, reaches=None, direct=None) -> dict:
    return {
        "eventType": event_type,
        "handler": handler,
        "handlerReachesTarget": reaches,
        "handlerDirectlyReachesTarget": direct,
    }


def _widget(short_id, *, listeners=None, **metadata) -> dict:
    widget = {
        "id": 1,
        "idName": short_id,
        "type": "android.widget.Button",
        "text": "",
        "hint": "",
        "inputType": "",
        "entries": [],
        "prompt": None,
        "spinnerMode": None,
        "contentDescription": None,
        "tooltipText": None,
        "listeners": listeners or [],
    }
    widget.update(metadata)
    return widget


def _window(window_id, name, widgets, window_type="ACTIVITY") -> dict:
    return {
        "id": window_id,
        "type": window_type,
        "name": name,
        "isMain": False,
        "widgets": widgets,
    }


def _reaching_class(class_name, methods, component_type="class") -> dict:
    return {
        "className": class_name,
        "componentType": component_type,
        "isMain": False,
        "methods": methods,
    }


def _wtgless_document() -> dict:
    """The producer's first-pass shape: substrate present, WTG stage unfinished.

    `reachability` and `windows` are populated as `INV-ANA-20` requires of either
    pass, `transitions` is empty and the `"complete": true` sentinel was never
    written — the exact document 45 of the 164 `jca_android` APKs produce.
    """
    document = _document(
        reachability=[
            _reaching_class(
                "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
            )
        ],
        windows=[
            _window(
                1,
                "com.example.MainActivity",
                [
                    _widget(
                        "btn_crypto", listeners=[_listener("click", "<A: void h()>")]
                    ),
                    _widget("field_user", hint="user"),
                ],
            ),
            _window(
                2,
                "com.example.MainActivity#OptionsMenu",
                [_widget("menu_run", listeners=[_listener("click", "<A: void h()>")])],
                window_type="OPTIONSMENU",
            ),
        ],
    )
    del document["complete"]
    return document


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("long_click", "longclick"),
        ("longClick", "longclick"),
        ("LONG-CLICK", "longclick"),
        ("click", "click"),
        ("", ""),
        (None, None),
    ],
)
def test_normalize_event_type(raw, expected):
    assert _normalize_event_type(raw) == expected


@pytest.mark.parametrize(
    "window_name,expected",
    [
        ("com.example.MainActivity", "com.example.MainActivity"),
        ("com.example.MainActivity#OptionsMenu", "com.example.MainActivity"),
        ("#OptionsMenu", ""),
    ],
)
def test_base_activity(window_name, expected):
    assert _base_activity(window_name) == expected


# ---------------------------------------------------------------------------
# Reachability index
# ---------------------------------------------------------------------------


def test_index_reachability_stores_direct_and_transitive():
    by_signature = _index_reachability(
        [
            {
                "className": "com.example.A",
                "componentType": "class",
                "methods": [_method("<A: void a()>", reaches=True)],
            }
        ],
        0,
    ).by_signature
    assert by_signature["<A: void a()>"] == (False, True)


def test_index_reachability_direct_only_method_is_transitive():
    """
    The producer emits methods with `directlyReachesTarget` and no `reachesTarget`
    (33 methods across 16 corpus apps). Storing `reachesTarget` unmodified — what
    the jar's index did — would derive a widget that is direct but not transitive,
    an incoherent state.
    """
    by_signature = _index_reachability(
        [
            {
                "className": "com.example.A",
                "methods": [_method("<A: void a()>", direct=True, reaches=False)],
            }
        ],
        0,
    ).by_signature
    assert by_signature["<A: void a()>"] == (True, True)


def test_index_reachability_merges_duplicate_signatures_by_or():
    """
    Duplicate signatures merge by OR, not by last-write, so the index does not
    depend on the producer's emission order.
    """
    entries = [
        {
            "className": "com.example.A",
            "methods": [_method("<A: void a()>", direct=True, reaches=False)],
        },
        {
            "className": "com.example.A",
            "methods": [_method("<A: void a()>", direct=False, reaches=True)],
        },
    ]
    forward = _index_reachability(entries, 0).by_signature
    backward = _index_reachability(list(reversed(entries)), 0).by_signature
    assert forward["<A: void a()>"] == (True, True)
    assert backward["<A: void a()>"] == (True, True)


def test_index_reachability_keeps_unreaching_methods():
    """
    A listed method that reaches nothing is indexed with `(False, False)`, so a
    listed D8 wrapper is answered by its own flags and never reaches the class
    recovery (INV-DRV-09).
    """
    index = _index_reachability(
        [
            {
                "className": "com.example.A",
                "componentType": "activity",
                "methods": [
                    _method("<A: void a()>"),
                    _method("<A: void lambda$a$0()>", name="lambda$a$0"),
                ],
            }
        ],
        0,
    )
    assert index.by_signature == {
        "<A: void a()>": (False, False),
        "<A: void lambda$a$0()>": (False, False),
    }
    assert index.lambda_by_class == {}
    assert index.activity_classes == set()


def test_index_reachability_indexes_reaching_lambda_bodies_by_class():
    lambda_by_class = _index_reachability(
        [
            {
                "className": "com.example.A",
                "methods": [
                    _method(
                        "<A: void lambda$onCreate$0()>",
                        name="lambda$onCreate$0",
                        reaches=True,
                    ),
                    _method(
                        "<A: void lambda$onCreate$1()>",
                        name="lambda$onCreate$1",
                        direct=True,
                    ),
                    _method("<A: void onCreate()>", name="onCreate", reaches=True),
                ],
            }
        ],
        0,
    ).lambda_by_class
    assert lambda_by_class == {"com.example.A": (True, True)}


def test_index_reachability_collects_activity_classes():
    activity_classes = _index_reachability(
        [
            {
                "className": "com.example.CryptoActivity",
                "componentType": "activity",
                "methods": [_method("<C: void a()>", reaches=True)],
            },
            {
                "className": "com.example.Helper",
                "componentType": "class",
                "methods": [_method("<H: void b()>", reaches=True)],
            },
            {
                "className": "com.example.IdleActivity",
                "componentType": "activity",
                "methods": [_method("<I: void c()>")],
            },
        ],
        0,
    ).activity_classes
    assert activity_classes == {"com.example.CryptoActivity"}


def test_index_reachability_skips_malformed_entries():
    """A single odd entry is producer noise and must not cost the whole app."""
    by_signature = _index_reachability(
        [
            "not-an-object",
            {"className": "com.example.A", "methods": "not-a-list"},
            {"className": "com.example.A", "methods": [None, 7]},
            {
                "className": "com.example.A",
                "methods": [_method("<A: void a()>", reaches=True)],
            },
        ],
        0,
    ).by_signature
    assert by_signature == {"<A: void a()>": (False, True)}


# ---------------------------------------------------------------------------
# derive() preconditions
# ---------------------------------------------------------------------------


def test_derive_accepts_document_without_sentinel():
    """
    The first-pass document is the producer's deliberate intermediate report, not
    a truncated file, so it derives. Its missing WTG surfaces as an empty `wtg`
    map, which is where the device already looks for it (INV-DRV-08).
    """
    artifact = derive(_wtgless_document())
    assert artifact["wtg"] == {}
    assert artifact["stats"]["wtgEdges"] == 0
    # Not a vacuous pass: the substrate the explorer scores against is there.
    assert artifact["mopActivities"] == ["com.example.MainActivity"]


def test_derive_accepts_false_sentinel():
    """A false sentinel derives, and derives to the same bytes as an absent one.

    Two documents differing only in a field `derive()` no longer reads must encode
    identically, which is `INV-DRV-05` determinism applied to this change.
    """
    explicit = _wtgless_document()
    explicit["complete"] = False
    assert serialize_canonical(derive(explicit)) == serialize_canonical(
        derive(_wtgless_document())
    )


def test_derive_wtgless_still_derives_widget_sections():
    """
    `mopActivities`, `optionsMenus` and `widgets` are joined out of `reachability`
    and `windows`, so the WTG stage cannot influence them. Pinning the equality
    keeps a future reader from assuming a sentinel-less run yields a thin artifact.
    """
    sealed_document = _wtgless_document()
    sealed_document["complete"] = True
    wtgless = derive(_wtgless_document())
    sealed = derive(sealed_document)

    for section in ("mopActivities", "optionsMenus", "widgets"):
        assert wtgless[section] == sealed[section]
    assert wtgless["mopActivities"] and wtgless["optionsMenus"] and wtgless["widgets"]


def test_derive_requires_package():
    with pytest.raises(DerivationError, match="package"):
        derive(_document(package=None))


def test_derive_refuses_non_dict_components():
    with pytest.raises(DerivationError, match="components"):
        derive(_document(components=["activities"]))


def test_derive_refuses_non_list_reachability():
    with pytest.raises(DerivationError, match="reachability"):
        derive(_document(reachability=7))


def test_derive_refuses_non_list_windows():
    with pytest.raises(DerivationError, match="windows"):
        derive(_document(windows={"0": {}}))


def test_derive_refuses_non_dict_document():
    with pytest.raises(DerivationError):
        derive(["not", "a", "document"])


def test_derive_treats_absent_sections_as_empty():
    artifact = derive({"complete": True, "package": "com.example"})
    assert artifact["formatVersion"] == 2
    assert artifact["package"] == "com.example"
    assert artifact["mainActivity"] is None


def test_derive_records_supplied_provenance():
    artifact = derive(
        _document(), source_file="com.example_1.apk.json", source_digest="sha256:ab12"
    )
    assert artifact["source"] == {
        "digest": "sha256:ab12",
        "file": "com.example_1.apk.json",
        "generator": "aperv-derive/2",
    }


def test_derive_does_not_mutate_the_document():
    document = _document(
        windows=[
            {
                "id": 1,
                "type": "ACTIVITY",
                "name": "com.example.MainActivity",
                "widgets": [],
            }
        ]
    )
    before = repr(document)
    derive(document)
    assert repr(document) == before


# ---------------------------------------------------------------------------
# Widget MOP flags (INV-DRV-01)
# ---------------------------------------------------------------------------


def test_producer_precedence_wins():
    """
    A producer that answers the reach question wins over the local join, even when
    the handler is absent from `reachability` entirely.
    """
    artifact = derive(
        _document(
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_ok",
                            listeners=[
                                _listener(
                                    "click",
                                    "<A: void unknown()>",
                                    reaches=True,
                                    direct=False,
                                )
                            ],
                        )
                    ],
                )
            ]
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["mop"] == {"click": "transitive"}


def test_direct_implies_transitive():
    """
    The shape 33 methods across 16 corpus apps have: `directlyReachesTarget` true
    with `reachesTarget` false. Storing the producer's bits unmodified would emit a
    widget that is direct but not transitive.
    """
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity",
                    [_method("<A: void onClick(View)>", direct=True, reaches=False)],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_ok",
                            listeners=[_listener("click", "<A: void onClick(View)>")],
                        )
                    ],
                )
            ],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["mop"] == {"click": "both"}


def test_no_widget_is_direct_without_transitive():
    """`direct` alone is unreachable on the wire, whichever tier derived the flags."""
    artifact = derive(
        _document(
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_ok",
                            listeners=[
                                _listener(
                                    "click", "<A: void a()>", reaches=False, direct=True
                                )
                            ],
                        )
                    ],
                )
            ]
        )
    )
    values = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]["mop"].values()
    assert "direct" not in values
    assert list(values) == ["both"]


def test_synthetic_lambda_recovered():
    """
    A D8 wrapper handler the exact join misses is recovered from its enclosing
    class's reaching lambda body — the gap that affects every desugared app.
    """
    handler = (
        "<com.example.MainActivity$$ExternalSyntheticLambda0: "
        "void onClick(android.view.View)>"
    )
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity",
                    [
                        _method(
                            "<com.example.MainActivity: void lambda$onCreate$0(View)>",
                            name="lambda$onCreate$0",
                            reaches=True,
                        )
                    ],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [_widget("btn_ok", listeners=[_listener("click", handler)])],
                )
            ],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["mop"] == {"click": "transitive"}
    assert artifact["stats"]["recovered"] == 1
    assert artifact["stats"]["syntheticLambda"] == 1


def test_listed_wrapper_keeps_its_own_flags():
    """
    A wrapper listed in `reachability` reaching nothing stays `none` even when a
    sibling lambda of its class reaches: the producer links each wrapper to its
    own body, so the class OR would lend it a sibling's flag (INV-DRV-09). The
    unlisted wrapper of the same class is still recovered.
    """
    listed = (
        "<com.example.MainActivity$$ExternalSyntheticLambda1: "
        "void onClick(android.view.View)>"
    )
    absent = (
        "<com.example.MainActivity$$ExternalSyntheticLambda0: "
        "void onClick(android.view.View)>"
    )
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity",
                    [
                        _method(
                            "<com.example.MainActivity: void lambda$onCreate$0(View)>",
                            name="lambda$onCreate$0",
                            reaches=True,
                        )
                    ],
                ),
                _reaching_class(
                    "com.example.MainActivity$$ExternalSyntheticLambda1",
                    [_method(listed, name="onClick")],
                ),
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget("btn_listed", listeners=[_listener("click", listed)]),
                        _widget("btn_absent", listeners=[_listener("click", absent)]),
                    ],
                )
            ],
        )
    )
    widgets = artifact["widgets"]["com.example.MainActivity"]
    assert "btn_listed" not in widgets
    assert widgets["btn_absent"]["mop"] == {"click": "transitive"}
    assert artifact["stats"]["flagged"] == 1
    assert artifact["stats"]["recovered"] == 1
    assert artifact["stats"]["syntheticLambda"] == 2
    assert artifact["stats"]["handlersUnmatched"] == 2


def test_listed_wrapper_alone_stays_unflagged():
    """The spec scenario: the only wrapper is listed, false, and stays `none`."""
    listed = (
        "<com.example.MainActivity$$ExternalSyntheticLambda1: "
        "void onClick(android.view.View)>"
    )
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity",
                    [
                        _method(
                            "<com.example.MainActivity: void lambda$onCreate$0(View)>",
                            name="lambda$onCreate$0",
                            reaches=True,
                        )
                    ],
                ),
                _reaching_class(
                    "com.example.MainActivity$$ExternalSyntheticLambda1",
                    [_method(listed, name="onClick")],
                ),
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_ok",
                            listeners=[_listener("click", listed)],
                            contentDescription="ok",
                        )
                    ],
                )
            ],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["mop"] == {"click": "none"}
    assert artifact["mopActivities"] == []
    assert artifact["stats"]["recovered"] == 0


def test_synthetic_lambda_not_recovered_without_lambda():
    """
    The recovery may not flag every wrapper: a class with no reaching lambda body
    leaves the widget unflagged, and only the diagnostics record the miss.
    """
    handler = (
        "<com.example.MainActivity$$ExternalSyntheticLambda0: "
        "void onClick(android.view.View)>"
    )
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity",
                    [
                        _method(
                            "<com.example.MainActivity: void onCreate()>",
                            name="onCreate",
                            reaches=True,
                        )
                    ],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [_widget("btn_ok", listeners=[_listener("click", handler)])],
                )
            ],
        )
    )
    assert artifact["widgets"] == {}
    assert artifact["mopActivities"] == []
    assert artifact["stats"]["syntheticLambda"] == 1
    assert artifact["stats"]["recovered"] == 0
    assert artifact["stats"]["handlersUnmatched"] == 1


def test_per_event_flags_independent():
    """
    The explicit `none` entry is what suppresses the aggregate fall-back on the
    query side, so omitting it would make long-click inherit the click flag.
    """
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity",
                    [_method("<A: void onClick(View)>", reaches=True)],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_ok",
                            listeners=[
                                _listener("click", "<A: void onClick(View)>"),
                                _listener("long_click", "<A: void onLong(View)>"),
                            ],
                        )
                    ],
                )
            ],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["mop"] == {"click": "transitive", "longclick": "none"}


def test_null_event_type_folds_into_aggregate():
    """
    A null event type has no addressable key. When it is the widget's only flagged
    source the reserved empty key carries it, so the jar's OR-over-the-map recompute
    of the aggregate does not lose the flag.
    """
    document = _document(
        reachability=[
            _reaching_class(
                "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
            )
        ],
        windows=[
            _window(
                1,
                "com.example.MainActivity",
                [_widget("btn_ok", listeners=[_listener(None, "<A: void h()>")])],
            )
        ],
    )
    artifact = derive(document)
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["mop"] == {"": "transitive"}
    assert artifact["mopActivities"] == ["com.example.MainActivity"]


def test_null_event_type_leaves_no_key_when_another_event_is_flagged():
    """
    With a keyed flagged listener present the aggregate is already recoverable, so
    the null-typed listener contributes no key at all.
    """
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_ok",
                            listeners=[
                                _listener(None, "<A: void h()>"),
                                _listener("click", "<A: void h()>"),
                            ],
                        )
                    ],
                )
            ],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["mop"] == {"click": "transitive"}


# ---------------------------------------------------------------------------
# Widget map keying, collisions and activity marking (INV-DRV-02)
# ---------------------------------------------------------------------------


def test_flagged_empty_id_marks_activity():
    """
    The AC3 rule: the widget is unscorable without an id, the activity is not.
    Deriving the set from the emitted map would silently shrink it — 19 corpus apps
    carry 1,263 such widgets.
    """
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.CryptoActivity",
                    [_method("<A: void h()>", reaches=True)],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.CryptoActivity",
                    [_widget("", listeners=[_listener("click", "<A: void h()>")])],
                )
            ],
        )
    )
    assert artifact["widgets"] == {}
    assert artifact["stats"]["droppedFlaggedNoId"] == 1
    assert artifact["mopActivities"] == ["com.example.CryptoActivity"]


@pytest.mark.parametrize("flagged_first", [True, False])
def test_collision_keeps_strongest_flag(flagged_first):
    flagged = _widget(
        "btn_ok", listeners=[_listener("click", "<A: void h()>")], hint="flagged"
    )
    unflagged = _widget("btn_ok", hint="unflagged")
    widgets = [flagged, unflagged] if flagged_first else [unflagged, flagged]
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
                )
            ],
            windows=[_window(1, "com.example.MainActivity", widgets)],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["hint"] == "flagged"


def test_collision_tie_keeps_first():
    """Equal rank keeps the resident, so metadata survival is first-occurrence."""
    artifact = derive(
        _document(
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget("btn_ok", hint="user"),
                        _widget("btn_ok", hint="password"),
                    ],
                )
            ]
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["hint"] == "user"


def test_windows_sharing_a_base_activity_accumulate():
    artifact = derive(
        _document(
            windows=[
                _window(1, "com.example.MainActivity", [_widget("btn_ok", hint="a")]),
                _window(
                    2,
                    "com.example.MainActivity#OptionsMenu",
                    [_widget("menu_item", hint="b")],
                    window_type="OPTIONSMENU",
                ),
            ]
        )
    )
    assert set(artifact["widgets"]["com.example.MainActivity"]) == {
        "btn_ok",
        "menu_item",
    }


def test_unflagged_metadataless_widget_projected_away():
    artifact = derive(
        _document(
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [_widget("btn_plain"), _widget("field_user", hint="user")],
                )
            ]
        )
    )
    assert set(artifact["widgets"]["com.example.MainActivity"]) == {"field_user"}


def test_stats_count_map_not_wire():
    """
    The counters describe the substrate the explorer scores against; the emission
    filter is a wire concern that must not move them.
    """
    widgets = [_widget(f"btn_{i}") for i in range(35)]
    widgets += [_widget(f"field_{i}", hint="x") for i in range(3)]
    widgets += [
        _widget(f"btn_mop_{i}", listeners=[_listener("click", "<A: void h()>")])
        for i in range(2)
    ]
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
                )
            ],
            windows=[_window(1, "com.example.MainActivity", widgets)],
        )
    )
    assert artifact["stats"]["widgetsTotal"] == 40
    assert artifact["stats"]["flagged"] == 2
    assert len(artifact["widgets"]["com.example.MainActivity"]) == 5


def test_options_menu_record_uses_parsed_widgets():
    """
    `hasFlaggedWidget` is tested before the empty-id drop: an id-less menu item
    still makes the menu a MOP gateway.
    """
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity#OptionsMenu",
                    [_widget("", listeners=[_listener("click", "<A: void h()>")])],
                    window_type="OPTIONSMENU",
                )
            ],
        )
    )
    assert artifact["optionsMenus"] == [
        {"activity": "com.example.MainActivity", "hasFlaggedWidget": True}
    ]
    assert artifact["widgets"] == {}


def test_options_menu_records_merge_per_activity_by_or():
    """
    Two menu windows on one activity emit one record, so the wire carries no
    ordering question the jar would have to resolve.
    """
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity#OptionsMenu",
                    [_widget("a")],
                    window_type="OPTIONSMENU",
                ),
                _window(
                    2,
                    "com.example.MainActivity#OptionsMenu",
                    [_widget("b", listeners=[_listener("click", "<A: void h()>")])],
                    window_type="OPTIONSMENU",
                ),
            ],
        )
    )
    assert artifact["optionsMenus"] == [
        {"activity": "com.example.MainActivity", "hasFlaggedWidget": True}
    ]


# ---------------------------------------------------------------------------
# DIALOG re-keying and the WTG click view (INV-DRV-03)
# ---------------------------------------------------------------------------


def _transition(source_id, target_id, events) -> dict:
    return {"sourceId": source_id, "targetId": target_id, "events": events}


def _event(event_type, widget_name="", widget_class="android.widget.Button") -> dict:
    return {
        "type": event_type,
        "handler": "",
        "widgetId": 1,
        "widgetClass": widget_class,
        "widgetName": widget_name,
    }


def test_dialog_merge_promotes_host():
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
                )
            ],
            windows=[
                _window(1, "com.example.MainActivity", [_widget("btn_open", hint="x")]),
                _window(
                    2,
                    "android.app.AlertDialog",
                    [
                        _widget(
                            "btn_confirm",
                            listeners=[_listener("click", "<A: void h()>")],
                        )
                    ],
                    window_type="DIALOG",
                ),
            ],
            transitions=[_transition(1, 2, [_event("click", "btn_open")])],
        )
    )
    assert "btn_confirm" in artifact["widgets"]["com.example.MainActivity"]
    assert "android.app.AlertDialog" not in artifact["widgets"]
    assert artifact["mopActivities"] == [
        "android.app.AlertDialog",
        "com.example.MainActivity",
    ]


def test_dialog_class_retained_in_activity_set():
    """
    WTG edges into the dialog are keyed by the dialog class and the OPTIONSMENU
    gateway tests membership of the edge target, so dropping the dialog's own entry
    would silently disable that detection.
    """
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
                )
            ],
            windows=[
                _window(1, "com.example.MainActivity", []),
                _window(
                    2,
                    "android.app.AlertDialog",
                    [
                        _widget(
                            "btn_confirm",
                            listeners=[_listener("click", "<A: void h()>")],
                        )
                    ],
                    window_type="DIALOG",
                ),
            ],
            transitions=[_transition(1, 2, [_event("click")])],
        )
    )
    assert "android.app.AlertDialog" in artifact["mopActivities"]


def test_dialog_first_incoming_edge_wins():
    artifact = derive(
        _document(
            windows=[
                _window(1, "com.example.ActivityA", []),
                _window(2, "com.example.ActivityB", []),
                _window(
                    3,
                    "android.app.AlertDialog",
                    [_widget("btn_confirm", hint="confirm")],
                    window_type="DIALOG",
                ),
            ],
            transitions=[
                _transition(1, 3, [_event("click")]),
                _transition(2, 3, [_event("click")]),
            ],
        )
    )
    assert "btn_confirm" in artifact["widgets"]["com.example.ActivityA"]
    assert "com.example.ActivityB" not in artifact["widgets"]


def test_orphan_dialog_keeps_key():
    artifact = derive(
        _document(
            windows=[
                _window(
                    2,
                    "android.app.AlertDialog",
                    [_widget("btn_confirm", hint="confirm")],
                    window_type="DIALOG",
                )
            ]
        )
    )
    assert "btn_confirm" in artifact["widgets"]["android.app.AlertDialog"]
    assert artifact["stats"]["orphanDialogs"] == 1


def test_dialog_merge_uses_mop_rank():
    """A dialog widget never displaces a stronger host widget under the same id."""
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity", [_method("<A: void h()>", reaches=True)]
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_ok",
                            listeners=[_listener("click", "<A: void h()>")],
                            hint="host",
                        )
                    ],
                ),
                _window(
                    2,
                    "android.app.AlertDialog",
                    [_widget("btn_ok", hint="dialog")],
                    window_type="DIALOG",
                ),
            ],
            transitions=[_transition(1, 2, [_event("click")])],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["hint"] == "host"


def test_dialog_widgets_are_moved_not_copied():
    """The map key moves, so the widget counters do not inflate."""
    artifact = derive(
        _document(
            windows=[
                _window(1, "com.example.MainActivity", []),
                _window(
                    2,
                    "android.app.AlertDialog",
                    [_widget("btn_confirm", hint="confirm")],
                    window_type="DIALOG",
                ),
            ],
            transitions=[_transition(1, 2, [_event("click")])],
        )
    )
    assert artifact["stats"]["widgetsTotal"] == 1


def test_wtg_click_only_deduped_base_keyed():
    artifact = derive(
        _document(
            windows=[
                _window(
                    1,
                    "com.example.MainActivity#OptionsMenu",
                    [],
                    window_type="OPTIONSMENU",
                ),
                _window(2, "com.example.CipherActivity", []),
            ],
            transitions=[
                _transition(1, 2, [_event("click", "menu_cipher")]),
                _transition(1, 2, [_event("click", "menu_cipher")]),
                _transition(1, 2, [_event("long_click", "menu_cipher")]),
            ],
        )
    )
    assert artifact["wtg"] == {
        "com.example.MainActivity": [
            {"widget": "menu_cipher", "target": "com.example.CipherActivity"}
        ]
    }
    assert artifact["stats"]["dedupedTransitions"] == 1
    assert artifact["stats"]["wtgEdges"] == 1


def test_wtg_widget_name_defaults_to_empty_string():
    artifact = derive(
        _document(
            windows=[
                _window(1, "com.example.MainActivity", []),
                _window(2, "com.example.CipherActivity", []),
            ],
            transitions=[
                _transition(
                    1,
                    2,
                    [{"type": "click", "widgetId": 1, "widgetClass": "b"}],
                )
            ],
        )
    )
    assert artifact["wtg"]["com.example.MainActivity"] == [
        {"widget": "", "target": "com.example.CipherActivity"}
    ]


def test_wtg_drops_edges_with_unresolvable_endpoints():
    artifact = derive(
        _document(
            windows=[_window(1, "com.example.MainActivity", [])],
            transitions=[_transition(1, 99, [_event("click")])],
        )
    )
    assert artifact["wtg"] == {}
    assert artifact["stats"]["wtgEdges"] == 0


# ---------------------------------------------------------------------------
# Activity sets (A′) and components
# ---------------------------------------------------------------------------


def test_augmented_union_three_sources():
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.A", [_method("<A: void h()>", reaches=True)]
                ),
                _reaching_class(
                    "C",
                    [_method("<C: void h()>", reaches=True)],
                    component_type="activity",
                ),
            ],
            windows=[
                _window(
                    1,
                    "A",
                    [_widget("btn", listeners=[_listener("click", "<A: void h()>")])],
                )
            ],
            components={
                "activities": [
                    {"className": "B", "reachesTarget": True, "intentFilters": []},
                    {"className": "D", "reachesTarget": False, "intentFilters": []},
                ]
            },
        )
    )
    assert artifact["mopActivities"] == ["A"]
    assert artifact["mopActivitiesAugmented"] == ["A", "B", "C"]


def test_augmented_superset_of_widget_derived():
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.A", [_method("<A: void h()>", reaches=True)]
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.CryptoActivity",
                    [_widget("btn", listeners=[_listener("click", "<A: void h()>")])],
                )
            ],
            components={"activities": []},
        )
    )
    assert set(artifact["mopActivities"]) <= set(artifact["mopActivitiesAugmented"])
    assert "com.example.CryptoActivity" in artifact["mopActivitiesAugmented"]


def test_components_rename_reaches_target_and_compact_target_methods():
    artifact = derive(
        _document(
            components={
                "activities": [
                    {
                        "className": "A",
                        "isMain": True,
                        "exported": True,
                        "permission": None,
                        "reachesTarget": False,
                        "targetMethods": [],
                        "intentFilters": [],
                    }
                ],
                "receivers": [
                    {
                        "className": "R",
                        "isMain": False,
                        "exported": True,
                        "permission": "p",
                        "reachesTarget": True,
                        "targetMethods": ["<R: void onReceive()>"],
                        "intentFilters": [
                            {
                                "actions": ["android.intent.action.BOOT_COMPLETED"],
                                "categories": ["android.intent.category.DEFAULT"],
                                "data": {"schemes": ["x"]},
                            }
                        ],
                    }
                ],
                "providers": [
                    {
                        "className": "P",
                        "authorities": "com.example.provider",
                        "exported": False,
                        "permission": None,
                        "readPermission": "r",
                        "writePermission": "w",
                        "reachesTarget": True,
                        "targetMethods": [],
                    }
                ],
            }
        )
    )
    assert artifact["components"]["activities"][0]["reachesMop"] is False
    receiver = artifact["components"]["receivers"][0]
    assert receiver["reachesMop"] is True
    assert receiver["hasTargetMethods"] is True
    assert receiver["intentFilters"] == [
        {
            "actions": ["android.intent.action.BOOT_COMPLETED"],
            "categories": ["android.intent.category.DEFAULT"],
        }
    ]
    provider = artifact["components"]["providers"][0]
    assert provider["authorities"] == "com.example.provider"
    assert "readPermission" not in provider
    assert "writePermission" not in provider
    # `exported` is fed in by every component of this document and must reach none
    # of them. The jar's launcher is forbidden to consult export status, so the
    # field's only possible use is one the spec rules out; asserting its absence
    # here means a reinstatement fails loudly instead of quietly widening the wire.
    assert "exported" not in artifact["components"]["activities"][0]
    assert "exported" not in receiver
    assert "exported" not in provider


# ---------------------------------------------------------------------------
# Per-activity deep link (INV-DRV-07)
# ---------------------------------------------------------------------------


def _activity_with_filters(filters) -> dict:
    return _document(
        components={
            "activities": [
                {
                    "className": "A",
                    "isMain": False,
                    "exported": True,
                    "permission": None,
                    "reachesTarget": False,
                    "targetMethods": [],
                    "intentFilters": filters,
                }
            ]
        }
    )


def _filter(actions, **data) -> dict:
    return {
        "actions": actions,
        "categories": [],
        "data": {
            "schemes": data.get("schemes", []),
            "hosts": data.get("hosts", []),
            "ports": [],
            "paths": data.get("paths", []),
            "pathPrefixes": [],
            "pathPatterns": [],
            "mimeTypes": [],
        },
    }


def test_deep_link_from_first_action_view():
    artifact = derive(
        _activity_with_filters(
            [
                _filter(["android.intent.action.MAIN"], schemes=["ignored"]),
                _filter(
                    ["android.intent.action.VIEW"],
                    schemes=["myapp"],
                    hosts=["detail"],
                    paths=["/x"],
                ),
                _filter(["android.intent.action.VIEW"], schemes=["second"]),
            ]
        )
    )
    assert artifact["components"]["activities"][0]["deepLinkUri"] == "myapp://detail/x"


def test_deep_link_absent_without_scheme():
    artifact = derive(_activity_with_filters([_filter(["android.intent.action.VIEW"])]))
    assert "deepLinkUri" not in artifact["components"]["activities"][0]


def test_deep_link_absent_without_action_view():
    artifact = derive(
        _activity_with_filters(
            [_filter(["android.intent.action.MAIN"], schemes=["myapp"])]
        )
    )
    assert "deepLinkUri" not in artifact["components"]["activities"][0]


def test_deep_link_absent_without_filters():
    artifact = derive(_activity_with_filters([]))
    activity = artifact["components"]["activities"][0]
    assert "deepLinkUri" not in activity
    assert "data" not in activity
    assert "intentFilters" not in activity


def test_deep_link_empty_host_and_path():
    artifact = derive(
        _activity_with_filters(
            [_filter(["android.intent.action.VIEW"], schemes=["myapp"])]
        )
    )
    assert artifact["components"]["activities"][0]["deepLinkUri"] == "myapp://"


def test_deep_link_scheme_and_host_without_path():
    """
    A host with no path: the host reaches the URI and the path defaults to empty
    on its own.

    The two cases either side of this one — everything present and scheme only —
    are both satisfied by a rule that treats host and path as a single optional
    unit, so neither can tell that the two default independently. This one can,
    which is why it survived the migration out of the jar's `ActivityFrontierTest`
    when `buildDeepLinkUri` was deleted (`rearch-07` 5.3a): it is the last
    assertion standing between a generator that drops the host of a path-less
    filter and an activity frontier that silently loses its deep links.
    """
    artifact = derive(
        _activity_with_filters(
            [
                _filter(
                    ["android.intent.action.VIEW"],
                    schemes=["https"],
                    hosts=["x.com"],
                )
            ]
        )
    )
    assert artifact["components"]["activities"][0]["deepLinkUri"] == "https://x.com"


# ---------------------------------------------------------------------------
# Targets and distances (format 2, INV-DRV-10)
# ---------------------------------------------------------------------------


def test_cut_weighed_keeps_every_pair_within_three_calls_by_distance_then_index():
    assert _cut_weighed({7: 4, 2: 2, 5: 1, 9: 2, 4: 3, 8: 0}) == [
        [8, 0],
        [5, 1],
        [2, 2],
        [9, 2],
        [4, 3],
    ]
    assert _cut_weighed({0: 4, 1: 5}) == []
    assert _cut_weighed({}) == []


def test_cut_nearest_keeps_the_nearest_three_by_distance_then_index():
    assert _cut_nearest({7: 4, 2: 2, 5: 1, 9: 2}) == [[5, 1], [2, 2], [9, 2]]
    assert _cut_nearest({0: 4, 1: 5}) == [[0, 4], [1, 5]]
    assert _cut_nearest({}) == []


def test_merge_minima_keeps_the_smaller_distance_per_target():
    into = {1: 3, 2: 5}
    assert _merge_minima(into, {2: 4, 3: 1}) is into
    assert into == {1: 3, 2: 4, 3: 1}


def test_pair_rules_hold_over_random_minima():
    """
    INV-DRV-10 over seeded random minima: the merge keeps the minimum per target.
    Both cuts keep each index once, sorted by `(d, i)`, with the merged distance.
    `_cut_weighed` keeps exactly the targets at `d <= DIST_WEIGHED_MAX`;
    `_cut_nearest` keeps at most `DIST_K`, with no dropped pair nearer than a kept one.
    """
    rng = random.Random(122)
    for _ in range(500):
        targets = rng.randint(1, 40)
        left = {
            rng.randrange(targets): rng.randint(0, 10)
            for _ in range(rng.randint(0, 15))
        }
        right = {
            rng.randrange(targets): rng.randint(0, 10)
            for _ in range(rng.randint(0, 15))
        }

        merged = _merge_minima(dict(left), right)
        assert set(merged) == set(left) | set(right)
        for target, distance in merged.items():
            assert distance == min(
                d for d in (left.get(target), right.get(target)) if d is not None
            )

        for pairs in (_cut_weighed(merged), _cut_nearest(merged)):
            assert len({i for i, _ in pairs}) == len(pairs)
            assert all(0 <= i < targets and merged[i] == d for i, d in pairs)
            keys = [(d, i) for i, d in pairs]
            assert keys == sorted(keys)

        weighed = _cut_weighed(merged)
        assert {i for i, _ in weighed} == {
            i for i, d in merged.items() if d <= DIST_WEIGHED_MAX
        }

        nearest = _cut_nearest(merged)
        assert len(nearest) == min(DIST_K, len(merged))
        keys = [(d, i) for i, d in nearest]
        dropped = [(d, i) for i, d in merged.items() if [i, d] not in nearest]
        assert all(key < other for key in keys for other in dropped)


def test_read_pairs_skips_malformed_entries():
    """
    Noise inside a well-typed section is skipped: a non-pair, an index outside
    `[0, targets)`, a negative distance, a bool and a float are all dropped, and a
    repeated index keeps its minimum.
    """
    raw = [
        [0, 2],
        [1],
        "x",
        [5, 1],
        [-1, 1],
        [2, -1],
        [True, 1],
        [3, False],
        [1.0, 2],
        [4, 3, 9],
        [0, 1],
    ]
    assert _read_pairs(raw, 5) == {0: 1}
    assert _read_pairs("not-a-list", 5) == {}
    assert _read_pairs([[0, 1]], 0) == {}


def test_derive_refuses_non_list_distance_targets():
    with pytest.raises(DerivationError):
        derive(_document(distanceTargets={"0": "x"}))


def test_widget_distance_is_the_minimum_over_its_handlers_within_three_calls():
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(13),
            reachability=[
                _reaching_class(
                    "com.example.Handlers",
                    [
                        _method(
                            "<A: void a()>",
                            reaches=True,
                            distances=[[2, 3], [5, 1], [7, 4], [8, 3]],
                        ),
                        _method(
                            "<A: void b()>",
                            reaches=True,
                            distances=[[2, 2], [9, 6], [11, 1], [12, 3]],
                        ),
                    ],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_ok",
                            listeners=[
                                _listener("click", "<A: void a()>"),
                                _listener("click", "<A: void b()>"),
                            ],
                        )
                    ],
                )
            ],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["dist"] == {"click": [[5, 1], [11, 1], [2, 2], [8, 3], [12, 3]]}
    assert artifact["targets"] == 13


def test_a_widget_whose_targets_are_all_four_calls_away_carries_no_pair():
    """
    The widget stays emitted and flagged, with no `dist`; its activity still ranks
    the pairs, because an activity starts from its widgets' uncut minima.
    """
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(2),
            reachability=[
                _reaching_class(
                    "com.example.Handlers",
                    [
                        _method(
                            "<A: void a()>", reaches=True, distances=[[0, 4], [1, 5]]
                        )
                    ],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_far", listeners=[_listener("click", "<A: void a()>")]
                        )
                    ],
                )
            ],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_far"]
    assert entry["mop"] == {"click": "transitive"}
    assert "dist" not in entry
    assert artifact["activityDist"] == {"com.example.MainActivity": [[0, 4], [1, 5]]}


def test_activity_dist_keeps_the_three_nearest_targets():
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(5),
            reachability=[
                _reaching_class(
                    "com.example.Handlers",
                    [
                        _method(
                            "<A: void a()>", reaches=True, distances=[[1, 0], [2, 1]]
                        ),
                        _method(
                            "<A: void b()>", reaches=True, distances=[[3, 1], [4, 2]]
                        ),
                    ],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "first", listeners=[_listener("click", "<A: void a()>")]
                        ),
                        _widget(
                            "second", listeners=[_listener("click", "<A: void b()>")]
                        ),
                    ],
                )
            ],
        )
    )
    widgets = artifact["widgets"]["com.example.MainActivity"]
    assert widgets["first"]["dist"] == {"click": [[1, 0], [2, 1]]}
    assert widgets["second"]["dist"] == {"click": [[3, 1], [4, 2]]}
    assert artifact["activityDist"] == {
        "com.example.MainActivity": [[1, 0], [2, 1], [3, 1]]
    }


def test_unlisted_wrapper_takes_its_distances_from_the_recovered_lambdas():
    handler = (
        "<com.example.MainActivity$$ExternalSyntheticLambda0: "
        "void onClick(android.view.View)>"
    )
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(8),
            reachability=[
                _reaching_class(
                    "com.example.MainActivity",
                    [
                        _method(
                            "<com.example.MainActivity: void lambda$onCreate$0()>",
                            name="lambda$onCreate$0",
                            reaches=True,
                            distances=[[4, 2]],
                        ),
                        _method(
                            "<com.example.MainActivity: void lambda$onCreate$1()>",
                            name="lambda$onCreate$1",
                            reaches=True,
                            distances=[[4, 1], [6, 3]],
                        ),
                    ],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [_widget("btn_ok", listeners=[_listener("click", handler)])],
                )
            ],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["dist"] == {"click": [[4, 1], [6, 3]]}


def test_producer_precedence_listener_takes_its_distances_from_the_join():
    """The producer supplies flags and no distance, so the pairs come from the join."""
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(3),
            reachability=[
                _reaching_class(
                    "com.example.Handlers",
                    [_method("<A: void h()>", reaches=True, distances=[[1, 2]])],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_ok",
                            listeners=[
                                _listener(
                                    "click", "<A: void h()>", reaches=True, direct=True
                                )
                            ],
                        )
                    ],
                )
            ],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
    assert entry["mop"] == {"click": "both"}
    assert entry["dist"] == {"click": [[1, 2]]}


def test_handler_table_lists_a_class_that_reaches_nothing():
    reaching_nothing = "com.example.ui.ScreenKt$Body$1$1"
    reaching = "com.example.ui.ScreenKt$Body$2"
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(4),
            reachability=[
                _reaching_class(
                    reaching_nothing,
                    [
                        _method(
                            f"<{reaching_nothing}: java.lang.Object invoke()>",
                            name="invoke",
                        )
                    ],
                ),
                _reaching_class(
                    reaching,
                    [
                        _method(
                            f"<{reaching}: java.lang.Object invoke(java.lang.Object)>",
                            name="invoke",
                            reaches=True,
                            distances=[[3, 2]],
                        )
                    ],
                ),
            ],
        )
    )
    assert artifact["handlers"] == {
        reaching_nothing: {"mop": {"click": "none", "longclick": "none"}},
        reaching: {
            "mop": {"click": "transitive", "longclick": "transitive"},
            "dist": {"click": [[3, 2]], "longclick": [[3, 2]]},
        },
    }


def test_an_event_cut_to_nothing_loses_its_key_while_another_keeps_its_pairs():
    """
    The cut is per event: `longclick`, whose only target is four calls away, has no
    key in `dist`, while `click` keeps its pair, and both keep their flags.
    """
    handlers = "com.example.Handlers"
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(3),
            reachability=[
                _reaching_class(
                    handlers,
                    [
                        _method(
                            f"<{handlers}: void onClick(android.view.View)>",
                            name="onClick",
                            reaches=True,
                            distances=[[1, 1]],
                        ),
                        _method(
                            f"<{handlers}: boolean onLongClick(android.view.View)>",
                            name="onLongClick",
                            reaches=True,
                            distances=[[2, 4]],
                        ),
                    ],
                )
            ],
        )
    )
    assert artifact["handlers"][handlers] == {
        "mop": {"click": "transitive", "longclick": "transitive"},
        "dist": {"click": [[1, 1]]},
    }


def test_handler_table_matches_handler_methods_by_name_and_parameters():
    """
    `onClick(View)` fills `click`, `onLongClick(View)` fills `longclick` whatever its
    `boolean` return, and the Object-returning `invoke` fills both. Two methods
    filling one event OR their flags and merge their pairs, and the merged list is
    cut at `d <= 3` as a widget's is, so `onClick`'s pair at `d = 4` drops. A typed
    `void invoke()`, an `onClick` of another parameter list and a constructor are
    not handlers.
    """
    handlers = "com.example.Handlers"
    others = "com.example.NotHandlers"
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(6),
            reachability=[
                _reaching_class(
                    handlers,
                    [
                        _method(
                            f"<{handlers}: void onClick(android.view.View)>",
                            name="onClick",
                            reaches=True,
                            distances=[[1, 3], [2, 4]],
                        ),
                        _method(
                            f"<{handlers}: java.lang.Object invoke()>",
                            name="invoke",
                            direct=True,
                            distances=[[1, 1]],
                        ),
                        _method(
                            f"<{handlers}: boolean onLongClick(android.view.View)>",
                            name="onLongClick",
                        ),
                    ],
                ),
                _reaching_class(
                    others,
                    [
                        _method(
                            f"<{others}: void invoke()>",
                            name="invoke",
                            reaches=True,
                            distances=[[0, 1]],
                        ),
                        _method(
                            f"<{others}: void onClick(int)>",
                            name="onClick",
                            reaches=True,
                        ),
                        _method(
                            f"<{others}: void <init>()>", name="<init>", reaches=True
                        ),
                    ],
                ),
            ],
        )
    )
    assert artifact["handlers"] == {
        handlers: {
            "mop": {"click": "both", "longclick": "both"},
            "dist": {"click": [[1, 1]], "longclick": [[1, 1]]},
        }
    }


def test_document_without_distances_derives_with_no_target():
    """
    A September document has no `distanceTargets`, so `targets` is 0 and every
    pair fails the range check, even one a method happens to carry.
    """
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.MainActivity",
                    [_method("<A: void h()>", reaches=True, distances=[[0, 1]])],
                    component_type="activity",
                ),
                _reaching_class(
                    "com.example.Listener",
                    [
                        _method(
                            "<com.example.Listener: void onClick(android.view.View)>",
                            name="onClick",
                            reaches=True,
                        )
                    ],
                ),
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [_widget("btn", listeners=[_listener("click", "<A: void h()>")])],
                )
            ],
        )
    )
    assert artifact["targets"] == 0
    assert artifact["handlers"] == {
        "com.example.Listener": {"mop": {"click": "transitive"}}
    }
    assert "dist" not in artifact["widgets"]["com.example.MainActivity"]["btn"]
    assert artifact["activityDist"] == {}


@pytest.mark.parametrize("direct_first", [True, False])
def test_colliding_widgets_merge_their_distances_by_the_minimum(direct_first):
    reachability = [
        _reaching_class(
            "com.example.Handlers",
            [
                _method("<A: void zeroHop()>", direct=True, distances=[[3, 0]]),
                _method("<A: void deep()>", reaches=True, distances=[[3, 1], [5, 2]]),
            ],
        )
    ]
    direct = _widget("submit", listeners=[_listener("click", "<A: void zeroHop()>")])
    transitive = _widget("submit", listeners=[_listener("click", "<A: void deep()>")])
    widgets = [direct, transitive] if direct_first else [transitive, direct]
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(6),
            reachability=reachability,
            windows=[_window(1, "com.example.MainActivity", widgets)],
        )
    )
    entry = artifact["widgets"]["com.example.MainActivity"]["submit"]
    assert entry["mop"] == {"click": "both"}
    assert entry["dist"] == {"click": [[3, 0], [5, 2]]}


def test_an_activity_constructor_does_not_count_toward_its_distance():
    def activity_dist(on_resume):
        return derive(
            _document(
                distanceTargets=_distance_targets(24),
                reachability=[
                    _reaching_class(
                        "com.example.A",
                        [
                            _method(
                                "<com.example.A: void <init>()>",
                                name="<init>",
                                reaches=True,
                                distances=[[23, 0]],
                            ),
                            _method(
                                "<com.example.A: void <clinit>()>",
                                name="<clinit>",
                                reaches=True,
                                distances=[[22, 0]],
                            ),
                            on_resume,
                        ],
                        component_type="activity",
                    )
                ],
            )
        )["activityDist"]

    assert activity_dist(
        _method(
            "<com.example.A: void onResume()>",
            name="onResume",
            reaches=True,
            distances=[[2, 5]],
        )
    ) == {"com.example.A": [[2, 5]]}
    assert (
        activity_dist(_method("<com.example.A: void onResume()>", name="onResume"))
        == {}
    )


def test_dialog_pairs_move_to_the_host_widget_and_activity():
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(5),
            reachability=[
                _reaching_class(
                    "com.example.Handlers",
                    [
                        _method("<A: void open()>", reaches=True, distances=[[4, 3]]),
                        _method(
                            "<A: void confirm()>", reaches=True, distances=[[1, 2]]
                        ),
                    ],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [
                        _widget(
                            "btn_open",
                            listeners=[_listener("click", "<A: void open()>")],
                        )
                    ],
                ),
                _window(
                    2,
                    "android.app.AlertDialog",
                    [
                        _widget(
                            "btn_confirm",
                            listeners=[_listener("click", "<A: void confirm()>")],
                        )
                    ],
                    window_type="DIALOG",
                ),
            ],
            transitions=[_transition(1, 2, [_event("click", "btn_open")])],
        )
    )
    host = artifact["widgets"]["com.example.MainActivity"]
    assert host["btn_confirm"]["dist"] == {"click": [[1, 2]]}
    assert artifact["activityDist"] == {"com.example.MainActivity": [[1, 2], [4, 3]]}


def test_an_id_less_widget_still_reaches_its_activity_distance():
    """
    The empty-short-id rule keeps the widget off the wire, not off its activity,
    for the reason INV-DRV-02 gives for the activity sets; every event counts.
    """
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(2),
            reachability=[
                _reaching_class(
                    "com.example.Handlers",
                    [_method("<A: void h()>", reaches=True, distances=[[0, 3]])],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [_widget("", listeners=[_listener("long_click", "<A: void h()>")])],
                )
            ],
        )
    )
    assert artifact["widgets"] == {}
    assert artifact["activityDist"] == {"com.example.MainActivity": [[0, 3]]}


def test_an_activity_reaching_only_through_its_constructor_stays_out_of_source_3():
    artifact = derive(
        _document(
            reachability=[
                _reaching_class(
                    "com.example.A",
                    [
                        _method(
                            "<com.example.A: void <init>()>",
                            name="<init>",
                            reaches=True,
                        ),
                        _method(
                            "<com.example.A: void <clinit>()>",
                            name="<clinit>",
                            direct=True,
                        ),
                    ],
                    component_type="activity",
                ),
                _reaching_class(
                    "com.example.B",
                    [
                        _method(
                            "<com.example.B: void <init>()>",
                            name="<init>",
                            reaches=True,
                        ),
                        _method(
                            "<com.example.B: void onCreate()>",
                            name="onCreate",
                            reaches=True,
                        ),
                    ],
                    component_type="activity",
                ),
            ]
        )
    )
    assert artifact["mopActivitiesAugmented"] == ["com.example.B"]


# ---------------------------------------------------------------------------
# Projection as a whole, canonical serialization and provenance
# ---------------------------------------------------------------------------

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cryptoapp.apk.json")


@pytest.fixture(scope="module")
def cryptoapp_bytes() -> bytes:
    with open(FIXTURE_PATH, "rb") as fixture:
        return fixture.read()


@pytest.fixture(scope="module")
def cryptoapp(cryptoapp_bytes) -> dict:
    return derive(
        json.loads(cryptoapp_bytes),
        source_file="cryptoapp.apk.json",
        source_digest=digest_of_file(FIXTURE_PATH),
    )


def test_derive_cryptoapp_ground_truth(cryptoapp):
    """
    The whole projection against the gh120 producer output for cryptoapp.

    `CryptographyActivity` is in the set through the exact join: its
    `$$ExternalSyntheticLambda0` wrapper handler carries its own `reachesTarget`,
    because the producer links each wrapper to its body (INV-ANA-77), so nothing
    is recovered. `MainActivity` reaches a target only through its own `<init>`,
    a boundary target, so it stays out of the augmented set and has no
    `activityDist` entry.
    """
    assert cryptoapp["package"] == "br.unb.cic.cryptoapp"
    assert cryptoapp["mainActivity"] == "br.unb.cic.cryptoapp.MainActivity"
    assert cryptoapp["mopActivities"] == [
        "br.unb.cic.cryptoapp.cipher.CipherActivity",
        "br.unb.cic.cryptoapp.generated.CryptographyActivity",
        "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity",
    ]
    assert cryptoapp["optionsMenus"] == [
        {"activity": "br.unb.cic.cryptoapp.MainActivity", "hasFlaggedWidget": False}
    ]

    assert cryptoapp["mopActivitiesAugmented"] == cryptoapp["mopActivities"]

    main_edges = cryptoapp["wtg"]["br.unb.cic.cryptoapp.MainActivity"]
    targets = {edge["target"] for edge in main_edges}
    assert set(cryptoapp["mopActivities"]) <= targets

    assert len(cryptoapp["components"]["activities"]) == 4
    providers = cryptoapp["components"]["providers"]
    assert len(providers) == 1
    assert providers[0]["authorities"] == "br.unb.cic.cryptoapp.androidx-startup"
    assert all(
        component["reachesMop"] is False
        for components in cryptoapp["components"].values()
        for component in components
    )

    assert cryptoapp["stats"]["windows"] == 5
    assert cryptoapp["stats"]["flagged"] == 3
    assert cryptoapp["stats"]["recovered"] == 0

    assert cryptoapp["formatVersion"] == 2
    assert cryptoapp["targets"] == 27

    cipher = "br.unb.cic.cryptoapp.cipher.CipherActivity"
    generated = "br.unb.cic.cryptoapp.generated.CryptographyActivity"
    digest = "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity"
    widgets = cryptoapp["widgets"]
    assert widgets[digest]["buttonGenerateHash"]["dist"] == {"click": [[22, 2]]}
    # Both of its handler's pairs are at d = 4, which the jar does not weigh.
    assert widgets[cipher]["btn_cipher_encrypt"]["mop"] == {"click": "transitive"}
    assert "dist" not in widgets[cipher]["btn_cipher_encrypt"]
    assert widgets[generated]["executeButton"]["dist"] == {
        "click": [[16, 3], [17, 3], [18, 3]]
    }

    assert cryptoapp["handlers"] == {
        f"{cipher}$1": {"mop": {"click": "transitive"}},
        f"{generated}$$ExternalSyntheticLambda0": {
            "mop": {"click": "transitive"},
            "dist": {"click": [[16, 3], [17, 3], [18, 3]]},
        },
    }
    assert cryptoapp["activityDist"] == {
        cipher: [[0, 2], [1, 2]],
        generated: [[12, 0], [13, 0], [14, 0]],
        digest: [[22, 2]],
    }


# The shape of a Soot method signature, `<class: return name(params)>`.
SOOT_SIGNATURE_PATTERN = re.compile(r"^<[^<>:]+: \S+ [^\s(]+\(.*\)>$")


def _signature_strings(node):
    """Every key or string value in the artifact shaped like a method signature."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if SOOT_SIGNATURE_PATTERN.match(key):
                found.append(key)
            found.extend(_signature_strings(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_signature_strings(item))
    elif isinstance(node, str) and SOOT_SIGNATURE_PATTERN.match(node):
        found.append(node)
    return found


def _target_keys(node, path="artifact"):
    """Every `*Target*` key in the artifact, as `path.key` strings."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if "Target" in key:
                found.append(f"{path}.{key}")
            found.extend(_target_keys(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(_target_keys(item, f"{path}[{index}]"))
    return found


def test_no_target_keys_on_wire():
    """
    The producer's neutral `*Target` vocabulary stops at this boundary, and the
    call graph that dominated the bytes does not cross it at all.

    `hasTargetMethods` is the single documented exception — the boolean the
    `targetMethods` signature list compacts to, whose name belongs to the jointly
    defined wire format. It only exists on receivers and services, so a document
    declaring neither makes this assertion vacuous; the components below are what
    give it a subject. Format 2 carries target indices and handler class names,
    never a signature: the `distanceTargets` list and the handler methods below
    are what give that half a subject (INV-DRV-06).
    """
    component = {
        "className": "C",
        "isMain": False,
        "exported": True,
        "permission": None,
        "reachesTarget": True,
        "targetMethods": ["<C: void onReceive()>"],
        "intentFilters": [],
    }
    handler = "<com.example.Listener: void onClick(android.view.View)>"
    artifact = derive(
        _document(
            distanceTargets=_distance_targets(2),
            reachability=[
                _reaching_class(
                    "com.example.Listener",
                    [
                        _method(
                            handler, name="onClick", reaches=True, distances=[[1, 1]]
                        )
                    ],
                )
            ],
            windows=[
                _window(
                    1,
                    "com.example.MainActivity",
                    [_widget("btn", listeners=[_listener("click", handler)])],
                )
            ],
            components={
                "activities": [component],
                "receivers": [component],
                "services": [component],
                "providers": [{**component, "authorities": "a"}],
            },
        )
    )

    assert artifact["components"]["receivers"][0]["hasTargetMethods"] is True
    assert sorted(set(_target_keys(artifact))) == [
        "artifact.components.receivers[0].hasTargetMethods",
        "artifact.components.services[0].hasTargetMethods",
    ]
    sections = (
        "reachability",
        "windows",
        "transitions",
        "listeners",
        "distanceTargets",
    )
    for section in sections:
        assert section not in artifact
    assert artifact["handlers"]["com.example.Listener"]["dist"] == {"click": [[1, 1]]}
    assert _signature_strings(artifact) == []


def test_no_target_keys_on_the_cryptoapp_projection(cryptoapp):
    assert _target_keys(cryptoapp) == []
    sections = (
        "reachability",
        "windows",
        "transitions",
        "listeners",
        "distanceTargets",
    )
    for section in sections:
        assert section not in cryptoapp
    assert _signature_strings(cryptoapp) == []


def test_provenance_digest_matches_the_input(cryptoapp, cryptoapp_bytes):
    expected = hashlib.sha256(cryptoapp_bytes).hexdigest()
    assert cryptoapp["source"]["digest"] == f"sha256:{expected}"
    assert cryptoapp["source"]["file"] == "cryptoapp.apk.json"
    assert cryptoapp["source"]["generator"] == "aperv-derive/2"


def test_serialize_canonical_is_byte_stable(cryptoapp_bytes):
    """
    Byte stability must survive a fresh process, where Python's hash randomization
    reorders every set the derivation builds. Two runs under different hash seeds
    are the honest check; repeating in-process would not exercise it.
    """
    script = (
        "import json,sys;"
        "sys.path.insert(0, sys.argv[1]);"
        "from aperv_tool.tools.aperv.derive_mop_artifact import derive, "
        "serialize_canonical;"
        "from rv_android_core.util.analysis_document import digest_of_file;"
        "raw = open(sys.argv[2], 'rb').read();"
        "a = derive(json.loads(raw), source_file='cryptoapp.apk.json', "
        "source_digest=digest_of_file(sys.argv[2]));"
        "sys.stdout.buffer.write(serialize_canonical(a))"
    )
    source_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")

    outputs = []
    for seed in ("0", "12345"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        result = subprocess.run(
            [sys.executable, "-c", script, source_root, FIXTURE_PATH],
            capture_output=True,
            check=True,
            env=env,
        )
        outputs.append(result.stdout)

    assert outputs[0] == outputs[1]
    assert outputs[0] == serialize_canonical(
        derive(
            json.loads(cryptoapp_bytes),
            source_file="cryptoapp.apk.json",
            source_digest=digest_of_file(FIXTURE_PATH),
        )
    )


def test_key_order_independent_of_input_order():
    """Sorted keys make the bytes a function of content, not of construction."""
    forward = {"complete": True, "package": "com.example", "mainActivity": "M"}
    reordered = {"mainActivity": "M", "package": "com.example", "complete": True}
    assert serialize_canonical(derive(forward)) == serialize_canonical(
        derive(reordered)
    )


def test_stats_do_not_affect_sets():
    """
    An orphan dialog moves two counters and nothing else: no flag, no set, no edge
    may depend on a diagnostic.
    """
    base = _document(
        windows=[_window(1, "com.example.MainActivity", [_widget("btn", hint="x")])]
    )
    with_orphan = _document(
        windows=[
            _window(1, "com.example.MainActivity", [_widget("btn", hint="x")]),
            _window(9, "android.app.AlertDialog", [], window_type="DIALOG"),
        ]
    )

    plain = derive(base)
    noisy = derive(with_orphan)
    assert noisy["stats"] != plain["stats"]
    assert noisy["stats"]["orphanDialogs"] == 1

    del plain["stats"], noisy["stats"]
    assert plain == noisy


def test_collision_direct_outranks_transitive_resident():
    """
    The `direct` rank is the one gh96 restored, so the collision policy has to be
    able to see it: a 0-hop handler must displace an any-depth resident under the
    same short id, whichever order the producer listed the windows in.
    """
    reachability = [
        _reaching_class(
            "com.example.MainActivity",
            [
                _method("<A: void deep()>", reaches=True),
                _method("<A: void zeroHop()>", direct=True),
            ],
        )
    ]
    transitive = _widget(
        "btn_ok", listeners=[_listener("click", "<A: void deep()>")], hint="transitive"
    )
    direct = _widget(
        "btn_ok", listeners=[_listener("click", "<A: void zeroHop()>")], hint="direct"
    )

    for widgets in ([transitive, direct], [direct, transitive]):
        artifact = derive(
            _document(
                reachability=reachability,
                windows=[_window(1, "com.example.MainActivity", widgets)],
            )
        )
        entry = artifact["widgets"]["com.example.MainActivity"]["btn_ok"]
        assert entry["hint"] == "direct"
        assert entry["mop"] == {"click": "both"}


# ---------------------------------------------------------------------------
# Streaming read with the pair reduction (INV-APV-64)
# ---------------------------------------------------------------------------

STREAMING_POLICY = PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K)


def _streamed_artifact(path: str) -> bytes:
    """The artifact bytes `_derive_mop_artifact` produces on a cache miss."""
    document, truncated = read_analysis_document(path, STREAMING_POLICY)
    assert not truncated
    return serialize_canonical(
        derive(
            document,
            source_file=os.path.basename(path),
            source_digest=digest_of_file(path),
        )
    )


def _whole_artifact(path: str) -> bytes:
    """The artifact bytes of the whole-document parse the reduction must match."""
    with open(path, encoding="utf-8") as source:
        document = json.load(source)
    return serialize_canonical(
        derive(
            document,
            source_file=os.path.basename(path),
            source_digest=digest_of_file(path),
        )
    )


def test_streaming_byte_identical_on_cryptoapp():
    assert _streamed_artifact(FIXTURE_PATH) == _whole_artifact(FIXTURE_PATH)


def test_compact_document_derives_the_same_artifact(tmp_path):
    """
    GATOR's compact output keeps per method the pairs the derive can use, so the
    artifact derived from it equals the one derived from the full document of the
    same analysis (INV-ANA-89). The compact document is the converter's output for
    the fixture, which is byte-identical to GATOR's compact output (INV-ANA-87).
    Both derivations are given the full document's provenance: `source.digest`
    names the file the artifact was derived from, and only that field may differ.
    """
    from rv_static_analysis.compact import compact_document

    compact_path = tmp_path / "cryptoapp.apk.json"
    compact_document(FIXTURE_PATH, str(compact_path))

    def artifact(path) -> bytes:
        document, truncated = read_analysis_document(str(path), STREAMING_POLICY)
        assert not truncated
        return serialize_canonical(
            derive(
                document,
                source_file="cryptoapp.apk.json",
                source_digest=digest_of_file(FIXTURE_PATH),
            )
        )

    # The conversion dropped pairs, so the two inputs really differ.
    assert compact_path.stat().st_size < os.path.getsize(FIXTURE_PATH)
    assert artifact(compact_path) == artifact(FIXTURE_PATH)


# Pairs of the synthetic document below. The methods MainActivity's widgets and
# its own `onCreate` reach hold no pair within DIST_WEIGHED_MAX, so its
# `activityDist` comes entirely from pairs beyond d = 3, one target from each of
# three methods. The third, `[11, 6]`, is the third nearest of `c()`, whose two
# nearer targets lose the merge to `a()` and `b()`: a reduction keeping fewer than
# DIST_K per method would lose it. Every far method also holds pairs past its own
# three nearest, which the reduction drops.
_FAR_A = [[0, 6], [0, 4], [1, 7], [2, 8], [3, 9], [4, 10]]
_FAR_B = [[5, 5], [6, 9], [7, 10], [8, 11], [5, 12]]
_FAR_C = [[0, 5], [5, 6], [11, 6], [10, 12], [12, 14]]
_FAR_C_DUPLICATE = [[9, 8], [11, 7], [13, 15]]
_ON_CREATE = [[12, 7], [13, 20], [14, 21], [15, 22]]
_NEAR_D = [[13, 1], [14, 3], [15, 2], [0, 1], [1, 9], [2, 12]]
_CLICK = [[3, 4], [4, 5], [5, 6], [6, 7]]
# Entries `_read_pairs` skips. `[50, 0]` is out of range: if it took one of the
# three nearest places in its method, the reduction would drop a pair the
# derivation reads.
_NOISE = [
    [50, 0],
    [1],
    ["x", 2],
    [True, 1],
    [1, 2.0],
    [-1, 2],
    [2, -1],
    [[1], 2],
    {"i": 1},
    [1, 2, 3],
    None,
]
_TARGET_COUNT = 16
_ACTIVITY_METHODS = {
    "<A: void a()>": _FAR_A,
    "<A: void b()>": _FAR_B,
    "<A: void c()>": _FAR_C,
    "<com.example.MainActivity: void onCreate(android.os.Bundle)>": _ON_CREATE,
}


def _far_targets_document(targets_first: bool) -> dict:
    """A document whose activity's three nearest targets lie beyond d = 3."""
    reachability = [
        _reaching_class(
            "com.example.Handlers",
            [
                _method("<A: void a()>", reaches=True, distances=_FAR_A + _NOISE),
                _method("<A: void b()>", reaches=True, distances=_FAR_B),
                _method("<A: void c()>", reaches=True, distances=_FAR_C),
                _method("<A: void d()>", reaches=True, distances=_NOISE + _NEAR_D),
                _method("<A: void e()>", reaches=False, distances="none"),
                _method("<A: void f()>", reaches=False, distances={"0": 1}),
            ],
        ),
        _reaching_class(
            "com.example.MainActivity",
            [
                _method(
                    "<com.example.MainActivity: void onCreate(android.os.Bundle)>",
                    name="onCreate",
                    reaches=True,
                    distances=_ON_CREATE,
                ),
                _method(
                    "<com.example.MainActivity: void <init>()>",
                    name="<init>",
                    reaches=True,
                    distances=[[1, 0]],
                ),
            ],
            component_type="activity",
        ),
        _reaching_class(
            "com.example.Duplicates",
            [_method("<A: void c()>", reaches=True, distances=_FAR_C_DUPLICATE)],
        ),
        _reaching_class(
            "com.example.Click",
            [
                _method(
                    "<com.example.Click: void onClick(android.view.View)>",
                    name="onClick",
                    reaches=True,
                    distances=_CLICK,
                )
            ],
        ),
    ]
    windows = [
        _window(
            1,
            "com.example.MainActivity",
            [
                _widget("far_a", listeners=[_listener("click", "<A: void a()>")]),
                _widget("far_b", listeners=[_listener("click", "<A: void b()>")]),
                _widget("far_c", listeners=[_listener("long_click", "<A: void c()>")]),
            ],
        ),
        _window(
            2,
            "com.example.OtherActivity",
            [_widget("near_d", listeners=[_listener("click", "<A: void d()>")])],
        ),
    ]
    document = {"package": "com.example", "mainActivity": "com.example.MainActivity"}
    if targets_first:
        document["distanceTargets"] = _distance_targets(_TARGET_COUNT)
    document.update(reachability=reachability, windows=windows, transitions=[])
    document["components"] = {}
    if not targets_first:
        document["distanceTargets"] = _distance_targets(_TARGET_COUNT)
    document["complete"] = True
    return document


@pytest.mark.parametrize(
    "targets_first", [True, False], ids=["targets-before-reachability", "targets-last"]
)
def test_streaming_byte_identical_when_nearest_targets_lie_beyond_the_cut(
    tmp_path, targets_first
):
    """
    The reduction keeps each method's three nearest targets, not only those within
    DIST_WEIGHED_MAX, because an activity's three nearest after the merge can all
    lie beyond the cut and come from different methods. GATOR writes
    `distanceTargets` before `reachability`; the other order leaves the reader
    without the index bound while the pairs stream past, and must still match.
    """
    document = _far_targets_document(targets_first)
    path = tmp_path / "far.apk.json"
    path.write_text(json.dumps(document, indent=2))

    assert _streamed_artifact(str(path)) == _whole_artifact(str(path))

    # The document exercises the case: MainActivity's three nearest are beyond
    # d = 3, and each comes from a different method.
    artifact = derive(document)
    nearest = artifact["activityDist"]["com.example.MainActivity"]
    assert nearest == [[0, 4], [5, 5], [11, 6]]
    assert all(distance > DIST_WEIGHED_MAX for _, distance in nearest)
    origins = [
        {
            signature
            for signature, pairs in _ACTIVITY_METHODS.items()
            if [index, distance] in pairs
        }
        for index, distance in nearest
    ]
    assert all(len(origin) == 1 for origin in origins)
    assert len(set().union(*origins)) == len(nearest)

    # A reduction to the pairs within DIST_WEIGHED_MAX alone would lose them.
    cut = json.loads(json.dumps(document))
    for entry in cut["reachability"]:
        for method in entry["methods"]:
            pairs = method.get("targetDistances")
            if isinstance(pairs, list):
                method["targetDistances"] = [
                    pair
                    for pair in pairs
                    if isinstance(pair, list)
                    and len(pair) == 2
                    and isinstance(pair[1], int)
                    and pair[1] <= DIST_WEIGHED_MAX
                ]
    assert derive(cut)["activityDist"] != artifact["activityDist"]

    # And the reader did drop pairs: with the index bound known, each method
    # carries only its survivors, noise and the out-of-range `[50, 0]` included.
    if targets_first:
        streamed, _ = read_analysis_document(str(path), STREAMING_POLICY)
        reduced = {
            method["signature"]: method["targetDistances"]
            for entry in streamed["reachability"]
            for method in entry["methods"]
            if entry["className"] == "com.example.Handlers"
        }
        assert reduced["<A: void a()>"] == [[0, 4], [1, 7], [2, 8]]
        assert reduced["<A: void d()>"] == [[0, 1], [13, 1], [15, 2], [14, 3]]
