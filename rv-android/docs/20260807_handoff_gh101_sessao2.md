# Session handoff — continue gh101, JCA specification conformance (session 2)

> Paste this whole file as the first message of the new session.

---

## 0. Who you are and where you are

You are Claude Code in the RVSEC / RV-Android research codebase (PhD work of Pedro
Costa, `phtcosta@gmail.com`). Primary working directory:

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

Git branch **`modules`**. Tip when this file was written: `1217d6ff`.

**`rv-android` is a subdirectory of the `rvsec` git repository, not a separate
repo.** One `git commit` covers both sides. This matters: the freeze check runs
`git -C $RVSEC_HOME diff` over `rvsec/...` paths and works because it is the same
repository.

`$WS` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`.
`RVSEC_HOME` is already exported and points at `$WS/rvsec`. **Anything outside
`rv-android` must be written with an absolute path** — standing user instruction,
for code, docs and prose alike.

Another session implements the sibling change `gh100-weaver-emission-fidelity` on
this same branch. Do not rebase, force-push or reorder. Stage only your own paths.
§8 covers the one real coupling.

---

## 1. What this session must finish

Implement `openspec/changes/gh101-jca-spec-conformance/` — GitHub issue
[#101](https://github.com/PAMunb/rvsec/issues/101). **Progress: 21 of 51 tasks.**
Groups 1, 2 and most of 3 are done and committed. What remains:

- **First**: fold a settled decision into the artefacts (§3). Do this before
  writing more code.
- Then task 3.4, the new group it depends on, and groups 4 to 9.

---

## 2. Non-negotiable working rules

Read `CLAUDE.md` at the repo root and at `$WS/rvsec/CLAUDE.md` first, then
`docs/WORKFLOW.md`.

1. **Follow the OpenSpec workflow rigorously.** Anything under
   `openspec/changes/gh101-*/` goes through the **skills** invoked with the
   `Skill` tool: `openspec-apply-change`, `openspec-update-change`,
   `openspec-verify-change`, `openspec-sync-specs`, `openspec-archive-change`.
   **Never** hand-write or hand-edit an OpenSpec artefact outside a skill that
   told you to. The `.mop`, Java and Python edits are normal work — the rule is
   about the artefacts.
2. **The `jca` set is FROZEN** at commit `7e7acb69` (decision D-S0). Not one byte
   of `$MOP/jca`, not one byte of
   `$CORE/jca/util/CipherTransformationUtil.java`. Every correction lands in
   `jca_android` alone. You will read the same defective line twice and must fix
   only one copy; the freeze check exists to catch the urge.
3. **Do NOT touch the MetaCrySL tree** (`$WS/MetaCrySL`). It belongs to another
   session. `$WS/MetaCrySL/generated/api30/` (33 `.cryptsl`) is **read-only
   input**.
4. **NEVER start, stop or manage Android emulators.** No exceptions. Permanent.
5. **Never add `Co-Authored-By`** or any co-author trailer.
6. **Language**: code, comments, commit messages, issues and OpenSpec artefacts in
   **English**; prose to the user in **Brazilian Portuguese with correct
   accentuation**.
7. **P1–P4** (`CLAUDE.md`): simplicity; narrative docs that explain *why*; no
   backward compatibility; current-state comments only.
8. **Terminology**: "MOP" = *monitored operations*, never "security operations".
9. **Read-only**: `$WS/ase-journal/dataset/results`, `$WS/rvsec-dataset`,
   `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/`. Do **not** run
   `uv run` from inside `$WS/rvsec-dataset` — it rebuilds that project's `.venv`.
   Use plain `python3` for probes outside `rv-android`.
10. Use the session scratchpad for temporary files, never `/tmp` directly.
11. **Commits**: `refs #101` during work, `closes #101` only in the final one.
12. Ask before running anything heavy; a campaign has been occupying this machine.

---

## 3. DO THIS FIRST — the artefacts owe one decision

The user decided (2026-08-07) to **repair all sixteen remaining all-fail events**,
not only the two the change originally named. See §5 for the evidence. The
artefacts do not yet reflect it.

Invoke `openspec-update-change` for `gh101-jca-spec-conformance` and fold in:

- **A new task group** for the sixteen, in eight specifications:
  `IvParameterSpecSpec.c3`/`c4`, `KeyPairGeneratorSpec.initError`,
  `MessageDigestSpec.reset`, `PBEKeySpecSpec.f1`/`f2`/`err1`/`err2`/`err3`,
  `PBEParameterSpecSpec.c3`, `SecretKeySpecSpec.c3`/`c4`,
  `SecureRandomSpec.c3`/`g4`/`setSeed3`, `SignatureSpec.g3`. Place it after
  Group 3 and renumber, or add it as a Group 3b — your call, but keep the linear
  shape. Each task should carry the events it closes so completion is arithmetic.
- **INV-INS-110 needs no carve-out** — repairing all sixteen makes it true as
  written. Say so; do not weaken the invariant.
- `proposal.md` and `design.md` should record that the two named events were the
  visible tip of an eighteen-event pattern, and what it is worth in the published
  dataset (the table in §5).
- Note in `design.md` that `PBEKeySpecSpec.f1`/`f2` also carry the binding defect
  (no `returning` clause, empty parameter slice), so they need both halves, like
  the two already repaired.

Then run `openspec validate gh101-jca-spec-conformance --type change` and commit
the artefact change on its own before writing code.

---

## 4. What is already done, and what it established

### Group 1 — the records (commit `b83cb91d`)

Everything downstream is checked by counting rather than by reading. Committed
under `data/gh101/`, each with the script that produced it in `scripts/`:

| file | what it holds |
|---|---|
| `predicate_inventory_{jca,jca_android}.csv` | 85 `ExecutionContext` sites each — 49 writes, 27 reads, 9 removals |
| `predicate_edges.csv` | one row per CrySL predicate clause with whether the set implements it |
| `edge_counts_per_file.csv` | per `.mop`, how many edges it must close |
| `conformance_record.csv` | 23 verdicts, none blank (INV-INS-113) |
| `divergence_record.csv` | every hunk by which the sets differ, with its reason |
| `README.md` | the narrative, including a precise reconciliation with the investigation's counts |
| `frozen_set_debt.md` | what `jca` knowingly retains |
| `algorithm_naming.md` | the case/alias gap, measured from both ends |

Facts established, all reproducible:

- The two inventories are identical in every column but `line`. The task text
  expected "modulo the directory prefix"; the `file` column carries no prefix, so
  the real difference is line numbering. The substantive claim holds exactly: the
  derivation did not touch the predicate graph.
- 20 of 23 `Property` constants do not function as an edge (3 live, 18 written and
  never read, 1 read and never written, 1 only removed).
- 84 CrySL clauses over the 22 rules with a `.mop` counterpart: 47 present, 37
  absent, and the 37 partition **exactly** as the investigation's §4.5 —
  23 translation defect / 11 capability absent / 2 deliberate omission / 1
  inexpressible.
- **36 edges to close**: 5 in group 3, 20 in group 4, 11 in group 5.
- The conformance record's 10 `anchored` verdicts are exactly the ten files the
  tier map lists as adapted. No file is `contradicted`.

### Group 2 — the derived Cipher tables (commit `2a36defa`)

- New `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil`, **beside** the
  frozen class, not in a `jca_android` package. The user chose this form.
- `jca_android/CipherSpec.mop` changed **one line**: it reaches the utility
  through a *static wildcard import* and calls bare `isValid(...)`, so all five
  call sites are byte-identical.
- Three decisions that are not transcription, each with a corpus call site behind
  it: comparison folds **case and hyphens**; an unspecified component is
  unconstrained; a pair the rule places no padding implication on admits any
  padding.
- 13 JUnit tests, all passing.

### Group 3 — the two hot specifications (commit `1217d6ff`)

Done: 3.1, 3.2, 3.3, 3.5, 3.6. **3.4 is open** and is the bridge to the new group.

- `TrustManagerFactorySpec.gtm1` carried **four** defects, not the three
  enumerated. The fourth is the binding: it named `k` where the specification
  parameter is `mf`, and the generated monitor proves the consequence — it
  dispatched `gtm1` on `TrustManagerFactorySpec__Map`, the empty parameter slice,
  where the correct sibling dispatches `gkm1` on `KeyManagerFactorySpec_k_Map`.
- Both hot events entered their automaton with the `unsafeAlg` shape
  `KeyManagerFactorySpec` already uses. Verified in the generated monitor: both
  rows moved from `{3,3,3,3}` to `{0,3,3,3}`.
- Four predicate-graph edges closed. The three `SSLContextSpec` REQUIRES are read
  **in the event body, not as a `condition(...)` guard** — a failing guard takes
  no transition, which would silently remove `init` from the automaton.
- `TrustManagerFactorySpec.init` binds its single argument as `Object` and
  discriminates by type, because CrySL states two events there (`i1: init(keyStore)`,
  `i2: init(params)`) that the translation fused into one disjunctive pointcut.

---

## 5. The finding that reopened scope, and the user's decision

Writing task 3.4's check (`scripts/gh101_monitor_transition_check.py`) showed the
frozen set has **18** events with an all-fail transition row, not 2. Sixteen
remain in the derived set, in eight specifications, all one shape: an
error-reporting event with a negated or violating guard, which reports in its body
and never entered the automaton. Most of them **do** bind the monitored object, so
each firing produces a real report *and* a sequence violation on top of it.

Recomputed from `$WS/ase-journal/dataset/results/errors.csv` — note the error type
lives in `unique_msg`, field 4 of the `:::`-separated composite, **not** in
`message`:

| origin | `InvalidSequenceOfMethodCalls` events | of that category | of all 97,018 |
|---|---:|---:|---:|
| the 8 specifications carrying the sixteen | 23,292 | 32.9% | 24.0% |
| the 2 repaired in Group 3 | 26,525 | 37.5% | 27.3% |
| **together** | **49,817** | **70.4%** | **51.3%** |

**70% of every `InvalidSequenceOfMethodCalls` in the published dataset comes from
events that should not be judging sequence at all.** This is the concrete
mechanism behind the co-emission the investigation measured.

**The user's decision: repair all sixteen in the derived set, as a new group.**
Use the same `unsafeAlg` idiom. Do not weaken INV-INS-110.

One caution learned the hard way: the first version of the check matched only
`AbstractAtomicMonitor` and silently skipped every specification whose events land
in the empty parameter slice — which is exactly where the defective events were.
It now matches `Abstract(Atomic|Synchronized)Monitor` and both forms of the fail
computation (`nextstate == N` and `Prop_1_state == N`). If you extend it, verify
against the frozen set, where the answer is known to be 18.

---

## 6. Remaining work

- [ ] **Artefact update** (§3), first, via `openspec-update-change`.
- [ ] **New group**: the sixteen events, eight `.mop` files, `jca_android` only.
      Each hunk into the divergence record as it lands.
- [ ] **3.4**: rerun `gh101_monitor_transition_check.py` over a freshly generated
      derived monitor; it must report none. That closes both 3.4 and the new group.
- [ ] **Group 4** — predicate graph, `.mop` only. **20 edges over ten files**:
      `KeyPairSpec` 4, `CipherSpec` 4, `MacSpec` 3, `KeyStoreSpec` 2,
      `SignatureSpec` 2, and one each in `KeyGeneratorSpec`,
      `KeyManagerFactorySpec`, `KeyPairGeneratorSpec`, `SecretKeySpec`,
      `SecretKeySpecSpec`. Includes the wrong constant at `KeyPairSpec.mop:38`.
      Also record the 2 deliberate omissions and the 1 inexpressible edge.
- [ ] **Group 5** — new vocabulary. **9** new `Property` constants closing **11**
      edges (`generatedCipher` carries three, `generatedManagerFactoryParameters`
      two): `preparedAlg`, `preparedOAEP`, `generatedCipher`, `preparedRSA`,
      `preparedDSA`, `preparedEC`, `generatedManagerFactoryParameters`,
      `cipheredInputStream`, `cipheredOutputStream`. Each lands **with its
      reader**. The enum goes 23 → 32.
- [ ] **Group 6** — `jca_android` as a first-class `specification_set` value in
      `modules/rv-experiment/src/rv_experiment/config.py` (`:424` values, `:671`
      mapping). The only Python in `rv-android`.
- [ ] **Group 7** — the write/read guard derived from the inventory, the
      deliberate-omission list as versioned data, and the four record entries.
- [ ] **Group 8** — empirical verification, blocked on gh100 task 5.3. If it has
      not landed, **record as blocked citing the artefact; do not substitute a
      weaker check**.
- [ ] **Group 9** — verification, lint, `/rv-verify rv-experiment`,
      `/rv-code-reviewer`, `/rv-docs-sync`.

Then: tick issue #101's acceptance criteria one by one **before** closing, any
criterion not literally met getting an inline note
(`- [x] ~~criterion~~ — superseded by …`), never a silent tick and never a blank
box. Sync the delta spec explicitly with `openspec-sync-specs` **before**
archiving, then `openspec archive gh101-jca-spec-conformance --skip-specs`. Final
commit uses `closes #101`.

---

## 7. Commands

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
MOP=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources
CORE=$RVSEC_HOME/rvsec/rvsec-core/src/main/java/br/unb/cic/mop

# where the change stands
openspec status --change gh101-jca-spec-conformance --json
openspec instructions apply --change gh101-jca-spec-conformance --json
openspec validate gh101-jca-spec-conformance --type change

# INV-INS-109 (a) — the freeze. MUST be empty, at the end of every group.
git -C $RVSEC_HOME diff 7e7acb69 -- \
  rvsec/rvsec-mop/src/main/resources/jca \
  rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java

# INV-INS-109 (b) — every hunk of the set diff needs an entry
uv run python scripts/gh101_divergence_record.py --check
uv run python scripts/gh101_divergence_record.py --refresh   # skeleton for new hunks

# the four gates together
uv run pytest tests/parity/test_gh101_specset_gates.py --import-mode=importlib -o "addopts=" -q

# regenerate the records
uv run python scripts/gh101_predicate_inventory.py $MOP/jca_android -o data/gh101/predicate_inventory_jca_android.csv
uv run python scripts/gh101_predicate_edges.py --inventory data/gh101/predicate_inventory_jca_android.csv \
    --edges data/gh101/predicate_edges.csv --counts data/gh101/edge_counts_per_file.csv
uv run python scripts/gh101_conformance_check.py -o data/gh101/conformance_record.csv

# generate monitors from a set and check INV-INS-110  (S = your scratchpad)
rm -rf $S/gen && mkdir -p $S/gen/specs $S/gen/out
cp $MOP/jca_android/*.mop $S/gen/specs/
$RVSEC_HOME/javamop/bin/javamop -d $S/gen/out -merge $S/gen/specs/*.mop
mv $S/gen/specs/*.rvm $S/gen/out/          # javamop leaves .rvm in the SOURCE dir
$RVSEC_HOME/rv-monitor/bin/rv-monitor -d $S/gen/out -merge $S/gen/out/*.rvm
uv run python scripts/gh101_monitor_transition_check.py $S/gen/out/MultiSpec_1RuntimeMonitor.java

# Java side — one module, no install, safe beside the other session
cd $RVSEC_HOME && mvn -o -pl rvsec/rvsec-core test
```

Always copy the `.mop` to the scratchpad before running javamop: it writes `.rvm`
into the **source** directory.

---

## 8. Coordination with the parallel gh100 session

| concern | status |
|---|---|
| file overlap | none — you own `$MOP/jca_android` and `rvsec-core`; they own `$DEXLIB2/*` and two Python modules |
| dependency | one, yours on them: your group 8 waits on their task 5.3 |
| Maven | shared reactor and `~/.m2`. Do not run `mvn install` while they build. `mvn -o -pl rvsec/rvsec-core test` is scoped and safe. Check `pgrep -af mvn` first |
| **descriptor drift — ACT ON THIS** | their tasks 4.2/4.3/6.2 run V2 against **`jca_android`**, the set you are editing. Their 4.3 pins the descriptor and monitor sources, and **4.2/4.3 have not run yet** (their progress: 16/45, group 4 is a barrier). Your edits are safe only while they land *before* their red run. Their own task 4.3 names issue #101 as the risk. Tell the user to relay this, or message the session if it is running (`ListAgents`) |
| spec sync | you MODIFY *Specification Set Support (FR03)*; they MODIFY a different requirement, so order does not matter. Before syncing, `grep -ln "<Requirement title>" openspec/changes/*/specs/*/spec.md` to confirm nothing else claims yours |
| invariants | INV-INS-109 to 113 are yours, 104 to 108 theirs |
| git | same branch and same repository, `refs #101`, stage only your paths, no rebase |

---

## 9. Decisions already settled — do not re-open

- **D-S0**: `jca` frozen, corrections in the derived set alone. Supersedes D1.
- **D-S3 as revised**: the derived Cipher tables live in
  `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil`, a sibling class in
  the existing package. The earlier `jca_android` package form is dead, and so is
  the even earlier "parameterise, do not duplicate".
- **D-S7**: freeze check plus divergence record replace the parity check.
- **D-S8**: `jca_android` becomes a first-class `specification_set` value.
- D3 (both sides on the same CrySL release), D5 (no conditioning by API level),
  D6 (uniform anchoring).
- **The spelling variants stay.** The user decided the translation-added spellings
  (`HMAC-SHA256`, `HMAC/SHA256`, `HMACSHA256`, `SHA256`) are kept and declared as
  translation artefacts, not removed.
- **Case/alias normalisation is repaired in the Cipher utility only.** The nine
  call sites in the other specifications are recorded in
  `data/gh101/algorithm_naming.md`, not fixed. The proper fix — a helper that
  resolves the observed name to its canonical form through
  `Security.getProviders()` inside the emulator — is recorded there as a design
  and is deliberately not built.
- **Repair all sixteen remaining all-fail events** (§5). New decision, 2026-08-07.

---

## 10. Open questions that are the user's

- The two rule gaps the corpus sweep surfaced and the tier map does not record:
  `X509` for `(Trust|Key)ManagerFactory` (6 apps) and `RSA/NONE/NoPadding` for
  `Cipher`. Both are absent from every list in the chain, including upstream CrySL
  1.5.2, because neither CrySL nor MetaCrySL models provider **aliases**. The user
  was asked whether to record only, record and open issues, or repair, and chose
  none of them yet — recording is done in `data/gh101/algorithm_naming.md`; ask
  again if issues should be opened.
- Whether the deliberate upstream deviations in the `Cipher` rule (`NoPadding` and
  `PKCS1Padding` for RSA) are corrected or recorded. Transcribed as authored for
  now, which is what D-S4 requires.
- Whether the two deliberate predicate-graph omissions stay omissions. The
  substitution they rest on is half-built: `isInAcceptingState` is never read from
  any `.mop`, so the mechanism is inert at runtime.
- The board card for #101 is in "No Status" and cannot be moved from here — the
  `gh` token lacks the `project` scope. Only the user can run
  `gh auth refresh -s project`.

---

## 11. Learnings worth carrying

- **The handoff's enumerations were floors, not ceilings.** `gtm1` had four
  defects where three were listed; the all-fail pattern had eighteen events where
  two were listed. Verify counts against the artefact rather than the prose, and
  when a check is written, run it against the frozen set first — its answer is
  the baseline that tells you whether the check itself is complete.
- **A check that passes too easily is a bug in the check.** The transition checker
  passed the frozen set until it was taught the second monitor kind.
- **Derive, do not transcribe.** Every table in `data/gh101/` came out of a script
  reading the rules and the specifications. That is what let the reconciliation
  with the investigation be exact rather than approximate.
- **The user asked for less orchestration, not more.** The groups are linear on
  purpose. Do not fan them out.
- **Ask when the scope changes, not after.** The sixteen-event finding was brought
  to the user with the measured cost before any of it was repaired, and the answer
  changed the plan.
