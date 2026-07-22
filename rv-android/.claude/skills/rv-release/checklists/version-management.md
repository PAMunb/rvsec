# Version Management

Guidelines for version numbering and synchronization in uv workspaces.

---

## Semantic Versioning (SemVer)

Version format: **MAJOR.MINOR.PATCH**

| Component | Increment When | Example |
|-----------|----------------|---------|
| **MAJOR** | Incompatible API changes | 1.0.0 → 2.0.0 |
| **MINOR** | Backwards-compatible functionality | 1.0.0 → 1.1.0 |
| **PATCH** | Backwards-compatible bug fixes | 1.0.0 → 1.0.1 |

### Pre-release Versions

For testing before stable release:

| Format | Use Case | Example |
|--------|----------|---------|
| `X.Y.Z-alpha.N` | Early testing, unstable | 2.0.0-alpha.1 |
| `X.Y.Z-beta.N` | Feature complete, testing | 2.0.0-beta.1 |
| `X.Y.Z-rc.N` | Release candidate | 2.0.0-rc.1 |

### Build Metadata

Optional build information (ignored in versioning):

```
X.Y.Z+build.123
X.Y.Z+20260124
```

---

## Version Identification

Every version is uniquely identified by:

1. **Component name** - The module name (e.g., `rv-android-core`)
2. **Version number** - SemVer string (e.g., `1.2.3`)

Example: `rv-android-core-1.2.3`

### Where Versions Are Stored

| Location | Purpose | Format |
|----------|---------|--------|
| `pyproject.toml` | Package metadata | `version = "1.2.3"` |
| `__init__.py` | Runtime access | `__version__ = "1.2.3"` |
| Git tag | Release marker | `v1.2.3` |

---

## Multi-Module Version Strategies

### Synchronized Versioning (Recommended)

All modules share the same version number.

**Pros**:
- Simple to understand
- Clear what versions work together
- Easy release coordination

**Cons**:
- Patch to one module bumps all
- May seem like more changes than actual

**Implementation**:
```bash
# All modules at v1.2.3
# Any change → all bump to v1.2.4 or v1.3.0 or v2.0.0
```

### Independent Versioning

Each module has its own version.

**Pros**:
- Granular version control
- Only bump what changed

**Cons**:
- Complex dependency management
- Need compatibility matrix
- Harder to communicate "what works together"

**Implementation**:
```bash
# rv-android-core: v2.1.0
# rv-agent: v1.5.3
# Must document which versions are compatible
```

### Hybrid Approach

Core modules synchronized, extensions independent.

**Implementation**:
```bash
# Core (synchronized): rv-android-core, rv-platform, rv-tools
# Extensions (independent): aperv-llm-validation
```

---

## Version Synchronization

### Check Version Consistency

```bash
#!/bin/bash
# Check all module versions
echo "Module Versions:"
echo "================"
for dir in modules/*/; do
    name=$(basename "$dir")
    if [ -f "$dir/pyproject.toml" ]; then
        version=$(grep '^version = ' "$dir/pyproject.toml" | cut -d'"' -f2)
        echo "$name: $version"
    fi
done
```

### Sync Versions Script

```bash
#!/bin/bash
# Sync all modules to a new version
NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

for dir in modules/*/; do
    name=$(basename "$dir")
    if [ -f "$dir/pyproject.toml" ]; then
        # Update pyproject.toml
        sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" "$dir/pyproject.toml"

        # Update __init__.py if exists
        init_file="$dir/src/${name//-/_}/__init__.py"
        if [ -f "$init_file" ]; then
            sed -i "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/" "$init_file"
        fi

        echo "Updated $name to $NEW_VERSION"
    fi
done
```

---

## Dependency Version Constraints

### Constraint Types

| Constraint | Meaning | Example |
|------------|---------|---------|
| `^1.2.3` | Compatible | >=1.2.3, <2.0.0 |
| `~1.2.3` | Patch-level | >=1.2.3, <1.3.0 |
| `>=1.2.3` | Minimum version | >=1.2.3 |
| `==1.2.3` | Exact version | Only 1.2.3 |
| `>=1.2,<2.0` | Range | >=1.2.0, <2.0.0 |

### Inter-Module Dependencies

For internal modules, use compatible constraint:

```toml
[project.dependencies]
rv-android-core = "^1.2.3"
```

This allows:
- Patch updates automatically (1.2.4, 1.2.5)
- Minor updates automatically (1.3.0, 1.4.0)
- Blocks major updates (2.0.0 requires manual update)

---

## Version Bump Decision Tree

```
Has the public API changed in a backwards-incompatible way?
│
├── YES → MAJOR bump (X.0.0)
│         Examples:
│         - Removed public function
│         - Changed function signature
│         - Changed return type
│         - Renamed module/package
│
└── NO → Has new functionality been added?
         │
         ├── YES → MINOR bump (X.Y.0)
         │         Examples:
         │         - New public function
         │         - New optional parameter
         │         - New module
         │         - Deprecated (but not removed) API
         │
         └── NO → PATCH bump (X.Y.Z)
                   Examples:
                   - Bug fix
                   - Performance improvement
                   - Documentation update
                   - Internal refactoring
```

---

## Deprecation Process

When removing features, follow deprecation cycle:

### Phase 1: Deprecation Warning (Minor Release)

```python
import warnings

def old_function():
    warnings.warn(
        "old_function is deprecated and will be removed in v2.0.0. "
        "Use new_function instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function()
```

### Phase 2: Document Deprecation

In CHANGELOG.md:
```markdown
### Deprecated
- `old_function()` - Use `new_function()` instead. Will be removed in v2.0.0.
```

### Phase 3: Remove (Major Release)

In the major release:
- Remove deprecated code
- Document in CHANGELOG.md as "Breaking Changes"
- Update migration guide

---

## Version in Code

### Reading Version at Runtime

```python
# In __init__.py
__version__ = "1.2.3"

# Or read from pyproject.toml
from importlib.metadata import version
__version__ = version("rv-android-core")
```

### Version Checks

```python
from packaging import version

if version.parse(rv_android_core.__version__) >= version.parse("2.0.0"):
    # Use new API
    pass
else:
    # Use old API
    pass
```

---

## Quick Reference

### Bump Commands

```bash
# Manual version bump
# Edit pyproject.toml version field directly

# Manual
# Edit pyproject.toml directly
```

### Check Current Version

```bash
# From pyproject.toml
grep '^version = ' pyproject.toml

# From installed package
python -c "import rv_android_core; print(rv_android_core.__version__)"

# From pyproject.toml
grep '^version = ' pyproject.toml | cut -d'"' -f2
```
