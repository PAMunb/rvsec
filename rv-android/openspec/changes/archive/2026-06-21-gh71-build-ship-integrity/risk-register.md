# Risk Register: gh71-build-ship-integrity

> GitHub Issue: rvsec#71 — Full SDD. Companion to `proposal.md` / `design.md` / ADR 0005.
> Authoritative sources of risk: `design.md` §Risks/Trade-offs + §Error Handling + §Decisions
> (D1–D6), ADR `docs/adr/0005-build-ape-rv-jar-from-source-in-image.md` §Consequences, and the
> impact section of `proposal.md`. This register applies the **proactive strategy**: every risk is
> documented *before* the build-chain edit, each with an RMMM (Mitigation / Monitoring / Management)
> plan, so the failure modes that a build-time external dependency introduces are anticipated rather
> than discovered at the next image build.

## Scope under analysis

Delete the git-committed `ape-rv.jar` and, in the **same atomic commit**, add a single-stage `RUN`
to `docker/rvandroid/Dockerfile` that clones `https://github.com/phtcosta/ape.git` (default branch,
no `ARG`/no pin), runs `mvn package`, and copies the freshly built `target/ape-rv.jar` into the
`aperv-tool` module directory inside the image (ADR 0005, design D1–D6). No image tag bump; no
`docker-compose.*.yml` / `calibration_orchestrator.py` edits; no Python source change.

This is a **build-pipeline change with a new build-time external dependency** (an anonymous HTTPS
clone of a *separate* repo) plus a **binary-provenance change** (committed artifact → built
artifact). Per the **Risk Projection** principle the analysis concentrates on the risks that this
combination introduces: build-time availability of `phtcosta/ape`, reliance on the base-image
toolchain, the atomicity of the delete+build pair, the "no tag bump → consumers must rebuild"
property, and the non-determinism of tracking an unpinned default branch over time.

## Summary

| Risk Level | Count |
|------------|-------|
| Critical | 0 |
| High | 2 |
| Medium | 3 |
| Low | 3 |
| **Total** | **8** |

| ID | Title | Category | Prob. | Effect | Level |
|----|-------|----------|-------|--------|-------|
| RISK-001 | `phtcosta/ape` not public / unreachable at build → image build fails | Technology (external dep, build-time) | Moderate | Serious | **High** |
| RISK-002 | Non-atomic landing: jar deleted without (or before) the build step → `aperv:*` JAR resolution fails | Tools (build/artifact coupling) | Moderate | Serious | **High** |
| RISK-003 | Unpinned default branch → a future breaking `ape` change silently breaks the build over time | Technology (non-determinism) | Moderate | Tolerable | **Medium** |
| RISK-004 | RUN-placement vs. the existing compound `RUN` (clone+install+`uv sync` are one layer) → wrong sequencing or stale cache | Tools (Dockerfile structure) | Moderate | Tolerable | **Medium** |
| RISK-005 | No image tag bump → consumers run the stale committed jar until they rebuild/pull | Process (release/consumption) | High | Tolerable | **Medium** |
| RISK-006 | Base-image toolchain assumption breaks on a future base bump (`d8`/`mvn`/`git`/JDK / `release=11`) | Tools (base image) | Low | Serious | **Low** |
| RISK-007 | Longer build / layer-cache churn (clone + `mvn package` re-runs every build) | Tools (build performance) | High | Insignificant | **Low** |
| RISK-008 | Built jar still mismatches the static-analysis schema (the gh71 fix does not actually fix MOP boost) | Product (regression / fix efficacy) | Low | Serious | **Low** |

---

## Top Risks

### RISK-001: `phtcosta/ape` not public or unreachable at build → image build fails
- **Category**: Technology (new build-time external dependency)
- **Description**: The new `RUN` performs an **anonymous HTTPS clone of a separate repository**
  (`phtcosta/ape`) that is not the `rvsec` repo already cloned on line 13. If `phtcosta/ape` is
  **private** (or is later made private), renamed, or the registry/network is unreachable at build
  time, `git clone` fails and — by design, there is no fallback binary anymore — the whole image
  build aborts. The design's own Error Handling table lists this as the first failure mode.
- **Why this is a top risk (Risk Projection)**: this is a **new** dependency the previous build did
  not have (the jar used to travel inside the `rvsec` clone). It is a hard pre-condition (design D4,
  task 1.1) whose state is *outside this repository's control* — a GitHub repo-visibility toggle by
  the owner can break every future build with no code change here. Effect is Serious because the
  build fails loudly and completely; there is no degraded image. Probability is Moderate, not Low,
  precisely because the "make it public" step is a manual operational action that must precede the
  *first* build and stay true for *every* subsequent one.
- **Probability**: Moderate · **Effect**: Serious · **Level**: High
- **Mitigation strategy**: Avoidance (pre-condition gate) + Minimization (loud, early failure)
  - **Avoidance**: confirm `phtcosta/ape` is public over anonymous HTTPS **before the first build**
    (task 1.1: `git ls-remote https://github.com/phtcosta/ape.git` succeeds without credentials).
    Keep the repo public for as long as the image is built.
  - **Minimization**: HTTPS anonymous clone mirrors the existing `rvsec` clone — same failure
    surface, no SSH key / build secret introduced (design D4). Failure is loud at build time, never
    a silent stale-jar ship.
- **Indicators (Monitoring)**:
  - `git ls-remote https://github.com/phtcosta/ape.git` exits 0 without prompting for credentials
    (Green); prompts for / requires credentials (Red — repo is private).
  - Image build log shows the `git clone .../ape.git` step completing (Green) vs. `Repository not
    found` / `Authentication failed` / network error (Red).
- **Contingency (Management)**:
  - **Trigger**: clone step fails in any image build, or `ls-remote` indicates the repo is private.
  - **Actions**: (1) make `phtcosta/ape` public; (2) if it must stay private, this is a **design
    change** (re-open D4: SSH deploy key / BuildKit secret / submodule) — do not silently fall back
    to a committed jar, that re-introduces the gh71 root cause; (3) verify network egress to GitHub
    from the build host.
  - **Owner**: change author (repo visibility) / build operator (network).
- **Status**: Open

---

### RISK-002: Non-atomic landing — jar deleted without (or before) the build step
- **Category**: Tools (build / artifact coupling)
- **Description**: Today the committed `ape-rv.jar` reaches the image **only** because it is tracked
  inside the `rvsec` repo cloned on Dockerfile line 13. If the `git rm` of the jar (task 2.2) lands
  **without** the new `RUN`, or in a **separate earlier commit**, the resulting image has no jar in
  the `aperv-tool` module dir → `JarResolver._resolve_jar_path` raises `RVToolExecutionError` and
  **every `aperv:*` run fails at JAR resolution**. The two halves are individually unsafe; only the
  pair is consistent (design D5, ADR 0005 §Decision 3).
- **Why this is a top risk (Risk Projection)**: the change spans **three coupled edits** (delete jar
  + `.gitignore` + Dockerfile RUN) that *must* be one commit. The most natural mistakes — committing
  the cleanup first "to keep the build edit clean", or rebasing/splitting during review — produce a
  broken intermediate state on the `modules` branch that anyone building from that SHA inherits.
  Effect is Serious (total `aperv:*` outage from that image); the mitigation is purely procedural,
  so the residual risk is operator discipline.
- **Probability**: Moderate · **Effect**: Serious · **Level**: High
- **Mitigation strategy**: Avoidance (single atomic commit) + verification gate
  - **Avoidance**: land tasks 2.1–2.6 in **one commit** (`closes #71`, task 3.7); the tasks.md
    header already marks groups 2.* as a single-commit unit.
  - **Gate**: before committing, the working tree must simultaneously show the jar removed from
    tracking, `.gitignore` updated, and the Dockerfile RUN present — verify all three in the same
    `git status` / `git diff --cached` (tasks 3.1–3.2).
- **Indicators**:
  - `git show --stat HEAD` for the change commit lists **all three** paths
    (`.../ape-rv.jar` deleted, `.../.gitignore` modified, `docker/rvandroid/Dockerfile` modified).
    Fewer than three is Red.
  - Post-build smoke (task 3.3): `/opt/rvsec/.../ape-rv.jar` exists and is non-empty.
- **Contingency**:
  - **Trigger**: the commit contains only a subset of the three edits, or the smoke build finds no
    jar in the module dir.
  - **Actions**: `git reset`/amend to recombine into one commit before pushing; if already pushed,
    follow with a single corrective commit that restores the consistent state (never leave the
    `modules` branch tip in the broken half-state).
  - **Owner**: implementer.
- **Status**: Open

---

### RISK-003: Unpinned default branch → a future breaking `ape` change silently breaks the build over time
- **Category**: Technology (build non-determinism over time)
- **Description**: The design deliberately clones the **default branch with no `ARG`/no SHA pin**
  (D3, "always current"). The benefit is that the shipped jar always tracks `ape` HEAD; the cost is
  that the build is **non-reproducible across time** — two builds of the *same* Dockerfile SHA on
  different days can ship different jars, and a future breaking commit on `ape` master (a `pom.xml`
  change, a `release` bump, a compile error, a `d8` incompatibility) can break the rvandroid image
  build or change `aperv` behaviour **without any change in this repo**.
- **Why this risk (Risk Projection)**: this is the explicit trade-off the team accepted (D3), so the
  goal here is not to reverse it but to make it **monitorable**. Probability is Moderate over the
  image's lifetime (ape is an active, separately owned repo). Effect is Tolerable because the failure
  is loud (a broken build) or detectable (a re-run with the right smoke), and the remedy is a known
  one-line edit (pin a ref). It is *not* High because the smoke build (task 3.3) catches a broken
  build immediately, and a behavioural change would surface in the researcher's final 169-APK run.
- **Probability**: Moderate · **Effect**: Tolerable · **Level**: Medium
- **Mitigation strategy**: Acceptance (documented design choice) + Minimization (escape hatch ready)
  - **Acceptance**: "always current" is the desired default (D3); pinning is explicitly out of scope
    for this change.
  - **Minimization**: the escape hatch is a **one-line Dockerfile edit** — add `--branch <ref>` (or a
    pinned SHA checkout) to the clone if a specific `ape` ref is ever required (D3, ADR 0005 §D3). No
    `ARG` plumbing exists, by design, so the change is local and obvious when needed.
- **Indicators**:
  - The image smoke build (task 3.3) on a fresh `--no-cache` build succeeds; a sudden failure of a
    previously-green build with no change in this repo is the canary that `ape` HEAD broke.
  - `[APE-RV] MOP boost` fires with `maxBoost>0` in the researcher's validation run (the same metric
    that was 0/147,153 in the incident) — a regression here points at an `ape` HEAD behaviour change.
- **Contingency**:
  - **Trigger**: a no-cache build fails with no local change, or MOP boost regresses after an image
    rebuild.
  - **Actions**: identify the offending `ape` commit; **pin** the clone to the last-known-good ref
    (one-line Dockerfile edit); raise the breakage upstream in `phtcosta/ape`; rebuild.
  - **Owner**: change author / build operator.
- **Status**: Open (accepted trade-off)

---

### RISK-004: RUN placement vs. the existing compound `RUN` (clone + install + `uv sync` are one layer)
- **Category**: Tools (Dockerfile structure / layer caching)
- **Description**: The design/tasks describe placing the ape `RUN` "after the rvsec clone (line 13)
  and before `uv sync`". But in the **current** Dockerfile, the clone, `mvn clean install`,
  `mvn clean compile`, and `uv sync --no-dev` are a **single compound `RUN`** (lines 13–17), and the
  dexlib2 freshness gate is a *separate* `RUN` (lines 19–26). "Before `uv sync`" is therefore not a
  gap between two RUN steps — `uv sync` lives inside line 13's compound command. If the ape build is
  added as a new standalone `RUN` after line 17, it runs *after* `uv sync` (which is harmless for the
  jar, since `aperv-tool` resolves the jar at runtime, not at `uv sync` time) — but the literal
  reading of the task ("before `uv sync`") cannot be satisfied without restructuring line 13's
  compound RUN. Misreading this could lead an implementer to split the compound RUN unnecessarily or
  to place the copy where the target module path does not yet exist.
- **Why this risk (Risk Projection)**: it is a concrete structural mismatch between the task wording
  and the file as it stands — exactly the kind of ambiguity that produces a wrong edit. Effect is
  Tolerable (caught by the Dockerfile review gate and the smoke build), but Probability is Moderate
  because the task text and the file disagree. Note the target copy path
  `/opt/rvsec/rv-android/modules/aperv-tool/...` **exists after** the line-13 clone (the rvsec repo
  contains `rv-android/modules/...`), so a standalone `RUN` after line 17 is the structurally sound
  placement; the "before `uv sync`" intent is about *not* depending on `uv sync` for the jar, which a
  post-`uv sync` RUN also satisfies.
- **Probability**: Moderate · **Effect**: Tolerable · **Level**: Medium
- **Mitigation strategy**: Minimization (precise placement) + verification gate
  - **Minimization**: add the ape build as a **new standalone `RUN`** after the line-13 compound RUN
    (and it may sit alongside the existing dexlib2 gate at 19–26), since the copy target path exists
    once the rvsec repo is cloned and the jar is consumed at *runtime*, not at `uv sync`. Do **not**
    split the existing compound RUN — that is needless churn (P1). Reconcile the tasks.md wording with
    the actual file structure during apply (the operative invariant is INV-TOOL-24: single `FROM`,
    after the rvsec clone — both satisfied by a post-line-17 standalone RUN).
  - **Gate**: Dockerfile review (task 3.2) — single `FROM`; ape RUN after the rvsec clone; copy
    target path resolves; `grep -c APE_REF` == 0.
- **Indicators**:
  - `grep -c '^FROM' docker/rvandroid/Dockerfile` == 1.
  - Smoke build (task 3.3) finds the jar at the module path (proves the copy target existed at build
    time).
- **Contingency**:
  - **Trigger**: smoke build fails on `cp` (no such target dir) or the review finds a split/duplicated
    `FROM`.
  - **Actions**: move the ape `RUN` to after the rvsec clone completes (so the module dir exists);
    revert any unnecessary split of the compound RUN.
  - **Owner**: implementer.
- **Status**: Open

---

### RISK-005: No image tag bump → consumers keep running the stale committed jar until they rebuild/pull
- **Category**: Process (release / consumption)
- **Description**: The change rebuilds the image **in place with no tag change** (proposal "No image
  tag change"; ADR 0005 §Consequences). Anyone holding a previously-built/pulled image — including a
  CI cache, a researcher's local image, or the very 169-APK pipeline that exposed the incident —
  continues to run the **old jar with the `reachesMop` bug** until they explicitly rebuild or
  re-pull. Because the tag is unchanged, there is no version signal that a rebuild is required; a
  stale cached image looks identical by tag.
- **Why this risk (Risk Projection)**: the entire point of gh71 is to make MOP boost fire, and that
  benefit **does not reach any consumer who does not rebuild**. Probability is High (cached/old images
  are the norm), but Effect is Tolerable: the failure mode is "no improvement yet", identical to
  today's known-bad state, not a new regression — and it is fully recoverable by a rebuild/pull.
- **Probability**: High · **Effect**: Tolerable · **Level**: Medium
- **Mitigation strategy**: Minimization (explicit rebuild step) + Monitoring (provenance check)
  - **Minimization**: the researcher's final 169-APK validation run (proposal Out-of-Scope, but the
    consumer of this fix) **must rebuild the image first** — make "rebuild rvandroid image (no
    cache for the ape layer)" an explicit pre-step of that run, not an assumption.
  - **Monitoring**: verify the running image actually carries a source-built jar before trusting MOP
    metrics (provenance check below).
- **Indicators**:
  - In the image used for validation, the jar build timestamp / `unzip -l ape-rv.jar` content is
    newer than the committed-jar baseline (`c5d76943`), i.e. it is the source-built artifact.
  - First validation run shows `[APE-RV] MOP boost maxBoost>0` for a non-zero fraction of evaluations
    (vs. 0/147,153 in the incident).
- **Contingency**:
  - **Trigger**: MOP boost still 0 in validation, or the image jar matches the old committed binary.
  - **Actions**: rebuild the image with `--no-cache` (at least for the ape clone/package layer),
    confirm the layer actually re-ran, re-pull on every consumer host, re-run validation.
  - **Owner**: build operator / researcher running validation.
- **Status**: Open

---

### RISK-006: Base-image toolchain assumption breaks on a future base bump
- **Category**: Tools (base image dependency)
- **Description**: The single-stage decision (D2) rests on the base image
  `phtcosta/rvandroid_tools:0.9.1` already providing `d8` (`/opt/android/build-tools/35.0.1/d8`),
  Maven 3.9.16, Git, and **JDK ≥ 11** (`ape/pom.xml` sets `maven.compiler.release=11`), with
  `ANDROID_HOME=/opt/android`. If the base is bumped to a tag that drops or relocates any of these
  (e.g. a different build-tools path so `mvn package`'s `d8` step can't find the binary, or a JDK too
  old for `release=11`), `mvn package` fails and the build aborts.
- **Why this risk (Risk Projection)**: the base tag is pinned (`0.9.1`), so the probability is **Low**
  for the *current* build — the assumption is verified in Explore (task 1.2). The risk materializes
  only on a future base bump that this change does not perform. Effect is Serious (build fails) but it
  is loud and caught by the smoke build.
- **Probability**: Low · **Effect**: Serious · **Level**: Low
- **Mitigation strategy**: Avoidance (verified pre-condition) + Monitoring (re-check on base bump)
  - **Avoidance**: re-run task 1.2
    (`docker run --rm phtcosta/rvandroid_tools:<tag> bash -c 'which d8 mvn git java && java -version'`)
    **whenever the base tag changes**; confirm JDK ≥ 11 and the `d8` path used by `ape`'s build.
  - **Acceptance**: build tools remain in the image (no multi-stage), which is already true today, so
    no new size regression (D2).
- **Indicators**:
  - `which d8 mvn git java` all resolve in the base image; `java -version` ≥ 11.
  - `ape`'s `mvn package` completes and `target/ape-rv.jar` is produced in the smoke build.
- **Contingency**:
  - **Trigger**: a base bump causes `mvn package` to fail on missing `d8`/`mvn`/JDK.
  - **Actions**: pin the base back to a known-good tag, or restore the missing tool in the base image;
    only if the base genuinely cannot carry build tools does multi-stage (rejected D2) get revisited.
  - **Owner**: build operator / base-image maintainer.
- **Status**: Open

---

### RISK-007: Longer build / layer-cache churn from clone + `mvn package`
- **Category**: Tools (build performance)
- **Description**: The new `RUN` adds a network clone plus a full `mvn package` of `ape` to every
  image build. Because the clone targets an unpinned default branch (RISK-003), the layer cannot be
  meaningfully cache-keyed on a ref, so it tends to re-run on rebuilds; `mvn package` + `d8` adds
  wall-time on top of the already-substantial `rvsec` `mvn clean install` (line 14).
- **Why this risk (Risk Projection)**: this is the explicit "longer image build" trade-off in design
  §Risks and ADR §Negative. Probability is High (it runs on every uncached build), but Effect is
  **Insignificant** — it is build-time cost only, with no runtime or correctness impact, and small
  relative to the existing rvsec Maven build.
- **Probability**: High · **Effect**: Insignificant · **Level**: Low
- **Mitigation strategy**: Acceptance + Minimization
  - **Acceptance**: documented trade-off (D2); cost is dominated by the pre-existing `mvn clean
    install` of `rvsec`.
  - **Minimization**: `-DskipTests` on the ape `mvn package` (illustrated in design §API Design)
    avoids running ape's test suite at image-build time; ordering the ape RUN so Docker layer caching
    can reuse upstream layers.
- **Indicators**: image build wall-time stays within the same order of magnitude as the current build
  (the rvsec Maven step dominates).
- **Contingency**:
  - **Trigger**: build time becomes operationally painful.
  - **Actions**: pin the ape ref (also addresses RISK-003) so the layer can cache; or pre-build the
    jar in a cached upstream layer. Not warranted unless measured.
  - **Owner**: build operator.
- **Status**: Open (accepted)

---

### RISK-008: Built jar still mismatches the static-analysis schema (fix does not actually fix MOP boost)
- **Category**: Product (fix efficacy / latent regression)
- **Description**: The premise of gh71 is that the **current `ape` source already parses
  `reachesTarget`** correctly (proposal "the correct parser already exists in the `ape` source
  tree"). If that premise is wrong — e.g. the `ape` HEAD `MopData` parser still reads `reachesMop`,
  or only partially handles the gh60 `reachesTarget` schema — then building from source ships a jar
  that is *fresh* but *still wrong*, and MOP boost stays 0. The build-chain fix would be necessary but
  not sufficient.
- **Why this risk (Risk Projection)**: this change deliberately makes **no `ape` source edit** (it
  trusts the parser is already correct), so the efficacy of the whole fix hinges on a fact this change
  does not itself verify. Probability is **Low** (the proposal states the parser is correct and ape
  `MopData` uses optional-field-tolerant `opt*` reads — cross-referenced in gh69 RISK-007), but Effect
  is Serious (the experiment-invalidating symptom recurs despite the change shipping "successfully").
- **Probability**: Low · **Effect**: Serious · **Level**: Low
- **Mitigation strategy**: Verification gate (end-to-end signal) + Avoidance (no silent acceptance)
  - **Verification**: the researcher's validation run must assert `[APE-RV] MOP boost maxBoost>0`
    fires for a non-zero fraction of evaluations on the same dataset that produced 0/147,153. A green
    image build alone does **not** prove the fix works — only the boost firing does (this is the true
    acceptance signal for rvsec#71).
  - **Avoidance**: if boost is still 0 with a confirmed source-built jar, escalate to an `ape`
    **source** fix (a separate change) — do not declare gh71 closed on build-chain green alone.
- **Indicators**:
  - On a known generic/JCA-positive APK in the validation run, `maxBoost>0` count > 0.
  - The ape `MopData` parser in the shipped jar reads `reachesTarget` (spot-check via a single-APK
    run with debug logging on the signature-index build).
- **Contingency**:
  - **Trigger**: MOP boost still 0/N after a confirmed source-built, rebuilt image.
  - **Actions**: open a follow-up `ape` source change to fix the parser; this register's RISK-005
    indicators rule out a stale-image cause first.
  - **Owner**: change author / researcher.
- **Status**: Open

---

## Monitoring Schedule

- **Review cadence**: at each phase boundary of this small build-chain change —
  - **End of Design (now)**: register created; RISK-001 (pre-condition) and RISK-002 (atomicity)
    mitigations are encoded as explicit tasks (1.1, 2.1–2.6, 3.1–3.2, 3.7); RISK-004 placement is to
    be reconciled with the actual Dockerfile structure during apply.
  - **During Implement (`/opsx:apply`)**: re-check RISK-002 (all three edits staged together) and
    RISK-004 (single `FROM`, copy target exists) before composing the commit.
  - **During Verify (`/rv-verify` + `/opsx:verify`)**: RISK-001 (clone succeeds, ls-remote public),
    RISK-002 (commit shows all three paths; jar present post-build), RISK-004 (single `FROM`), and
    RISK-006 (toolchain present) are hard gates via tasks 3.1–3.5.
  - **At researcher validation (out of scope here, but the consumer of the fix)**: RISK-005 (image
    rebuilt, not cached) and RISK-008 (MOP boost actually fires) are the true acceptance gates for
    rvsec#71 closure.
- **Risk review checklist** (run at each boundary):
  - [ ] RISK-001: `git ls-remote https://github.com/phtcosta/ape.git` public/anonymous still green?
  - [ ] RISK-002: does the change commit show **all three** paths (jar deleted, `.gitignore`,
        Dockerfile)?
  - [ ] RISK-003/RISK-008: did a no-cache rebuild succeed and does MOP boost fire (`maxBoost>0`)?
  - [ ] RISK-004: single `FROM`; ape RUN after the rvsec clone; copy target path resolves at build?
  - [ ] RISK-005: is the validation run using a freshly rebuilt/pulled image (not a cached one)?
  - [ ] RISK-006: `which d8 mvn git java` resolve in the base; JDK ≥ 11?
  - [ ] Any risk closeable?
- **Owner**: change author (Pedro Costa).

## Cross-references

- GitHub Issue: **rvsec#71**
- ADR: `docs/adr/0005-build-ape-rv-jar-from-source-in-image.md` (Decisions D1–D6, Consequences)
- Change artifacts: `openspec/changes/gh71-build-ship-integrity/` — `proposal.md`, `design.md`
  (§Risks/Trade-offs, §Error Handling, §Decisions), `tasks.md` (1.1–3.7)
- Spec invariants (gh71 deltas): INV-TOOL-21 (build from source, no committed/bind-mount dep),
  INV-TOOL-22 (repo does not track the jar; `.gitignore` ignores it), INV-TOOL-23 (default branch,
  no `ARG`/no pin), INV-TOOL-24 (single-stage, new standalone RUN after the rvsec build step)
- Affected build files: `docker/rvandroid/Dockerfile`,
  `modules/aperv-tool/src/aperv_tool/tools/aperv/{ape-rv.jar (deleted), .gitignore}`
- Related register: `openspec/changes/gh69-generic-subtype-target-matching/risk-register.md`
  RISK-007 (ape `MopData` `opt*` field tolerance — context for RISK-008 here)
- Reference plan: `ape/docs/20260621_plano_correcao_aperv_e_modulos_relacionados.md` §B-1

## Change Log

| Date | Risk | Change |
|------|------|--------|
| 2026-06-21 | all | Register created at end of Design phase from `design.md` §Risks/Error-Handling/Decisions, ADR 0005, and `proposal.md` §Impact |
| 2026-06-21 | RISK-004 | Added after verifying `docker/rvandroid/Dockerfile`: clone+install+`uv sync` are a single compound `RUN` (lines 13–17), so "before `uv sync`" is not a between-RUN gap — placement nuance flagged for apply |
