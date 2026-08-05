"""
Tests for the host-side MOP artifact derivation.

Each relocated parse-time rule gets a named test on a synthetic fragment, so a
regression names the rule that broke rather than diffing a large fixture. The
cryptoapp ground truth covers the projection as a whole.
"""

import hashlib
import json
import os
import subprocess
import sys

import pytest

from aperv_tool.tools.aperv.derive_mop_artifact import (
    DerivationError,
    _base_activity,
    _index_reachability,
    _normalize_event_type,
    derive,
    digest_of,
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


def _method(signature, *, name=None, reaches=False, direct=False) -> dict:
    return {
        "name": name if name is not None else signature,
        "signature": signature,
        "reachable": True,
        "reachesTarget": reaches,
        "directlyReachesTarget": direct,
    }


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
    by_signature, _, _ = _index_reachability(
        [
            {
                "className": "com.example.A",
                "componentType": "class",
                "methods": [_method("<A: void a()>", reaches=True)],
            }
        ]
    )
    assert by_signature["<A: void a()>"] == (False, True)


def test_index_reachability_direct_only_method_is_transitive():
    """
    The producer emits methods with `directlyReachesTarget` and no `reachesTarget`
    (33 methods across 16 corpus apps). Storing `reachesTarget` unmodified — what
    the jar's index did — would derive a widget that is direct but not transitive,
    an incoherent state.
    """
    by_signature, _, _ = _index_reachability(
        [
            {
                "className": "com.example.A",
                "methods": [_method("<A: void a()>", direct=True, reaches=False)],
            }
        ]
    )
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
    forward, _, _ = _index_reachability(entries)
    backward, _, _ = _index_reachability(list(reversed(entries)))
    assert forward["<A: void a()>"] == (True, True)
    assert backward["<A: void a()>"] == (True, True)


def test_index_reachability_skips_unreaching_methods():
    by_signature, _, _ = _index_reachability(
        [{"className": "com.example.A", "methods": [_method("<A: void a()>")]}]
    )
    assert by_signature == {}


def test_index_reachability_indexes_reaching_lambda_bodies_by_class():
    _, lambda_by_class, _ = _index_reachability(
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
        ]
    )
    assert lambda_by_class == {"com.example.A": (True, True)}


def test_index_reachability_collects_activity_classes():
    _, _, activity_classes = _index_reachability(
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
        ]
    )
    assert activity_classes == {"com.example.CryptoActivity"}


def test_index_reachability_skips_malformed_entries():
    """A single odd entry is producer noise and must not cost the whole app."""
    by_signature, _, _ = _index_reachability(
        [
            "not-an-object",
            {"className": "com.example.A", "methods": "not-a-list"},
            {"className": "com.example.A", "methods": [None, 7]},
            {
                "className": "com.example.A",
                "methods": [_method("<A: void a()>", reaches=True)],
            },
        ]
    )
    assert by_signature == {"<A: void a()>": (False, True)}


# ---------------------------------------------------------------------------
# derive() preconditions
# ---------------------------------------------------------------------------


def test_derive_requires_completion_sentinel():
    document = _document()
    del document["complete"]
    with pytest.raises(DerivationError, match="complete"):
        derive(document)


def test_derive_refuses_incomplete_document():
    with pytest.raises(DerivationError, match="complete"):
        derive(_document(complete=False))


def test_derive_requires_package():
    with pytest.raises(DerivationError, match="package"):
        derive(_document(package=None))


def test_derive_refuses_non_dict_components():
    with pytest.raises(DerivationError, match="components"):
        derive(_document(components=["activities"]))


def test_derive_refuses_non_list_windows():
    with pytest.raises(DerivationError, match="windows"):
        derive(_document(windows={"0": {}}))


def test_derive_refuses_non_dict_document():
    with pytest.raises(DerivationError):
        derive(["not", "a", "document"])


def test_derive_treats_absent_sections_as_empty():
    artifact = derive({"complete": True, "package": "com.example"})
    assert artifact["formatVersion"] == 1
    assert artifact["package"] == "com.example"
    assert artifact["mainActivity"] is None


def test_derive_records_supplied_provenance():
    artifact = derive(
        _document(), source_file="com.example_1.apk.json", source_digest="sha256:ab12"
    )
    assert artifact["source"] == {
        "digest": "sha256:ab12",
        "file": "com.example_1.apk.json",
        "generator": "aperv-derive/1",
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
        source_digest=digest_of(cryptoapp_bytes),
    )


def test_derive_cryptoapp_ground_truth(cryptoapp):
    """
    The whole projection against the fixture the jar's own suite parses.

    `CryptographyActivity` is in the set through the D8 recovery: the exact join
    drops its `$$ExternalSyntheticLambda0` wrapper handler and the reaching
    `lambda$setupExecuteButton$0` body restores it — the same three flagged widgets
    the jar asserts when it parses this fixture raw.
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

    main_edges = cryptoapp["wtg"]["br.unb.cic.cryptoapp.MainActivity"]
    targets = {edge["target"] for edge in main_edges}
    assert "br.unb.cic.cryptoapp.cipher.CipherActivity" in targets
    assert "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity" in targets

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
    assert cryptoapp["stats"]["recovered"] == 1


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
    give it a subject.
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
    artifact = derive(
        _document(
            components={
                "activities": [component],
                "receivers": [component],
                "services": [component],
                "providers": [{**component, "authorities": "a"}],
            }
        )
    )

    assert artifact["components"]["receivers"][0]["hasTargetMethods"] is True
    assert sorted(set(_target_keys(artifact))) == [
        "artifact.components.receivers[0].hasTargetMethods",
        "artifact.components.services[0].hasTargetMethods",
    ]
    for section in ("reachability", "windows", "transitions", "listeners"):
        assert section not in artifact


def test_no_target_keys_on_the_cryptoapp_projection(cryptoapp):
    assert _target_keys(cryptoapp) == []
    for section in ("reachability", "windows", "transitions", "listeners"):
        assert section not in cryptoapp


def test_provenance_digest_matches_the_input(cryptoapp, cryptoapp_bytes):
    expected = hashlib.sha256(cryptoapp_bytes).hexdigest()
    assert cryptoapp["source"]["digest"] == f"sha256:{expected}"
    assert cryptoapp["source"]["file"] == "cryptoapp.apk.json"
    assert cryptoapp["source"]["generator"] == "aperv-derive/1"


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
        "serialize_canonical, digest_of;"
        "raw = open(sys.argv[2], 'rb').read();"
        "a = derive(json.loads(raw), source_file='cryptoapp.apk.json', "
        "source_digest=digest_of(raw));"
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
            source_digest=digest_of(cryptoapp_bytes),
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
