# Survivability: Resistance, Recognition, Recovery

Read in Phase 5, only when a finding is high or critical and threatens what a campaign must
keep: the host, the corpus, the instrumented APKs or the results. Use it to shape the
mitigations of that finding, not as a separate audit.

The essential service here is a campaign that finishes with trustworthy results. A crashed
emulator or a failed task is routine; lost or silently corrupted results, or a compromised host,
are not.

---

## Resistance: keep the attack from landing

| Asset | Controls to look for |
|-------|---------------------|
| Host | Container without `privileged`, only `/dev/kvm`, no Docker socket unless required, bounded JVM heaps and timeouts |
| Corpus and inputs | Read-only bind mounts (`:ro`) |
| Results | Writable mount per container, no shared results directory between containers |
| Lab network | Emulator outbound traffic limited to what the campaign needs; LAN services not published further |
| Secrets | `.env` git-ignored; keystore used only for lab-signed APKs |

## Recognition: notice that something went wrong

- [ ] Each task result records exit codes, timeouts and parser failures, so an APK that
      crashes a tool shows up as such and not as an empty success.
- [ ] Campaign monitoring flags containers that stop, hang or exceed memory.
- [ ] Unexpected files outside a container's results directory, or changes to the corpus, are
      detectable (digests of inputs recorded in the task metadata).

## Recovery: return to a trustworthy state

- [ ] A failed task can be re-run alone (resume) without touching finished tasks.
- [ ] Restart policies do not bring a container back over finished results.
- [ ] The corpus, the instrumented APKs and the static-analysis outputs can be rebuilt from
      recorded inputs, or are backed up outside the containers.
- [ ] A suspected host compromise has a clear first step: stop the campaign containers, keep the
      results read-only, and rebuild the image from pinned bases.

## Mapping a finding to mitigations

For a high or critical finding, state one control for each column, with where it lives:

| Finding | Resistance | Recognition | Recovery |
|---------|------------|-------------|----------|
| RVS-F-00N | the fix or the containment | how a recurrence would be noticed | how affected results are identified and redone |
