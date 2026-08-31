"""`TaskResult.write_errors` survives serialization (INV-CORE-61, task 5.5).

The field counted rows a task lost while its results were being written and then
went nowhere: `to_dict()` did not carry it, so the count lived for the length of
the process. Downstream, a task whose violations were lost to a write failure was
indistinguishable from a task that had none — the same silence this whole change
removes, one layer further out.

The type matters as much as the presence. It is `Dict[str, int]`, a per-artefact
loss **count**, consumed as a number by `result_processor`. Serializing it as a
list of messages would carry the fact and destroy the quantity.
"""

from rv_android_core.domain.task import TaskResult, TaskState


class TestWriteErrorsRoundTrip:
    def test_counts_survive_to_dict_and_back(self):
        result = TaskResult(state=TaskState.COMPLETED)
        result.write_errors = {"errors.csv": 3, "results.json": 1}

        restored = TaskResult.from_dict(result.to_dict())

        assert restored.write_errors == {"errors.csv": 3, "results.json": 1}

    def test_the_field_is_serialized_as_a_mapping_of_counts(self):
        """A list of artefact names would round-trip the fact and lose the
        number, which is the only thing INV-PLT-32 asked for."""
        result = TaskResult(state=TaskState.COMPLETED)
        result.write_errors = {"errors.csv": 7}

        payload = result.to_dict()

        assert payload["write_errors"] == {"errors.csv": 7}
        assert isinstance(payload["write_errors"]["errors.csv"], int)

    def test_an_empty_map_round_trips_as_an_empty_map(self):
        """The common case: no loss is not the same fact as no record of loss,
        but both read as `{}` here — the distinction lives in whether the run
        was recording at all, which every run now is."""
        restored = TaskResult.from_dict(TaskResult(state=TaskState.COMPLETED).to_dict())

        assert restored.write_errors == {}

    def test_a_legacy_tasks_json_without_the_key_still_loads(self):
        """Every `tasks.json` written before this change is in this state, and
        the resume protocol reads them. Defaulting to `{}` is the honest
        reading: nothing was recorded because nothing was recording."""
        legacy = {
            "state": "COMPLETED",
            "start_time": None,
            "end_time": None,
            "tool_execution_start": None,
            "execution_time_seconds": 42,
            "error_message": None,
            "logcat_file": "app_1_300_monkey.logcat",
            "trace_file": "app_1_300_monkey.trace",
            "coverage_metrics": {"method_coverage": 10.0},
            "detected_errors_count": 0,
            "state_transitions": [],
        }

        restored = TaskResult.from_dict(legacy)

        assert restored.write_errors == {}
        assert restored.state is TaskState.COMPLETED
        assert restored.execution_time_seconds == 42
