## 1. Rewrite CI workflow

- [x] 1.1 Rewrite `.github/workflows/ci.yml` with two independent jobs (`maven-build`, `python-test`), removing all Poetry references, dead modules, `continue-on-error`, and disk space hacks. Both jobs remove `backup/` directories after checkout.

## 2. Verification

- [x] 2.1 Validate YAML syntax of the new `ci.yml`
- [x] 2.2 Verify acceptance criteria from plan.md
