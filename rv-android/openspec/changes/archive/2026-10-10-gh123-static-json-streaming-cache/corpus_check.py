"""gh123 task 5.1 — streaming readers against the whole-document path, on real documents.

For each document given on the command line:

1. parser: the model `StaticAnalysisParser.parse_file` builds in streaming equals the
   model the section parsers build from `json.load` of the same file (INV-ANA-80);
2. derive: `serialize_canonical(derive(...))` of the document read in streaming with
   `PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K)` is byte-identical to the one of
   `json.load` of the same file (INV-APV-64).

The corpus documents are inputs passed as paths; nothing here names one. The
`json.load` side holds the whole document (about 3 times its size), so run one
process at a time and check the file size first.

Usage: python -I corpus_check.py <doc.apk.json> [...]   (prints one Markdown row each)
"""

import gc
import json
import os
import sys
import time

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
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser


def snapshot(model) -> dict:
    """Every field a consumer can read (same comparison as TestStreamingEquivalence)."""
    data = model.model_dump(mode="json")
    data["wtg"]["window_ids"] = sorted(data["wtg"]["window_ids"])
    data["wtg_edges"] = sorted(
        (
            source,
            target,
            [
                (e.widget_id, e.event_type.name, e.method, e.target_window_class, e.target_reaches_target)
                for e in attributes["events"]
            ],
        )
        for source, target, attributes in model.wtg.graph.edges(data=True)
    )
    return data


def check(path: str) -> str:
    name = os.path.basename(path)
    digest = digest_of_file(path)
    parser = StaticAnalysisParser()

    t0 = time.monotonic()
    model = parser.parse_file(path)
    methods = len(model.classes.methods)
    streamed_model = snapshot(model)
    del model
    t_parse = time.monotonic() - t0

    t0 = time.monotonic()
    reduced, truncated = read_analysis_document(path, PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K))
    assert not truncated, f"{name}: truncated"
    streamed_artifact = serialize_canonical(derive(reduced, source_file=name, source_digest=digest))
    t_derive = time.monotonic() - t0
    del reduced
    gc.collect()

    t0 = time.monotonic()
    with open(path, encoding="utf-8") as handle:
        whole = json.load(handle)
    reference_model = snapshot(parser._build_model(whole))
    reference_artifact = serialize_canonical(derive(whole, source_file=name, source_digest=digest))
    t_whole = time.monotonic() - t0
    del whole
    gc.collect()

    model_equal = streamed_model == reference_model
    artifact_equal = streamed_artifact == reference_artifact
    return (
        f"| {name} | {os.path.getsize(path) / 1e9:.3f} | {methods} | "
        f"{'yes' if model_equal else '**NO**'} | {'yes' if artifact_equal else '**NO**'} | "
        f"{len(streamed_artifact)} | {t_parse:.0f} | {t_derive:.0f} | {t_whole:.0f} |"
    )


if __name__ == "__main__":
    for argument in sys.argv[1:]:
        print(check(argument), flush=True)
