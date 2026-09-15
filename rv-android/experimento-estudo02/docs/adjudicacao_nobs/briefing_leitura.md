# NOBS census — shared briefing for every dossier agent

You are one of several read-only agents classifying every `NOBS` accusation of the campaign
`experimento-estudo02` (jca_android spec set, dexlib2 weaver, 163 Android apps). You write ONLY
inside `SP=/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/130bf8f2-f1f3-46d3-88ea-a2754d0a35ab/scratchpad/nobs`
(downloads go to `$SP/src/`). You never modify any repository, never commit, never start
emulators or containers, never run `find` from `/home/pedro`, `/pedro`, `/arquivos` or `/` (slow
HDD: it freezes the machine). Do NOT read any `docs/analise_*` file (other models' analyses). The
shell `grep` is an ugrep wrapper: use `/usr/bin/grep`. System `python3` has no pandas; use
`uv run python` from `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android`.

## What NOBS means (verified by the orchestrator)

A `jca_android` `.mop` event reads a CrySL `REQUIRES` predicate through
`PredicateStore.instance().validate(Property.X, obj, values...)` (or `validateAny`). Source:
`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`.
It returns `NOT_OBSERVED` — and the spec emits a `…-NOBS-nn` code — when:

1. `obj` is `null` (line 343-345), or
2. no `ensure(Property.X, <that exact object>)` was ever recorded. The store is keyed by **object
   identity** (weak refs, `System.identityHashCode`), not `equals`: a copy of an array
   (`Arrays.copyOf`, `copyOfRange`, `clone`, `System.arraycopy` into a new array, `ByteBuffer`
   slicing, re-encoding) carries no predicate even if the original did.

`VIOLATED` (a different code family, not ours) means the object carries the predicate with other
values or it was withdrawn. So NOBS = "the monitor never saw this exact object come out of an
accepted producer".

Producers are other events (often in other specs) that call `ensure(...)`. Many producers ensure
**only when their own requirements were satisfied** (e.g. `IvParameterSpec.mop` c1 binds/prepares
only on `SATISFIED`), so an upstream NOBS can **cascade** into a downstream NOBS.

## What the weaver can and cannot see (verified)

- Monitors fire only at **call sites inside the APK's own dex code**. The aspect's
  `baseAspectExclusions` skip classes in `sun..*, java..*, javax..*, com.sun..*,
  org.dacapo.harness..*, org.apache.commons..*, org.apache.geronimo..*, net.sf.cglib..*, mop..*,
  javamoprt..*, rvmonitorrt..*, com.runtimeverification..*`. Everything else bundled in the APK
  (app code, `androidx`, `kotlin`, `com.google.*` incl. tink/gms, okhttp, ktor, bundled
  bouncycastle/spongycastle/conscrypt) IS woven.
- Anything executed inside the Android framework / boot classpath (system Conscrypt provider,
  `android.security.keystore*`, `javax.crypto` internals, `sun.security.*`) is never observed: an
  object produced there reaches the app with no predicate.
- dexlib2 `after` advice is skipped when the matched call throws (differs from AspectJ's
  after-finally). Rarely relevant for NOBS, mention only if it is.
- The spec files that ran are byte-identical to
  `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/`
  (verified: no commit touched them or rvsec-core since the campaign's pinned commit a599be6b).
  Note `IvParameterSpec.mop` and `IvChainJunction.mop` have no `Spec` suffix in the file name;
  the spec names in the data are `IvParameterSpecSpec` / `IvChainJunctionSpec`.

## Input data

- `$SP/census_methods.csv` — 99 methods, columns `id,lib,cls,method,codes,apks,runs,src`.
- `$SP/census_sites.csv` — 181 sites `(cls, method, spec, code)` with `event`, `sources` (the
  `__LOC` file:line of the call site as recorded at runtime, e.g. `Platform.kt:78` — use it to
  pin the exact call and to confirm the library version), `apks`, `lines`, `runs_nobs_only`,
  `exp` (the expectation text the spec printed), `apk_list`.
- Raw rows if you need more: `data/results/estudo02_consolidado/errors.csv` (relative to the
  rv-android root; 139 916 rows; columns
  `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg`). Load with
  pandas, filter, never print it whole.

## Where the code is

- **App sources** (built at the same HEAD the APKs were built from):
  `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-dataset/repos/<apk file name>/`
  (directory name = the `apk` value, e.g. `app.eduroam.geteduroam_2685.apk/`). Use
  `/usr/bin/grep -rn` inside ONE repo directory, never across all repos.
- **Bundled libraries** (okhttp, tink, ktor, bouncycastle, gms, …): determine the version the APK
  bundles from that app's build files (`gradle/libs.versions.toml`, `build.gradle(.kts)`,
  lockfiles; for transitive deps like tink via `androidx.security:security-crypto`, read the
  parent POM on Maven Central), then fetch `-sources.jar` from Maven Central
  (`https://repo1.maven.org/maven2/...`, reachable) or Google Maven
  (`https://maven.google.com/...`) into `$SP/src/<artifact>-<version>/` with `curl` and unzip.
  Confirm the version by checking that the `sources` line number(s) land on the monitored call.
  If versions differ across APKs, check that the relevant method is the same in each, or classify
  per version.
- **Fallback when source cannot be obtained or the line does not match**: the uninstrumented APKs
  are in `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-dataset/jca_android/apks/`;
  `rv-android/lib/dex2jar/bin/d2j-dex2jar.sh` converts to a jar and `javap -c -p -classpath <jar> <class>`
  shows the bytecode. Say explicitly when a verdict rests on bytecode.
- The context7 MCP (library docs) may help with API semantics, but a verdict must rest on the code
  at the call site, not on docs.

## The question for every site

For site `(cls, method, spec, code)`: **which object does the read name, where did that exact
object come from on the path(s) that reach this call, and does that provenance make the program
actually do the insecure thing the requirement guards against?**

Procedure, per site:
1. Open the `.mop` of `spec`, find the event that emits `code`: which `Property`, which bound
   object/argument, `validate` vs `validateAny`. Then `/usr/bin/grep -n "Property.<X>"` across the
   jca_android dir to list every producer (`ensure`) of that property: spec, event, pointcut, and
   whether the ensure is gated on the producer's own verdict (cascade).
2. Open the call site at `sources` in the right code version. Trace the named object backwards
   (within the method, to callers, fields, storage) until you reach its origin.
3. Classify.

## Categories (exactly one per site)

- `MISUSE` — the program really does what the requirement guards against: hard-coded / constant /
  derived-from-non-secret key material, fixed or predictable or reused IV/nonce where the mode needs
  a fresh one, constant salt, trust-all TrustManager / hostname-less custom trust, SecureRandom with
  fixed seed, etc.
- `LEGIT_UNOBSERVABLE` — the provenance is correct but the monitor cannot see it by construction:
  IV/nonce read from the ciphertext on decryption; key bytes loaded from storage/keyset/network/
  key agreement output; `null` meaning "system default" (e.g. `TrustManagerFactory.init((KeyStore) null)`);
  object produced inside the framework; a correct object whose identity was lost by a copy.
  Put the specific reason in `mechanism`.
- `SPEC_DEFECT` — the provenance is correct AND observable in principle (an API call in woven code
  produces it), but the spec set does not credit it: missing producer spec, producer ensures a
  different object/property, wrong bound argument, etc. Cite the `.mop` lines.
- `UNDETERMINED` — you could not establish the provenance (source unavailable, value crosses an
  opaque boundary you cannot follow). Say what is missing.

A cascade is not a category: classify by the ROOT cause and fill `root` with the upstream site
(e.g. `TRUSTMANAGERFACTORY-NOBS-00 @ okhttp3.internal.platform.Platform.platformTrustManager`).
When different paths reaching the same site have different provenances (e.g. encrypt path vs
decrypt path, or one app vs another), pick the category that covers the path(s) that actually
produced the recorded rows if you can tell (look at `event`, neighbouring rows, the app's use), and
describe the split in `notes`; if you cannot tell, use the category of the dominant path and say so.

Recognise real misuse honestly — do not default to LEGIT because code is in a well-known library,
and do not default to MISUSE because CrySL flags it. Names like `Insecure*` or "trustAll" are hints
to read carefully, not verdicts.

## Output

Write two files, named with your group id `<G>`:

1. `$SP/verdicts_<G>.csv` — one row per site (every site of your methods; count them against
   `census_sites.csv`), UTF-8, header exactly:
   `id,cls,method,spec,code,category,mechanism,root,provenance,evidence,version,confidence,notes`
   - `id`: method id from `census_methods.csv`
   - `mechanism`: short snake_case tag (e.g. `iv_from_ciphertext`, `key_from_keyset`,
     `null_default_truststore`, `trust_all_manager`, `hardcoded_key`, `copy_loses_identity`,
     `cascade`, `producer_missing_in_specset`, `framework_producer`)
   - `provenance`: one sentence, Brazilian Portuguese WITH correct accents
   - `evidence`: `file:line` references separated by ` ; ` — the .mop read, the producer(s), the
     call site and the origin of the object (library paths relative to `$SP/src/`, app paths
     relative to the repos dir)
   - `version`: library artifact:version (or `app@HEAD`, or `bytecode`)
   - `confidence`: `alta`, `média` or `baixa`
   - `notes`: Portuguese, optional
   Quote fields with commas (use Python's csv module to write it).
2. `$SP/dossie_<G>.md` — Brazilian Portuguese with correct accents: for each method, a short
   section with the code excerpt at the call site (few lines, with file:line), the backward trace of
   the object, and the verdict per code. Lead with a table of your verdicts.

Final message back to the orchestrator: the counts per category, the list of `MISUSE` sites, every
`SPEC_DEFECT` with its `.mop` line, every `UNDETERMINED` with what is missing, and anything that
looked like a systematic pattern across sites. Keep it under 600 words.
