"""gh123 task 5.2 — one reader per process, for `/usr/bin/time -v` to report its peak RSS.

Modes:
  parse  <doc>              StaticAnalysisParser.parse_file (streaming, no parsed copy)
  cache  <results_dir> <apk> read_static_analysis_files: the first call on a directory
                            streams the source and writes <apk>.static.json, a second
                            call answers from that copy
  derive <doc>              the aperv derive on a cache miss: streaming read with the
                            pair reduction, derive(), serialize_canonical()

Paths are arguments; the script names no document. Run one process at a time.
Usage: /usr/bin/time -v uv run python -I measure_peak_rss.py <mode> <args...>
"""

import os
import sys
import time

from rv_android_core.constants import EXTENSION_PARSED_COPY


def main(mode: str, args: list[str]) -> None:
    started = time.monotonic()
    if mode == "parse":
        from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

        model = StaticAnalysisParser().parse_file(args[0])
        detail = f"methods={len(model.classes.methods)} windows={len(model.windows.windows)} transitions={len(model.wtg.transitions)}"
    elif mode == "cache":
        from rv_static_analysis.parser.static import static_analysis_parser

        results_dir, apk = args
        copy_path = os.path.join(results_dir, apk + EXTENSION_PARSED_COPY)
        hit = os.path.exists(copy_path)
        model = static_analysis_parser.read_static_analysis_files(results_dir, apk)
        detail = (
            f"{'hit' if hit else 'miss'} methods={len(model.classes.methods)} "
            f"copy_bytes={os.path.getsize(copy_path) if os.path.exists(copy_path) else 0}"
        )
    elif mode == "derive":
        from aperv_tool.tools.aperv.derive_mop_artifact import (
            DIST_K,
            DIST_WEIGHED_MAX,
            derive,
            serialize_canonical,
        )
        from rv_android_core.util.analysis_document import (
            PairPolicy,
            digest_of_file,
            read_analysis_document,
        )

        path = args[0]
        digest = digest_of_file(path)
        document, truncated = read_analysis_document(path, PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K))
        payload = serialize_canonical(derive(document, source_file=os.path.basename(path), source_digest=digest))
        detail = f"truncated={truncated} artifact_bytes={len(payload)}"
    else:
        raise SystemExit(f"unknown mode {mode!r}")
    print(f"{mode} {' '.join(args)}: {detail} wall={time.monotonic() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
