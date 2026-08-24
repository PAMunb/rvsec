# 10.1 — freeze and divergence

What this records: the run of task 10.1 on 2026-08-24 at `d631f228`, after Group 11 (D-15) landed.
Two questions are answered here. Did anything this change did move a frozen artefact? And is every
hunk that does move still recorded as a divergence? The answer to the first is no, to the second yes.

## Gates

| suite | result |
|---|---|
| `test_gh101_specset_gates.py`, `test_gh104_specset_gates.py`, `test_gh104_structural_gates.py`, `test_gh104_baseline.py`, `test_gh104_unique_msg_built_once.py` | **29 passed**, 84.6 s |
| the four-suite stamp (gh101 + gh104 specset + gh104 structural + gh105 predicate) | **97 passed**, 83.9 s |

Both were run with `--import-mode=importlib -o "addopts="`, the CI contract.

## Freeze

The freeze is on the specification *sources*. Each check names the base it is read against, because
the two bases are not interchangeable — see the note on `7e7acb69` below.

| what | base | result |
|---|---|---|
| `rvsec-mop/src/main/resources/jca/` and `rvsec-core/.../jca/util/CipherTransformationUtil.java` | `7e7acb69` (`jca` freeze base) | `git diff` empty |
| `rvsec-core/.../jca/util/AndroidCipherTransformationUtil.java` | `a3e6a165` (`pre-rename-head`) | `git diff` empty |
| `jca_android_bug_predicate/` — the archived derived set | `a3e6a165:.../jca_android` | **23/23 blobs identical by object id** |
| `MetaCrySL/generated/api30` | working tree | `git status --short` clean |

D-15 made `jca_android/CipherSpec.mop:36` **call** `CipherTransformationUtil` (`import static`,
task 11.3). The freeze forbids editing that class, not calling it, and the byte-identity check above
is what says the call cost it nothing.

### Why the archival is read blob-by-blob and not by `--find-renames`

`git diff --find-renames a3e6a165 -- jca_android jca_android_bug_predicate` reports 23 `M` and 25 `A`,
not 23 `R100`. That is rename detection working correctly, not a broken freeze: the successor set
occupies the **same path** the archived set left, so git pairs each old file with the new file of the
same name and calls it a modification, and the archived copies read as additions. The claim task 10.1
actually makes — zero content hunks on the renamed side — is therefore checked directly, by comparing
git object ids: for all 23 files, `a3e6a165:…/jca_android/<f>` and `HEAD:…/jca_android_bug_predicate/<f>`
are the same blob. Identical object ids are a stronger statement than `R100`, which tolerates
similarity below 100 only by threshold.

The 2 remaining additions under `jca_android` are the successor set's own new files; its other 23 are
the modifications this change and gh105 made to it, all of them recorded below.

### Why not `7e7acb69` for the rename half

`7e7acb69` predates gh101's edits to `jca_android/` (19 files, 720 insertions, 122 deletions on
2026-08-18). A rename diff against it can never show zero content hunks, whatever this change does.
It stays the base for the `jca` and `CipherTransformationUtil` half only.

## Divergence

| instrument | result |
|---|---|
| `gh104_divergence_record.py --check` | **285 hunks, all recorded**; 16 narrative entries |
| `gh104_mop_lint.py jca_android` | `ok: true`, no findings |
| `gh104_message_gate.py jca_android` | `ok: true`, empty counts (no self-contradicting envelope) |

The 14 divergence kinds in play: `allow-list`, `api30-omits`, `automaton`, `behavioural`,
`cipher-import`, `junction`, `message`, `oracle-wart`, `placement`, `platform-value`,
`predicate-removal`, `predicate-store`, `set-archived`, `spelling-variant`. The last four of those
first appear with D-15 and gh105; every hunk they cover carries a row.
