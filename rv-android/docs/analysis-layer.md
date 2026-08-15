# The campaign analysis layer

`aperv_tool.analysis` is an offline, read-only library over artifacts a campaign has already
produced. It runs on recorded bytes: no device, no emulator, no `adb`, nothing on the collection
path. Its purpose is that when the final campaign's output lands, the analysis it needs already
exists, already runs, and has already been checked against a campaign whose answers are known.

Two rules organise everything below, and neither is a style preference.

**It is generic.** No module, function, column or flag names a research question. The library
computes estimates and does not know what they are for; the coupling between a question and the
code that answers it lives in exactly one directory, `analysis/callers/`, and mostly in one file,
`rq_map.toml`. A test greps every other module to keep that true. The failure this prevents is
silent: a column named for a question, a branch that behaves one way "for the primary", and within
a few edits the library has stopped being reusable and has become one campaign's script with a
package around it.

**Every number leaves with its envelope.** A bare float cannot be emitted. An estimate travels
with what it estimated, how many units it covered, the two cardinalities of its basis, the
conventions that produced it and the list of everything left out — or it does not leave at all.
A fraction whose denominator nobody wrote down is unreadable, and a table of results that does not
carry its own attrition sends the reader to a log that is not beside it.

---

## The layers

The library is layered so that a change in the log format touches one layer. Reading downward, each
layer consumes only the one above it.

| Layer | Modules | What it establishes |
|---|---|---|
| **0 — run model and corpus** | `run_identity`, `runspec`, `tasks_record`, `loader`, `liveness`, `gates`, `corpus`, `clones` | Which runs exist, which of them count, and what the denominator is |
| **1 — outcome builders** | `outcomes`, `screen_visits` | Turning streams into labelled per-unit values under declared conventions |
| **2 — estimators** | `estimators/` — `paired_binary`, `paired_continuous`, `count_glm`, `multiarm`, `resampling`, `variance`, `multiplicity`, `decision`, `capacity` | One estimator per module; every function returns an `Envelope` |
| **3 — stream readers** | `step_bundle`, `state_coverage_join`, `violations`, `monitored_ops`, `static_artifact`, `baseline_ape`, `baseline_droidbot`, plus the three shipped readers `trace_ndjson`, `coverage_dump`, `clock_logcat_join` | Parsing the recorded artifacts |
| **4 — reporting** | `envelope`, `provenance`, `emit` | The result data structure, its re-derivability, and the files it becomes |
| **callers** | `callers/` + `rq_map.toml` | The only place a research-question identifier appears |

Layer 0 is where most of the judgement lives, and three of its decisions are worth stating outright.

**The identity is the run, and `task_id` is not.** A resume appends a new record with a fresh UUID
beside the old one, so the decisive campaign carries 1486 records for 1458 runs. Everything is keyed
on `(apk, arm, replica, timeout)`, and the 28 extra records are superseded attempts rather than
extra runs. `run_identity` owns that key — the filename regex, the arm table lookup, and the frame
columns — in one place, because two copies of a *parser* that drift disagree about which runs exist
and nothing reports the disagreement.

**`COMPLETED` is not "it worked".** The platform observes a process terminate; it does not observe
that the run explored. One run of the decisive campaign was written `COMPLETED` after 65 s of an
1800 s budget with an 864-byte trace, zero step lines and every coverage counter at zero — the
explorer had died in `setActivityController` with a `DeadObjectException`. Read as an outcome that
run is a legitimate zero, and it is not one. `liveness` is the sole owner of the per-run verdict, so
an excluded run is excluded once, for one reason, printed once.

**A gate that cannot be evidenced reports `not-run`.** Not a pass. `not-run` is a third status and it
is a *result*, which matters because the alternative — treating absent evidence as satisfied — is
how a campaign passes its own validity checks by not having run them.

---

## The freeze-item rule

A **freeze item** is a knob the pre-registration decides and the code must not. The library supplies
no default for any of them, and a function reached without one raises `FreezeItemUnset` naming what
is missing rather than proceeding.

The current items are the improvement margin, which `aperv` variant is primary, the corpus, the GLM
specification and its reference level, the replica-aggregation rule, the dedup convention, the
multiplicity strategy, and the application-size offset.

The rule is not defensive programming. Each of these changes the answer, and each has a value that
looks obviously right until someone checks: the sibling study's effect does not survive the
pure-size-offset specification (IRR 1.076 → 0.979, not significant), and the three replica rules
give 0, 1 and 2 discordant pairs on the same data. Code that picked one would be making the
author's decision and recording it nowhere.

The rule crosses the configuration boundary intact. TOML has no null, so a knob whose *decided*
value is "none" — no offset, no reference level — is written as the empty string and read back
through `Entry.optional`; **omitting the key is an error, not a way of saying none.** An entry whose
knobs are genuinely still open is written with them absent, on purpose: it loads, it reports as
wired, and it raises if anyone runs it. That is the correct behaviour for a question whose
pre-registration is unfinished, and it is pinned by a test so that a later pass does not "fix" it by
supplying something plausible.

---

## The two fixture classes

They answer different questions and are never mixed.

**FIXTURE-REAL** is the recorded decisive campaign (`experimento-comp162/`, roughly 40 GB, not in
this repository), pinned file by file with a sha256 in
`modules/aperv-tool/tests/fixtures/cmp162_manifest.json`, plus a hashed sample of the sibling
study's raw corpus. Tests over it prove **parity**: that the library reproduces what the campaign's
own scripts produced. There are three such tests and each says so in its docstring.

A test that reads either tree does one of exactly two things and never a third: it runs against the
pinned bytes, or it skips with a reason naming what is absent. It must never quietly pass because
the input was not there — a green suite that measured nothing is worse than a red one, because it
looks like evidence.

**FIXTURE-SYNTH** is hand-built data covering the degenerate cases no recorded campaign happens to
contain: all-zero paired differences, a saturated binary outcome where the intra-class correlation
degenerates, zero discordant pairs, and separation in the GLM. Tests over it prove **correctness**.

The distinction matters because parity and correctness are not the same claim and one is regularly
mistaken for the other. Reproducing a campaign's number proves the pipeline is unchanged. It proves
nothing whatever about whether the estimator is right — if the original was wrong, parity reproduces
the error exactly.

**cmp162 is a fixture, not a corpus.** No number computed on it answers a research question.

---

## Running the end-to-end smoke

Two tests exercise the whole chain with no device. They are ordinary tests and need no flag; they
skip, naming what is missing, when the recorded campaign is not on the machine.

```bash
# from the repository root
.venv/bin/python -m pytest modules/aperv-tool/tests/test_smoke_two_apps.py \
    modules/aperv-tool/tests/test_corrupted_fixture.py \
    --import-mode=importlib -o "addopts=" -q
```

`-o "addopts="` is not optional: without it the module's own `--cov=src` fires and changes what
collection does.

`test_smoke_two_apps` runs loader → gates → corpus → a catalogue-driven caller → emit over the two
applications the manifest names, and asserts every envelope carries its five parts. It asserts no
*result*: with two applications the estimator is below its own power floor by construction, and what
the test pins is that the envelope **says so**.

`test_corrupted_fixture` copies those two applications into a temporary directory, breaks three
things in the copy — a trace truncated to 864 bytes, a `summary.csv` removed, a `tasks.json` record
stripped of its application name — and asserts each one arrives in the envelope by identity and
reason, with the denominator shrinking visibly rather than quietly. All three of those defects
degrade silently by default: a truncated trace's zero reads as a genuine zero, a missing payload
becomes NaN and then `False`, and a record with no identity simply is not there. Each makes the
analysis look complete and moves the answer.

The campaign tree is never written to. The corrupted fixture copies first and then re-hashes every
pinned file to prove it.

The smoke earns its place. On its first run it caught two defects that every unit test had missed,
both of the same kind: `gates` and `liveness` read the identity column as `repetition` and the task
state as `task_state`, while the loader writes `rep` and `state`. The first raised on any real
frame; the second did not raise at all — every run read as a null state, failed the first criterion,
and the entire campaign came back inadmissible with a perfectly plausible reason. Unit tests on both
sides of a seam cannot see the seam.

---

## The activity-visit unit

Every question about guidance follow-through, form completion, or what a decision led to is a
question about a *screen*, not about a step. The step stream carries no such structure, so
`screen_visits` rebuilds it. Which grain to rebuild it at was decided by measurement, on 60 runs of
the decisive campaign totalling 15,702 steps.

The trace offers two candidates. `StepRow.state_key` is the agent's own abstract state and looks
like the finer, better answer. It is not a screen:

- median state-visit length **1** step, mean 1.66, and **75.5 %** of them are one step long;
- **84.6 %** of state-visit closings are transitions to another state *of the same Activity*;
- median **156.5** state-visits per run.

A combobox opening, a dialog, a menu, the soft keyboard appearing — each is another state of the
same Activity. The state grain is a step-level unit wearing a screen's name.

The Activity grain, on the same runs, sits in the middle of its own distribution: median **14.5**
visits per run, visit length mean 11.0 and median 2, p90 32, and **2.68** distinct state keys inside
the average visit. **37.8 %** of activity-visits are a single step, against 75.5 % at the state
grain.

The Activity grain also has a property the state grain cannot have: it is the only one comparable
**across** runs. A state key embeds a JVM identity hash and is run-local, so three replicas of one
application share **zero** state keys and **100 %** of their activities. A cross-run comparison at
state grain compares nothing.

So the activity-visit is the unit, and the state sequence is kept inside it as a descriptive
`state_trail`. Nothing is discarded — the combobox sub-trajectory stays legible as three spans of
one visit instead of becoming three visits.

**Recorded limitations**, both deliberate. Navigation between Fragments inside one Activity is
invisible at this grain; the longest measured visit is 294 steps. Splitting a visit on `MODEL_BACK`
or `MODEL_MENU` would address it and is not built, because the split would have to be decided
against a concrete question and no question has asked for it. And the trace records no typing, so
the form-fill proxy is the `EditText` click: 954 of them across the 60 runs, 382 of which changed
the state key within the same Activity.

---

## Boundaries

- **Off the collection path.** No module under `aperv_tool.analysis` is reachable from
  `tools/aperv/tool.py`, and a test walks the import graph to prove it.
- **`*.mop.json` is never opened.** It is the artifact the collection path derives; reading it here
  would couple the analysis to a file the analysis is supposed to be independent of.
- **No literal jar digest anywhere under `modules/`.** A campaign's declarations are supplied as
  data and compared against; they are never baked in.
- **The three shipped readers keep their existing behaviour**, and their existing test module is
  byte-untouched, so "the existing suite still passes unmodified" stays checkable with `git diff`
  rather than argued.
- **No research-question identifier outside `callers/`.**
