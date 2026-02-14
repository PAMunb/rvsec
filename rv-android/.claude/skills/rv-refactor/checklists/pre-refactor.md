# Pre-Refactor Checklist

Complete this checklist BEFORE starting any refactoring.

---

## 1. Analysis Complete

- [ ] Complexity metrics gathered
- [ ] Dependency analysis done
- [ ] Refactoring targets identified
- [ ] Risks assessed

## 2. Planning Complete

- [ ] Detailed plan created
- [ ] Steps ordered by dependencies
- [ ] Impact assessment done
- [ ] Rollback strategy defined

## 3. User Approval

- [ ] Analysis report presented to user
- [ ] Plan presented to user
- [ ] **User explicitly approved** (MANDATORY)

## 4. Environment Ready

- [ ] All tests currently passing
- [ ] No uncommitted changes in target files
- [ ] Backup directory exists

## 5. Backups Created

- [ ] All target files backed up
- [ ] Backup locations documented
- [ ] Rollback commands tested

---

## Pre-Flight Commands

```bash
# 1. Verify tests pass
cd modules/$MODULE
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/ -v

# 2. Check for uncommitted changes
git status

# 3. Create backup directory
mkdir -p backup

# 4. Backup target files
cp path/to/file.py backup/file_$(date +%Y%m%d).py
```

---

## Stop Conditions

**DO NOT proceed if:**

- [ ] Tests are failing
- [ ] User has not approved
- [ ] Backups not created
- [ ] Uncommitted changes exist in target files
