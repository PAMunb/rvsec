<!-- Dependency hints (for changes touching 20+ files):
     - Group N must complete first — Groups X, Y depend on it.
     - Groups X, Y are independent and can run in parallel.
     - Group Z (Verification) must run after all other groups. -->

## 1. <!-- Task Group Name (e.g., Prerequisites, Core Fix) -->

- [ ] 1.1 <!-- Task description -->
- [ ] 1.2 <!-- Task description -->
- [ ] 1.3 Run `/rv-doc-code <new-file-path>` <!-- for new modules/classes -->

## 2. <!-- Task Group Name (e.g., Implementation, Cleanup) -->

- [ ] 2.1 <!-- Task description -->
- [ ] 2.2 <!-- Task description -->
- [ ] 2.3 Run `/rv-test-run <module>`

## 3. Verification

- [ ] 3.1 Run `/rv-qa-lint-fix <module>`
- [ ] 3.2 Run `/rv-verify <module>`
- [ ] 3.3 Verify acceptance criteria from plan.md
