<!-- Subagent dispatch hints (for changes touching 20+ files):
     - Group N (Name) must complete first — Groups X, Y depend on it.
     - Groups X, Y are independent and can run in parallel after Group N.
     - Group Z integrates everything — must run after all other groups.
     - Critical path: N -> X -> Z.
     - This change touches NN files — use subagent orchestration (M parallel dispatches). -->

## 1. <!-- Foundation Group (e.g., Domain Models, Configuration) -->

- [ ] 1.1 <!-- Task description (models, config, constants) -->
- [ ] 1.2 <!-- Task description -->
- [ ] 1.3 Add unit tests for new models/config
- [ ] 1.4 Run `/rv-test-run <module>`

## 2. <!-- Core Implementation Group -->

- [ ] 2.1 <!-- Task description (core logic) -->
- [ ] 2.2 <!-- Task description -->
- [ ] 2.3 Add unit tests for core implementation
- [ ] 2.4 Run `/rv-doc-code <new-file-path>` <!-- for new modules/classes -->
- [ ] 2.5 Run `/rv-test-run <module>`

## 3. <!-- Additional Groups as needed -->

- [ ] 3.1 <!-- Task description -->
- [ ] 3.2 <!-- Task description -->
- [ ] 3.3 Run `/rv-verify <module>` <!-- intermediate checkpoint after major group -->

## 4. <!-- Integration & Verification -->

- [ ] 4.1 Add integration tests
- [ ] 4.2 Run `/rv-qa-lint-fix <module>`
- [ ] 4.3 Run `/rv-verify <module>`
- [ ] 4.4 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 4.5 Run `/rv-docs-sync <module>` <!-- if CLAUDE.md or architecture docs need updating -->
