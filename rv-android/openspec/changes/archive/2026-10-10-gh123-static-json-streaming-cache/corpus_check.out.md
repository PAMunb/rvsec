# gh123 task 5.1 — corpus check

Run on 2026-10-09 on the host, one process per document, in sequence, with
`uv run python -I corpus_check.py <doc>`. Documents are the gh120 final `.apk.json` files of
`rvsec-study03-replication-package/data/raw/e6-corpus/` (read only).

For each document, `corpus_check.py` compares:

- **model**: `StaticAnalysisParser.parse_file` (streaming, `PairPolicy.DROP`) against the section
  parsers applied to `json.load` of the same file, compared field by field (Pydantic dump plus WTG
  edges, as `TestStreamingEquivalence`);
- **artifact**: `serialize_canonical(derive(...))` of the document read in streaming with
  `PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K)` against the same of `json.load`, byte for byte.

| Document | GB | methods | model equal | artifact byte-identical | artifact bytes | parse s | derive s | `json.load` path s |
|---|---:|---:|---|---|---:|---:|---:|---:|
| org.fossify.keyboard_14.apk.json | 0.020 | 1010 | yes | yes | 55268 | 2 | 1 | 2 |
| net.pfiers.osmfocus_1009013.apk.json | 0.031 | 3446 | yes | yes | 38806 | 0 | 1 | 1 |
| com.absinthe.libchecker_2671.apk.json | 0.070 | 10420 | yes | yes | 95355 | 1 | 1 | 1 |
| at.techbee.jtx_216000015.apk.json | 2.018 | 22934 | yes | yes | 470047 | 27 | 38 | 27 |
| org.wikipedia_50595.apk.json | 2.160 | 39950 | yes | yes | 796361 | 30 | 43 | 44 |

The process peaks (`/usr/bin/time`) are those of the whole check, dominated by the `json.load`
reference side: 6.19 GB for jtx and 14.97 GB for wikipedia (the reference holds the whole document
and its derived artifact at once). They are not the readers' peaks; task 5.2 measures those one
reader per process.

The three small documents cover a complete document with a WTG (`fossify.keyboard`, 15 transitions,
`complete=true`) and two pre-WTG documents (`complete=false`, no `transitions`); wikipedia is complete
with 219 transitions, jtx is pre-WTG.
