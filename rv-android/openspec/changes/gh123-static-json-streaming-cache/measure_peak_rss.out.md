# gh123 task 5.2 — peak memory of each reader

Run on 2026-10-09 on the host (123 GB, nothing else heavy running), one process at a time, each as
`/usr/bin/time -v uv run python -I measure_peak_rss.py <mode> <args>`. Peaks are the
`Maximum resident set size` of the process (the `uv run` wrapper's child, which is the reader).
The documents are read from `rvsec-study03-replication-package/data/raw/e6-corpus/` (read only).
The `cache` mode runs on a directory under `data/gh123_measure/cache/<apk>/` whose `<apk>.json` is a
symbolic link to the corpus document, so the parsed copy is written beside the link and the corpus is
not touched.

| Reader | Document (size) | Peak RSS | Wall | Output |
|---|---|---:|---:|---|
| `parse_file` (streaming, no copy) | wikipedia (2.16 GB) | 243 MiB | 30.8 s | 39,950 methods, 331 windows, 219 transitions |
| `parse_file` (streaming, no copy) | sdmse (9.34 GB) | 230 MiB | 126.8 s | 62,386 methods, 3 windows, 0 transitions |
| `read_static_analysis_files`, miss | wikipedia | 242 MiB | 32.6 s | copy written, 17,681,500 bytes |
| `read_static_analysis_files`, hit | wikipedia | 220 MiB | 3.6 s | answered from the copy |
| `read_static_analysis_files`, miss | sdmse | 229 MiB | 129.7 s | copy written, 18,086,633 bytes |
| `read_static_analysis_files`, hit | sdmse | 209 MiB | 7.3 s | answered from the copy |
| aperv derive, miss (streaming + reduce + `derive` + serialize) | wikipedia | 187 MiB | 43.6 s | artifact 796,361 bytes |
| aperv derive, miss (streaming + reduce + `derive` + serialize) | sdmse | 685 MiB | 190.9 s | artifact 1,135,233 bytes |

## Against the scenario thresholds

- *a 2.16 GB document parses inside a campaign container* — wikipedia's streaming parse peaks at
  243 MiB, under the 3 GiB threshold (and the 7 GiB+ it reached before, when the container was
  killed in the first smoke run).
- *the largest corpus document derives inside a campaign container* — sdmse's derive peaks at
  685 MiB, under the 3 GiB threshold (about 29 GB projected for the whole-document `json.load`).

No measured peak contradicts a scenario, so task 5.3 needs no spec amendment.

## Notes

- The parsed copies are 17.7 MB (wikipedia) and 18.1 MB (sdmse) — 0.8 % and 0.19 % of their sources.
- A hit's wall time is the SHA-256 of the source plus a `json.load` of the copy; here the source was in
  the host's page cache from the previous run. On a cold cache the digest of sdmse is a sequential read of
  9.34 GB at disk speed.
- The streaming read runs at about 70 MB/s (wikipedia 2.16 GB in 30.8 s; sdmse 9.34 GB in 126.8 s); the
  derive with reduction at about 49 MB/s (sdmse in 190.9 s), and sdmse keeps about 3.8 M reduced pairs (count in `design.md`, Risks), which
  is what lifts its derive peak to 685 MiB.
