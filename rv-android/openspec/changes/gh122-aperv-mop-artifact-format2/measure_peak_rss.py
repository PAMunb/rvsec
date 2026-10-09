"""Task 7.7 of gh122: the peak memory of the derive path, before and after design D10.

Runs one derivation of one `.apk.json` copy and exits; the peak resident memory is
read by the caller from `/usr/bin/time -v` ("Maximum resident set size"). One mode
per fresh process, so neither run inherits the other's heap.

- `before`: the source read as it was before D10, restated here line for line from
  `tool.py` at commit c7da2cec: the whole file read into one `bytes` object, hashed,
  parsed with `json.loads`, and kept referenced until `derive()` returns.
- `after`: `ApeRVTool._derive_mop_artifact` itself, which hashes the file in chunks
  and parses it with `json.load` from a UTF-8 text handle.

Both modes derive and serialize the same artifact. `after` writes
`<apk>.mop.json` next to the copy, as the tool does in a task's results directory,
so the copy must live in a scratch directory, never beside an original. It also
deletes a cached `<apk>.mop.json` first, so the run is a cache miss.

Usage, from the repository root, one at a time (the documents are large and the
host's memory is shared). The interpreter is called directly so that `time` measures
the derive's process and not a launcher:
    /usr/bin/time -v .venv/bin/python -I <change>/measure_peak_rss.py before <copy>
    /usr/bin/time -v .venv/bin/python -I <change>/measure_peak_rss.py after <copy>
"""

import hashlib
import json
import os
import sys
from unittest.mock import MagicMock

from aperv_tool.tools.aperv import derive_mop_artifact as dm
from aperv_tool.tools.aperv.tool import ApeRVTool


def before(path):
    with open(path, "rb") as source_file:
        raw = source_file.read()
    digest = f"{dm.DIGEST_ALGORITHM}:{hashlib.sha256(raw).hexdigest()}"
    artifact = dm.derive(
        json.loads(raw), source_file=os.path.basename(path), source_digest=digest
    )
    payload = dm.serialize_canonical(artifact)
    print(f"before: {len(raw)} -> {len(payload)} bytes")


def after(path):
    directory, name = os.path.split(os.path.abspath(path))
    apk_name = name.removesuffix(".json")
    artifact_path = os.path.join(directory, f"{apk_name}{dm.ARTIFACT_SUFFIX}")
    if os.path.exists(artifact_path):
        os.unlink(artifact_path)
    task = MagicMock()
    task.results_dir = directory
    task.config.apk_name = apk_name
    written = ApeRVTool()._derive_mop_artifact(task)
    print(f"after: {os.path.getsize(path)} -> {os.path.getsize(written)} bytes")


if __name__ == "__main__":
    {"before": before, "after": after}[sys.argv[1]](sys.argv[2])
