# CLAUDE.md - rvsec-apk

## Purpose

APK metadata reader: parses an APK's `AndroidManifest.xml` (via FlowDroid's `ProcessManifest`
over binary AXML) to extract package name, application class, activities, and the
main-activity (intent-filter `android.intent.action.MAIN`). Also wraps Apktool for full
APK decompilation. No coverage/permission/service/receiver parsing despite what the
module README implies (see Gotchas).

## Role in pipeline

Runs before GATOR static analysis to give it a normalized view of "what package/activities
does this APK declare" — GATOR component enumeration and `AndroidUtil.isClassInApplicationPackage`
use `AppInfo` to decide whether a `SootClass` belongs to the app or to a library/framework.

## Relationships

- ⟶ `rvsec-gator` (`rvsec-gator/sootandroid`, `commons`): consumes `AppInfo`/`ActivityInfo`
  for component enumeration and app-vs-framework class classification.
- Depends on soot-infoflow(-android) (FlowDroid) for manifest/AXML parsing, not on
  `rv-android` (Python) directly; the Python side never imports this module — it consumes
  the artifacts this module produces indirectly through GATOR's output.

## Dependencies

- Internal: none within `rvsec-android` (leaf module for FlowDroid/Apktool integration).
- External: `de.fraunhofer.sit.sse.flowdroid:soot-infoflow` / `soot-infoflow-android`
  2.10.0, `org.apktool:apktool-lib` / `apktool-cli` 2.10.0 (version managed by parent
  `rvsec-android/pom.xml`).

## Key components

| Component | File | Purpose |
|---|---|---|
| `AppInfo` | `src/main/java/br/unb/cic/rvsec/apk/model/AppInfo.java` | Package, app name, label, activity set + main activity |
| `ActivityInfo` | `src/main/java/br/unb/cic/rvsec/apk/model/ActivityInfo.java` | Activity FQCN, short name, package, `isMain` |
| `AppReader` | `src/main/java/br/unb/cic/rvsec/apk/reader/AppReader.java` | `readApk(path)` (manifest → `AppInfo`), `decompileApp(AppInfo)` (Apktool decode) |
| `AndroidUtil` | `src/main/java/br/unb/cic/rvsec/apk/util/AndroidUtil.java` | `isAndroidMethod`, `isClassInApplicationPackage`, `isClassInSystemPackage` |
| `FileUtil`, `StringUtil` | `src/main/java/br/unb/cic/rvsec/apk/util/{FileUtil,StringUtil}.java` | Recursive dir delete; APK-path → label extraction |

## Build & invocation

`mvn clean install` from the module or the root reactor. The `package` phase runs
`maven-dependency-plugin:copy` to place `apktool-cli` at
`${main.basedir}/rv-android/lib/apktool/apktool.jar` — a side-effect consumed by the
Python `rv-android` pipeline (not by any Java module).

## References

- Consumers: `rvsec-gator/sootandroid` (component/app-package classification), `rvsec-gator/commons`.

## Gotchas / README corrections

- `${main.basedir}` is only resolved by the root Maven reactor (see root `pom.xml` /
  `.mvn` config); building `rvsec-apk` in isolation (`mvn -pl rvsec-apk`) silently skips
  the `apktool.jar` copy — no error, just a missing artifact for `rv-android`.
- The module README (`rvsec-apk/README.md`) claims parsing of permissions and of
  services/receivers/content providers; the actual code (`AppReader`) only reads
  package name, application class, and activities. There is no permission or
  service/receiver model in this module.
