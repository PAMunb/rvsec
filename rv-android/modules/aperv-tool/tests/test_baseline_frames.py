"""The two baseline frames are the `aperv` per-step frame, with declared holes.

Layers 1 and 2 of this library consume a per-step frame. If a baseline produced a
differently shaped one, every builder above would grow a branch per tool, and the
branch would be the place where an absent signal quietly became a zero. So both
parsers emit the same columns the `aperv` reader's `StepRow` defines, in the same
order, and write an explicit null wherever the tool prints no such signal.

The second half of the contract is the unit. A `droidbot` step is one dispatched
event, an `ape` step is a `SATA begin/end` cycle, an `aperv` step is a
`StepRecord`. The three are not the same quantity, so the unit rides every row
and a caller comparing counts has to see it (INV-CAN-20).
"""

from __future__ import annotations

from dataclasses import fields

import pandas as pd
from baseline_runs import trace_of

from aperv_tool.analysis import baseline_ape, baseline_droidbot, tasks_record
from aperv_tool.analysis.trace_ndjson import StepRow

# The columns each tool has no signal for, and therefore leaves null on every row.
APE_NULL_COLUMNS = (
    "t_epoch_ms",
    "activity_has_mop",
    "pick_channel",
    "mop",
    "mop_frontier",
    "wtg",
    "coverage",
    "menu",
    "form",
    "wtg_source",
    "mop_exposure",
    "patched",
    "counterfactual",
    "component",
    "llm",
    "outcome",
    "policy",
)
DROIDBOT_NULL_COLUMNS = APE_NULL_COLUMNS[:-1] + (
    "t_rel_ms",
    "priority",
    "source_state_key",
    "target_state_key",
    "model_activities",
    "model_states",
    "model_edges",
    "model_unvisited_actions",
    "model_visited_actions",
)


def _frames(directory, manifest):
    """One `ape` frame and one `droidbot` frame, both from pinned runs."""
    ape = baseline_ape.parse(
        trace_of(
            directory,
            manifest,
            apk="app.pwhs.universalinstaller_24.apk",
            repetition=1,
            timeout_s=60,
            arm="ape",
        )
    ).step_frame()
    droidbot = baseline_droidbot.parse(
        trace_of(
            directory,
            manifest,
            apk="app.maskan.chat_90.apk",
            repetition=3,
            timeout_s=300,
            arm="droidbot:bfs_naive",
        )
    ).step_frame()
    return ape, droidbot


def test_baseline_frames_match_aperv_shape(
    baseline_sample_dir, baseline_sample_manifest
) -> None:
    """Same columns, same order, nulls where the signal does not exist."""
    ape, droidbot = _frames(baseline_sample_dir, baseline_sample_manifest)

    # The `aperv` block is derived from the reader's record, not copied, so the
    # two cannot drift; and it is a prefix, so a consumer written against the
    # `aperv` frame reads a baseline without knowing it is one.
    aperv_block = tasks_record.IDENTITY_COLUMNS + tuple(
        field.name for field in fields(StepRow)
    )
    assert baseline_ape.APERV_STEP_COLUMNS == aperv_block
    assert baseline_ape.STEP_FRAME_COLUMNS[: len(aperv_block)] == aperv_block

    assert list(ape.columns) == list(baseline_ape.STEP_FRAME_COLUMNS)
    assert list(droidbot.columns) == list(baseline_ape.STEP_FRAME_COLUMNS)

    for column in APE_NULL_COLUMNS:
        assert ape[column].isna().all(), f"ape invented {column}"
    for column in DROIDBOT_NULL_COLUMNS:
        assert droidbot[column].isna().all(), f"droidbot invented {column}"

    # Non-vacuity: a frame of nothing but nulls would pass every assertion above.
    for column in ("step", "activity", "state_key", "action", "decision_source"):
        assert ape[column].notna().all(), f"ape lost {column}"
    for column in ("step", "action", "action_type"):
        assert droidbot[column].notna().all(), f"droidbot lost {column}"
    assert ape["t_rel_ms"].notna().all(), "ape does have a coarse clock"
    assert droidbot["activity"].notna().any(), "some droidbot events name a screen"

    # `state_key` is null exactly on the events dispatched without one — a
    # restart intent or an application kill, which the naive policies print with
    # no `Current state:` line above them either. It is a hole in the stream, not
    # in the parse.
    stateless = droidbot.loc[droidbot["state_key"].isna(), "action_type"]
    assert set(stateless) == {"IntentEvent", "KillAppEvent"}
    assert droidbot["state_key"].notna().sum() == len(droidbot) - len(stateless)

    # The identity block is the one `tasks_record` keys on, so the join to
    # `tasks.json` — the only source of a run's window, since no baseline trace
    # carries an end-of-run summary — is a merge and needs no adapter.
    joined = droidbot.merge(
        tasks_record.load(baseline_sample_dir / "tasks_slice.json")[0],
        on=list(tasks_record.IDENTITY_COLUMNS),
        how="left",
    )
    assert len(joined) == len(droidbot)
    assert joined["state"].eq("COMPLETED").all()
    assert joined["execution_time_s"].notna().all()


def test_step_unit_named(baseline_sample_dir, baseline_sample_manifest) -> None:
    """Every row names the unit it counts in, and the two units differ."""
    ape, droidbot = _frames(baseline_sample_dir, baseline_sample_manifest)

    assert baseline_ape.STEP_UNIT != baseline_droidbot.STEP_UNIT
    assert "ape" in baseline_ape.STEP_UNIT
    assert "droidbot" in baseline_droidbot.STEP_UNIT

    assert (ape["step_unit"] == baseline_ape.STEP_UNIT).all()
    assert (droidbot["step_unit"] == baseline_droidbot.STEP_UNIT).all()
    assert ape["step_unit"].nunique() == 1
    assert droidbot["step_unit"].nunique() == 1

    # The index's provenance travels with the unit: `ape` prints its own, this
    # library counts `droidbot`'s.
    assert not ape["step_index_synthesized"].any()
    assert droidbot["step_index_synthesized"].all()

    # Stacked, the pair is one frame whose row count means nothing on its own.
    # The unit column is what stops that number from being read as one quantity,
    # so it has to survive the concatenation the shared shape invites.
    stacked = pd.concat([ape, droidbot], ignore_index=True)
    assert list(stacked.columns) == list(baseline_ape.STEP_FRAME_COLUMNS)
    assert stacked["step_unit"].nunique() == 2
    assert len(stacked) == len(ape) + len(droidbot)
