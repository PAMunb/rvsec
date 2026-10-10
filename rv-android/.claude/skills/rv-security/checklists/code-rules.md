# Code Rules

Read in Phase 3, before reviewing any file. Findings cite these IDs in their **Rule** field.
Each rule says what is required, what to look for, and how to fix it. A pattern match is a lead;
it becomes a finding only after you trace the value to an attacker-controlled source (see
`trust-boundaries.md`).

---

## RVS-CMD-001: Subprocess arguments as a list, never through a shell

The platform drives `adb`, `docker`, `java` (apktool, instr-cli, GATOR, ajc) and the Android
build tools as subprocesses. A value that came from an APK (package name, component name, file
name inside the archive, label) or from model output must never be interpreted by a shell.

Required:
- Pass the command as a list (`Command(cmd, args)` or `subprocess.run([...])`).
- No `shell=True`, `os.system` or `sh -c`/`bash -c` with any value that is not a constant or an
  operator-controlled setting.
- Put `--` before positional paths when the tool supports it, so a name starting with `-` is not
  read as an option.
- Constrain variable parts to what they should be (a package name matches its grammar, a path
  resolves inside the work directory).

Look for: `shell=True`, `os.system(`, `Popen(` with a string, f-strings or `+` building a command
string, `" ".join(...)` passed to a shell.

Fix: rebuild the call as a list; when a shell feature is truly needed (pipes, redirection), do it
in Python instead.

## RVS-CMD-002: `adb shell` re-parses its arguments on the device

`adb shell a b c` joins the arguments and hands them to the device's shell, so a list on the host
does not protect values on the device. Component names, package names and text to type can come
from the APK or the model.

Required: quote each variable argument for the device shell (`shlex.quote`) or use an API that
does not go through the device shell (uiautomator2 calls, `am` with validated names).

Impact note: injection here runs inside the emulator. Rate it by what the device shell can reach,
not as a host compromise.

## RVS-ARC-001: Archive extraction stays inside the target directory

Python's `zipfile` already sanitizes member names on `extract`/`extractall`: it drops absolute
prefixes and `..` components, so a `ZipFile(...).extractall(target)` cannot write outside `target`
(checked on the workspace interpreter, Python 3.14: a member named `../../x` lands inside
`target`). Do not report zip-slip against `zipfile`. What the rule does require:

- `tarfile`: every `extract`/`extractall` passes `filter="data"` (without it, absolute names,
  `..` and links are honoured).
- Archives from the corpus: the total extracted size and the member count are capped, since
  `zipfile` bounds neither (decompression bombs).
- External extractors (apktool, `unzip`, `jar xf`) and hand-rolled extraction that builds
  `target / member` itself: resolve each path and reject it unless it stays under `target`.

Look for: `tarfile.open`, `extract(` with a hand-built destination path, subprocess calls to
`unzip`/`jar`/apktool on APKs or JARs derived from them, and `extractall(` on corpus archives
(size and count only).

## RVS-RES-001: Bounded resources for every external tool

Required: every subprocess that parses attacker-controlled input has a timeout that kills the
whole process tree; every JVM has an explicit `-Xmx`; parallel runs keep the sum of heaps below
host memory; output that can grow without bound (logs, JSON) is streamed or capped.

Look for: `Command(...)`/`subprocess.run` without `timeout`, `java` invocations without `-Xmx`,
whole-file reads of outputs whose size the APK drives.

## RVS-PAR-001: Untrusted text is parsed as data

Applies to LLM output, UI hierarchy dumps, logcat and tool output.

Required: `json.loads`, `xml.etree` with entity expansion off (or `defusedxml`) and explicit
patterns; validate the parsed structure (allowed action names, numeric ranges, coordinates within
the screen) before use. Never `eval`, `exec`, `pickle.loads` or `yaml.load` without `SafeLoader`
on such data. Regexes run over long untrusted text avoid nested quantifiers.

## RVS-PATH-001: Paths built from untrusted names stay in the work directory

Required: when a file name comes from an APK (entry names, package names, activity names),
normalize it and confirm the resolved path stays under the intended directory before reading or
writing.

## RVS-NET-001: Network calls have timeouts and fail closed

Required: every HTTP call (LLM endpoint, model downloads) sets a timeout; a failure ends or
degrades the task with a recorded error. TLS and authentication on the lab LLM endpoint are an
accepted exception (see Overrides in `SKILL.md`).

## RVS-SEC-001: Secrets are not printed, logged or committed

Required: keys and passwords come from `.env`, configuration or the keystore asset, never from
logs; logs and results do not echo them; `.env` stays git-ignored. Report a secret by location
and kind only.

## RVS-CTR-001: Container configuration keeps the emulator contained

Required: read-only mounts for inputs, writable mounts only for that container's results, no
`privileged`, devices limited to `/dev/kvm`, no published adb ports beyond localhost. A mounted
Docker socket is root on the host: the code that uses it must not take image names or arguments
from attacker-influenced data.

---

## What is not a fix

- Removing a timeout, a size cap, a path check or signature verification to get past a failure.
- Running a container `privileged` or as root to avoid a permission error.
- Skipping or deleting the test that exposes the problem.
- Catching and discarding the exception that reports the problem.

If a protection blocks legitimate work, the fix narrows or configures the protection; it does not
remove it.
