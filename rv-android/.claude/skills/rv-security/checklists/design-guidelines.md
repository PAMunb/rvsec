# Security Design Guidelines

Read in Phase 3 for system or module targets. Each guideline is stated once and then turned into
checks for rv-android. Cite `file:line` for every check you mark as met or failed; a check with no
code behind it in the target is "not applicable", not "met".

---

## 1. Base decisions on an explicit policy

The policy is the set of recorded decisions: accepted exceptions (Overrides in `SKILL.md`),
`docker/SECURITY.md`, the module `CLAUDE.md` files and the OpenSpec specs.

- [ ] Each control you rely on is written down somewhere, or is visible in code.
- [ ] A deviation from a recorded decision is reported against that decision, with its location.

## 2. Defense in depth

The layers between a corpus APK and the host are: the parser's own robustness, subprocess
timeouts and heap limits, the container, read-only mounts, and the emulator.

- [ ] For each boundary in `trust-boundaries.md`, name at least two layers and where each is set.
- [ ] No layer is the only thing standing between an APK and a writable host path.

## 3. Fail securely

- [ ] A parser or instrumenter failure marks the task failed; partial output is not consumed as
      if complete, unless a field records the degradation (as static analysis does on timeout).
- [ ] An unreachable LLM endpoint or emulator ends the task with a recorded error, not a hang.
- [ ] Error messages and logs do not include secrets.

## 4. Least privilege

- [ ] Containers run without `privileged`, with only `/dev/kvm` as a device.
- [ ] The Docker socket is mounted only in the composes that need sibling containers, and the
      code using it is reviewed (RVS-CTR-001).
- [ ] Writable mounts are limited to the container's own results directory.

## 5. Minimize attack surface

- [ ] No adb or other service ports published beyond localhost.
- [ ] Tools and parsers that a campaign does not use are not invoked on corpus APKs.
- [ ] The emulator's outbound network matches what the campaign needs (ask in Phase 4).

## 6. Secure defaults

- [ ] Defaults for timeouts, heap sizes and mounts are the safe ones; operators loosen them
      explicitly.
- [ ] Default endpoints and paths point to lab resources, not to public services.

## 7. Validate all inputs at the boundary

- [ ] APK-derived names (package, component, entry names) are validated before they reach a
      subprocess, a path or the device shell (RVS-CMD-001, RVS-CMD-002, RVS-PATH-001).
- [ ] LLM output is parsed as data and validated before an action runs (RVS-PAR-001).
- [ ] Operator input is validated by the Pydantic configuration at the CLI boundary.

## 8. Compartmentalize

- [ ] Each campaign container has its own results directory; one container cannot overwrite
      another's results.
- [ ] Per-APK temporary directories keep one APK's extraction away from another's.

## 9. Record security-relevant events

Here this means traceability of a campaign, not authentication logs.

- [ ] Every task records its inputs (APK digest, tool, configuration) and its outcome, including
      timeouts and parser failures.
- [ ] Unexpected writes or failures in instrumentation are visible in the task result, not only
      in a debug log.

## 10. Design for recovery

- [ ] Finished results cannot be overwritten by a restarted container (restart policy, resume
      logic).
- [ ] The corpus and the instrumented APKs can be rebuilt or are backed up outside the containers.
- [ ] See `survivability.md` when a high or critical finding threatens results or the host.
