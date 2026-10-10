"""INV-ANA-89 on one document pair: the MOP artifact derived from the full and from
the compact document (same provenance passed to derive(), since source.digest names
the input file) is byte-identical, and StaticAnalysisParser gives the same model.
Both reads stream; neither document is json.load-ed."""
import hashlib
import sys

from aperv_tool.tools.aperv.derive_mop_artifact import DIST_K, DIST_WEIGHED_MAX, derive, serialize_canonical
from rv_android_core.util.analysis_document import PairPolicy, read_analysis_document
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

full, compact = sys.argv[1:3]


def artifact(path):
    document, truncated = read_analysis_document(path, PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K))
    assert not truncated, path
    return serialize_canonical(derive(document, source_file="x.apk.json", source_digest="0" * 64))


def snapshot(path):
    data = StaticAnalysisParser().parse_file(path)
    snap = data.model_dump(mode="json")
    snap["wtg"]["window_ids"] = sorted(snap["wtg"]["window_ids"])
    snap["wtg_edges"] = sorted(
        (s, t, [(e.widget_id, e.event_type.name, e.method, e.target_window_class, e.target_reaches_target)
                for e in a["events"]])
        for s, t, a in data.wtg.graph.edges(data=True)
    )
    return snap, len(data.classes.methods)


a_full, a_compact = artifact(full), artifact(compact)
print("derive", "byte-identical" if a_full == a_compact else "DIFFERENT",
      len(a_full), hashlib.sha256(a_full).hexdigest()[:12])
(s_full, n), (s_compact, _) = snapshot(full), snapshot(compact)
print("parser", "equal" if s_full == s_compact else "DIFFERENT", f"methods={n}")
