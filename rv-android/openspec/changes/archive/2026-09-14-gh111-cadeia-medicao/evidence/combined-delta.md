# Task 8.10 — the combined D9 + D2 + D3 delta against the verification baseline

**Run 2026-08-30.** This is a **record**, not a re-derivation. The task's own mandate is to assert
the *shape* of the movement and to state the delivered values; the values themselves were measured
by task 1.7 (`evidence/probe/README.md`) and, for `screenshottile`, by the end-to-end acceptance run
of task 1.8 (`evidence/acceptance/README.md`).

## The four collapsed denominators — the shape

Each of the four moves from its collapsed count under the manifest guard to the full universe under
its own scope key. The **delivered** column is what the artefact carries: `RvsecAnalysisClient`
applies `isAppClass` before writing, so the generated resource classes are already out.

| APK | scope key | collapsed | raw | **delivered (INV-ANA-71)** | how it was obtained |
|---|---|---:|---:|---:|---|
| `br.com.colman.petals_3040000` | `br.com.colman.petals` | 1 | 771 | **762** | `D9Probe` prediction (task 1.7) |
| `com.github.livingwithhippos.unchained_60` | `com.github.livingwithhippos.unchained` | 2 | 1971 | **1952** | `D9Probe` prediction (task 1.7) |
| `com.nononsenseapps.feeder.play_4025` | `com.nononsenseapps.feeder` | 6 | 3589 | **3578** | `D9Probe` prediction (task 1.7) |
| `com.github.cvzi.screenshottile_148` | `com.github.cvzi` (detector) | 21 | 550 | **535** | **live end-to-end run**, both jars (task 1.8) |

**762 / 1952 / 3578 / 550 are superseded**, and for two different reasons. The first three were
pipeline counts under the *root-anchored* strip; the widening to the last segment (INV-ANA-71) moves
neither of them, because all their resource classes sit at the key's root — so those three numbers
survive the change of rule with the same value, which is why the widening is invisible in them. The
fourth does not survive: 550 was the ancestor-key case, where `com.github.cvzi.screenshottile.R` and
its `R$*` matched no root-anchored pattern and stayed **inside** the denominator. Pinning 550 would
have made this change's D9 acceptance number a denominator with fifteen resource classes in it.

## The controls stay invariant

`me.zhanghai.android.untracker_9` is the live-guard control: its code package matches a
`libPackages.txt` pattern and carries no build-type suffix, so the demotion loop really runs and the
pre/post keys coincide. Pre and post agree — see `evidence/acceptance/README.md`. `app.pachli_50`
was **not** used: no `libPackages.txt` pattern matches `app.pachli.*` (the only `app`-initial entries
are `apparat.*`), so its demotion loop never runs and the control cannot fail.

## The two corpus-wide assertions

Measured over the 162 stored artefacts of
`RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162`, by running
`StaticAnalysisParser.parse_file` over each and comparing the parsed class-name set against the set
the file itself carries:

```
artefacts:                                   162
total classes parsed:                    215,430
artefacts parsing to zero:                     0
names invented by the parser:                  0
```

**0 of 162 parse to zero** — every stored artefact carries a non-empty `reachability` (1 to 14,860
classes), which is the fact INV-PLT-15/16 depend on and the reason `measured` answers to the
denominator rather than to the presence of a recorded key.

**0 names invented** — a name in the parsed set that is absent from the file is exactly what
`SignatureNormalizer.normalize_class_name` produced whenever it fired. Before D3 this figure was
**465**, in 7 of the 162 APKs, split 305 / 75 / 35 / 19 / 15 / 14 / 2
(`evidence/d3-normalizer/README.md`). It is now zero over the whole corpus, not only over the seven.

## What this record does not claim

The three probe-predicted denominators have not been re-measured by an end-to-end run. The probe is
a prediction instrument by construction — it imports nothing from `presto.android`, reimplements the
demotion predicate and never mutates the Scene — so it characterises the hypothesis and cannot
accept the repair. What accepts the repair is the `screenshottile` run, which exercises the deployed
jar through the real client and reproduces the predicted 535 exactly.
