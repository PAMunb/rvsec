"""INV-ANA-84: the parsed copy of the analysis document is read only by rv-static-analysis.

`<apk>.static.json` is the source document without `distanceTargets` and
`targetDistances`, keyed by the source's digest. Its equality with the source holds
only through `static_analysis_parser.read_static_analysis_files`, which checks the
digest before believing it: a module that opened the copy on its own would read a
stale one as current after a re-analysis, and a device-side consumer would find no
distances in it. So the rule is checked over the workspace's code rather than left to
convention.
"""

import os

# Assembled from two pieces so this file's own source is not a match.
PARSED_COPY_SUFFIX = ".static" + ".json"
# The constant that spells the suffix. A production module that names it is
# building the copy's path, which is the parser's job.
PARSED_COPY_CONSTANT = "EXTENSION_PARSED_" + "COPY"

OWNING_MODULE = "rv-static-analysis"
# Where the suffix is defined; the only permitted match outside the owning module.
PERMITTED = {
    os.path.join("rv-android-core", "src", "rv_android_core", "constants.py"),
}


def _modules_root() -> str:
    """The workspace `modules/` directory, from this test file's location."""
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )


def test_no_module_outside_rv_static_analysis_references_the_parsed_copy():
    """
    Every `.py` file under `modules/`, sources and tests, is scanned for the suffix;
    every `.py` file under a module's `src/` is also scanned for the constant that
    spells it. A test elsewhere may name the constant — checking that the copy is
    written, say — but production code outside this module may not.

    Scope is `modules/`, the workspace's importable code. `rv-static-analysis` is
    skipped whole: it is the copy's owner, and this test lives in it.
    """
    root = _modules_root()
    offenders = []
    for module_dir in sorted(os.listdir(root)):
        module_path = os.path.join(root, module_dir)
        if module_dir == OWNING_MODULE or not os.path.isdir(module_path):
            continue
        for current, dirs, files in os.walk(module_path):
            dirs[:] = [d for d in dirs if d not in {"__pycache__", ".venv"}]
            for file_name in files:
                if not file_name.endswith(".py"):
                    continue
                path = os.path.join(current, file_name)
                relative = os.path.relpath(path, root)
                if relative in PERMITTED:
                    continue
                in_src = relative.split(os.sep)[1:2] == ["src"]
                with open(path, "r", errors="replace") as handle:
                    for number, line in enumerate(handle, start=1):
                        if PARSED_COPY_SUFFIX in line or (
                            in_src and PARSED_COPY_CONSTANT in line
                        ):
                            offenders.append(f"{path}:{number}: {line.strip()}")

    assert offenders == [], (
        "the parsed copy is read only through static_analysis_parser; these "
        "references are outside rv-static-analysis:\n" + "\n".join(offenders)
    )


def test_the_permitted_definition_exists():
    """The permitted match is real: if the constant moves, this list must follow."""
    for relative in PERMITTED:
        with open(os.path.join(_modules_root(), relative)) as handle:
            assert PARSED_COPY_SUFFIX in handle.read()
