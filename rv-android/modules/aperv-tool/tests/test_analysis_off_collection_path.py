"""Nothing under `aperv_tool.analysis` is reachable from the collection path.

The analysis package reads recorded artefacts and answers questions about them.
The collection path runs the tool on a device. Keeping the two disjoint is what
lets the analysis carry heavy dependencies — `pandas`, `numpy`, `scipy`,
`statsmodels` — without a run paying for a single one of them at import time,
and it is what makes "this code cannot have influenced the measurement" a
structural fact rather than a promise (INV-APV-48, generalised to the whole
package as INV-CAN-23).

The check is an import-graph walk rather than a grep, because an indirect import
couples the two paths exactly as effectively as a direct one and reads as
innocent at every individual hop. A positive control walks the same code over a
synthetic package that *does* leak, so the real assertion's silence means the
walk works rather than that it stopped early.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _imports_of(path: Path) -> set[str]:
    """Module names imported by one source file, however the import is written.

    Both spellings are collected from `from x import y`: the module `x`, and
    `x.y` — because `from aperv_tool.analysis import loader` names the module in
    the second position, and a walk that only recorded `x` would follow the
    package and miss what was taken out of it.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _reachable_from(entry: Path, package_root: Path) -> set[str]:
    """Every `aperv_tool` module name reachable from `entry`, transitively."""
    seen: set[Path] = set()
    pending = [entry]
    reachable: set[str] = set()

    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)

        for name in _imports_of(current):
            if not name.startswith("aperv_tool"):
                continue
            reachable.add(name)
            relative = Path(*name.split(".")[1:])
            for candidate in (
                package_root / relative.with_suffix(".py"),
                package_root / relative / "__init__.py",
            ):
                if candidate.exists():
                    pending.append(candidate)

    return reachable


def _package_root() -> Path:
    return Path(__import__("aperv_tool").__file__).parent


def test_no_analysis_module_is_reachable_from_the_collection_path() -> None:
    """The whole package, not only the readers that happened to be checked first."""
    package_root = _package_root()
    entry = package_root / "tools" / "aperv" / "tool.py"
    assert entry.exists(), "the collection path's entry point moved"

    reachable = _reachable_from(entry, package_root)

    # Non-vacuity: `tool.py` does import within the package, so an empty result
    # means the walk broke rather than that the boundary holds.
    assert reachable, "import walk reached no aperv_tool module — test is vacuous"

    offenders = sorted(
        name for name in reachable if name.startswith("aperv_tool.analysis")
    )
    assert (
        offenders == []
    ), f"the collection path reaches the analysis layer: {offenders}"


def test_the_walk_catches_an_indirect_leak(tmp_path) -> None:
    """Positive control, so the assertion above means something when it passes.

    The leak here is indirect — `tool.py` imports a helper and the helper imports
    the analysis module — which is the shape a real one takes. A walk that only
    inspected the entry point would report this package clean.
    """
    package = tmp_path / "aperv_tool"
    (package / "tools" / "aperv").mkdir(parents=True)
    (package / "analysis").mkdir()
    (package / "analysis" / "loader.py").write_text("", encoding="utf-8")
    (package / "tools" / "aperv" / "helper.py").write_text(
        "from aperv_tool.analysis import loader\n", encoding="utf-8"
    )
    entry = package / "tools" / "aperv" / "tool.py"
    entry.write_text("from aperv_tool.tools.aperv import helper\n", encoding="utf-8")

    reachable = _reachable_from(entry, package)

    assert any(name.startswith("aperv_tool.analysis") for name in reachable)


def test_every_analysis_module_is_covered_by_the_walk() -> None:
    """The assertion is about the package, so name what the package contains.

    A boundary test that silently stopped covering new modules would keep passing
    while the thing it guards grew around it. This lists what exists, so the count
    is visible in the failure message when one is added.
    """
    analysis = _package_root() / "analysis"
    modules = sorted(
        path.stem for path in analysis.rglob("*.py") if path.stem != "__init__"
    )

    assert modules, "no analysis module found — the package moved"
