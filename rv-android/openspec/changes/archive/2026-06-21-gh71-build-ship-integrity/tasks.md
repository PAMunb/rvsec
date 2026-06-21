<!-- Small, sequential change (3 build-chain files, one atomic commit). No subagent orchestration.
     Critical path: 1 (pre-conditions) -> 2 (atomic edit: Dockerfile + delete jar + .gitignore) -> 3 (verify).
     Groups 2.* must land in a SINGLE commit (the jar enters the image via the rvsec clone; neither
     half is safe alone — INV-TOOL-21/22, design D5). -->

## 1. Pre-conditions

- [x] 1.1 Confirm `phtcosta/ape` is **public** over HTTPS (`git ls-remote https://github.com/phtcosta/ape.git` succeeds without credentials). Required before the first image build (design D4).
- [x] 1.2 Confirm the base image toolchain is present (already verified in Explore; re-check if base changed): `docker run --rm phtcosta/rvandroid_tools:0.9.1 bash -c 'which d8 mvn git java'`.

## 2. Build-chain change (single atomic commit — INV-TOOL-21..24)

- [x] 2.1 Back up the committed jar to `backup/` (P3 safety): copy `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` → `backup/gh71-ape-rv-jar/`.
- [x] 2.2 `git rm` the committed jar `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` (INV-TOOL-22).
- [x] 2.3 Add `ape-rv.jar` to the empty `.gitignore` at `modules/aperv-tool/src/aperv_tool/tools/aperv/.gitignore` (INV-TOOL-22).
- [x] 2.4 Edit `docker/rvandroid/Dockerfile`: add a new standalone `RUN` after the existing rvsec build step (compound `RUN` at lines 13-17 that ends with `uv sync`) — do NOT split that compound RUN (P1) — that `git clone https://github.com/phtcosta/ape.git` (default branch, HTTPS, no `ARG`/no pin — INV-TOOL-23), runs `mvn package`, copies `target/ape-rv.jar` to `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar`, and cleans the clone (INV-TOOL-21, INV-TOOL-24).
- [x] 2.5 Confirm no image tag change and no `docker-compose.*.yml` / `calibration_orchestrator.py` edits (scope guard).
- [x] 2.6 Update docs: correct the "gitignored build artifact" claim in `modules/aperv-tool/CLAUDE.md` / `docs/architecture.md` to describe the build-from-source flow (clone → `mvn package` → copy).

## 3. Verification

- [x] 3.1 Repo state: `git ls-files modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` returns empty AND `git check-ignore -v modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` matches (INV-TOOL-22).
- [x] 3.2 Dockerfile review: `grep -c APE_REF docker/rvandroid/Dockerfile` == 0 (INV-TOOL-23); the ape `RUN` is a new standalone step after the existing rvsec compound RUN (lines 13-17, ending in `uv sync`); single `FROM` (INV-TOOL-24).
- [x] 3.3 Image smoke build (manual): `docker build docker/rvandroid` succeeds AND `/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` exists and is non-empty (INV-TOOL-21; spec scenario "Image built from scratch ships a source-compiled jar"). VERIFIED on `rvandroid:gh71-smoke`: ape `mvn package` BUILD SUCCESS; jar = 245640 B (non-empty), distinct from legacy committed 236967 B → source-compiled artifact, not the legacy binary.
- [x] 3.4 Run `uv run pytest modules/aperv-tool/tests/ --import-mode=importlib -o "addopts=" -v` — expected green (tests mock the jar).
- [x] 3.5 Run `/rv-verify aperv-tool`. (Tests 41 PASS, black/isort PASS. Lint FAIL is **pre-existing** in `tool.py`/`test_aperv_tool.py` — files gh71 does not touch, debt from gh55 `ba2c1aa6`; out of this change's scope per Non-Goal "no change to aperv-tool Python source". No regression introduced by gh71.)
- [x] 3.6 Invoke `/rv-code-reviewer` via Skill tool for this change.
- [x] 3.7 Commit atomically with `closes #71` (groups 2.1-2.6 in one commit; design D5).
