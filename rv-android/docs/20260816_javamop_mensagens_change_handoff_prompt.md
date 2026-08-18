# Handoff — plan a single OpenSpec change covering the whole JavaMOP message programme

**Date:** 2026-08-16
**How to use:** paste this entire file as the first message of a new session, opened at
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android`.
**Language:** every deliverable in **English** (code, docstrings, specs, OpenSpec artifacts, commit
messages may be pt-BR to match the repository's history). Notes to the user may be pt-BR — with
correct accentuation.

---

## 0. Your objective, in one paragraph

Read the main documents and the references they depend on, then **plan and create ONE OpenSpec
change** that contains every stage of the JavaMOP message programme. Follow `docs/WORKFLOW.md`
rigorously. The hard parts are not the writing: they are (a) getting the **execution order of the
groups and of the tasks inside each group** right, (b) designing for **parallelism** — which groups
can be dispatched to subagents simultaneously and which cannot, and (c) making sure **everything
that enters the change has been re-verified**, so that the change carries correct and sufficient
information for whoever executes it later, possibly months from now, without re-deriving anything.

You are not implementing. You are producing the change artifacts.

---

## 1. Hard rules, non-negotiable

- **Never start, stop or manage an Android emulator. Never run `emulator`, `adb`, or an experiment.**
  This applies to validation, testing, debugging — no exceptions. If something needs a device, it
  becomes a task in the change, not an action in this session.
- **OpenSpec artifacts are created exclusively through the skills** (`Skill` tool). Never
  `Write`/`Edit` directly on `proposal.md`, `design.md`, `tasks.md` or delta specs. This is
  `CLAUDE.md:187-189` and it overrides every other instinct. Technical Phase-0 documents under
  `docs/` are *not* OpenSpec artifacts (`docs/WORKFLOW.md:47`) and may be edited normally.
- **No `Co-Authored-By` trailer** on commits. The researcher is the sole author.
- **"MOP" means *monitored operations*** — never security terminology.
- **Tests always** `uv run pytest --import-mode=importlib -o "addopts=" modules/<module>/tests`.
- **P1–P4** govern everything you write: simplicity; narrative documentation that explains *why*;
  no backward compatibility (delete, with a `backup/` copy first); comments describe the current
  state, never migration history.
- **Portuguese, when you write it, carries correct accentuation.**

---

## 2. What this is about, and how it got here

RVSEC's violation reports are unreadable. In the published dataset **72.93 % of 97,018 records carry
the literal `unknown`**, and only 19 distinct messages exist in the whole corpus. The post-repair
Study-03 trial (`experimento-comp162`) is worse in that ratio, 79.91 % of 19,664 rows.

Between 16:24 and 23:44 on 2026-08-15 — one evening — four sessions produced a lineage of 19
documents, 9,032 lines: a root-cause plan, an adversarial review of it, four independent external
LLM validations, a design document proposing eight changes (C-0, C-1a, C-1, C-V, C-2, C-3, C-4,
C-5), two adversarial sessions over that design, four item-by-item extraction lists, and a
correction handoff.

On 2026-08-16 a fifth session verified the whole lineage adversarially, with eight subagents on
disjoint slices and blind re-measurement. Its output is
`docs/20260816_javamop_mensagens_verificacao.md` (1,053 lines) and it is the **most important
document for you** — it says which parts of the lineage survive, which do not, and what the plan
should actually be. All 20 documents are committed in **`3820e487`** on branch `modules`.

**Nothing has been implemented. No issue exists. No change exists. The first free number is
`gh104`.**

---

## 3. What is already established, and must not be re-litigated

### 3.1 Four decisions the researcher already took (2026-08-15)

| Decision | Choice |
|---|---|
| **D-A** — target set | **(ii)** a successor set derived from the frozen `jca`. **Do not touch `jca_android`.** |
| **`st=`** in the envelope | **Out of the contract.** Grammar is `v=1 code=… ev=… obj=… val='…' exp='…' msg='…'` |
| **D-C** — `args()` arity | **Land now**, with the corrected three-clause rule |
| **Order** | Correct the design document before opening issues |

### 3.2 Three questions that are still the researcher's, not yours

Take them to the user with the measured number beside each. Do not decide them yourself.

1. **The `generic` set / WS-8.** 145 of the 191 `.mop` files in the tree (75.9 %) never pass through
   `ErrorCollector`; the whole `generic` set collapses to one message form. Does it become a group
   inside this change, or a written non-goal? It changes the size of the programme.
2. **D-B, the oracle.** CrySL 1.5.2 vs MetaCrySL api30, per clause family. Smaller than it looked:
   the consequence is **38 %** of the `UnsafeAlgorithm` category (5,892 of 15,444), concentrated in
   `MessageDigestSpec`, not 97 %. Note that gh101 already states the framing as a MUST requirement
   ("the derived profile models availability, not recommendation") and applied it per spec — what is
   open is re-affirming it for the new set.
3. **Does `ev` enter the dedupe identity?** This is new and it decides whether one whole stage is
   worth existing. `ErrorSummary.equals` compares `(spec, error, class, method, location)`. The
   proposed `code` is `<SPEC>-ORDER-00` — a function of `spec`, and every spec has exactly one
   `@fail` block. Adding it refines nothing. If `ev` does not enter, per-event attribution stays
   impossible, which is the defect the programme exists to remove.

---

## 4. The documents, and what to take from each

Read in this order. Do not sample — these are the inputs your change will cite.

| # | File (under `docs/`) | Lines | What to take |
|---|---|---:|---|
| 1 | **`20260816_javamop_mensagens_verificacao.md`** | 1,053 | **Start here.** §9.1 is the plan in one page. §5 lists the errors that change decisions. §6 the design errors. §8 the defects nobody catalogued. §9.2 the exact mechanics of the message stage. |
| 2 | `20260815_javamop_mensagens_FINAL.md` | 521 | The design document: C-0..C-5, D-A..D-I, gates G-1..G-8, options O-1..O-9. **It has known errors** — see (1) §5 before quoting anything from it. |
| 3 | `20260815_javamop_mensagens_FINAL_analise_lacunas.md` | 818 | §3.1 the twin decomposition (the most reliable measurement of the lineage), §3.2 the corrected C-1a rule, §6 the four decisions, §7.1 the 11 corrections |
| 4 | `20260815_javamop_mensagens_validacao.md` | 850 | §3 consistency defects, §4 the three structural findings — **read them against (1) §4, which shows part of it was already known** |
| 5 | `20260815_javamop_mensagens.md` | 982 | The original plan. The only document that knows the `generic` set. WS-8 is at `:805-817` |
| 6 | `20260816_javamop_mensagens_correcao_handoff_prompt.md` | 610 | The five-phase framing. §8 has reproduction commands — **two of its definitions are wrong**, see §7 below |

**Prior work that the lineage failed to read, and that you must.** This is where half of the
"structural findings" already were:

- `data/gh101/frozen_set_debt.md` (250 l.) — what the frozen `jca` knowingly retains: the 18
  orphan events with the nominal list, the Cipher tables, **the "Form B" residue named and scoped to
  thirteen specifications** (task 3b.11b), and the corrected attribution of the empty `but found .`
  label (task 8.1 measured it: the cause was the weaver, not the specification).
- `openspec/changes/gh101-jca-spec-conformance/design.md` — decisions **D-S0..D-S14**. In particular
  **D-S9**, which considered and **rejected** the absorbing-state repair with two written reasons,
  and which declares that `INV-INS-110` deliberately does not cover the residue.
- `data/gh101/{predicate_omissions.csv, divergence_record.csv, conformance_record.csv,
  predicate_inventory_jca.csv, algorithm_naming.md, README.md}` — the omission register the
  `INV-INS-111` gate reads, the 106 divergence hunks, the 23 conformance verdicts.
- `openspec/changes/gh100-weaver-emission-fidelity/` — the weaver change whose wrapper merge
  **introduced** the arity defect that one stage of this programme repairs. It does not record it.
- `audit/20260808_validacao_jca_android/` — `fase0/pre_registro.md` (scope and the READY criterion),
  `global/juizglobal_relatorio.md` §10 (verdict REPROVADA 22/22; **G11 fails and is about gh101**).
- `docs/20260815_gh103_analysis_layer.md` — the offline analysis layer. Its `violations` reader is
  the canonical `errors.csv` reader; its freeze-item rule is the executable form of what D-F asks.

---

## 5. The plan you are encoding

### 5.1 Stages

```
E0 baseline ─┬─ E1 messages ───────────────┐
             ├─ E2 weaver arity            ├─→ E4 automata ──→ E5 predicates
             └─ E3 transport ──────────────┘         │
             EV validation ── spans all ─────────────┘
                                         E6 identity — only if question (3) is "yes"
```

| Stage | What it does | Depends on | Acceptance |
|---|---|---|---|
| **E0** baseline | Measure the residual budget on the E3 trial; register the classifier and the definitions as freeze items; read `errors.csv` through `aperv_tool.analysis.violations`, not a new parser | — | byte-identical rerun; every number leaves with numerator and denominator |
| **E1** messages | Give a 4th argument to the **25 three-argument report sites** (21 `@fail` + 4); fix the **11 lying messages**; switch **field → argument** at the 17 `but found` sites | D-A (where it lands); the lying-message census is a **precondition** | zero `unknown`; zero `but found .`; numeric literals in the message match the literals in the condition that guards it |
| **E2** weaver arity | Enforce positional `args()` arity when grouping advices into a merged wrapper, with the three-clause rule | D-C (decided); gh100 tasks 7.5/7.6 closed | a test proving the 16 advices with no `args()` survive grouping, plus the positive case; counter for excluded advices |
| **E3** transport | Grammar v1, sentinels, drop counters, fixed escapers and null guard, consumer matrix | E0 | property tests (comma, quotes, `\n`, `:::`, truncation); every drop counted |
| **EV** validation | The gates. **2 of 8 already exist.** Replace the unimplementable G-2b. Add the **differential harness** | — (starts day 1; becomes a hard prerequisite of E4) | G-2 becomes a pytest; G-6′ catches the duplicate `c1`; the harness runs before/after each repair |
| **E4** automata | Translation-defect repairs plus the newly catalogued defects | D-A · D-B · EV | each edit = row(s) + divergence-record entry + regressive example |
| **E5** predicates | New `ErrorType`s, missing producers, `condition()` moved into bodies | E4 · the `ExecutionContext` ruling | G-7 green, no new unjustified omission |
| **E6** identity | `code` into the identity and into `errors.csv` | question (3) · E1 · E3 | the declared count discontinuity is **non-zero** |

### 5.2 Parallelism — think about this carefully, it is the point

The `docs/WORKFLOW.md` §5 rule: group by **independence** (tasks sharing no files, no ordering
dependency → different subagents, run in parallel) and by **locality** (tasks in the same module or
directory → same subagent, to avoid merge conflicts). Size each subagent at **3–15 files**.

Facts that constrain the graph, all verified:

- **E1 and E4 edit the same 21 `.mop` files.** They cannot run in parallel per *change*; they can
  run in parallel **per file** with one owner per file at a time. The old plan's justification for
  sequencing E4 before E1 ("the message names states that E4 will create") **died** when `st` left
  the contract — if you keep that order, you need a new reason.
- **E2 is Java, in the sibling reactor** (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`), and
  shares no file with E1, E3 or E4. It parallelises with everything.
- **E3 is Python, in `rv-coverage`/`rv-android-core`/`rv-platform`/`aperv-tool`** — disjoint from E1,
  E2, E4.
- **EV creates new files** (`scripts/`, `tests/parity/`, a new `rvsec-mop/src/test`) and touches no
  existing spec. It parallelises with everything, and it must land before E4.
- **E0 is documentation and measurement scripts** — disjoint from everything.

So the realistic first wave is **E0 ∥ E2 ∥ E3 ∥ EV**, four subagents, disjoint file sets. E1 joins
as soon as D-A fixes the landing directory. E4 waits for EV. E5 last. E6 conditional.

Write the group dependency graph, the parallel-vs-sequential annotation and the critical path as
**HTML comments at the top of `tasks.md`** — the template asks for exactly that.

---

## 6. The `tasks.md` problem, and how to resolve it

You asked for per-group task files so the file stays small and the context window stays manageable.
That is the right instinct, and it collides with a schema rule. Both facts are verified:

- `openspec/schemas/rv-sdd/schema.yaml`, `apply:` block: **`tracks: tasks.md`**, and the tasks
  instruction says *"the apply phase parses checkbox format to track progress. Tasks not using
  `- [ ]` won't be tracked."*
- `docs/WORKFLOW.md:1049-1060`: the `tasks` artifact is detected by `tasks.md` existing.
- `docs/WORKFLOW.md:443`: the checkpoint rule — tick the checkbox immediately after each task,
  **before** starting the next — is the mechanism that lets a new session resume.

**Recommended resolution (do this unless the user says otherwise):**

`tasks.md` remains the single tracked artifact and holds **every** checkbox — it is the
roadmap/orchestrator, one `## N. Group` heading per stage, with the dispatch hints as HTML comments
at the top. Each group heading carries a pointer to a **per-group execution file** under
`openspec/changes/gh104-<name>/tasks/` (for example `tasks/E1-messages.md`) that holds what the
checkboxes cannot: the exact file inventory, the per-site table, the commands, the expected values,
the acceptance evidence, and the subagent brief. A subagent dispatched for a group reads **only its
group file**; the orchestrator reads only `tasks.md`.

This gives you small files per subagent *and* keeps resume working. It is additive — nothing in the
schema forbids extra files in the change directory.

**If the user prefers checkboxes to live in the per-group files**, that is a schema change, not a
convention: fork `openspec/schemas/rv-sdd/`, adjust `apply.tracks`, and validate with
`openspec schema validate rv-sdd`. Do not do it silently — raise it and get a ruling first.

---

## 7. Everything that enters the change must be re-verified

The lineage's central failure mode was **transporting numbers instead of measuring them**, and the
second was **not reading the prior work**. Your change will be executed later by someone with none
of this context, so a wrong number in `design.md` becomes a wrong repair.

Rule: **if a fact enters the change, you re-open its source in this session.** Not "the document
says"; "I read `file:line` and it says". Use subagents for breadth, with full reading and a
declaration of how many lines they read. Grep only ever *confirms absence* after you have read.

### Definitions you must fix before running anything

The old handoff's §8 gives one definition of "site" and applies it to two corpora. It is wrong for
one of them:

- **mute** = `message == 'unknown'` (after strip)
- **site** = `(spec, class, method, source)` **for `experimento-comp162` only**. The published
  article dataset has **10 columns and no `source`** — there, a site is the 3-tuple
  `(spec, class, method)`, and the twin numbers only reproduce under that.
- `experimento-comp162/results/*/*/errors.csv` are **8 disjoint shards**, not 8 replicas: 112
  distinct APKs, zero overlap, 3 tools × 3 repetitions inside each.
- **Form B**, as coded in the old handoff, is a *structural* detector (zero orphans + a self-loop at
  state 0 + something sinking from state 0). It is **not** the semantic property it is sold as, and
  it flags the gh101 repair as the disease. Do not put it in the change in that form.

### Oracle provenance — this one bites

`results/gh56-smoke/monitors/` is dated **2026-05-14**. It predates the freeze commit `7e7acb69`
(2026-08-07) and two source fixes: `9cec468b` (which inverts the `KeyManagerFactorySpec.init` guard)
and `2fa44ff5` (which canonicalises the PBE labels). Its **transition tables are byte-identical** to
the frozen control, so orphan/root-slice counts hold — but its **event bodies are pre-fix**.

> For anything beyond transition tables, use `results/gh101_group8_jca_frozen_control/monitors/`.

### Commands that reproduce (all read-only, run from `rv-android/`)

```bash
# reference dataset — expect: 97018 rows | 19 messages | 70760 unknown = 72.93 %
python3 -c "
import csv,collections
r=list(csv.DictReader(open('/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv')))
c=collections.Counter((x.get('message') or '').strip() for x in r)
print(len(r),'rows |',len(c),'messages |',c['unknown'],'unknown =',round(100*c['unknown']/len(r),2),'%')"

# comp162 — expect: 19664 rows | 15714 mute | 296 sites | 101 mute-legible twins (3950) | 12 mute-mute (838)
python3 -c "
import csv,glob,collections
rows=[]
for f in sorted(glob.glob('experimento-comp162/results/*/*/errors.csv')): rows+=list(csv.DictReader(open(f)))
def et(r):
    p=(r.get('unique_msg') or '').split(':::'); return p[3] if len(p)>3 else '?'
mute=lambda r:(r.get('message') or '').strip()=='unknown'
site=lambda r:(r['spec'],r['class'],r['method'],r['source'])
m=collections.Counter(site(r) for r in rows if mute(r)); l=collections.Counter(site(r) for r in rows if not mute(r))
print(len(rows),'rows |',sum(m.values()),'mute |',len(m),'sites')
print('mute-legible twins:',sum(m[s] for s in m if s in l),'in',len([s for s in m if s in l]),'sites')
per=collections.defaultdict(collections.Counter)
for r in rows:
    if mute(r): per[site(r)][et(r)]+=1
mm=[(s,c) for s,c in per.items() if len(c)>1 and min(c.values())==max(c.values())]
print('mute-mute twins   :',sum(sum(c.values()) for s,c in mm),'in',len(mm),'sites')"

# third-party attribution — the number the lineage argued about without measuring
# expect: 7-vendor list 78.49 % | +okio 82.67 % | +okio+spongycastle 82890 = 85.44 %
python3 -c "
import csv
r=list(csv.DictReader(open('/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv')))
base=['okhttp3.','com.google.','kotlin.','io.ktor.','org.bouncycastle.','androidx.','org.conscrypt.']
for lbl,p in [('plan list',base),('+okio',base+['okio.']),('+okio+spongy',base+['okio.','org.spongycastle.'])]:
    n=sum(1 for x in r if any(x['class'].startswith(q) for q in p))
    print('%-14s %6d %6.2f%%'%(lbl,n,100*n/len(r)))"

# orphan events (the existing G-2 gate) — expect 18 in 10 specs on the frozen control
python3 scripts/gh101_monitor_transition_check.py \
  results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java

# predicate graph gate (the existing G-7) — already a pytest
uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh101_specset_gates.py

# the four spec sets — expect jca 23/21/0, jca_android 23/21/0, generic 118/0/118, generic_new 27/0/27
cd ../rvsec/rvsec-mop/src/main/resources && for d in jca jca_android generic generic_new; do
  printf "%-12s files=%3d  with addError=%3d  with Log.v=%3d\n" "$d" \
    "$(ls $d/*.mop 2>/dev/null | wc -l)" \
    "$(grep -l addError $d/*.mop 2>/dev/null | wc -l)" \
    "$(grep -l 'Log\.v' $d/*.mop 2>/dev/null | wc -l)"; done; cd -

# the mechanical origin of `unknown` — expect 51 = 25 three-arg + 26 four-arg in jca
cd ../rvsec/rvsec-mop/src/main/resources/jca && grep -c 'new ErrorDescription' *.mop | \
  awk -F: '{s+=$2} END {print s" ErrorDescription calls"}'; cd -

# invariant collision — the two definitions that must be renumbered
grep -oE "INV-INS-[0-9]+" openspec/specs/instrumentation/spec.md | sort -u -V | tail -3
grep -nE "INV-INS-1(09|10)" openspec/changes/gh10{0,1}-*/specs/instrumentation/spec.md | cut -c1-120

# process state
openspec list
openspec status --change gh101-jca-spec-conformance
```

---

## 8. Process blockers to resolve before the change is created

These are not optional: the change will cite `INV-INS-110`, and that identifier currently means two
incompatible things.

1. **Archive gh102.** Complete (28/28 in the working tree, 26/28 at HEAD — two boxes are ticked but
   not committed) and its delta is already synced into the main specs. Commit the two boxes, archive.
2. **Archive gh101.** Complete (84/84) and its delta is **not** synced. `INV-INS-109..115` exist
   only inside the change. Archiving syncs them and forces the collision to be resolved.
3. **Resolve the `INV-INS-109`/`INV-INS-110` collision.** Both are defined twice with incompatible
   meanings — `gh100/specs/instrumentation/spec.md:63,65` (Layer-3 oracle key; Layer-3 comparator
   parsing) versus `gh101/specs/instrumentation/spec.md:43,47` (frozen `jca`; event present in the
   automaton). The main spec stops at `INV-INS-103`; the first free id is **`INV-INS-116`** (gaps
   exist at 28, 46–49, 74–79 if you prefer not to extend the top). **35 citations** live inside the
   two changes; **204** across the tree. Renumbering is not a two-line edit.
4. **Close gh100's 7.5 and 7.6.** `tasks.md:96` is a `7.4` marked `[x]` with full results and
   `tasks.md:97` is a duplicated `7.4` still `[ ]` — delete the duplicate. The real work is 7.5
   (`/rv-code-reviewer`) and 7.6 (`/rv-docs-sync`, conditional).
5. **gh101 has a stale record you should note, not fix here.** Tasks 4b.1–4b.4 and decision D-S10
   describe an `ExecutionContext` keyed by identity. Commit `e204e2a4` reverted that on 2026-08-11
   and nothing in gh101 records it. The predicate edge that task 5.1 closed (`generatedCipher`) only
   makes sense under `==`. This affects E5 and must be stated in the change.

---

## 9. The workflow to follow

**Track: Full SDD.** The change carries design decisions that need spec artifacts, spans four
modules plus the sibling Java reactor, and modifies contracts. Do not choose the track by file
count — `docs/WORKFLOW.md:193` warns about exactly that.

**Issue first** (`docs/WORKFLOW.md` §2). Templates live in `rvsec/.github/ISSUE_TEMPLATE/` — one
level **above** `rv-android` — and `blank_issues_enabled: false`, so a template is mandatory. Five
exist; the one that matches is **`feature.yml`** ("Feature Request", labels
`["type:feature", "track:full-sdd"]`). `documentation.yml` auto-applies `track:quick-path` and is
wrong for this. Use the cross-referencing convention: `refs #N` while working, `closes #N` on the
final commit, `Closes #N` in the PR body.

**Change directory:** `openspec/changes/gh104-<short-name>/`, lowercase, no date prefix (the archive
step adds it). Pick a name that names the outcome, not the mechanism.

**Route** (`docs/WORKFLOW.md:884`):

```
opsx:explore → opsx:new → opsx:continue ×4 (proposal, specs, design, tasks)
             → opsx:apply → rv-verify → /rv-code-reviewer → opsx:verify → opsx:archive
```

`opsx:continue` creates **one artifact per invocation** — that is its guardrail, not a bug. Two
undocumented skills exist in the tree (`openspec-propose`, `openspec-update-change`); they work but
diverge from what the WORKFLOW prescribes. Prefer the documented route.

Delta specs will land in the `instrumentation`, `analysis`, `core` and `platform` capabilities.
Check `openspec/specs/` for the existing names before writing the proposal's Capabilities section —
that section is the contract between the proposal and the specs phase.

---

## 10. Learnings, paid for in earlier sessions

- **Read the document *before* the target.** Two complete adversarial reviews missed that the design
  document silently dropped 76 % of the `.mop` files, because both started from the design document.
  Only reading the original plan revealed the hole.
- **Read the prior work, not just its file names.** The lineage listed `data/gh101/` among its
  sources and never opened it. Half of its "structural findings" were already there — measured,
  named, scoped, and in one case explicitly rejected with written reasons.
- **Verifying a count means verifying the universe it is counted over.** The numerator was usually
  right and the denominator wrong. It happened with "111 of 225 ids", with "97 % of the
  `UnsafeAlgorithm` category" (it was 97 % of one spec, 38 % of the category), and with a predicate
  census that came out all-zero because the API is `validate(...)`, not `getProperty(...)`.
- **Run the gate the document proposes.** Cheapest and most revealing test there is. But a green
  gate is not a healthy system: the existing G-2 passes a specification whose only event never
  changes state.
- **Extract semantics from the generated artifact, not the source text.** State indices do not
  follow declaration order, undeclared ERE symbols vanish silently, duplicate events merge, and
  root-slice dispatch is only visible in the generated monitor.
- **Agreement is not evidence.** The four external validations received one 349-line prompt that
  already asserted ten of the fourteen "facts" they then confirmed; the four unanimous rows are the
  four most explicit premises. The prompt itself says *"Agreement between agents is not proof."*
  Ask for the citation, and measure what carries a decision yourself.
- **Distinguish "a record that needs a better message" from "a record that should not exist."**
  30.5 % of the mute volume is the second kind. Corollary: the `unknown` percentage can **rise**
  while the system improves, because the denominator shrinks on purpose. Do not write an acceptance
  criterion that punishes that.
- **Repairing a defect can hide it.** Repairing an orphan event converts Form A into Form B: it
  leaves the gate's radar and keeps the behaviour. gh100 did the same thing at the weaver level.
  This is why the differential harness matters more than another static gate.
- **Do not take a subagent's conclusion at face value.** In the verification session one subagent
  declared the message stage mechanically broken; direct measurement showed the opposite, and
  accepting it would have killed the cheapest stage of the programme.

---

## 11. What NOT to do in this session

- Do not implement anything. No `.mop` edit, no weaver edit, no Python edit outside the change
  directory.
- Do not touch `jca` (frozen, with a parity gate that runs) or `jca_android` (decision D-A).
- Do not edit the historical documents of the lineage. They are the record of what was found when
  it was found; correcting them retroactively destroys traceability. This is P4 applied to
  documents. The verification report is the current one.
- Do not open the issue or create the change before the three researcher questions of §3.2 are
  answered and the blockers of §8 are resolved.
- Do not run an emulator, `adb`, Docker or an experiment. Ever.

---

## 12. Suggested first actions

1. Read `docs/20260816_javamop_mensagens_verificacao.md` in full — §9.1 first, then §5, §6, §8, §9.2.
2. Read `data/gh101/frozen_set_debt.md` and `gh101/design.md` D-S9 in full. Budget for this; it is
   the difference between planning a programme and re-planning one that already ran.
3. Dispatch subagents on disjoint slices to re-verify what will enter the change: the message-site
   inventory (25 three-arg sites, 11 lying messages, 17 `but found` sites), the gate inventory (what
   exists in `scripts/` and `tests/parity/` versus G-1..G-8), the consumer matrix, and the file
   inventory per stage. Full reading, line counts declared.
4. Take the three questions of §3.2 to the user, with the measured numbers beside each.
5. Resolve the blockers of §8.
6. Only then: `opsx:explore` → `opsx:new` → four `opsx:continue`.

Use the `sequential-thinking` MCP for the group ordering and the parallelism graph — that is
genuinely a multi-step problem with chained consequences. Use it to think, not to narrate.
