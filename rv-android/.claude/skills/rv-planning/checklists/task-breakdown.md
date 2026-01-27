# Task Breakdown Guidelines

How to decompose work into manageable, bite-sized tasks.

---

## Decomposition Principles

### 1. Single Responsibility

Each task should do ONE thing:

| Bad | Good |
|-----|------|
| "Update user service and add tests" | "Add validation to UserService.create()" |
| | "Add test for UserService.create() validation" |
| "Refactor and optimize" | "Extract common logic to helper function" |
| | "Add caching to frequently called method" |

### 2. Appropriate Size

Target: **2-5 minutes** implementation time per task.

| Size | Indication | Action |
|------|------------|--------|
| Too small | "Change variable name" | Combine with related tasks |
| Just right | "Add error handling to parse function" | Keep as is |
| Too large | "Implement authentication system" | Break down further |

### 3. Clear Boundaries

Each task should have:
- **Start point**: What state is assumed
- **End point**: What state is achieved
- **Verification**: How to confirm completion

---

## Decomposition Process

### Step 1: Identify the Work

List everything that needs to happen:

```markdown
Raw work items:
- Update model
- Change service
- Add validation
- Write tests
- Update docs
```

### Step 2: Group by File/Component

Organize by location:

```markdown
model.py:
- Add new field
- Update __init__

service.py:
- Import new dependency
- Add validation logic
- Handle new error case

test_service.py:
- Add test for validation
- Add test for error handling
```

### Step 3: Order by Dependency

Put foundation tasks first:

```markdown
1. Add new field to model (model.py)
2. Update model __init__ (model.py)
3. Import new dependency (service.py)
4. Add validation logic (service.py)
5. Handle new error case (service.py)
6. Add test for validation (test_service.py)
7. Add test for error handling (test_service.py)
```

### Step 4: Add Details

Fill in task template for each:

```markdown
### Task 1: Add new field to model

**Description**: Add `status` field with default value "pending"
**Files**: `src/models/model.py`
**Acceptance**: Model has status field, existing tests pass
**Risk**: Low
**Depends on**: None
```

---

## Task Types

### Code Tasks

| Type | Template |
|------|----------|
| **Create file** | Create `path/file.py` with [structure] |
| **Add function** | Add `function_name()` to `file.py` that [does what] |
| **Add class** | Add `ClassName` class with [methods] |
| **Add field** | Add `field_name` field to `ClassName` |
| **Add import** | Add import for `module` in `file.py` |
| **Modify logic** | Update `function_name()` to [new behavior] |
| **Delete code** | Remove `deprecated_function()` from `file.py` |

### Test Tasks

| Type | Template |
|------|----------|
| **Add unit test** | Add test for `function_name()` with [scenario] |
| **Add edge case** | Add test for `function_name()` when [edge case] |
| **Update test** | Update test for `function_name()` to reflect [change] |
| **Remove test** | Remove test for deleted `deprecated_function()` |

### Configuration Tasks

| Type | Template |
|------|----------|
| **Add config** | Add `setting_name` to configuration |
| **Update config** | Change `setting_name` from [old] to [new] |
| **Add dependency** | Add `package_name` to dependencies |

### Documentation Tasks

| Type | Template |
|------|----------|
| **Add docstring** | Add docstring to `function_name()` |
| **Update docs** | Update [section] in `README.md` |
| **Add example** | Add usage example for `ClassName` |

---

## Verification Criteria

Each task needs clear acceptance criteria:

### Patterns

| Pattern | Example |
|---------|---------|
| **State change** | "Field `status` exists with default 'pending'" |
| **Behavior** | "Function returns error when input is None" |
| **Test pass** | "All tests in `test_service.py` pass" |
| **Integration** | "Endpoint returns 200 with valid response" |
| **No regression** | "Existing tests continue to pass" |

### Checklist Style

```markdown
**Acceptance**:
- [ ] New field exists in model
- [ ] Default value is "pending"
- [ ] Existing tests pass
- [ ] Serialization includes new field
```

---

## Common Decomposition Mistakes

### 1. Tasks Too Large

**Symptom**: Task takes more than 10 minutes

**Fix**: Break down further

```markdown
# Too large
- Implement user authentication

# Better
- Add User model with password hash field
- Add hash_password() utility function
- Add authenticate_user() function
- Add /login endpoint
- Add test for hash_password()
- Add test for authenticate_user()
- Add test for /login endpoint
```

### 2. Tasks Too Coupled

**Symptom**: Can't complete one without the other

**Fix**: Identify the core dependency

```markdown
# Too coupled
- Task 1: Add validation
- Task 2: Add validation tests

# Better (explicit dependency)
- Task 1: Add validation
- Task 2: Add validation tests (depends on Task 1)
```

### 3. Vague Description

**Symptom**: "Update the code"

**Fix**: Be specific about what changes

```markdown
# Vague
- Update service

# Specific
- Add timeout parameter to service.fetch() with default 30s
```

### 4. Missing Acceptance Criteria

**Symptom**: "Done when it works"

**Fix**: Define observable completion

```markdown
# Missing criteria
- Acceptance: It works

# Clear criteria
- Acceptance: Function returns within 100ms for standard input
```

---

## Example Breakdowns

### Example 1: Add Logging

Original: "Add logging to the service"

Breakdown:
```markdown
1. Add logger import to service.py
2. Add logger initialization at module level
3. Add info log at service entry point
4. Add error log in exception handlers
5. Add debug log for intermediate steps
6. Add test verifying log output format
```

### Example 2: Refactor Function

Original: "Refactor calculate_total()"

Breakdown:
```markdown
1. Extract tax calculation to _calculate_tax()
2. Extract discount calculation to _calculate_discount()
3. Update calculate_total() to use helpers
4. Add test for _calculate_tax()
5. Add test for _calculate_discount()
6. Verify existing calculate_total() tests pass
```

### Example 3: Add New Endpoint

Original: "Add GET /users/{id} endpoint"

Breakdown:
```markdown
1. Add get_user_by_id() to user_repository.py
2. Add test for get_user_by_id()
3. Add get_user() to user_service.py
4. Add test for get_user()
5. Add /users/{id} route to user_router.py
6. Add test for GET /users/{id} endpoint
7. Update API documentation
```

---

## Checklist

Before finalizing tasks:

- [ ] Each task is 2-5 minutes
- [ ] Each task has single responsibility
- [ ] Each task has clear description
- [ ] Each task has specific files listed
- [ ] Each task has acceptance criteria
- [ ] Dependencies are explicit
- [ ] No circular dependencies
- [ ] Foundation tasks come first
