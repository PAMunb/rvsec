# gh122 task 7.7: peak memory of the derive path, before and after design D10

- **Run:** 2026-10-09, at commit `cf012e98` (groups 4, 6 and 7 of this change), with `measure_peak_rss.py` from this folder.
- **Host:** 123 GB of RAM, 106 GB available before the first run. One run at a time, each in a fresh process.
- **File:** `at.techbee.jtx_216000015.apk.json`, round A of the Study 03 v2 static analysis
  (`rvsec-study03-replication-package/data/raw/e6-static-analysis/final/`).
  - Size: **2,017,546,684 bytes**, which is 2.018 GB or 1.879 GiB. The "1.92 GB" quoted for this file earlier matches neither unit.
  - sha256 of the copy: `26c154416c0aea77188c246f5d949b8f3e48b0dec9570ca401106b08511c7355`, equal to the original's.
  - The copy sat in the gitignored `out/gh122_rss/`, on disk. `/tmp` on this host is tmpfs, so a copy there would have occupied RAM during the runs. The copy and the directory were deleted afterwards. Nothing was written next to the original.
- **Modes:**
  - `before` restates the read of `tool.py` at `c7da2cec`: the whole file read into one `bytes` object, hashed, parsed with `json.loads`, and kept referenced until `derive()` returns.
  - `after` calls `ApeRVTool._derive_mop_artifact` itself on a cache miss: `digest_of_file`, then `json.load` from a UTF-8 text handle.
- **Units:** `/usr/bin/time -v` reports "Maximum resident set size" in KiB. The GB figures below are 10^9 bytes; GiB is given beside them.

## Commands

From the repository root, one at a time:

```bash
C=openspec/changes/gh122-aperv-mop-artifact-format2
F=out/gh122_rss/at.techbee.jtx_216000015.apk.json
/usr/bin/time -v .venv/bin/python -I $C/measure_peak_rss.py before $F   # run 1, then again for run 2
/usr/bin/time -v .venv/bin/python -I $C/measure_peak_rss.py after  $F   # run 1, then again for run 2
```

The order was before 1, after 1, before 2, after 2.

## Result

| run | peak RSS (KiB) | peak RSS | peak / file size | wall time | artifact |
|---|---|---|---|---|---|
| before 1 | 8,107,048 | 8.302 GB (7.731 GiB) | 4.115 | 0:32.62 | 470,047 bytes |
| before 2 | 8,107,744 | 8.302 GB (7.732 GiB) | 4.115 | 0:31.73 | 470,047 bytes |
| after 1 | 6,135,896 | 6.283 GB (5.852 GiB) | 3.114 | 0:32.37 | 470,047 bytes |
| after 2 | 6,136,452 | 6.284 GB (5.852 GiB) | 3.115 | 0:31.53 | 470,047 bytes |

- **The saving is one file size.** Paired by run, it is 1,971,152 KiB and 1,971,292 KiB: 2.018 GB (1.880 GiB), which is 1.0005 times the file's size. That is **24.3 %** of the peak before D10, in both pairs. The peak falls from 4.1 to 3.1 times the file's size.
- **The spread is small.** The two runs of a mode differ by 696 KiB (`before`) and 556 KiB (`after`), under 0.01 % of the peak.
- **The output is unchanged.** All four runs derive a 470,047-byte artifact. The sha256 of the one `after` wrote is `87e2f6320a12785918e04adf235fba26010ce9c62415b5756026c97ce267d87e`, the same after both runs.
- **The wall time is unchanged.** It is 31.5 to 32.6 s in both modes, almost all of it in the parse and the derivation. Streaming the digest costs no time a reader would notice.

## What the saving is made of

What D10 removes is the `bytes` object, and nothing else. The decoded text is still built in both modes:
- before D10, `json.loads(raw)` decodes the bytes into a `str` before it parses;
- with D10, `json.load(fp)` gets the same `str` from `fp.read()`.

So the peak with D10 holds the text and the parsed document, about 3.1 file sizes. The peak before also held the `bytes`. The design expected "about one file size of a peak of about four", and the measurement agrees. This file is pure ASCII (0 bytes above 0x7F, counted on the copy), so its `str` takes one byte per character. A document whose text forced a wider `str` would cost more in both modes, and the saving would stay one file size.

## Raw `time -v` lines

```
== before 1
before: 2017546684 -> 470047 bytes
	Command being timed: ".venv/bin/python -I openspec/changes/gh122-aperv-mop-artifact-format2/measure_peak_rss.py before out/gh122_rss/at.techbee.jtx_216000015.apk.json"
	User time (seconds): 26.03
	System time (seconds): 6.58
	Percent of CPU this job got: 99%
	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:32.62
	Maximum resident set size (kbytes): 8107048
	Exit status: 0
== after 1
after: 2017546684 -> 470047 bytes
	Command being timed: ".venv/bin/python -I openspec/changes/gh122-aperv-mop-artifact-format2/measure_peak_rss.py after out/gh122_rss/at.techbee.jtx_216000015.apk.json"
	User time (seconds): 26.50
	System time (seconds): 5.85
	Percent of CPU this job got: 99%
	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:32.37
	Maximum resident set size (kbytes): 6135896
	Exit status: 0
== before 2
before: 2017546684 -> 470047 bytes
	Command being timed: ".venv/bin/python -I openspec/changes/gh122-aperv-mop-artifact-format2/measure_peak_rss.py before out/gh122_rss/at.techbee.jtx_216000015.apk.json"
	User time (seconds): 25.57
	System time (seconds): 6.14
	Percent of CPU this job got: 99%
	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:31.73
	Maximum resident set size (kbytes): 8107744
	Exit status: 0
== after 2
after: 2017546684 -> 470047 bytes
	Command being timed: ".venv/bin/python -I openspec/changes/gh122-aperv-mop-artifact-format2/measure_peak_rss.py after out/gh122_rss/at.techbee.jtx_216000015.apk.json"
	User time (seconds): 25.63
	System time (seconds): 5.87
	Percent of CPU this job got: 99%
	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:31.53
	Maximum resident set size (kbytes): 6136452
	Exit status: 0
```

Both `after` runs also logged `Derived MOP artifact … (2017546684 -> 470047 bytes, flagged=0/0 widgets, mopActivities=0, recovered=0)`. jtx has no flagged widget and no MOP activity. That does not bear on this measurement, which is about the source read.
