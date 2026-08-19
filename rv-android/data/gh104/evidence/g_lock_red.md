# Task 3.6 — `DispatcherLockReleaseTest` red before the framing lands

INV-INS-108: the test is written and run before the change that makes it pass.

- date: 2026-08-19T10:20:40-03:00
- generator commit under test: `41539390` plus this group's wave-1 edits; `Advice.java` carries the seam (`enterGuardedRegion`/`leaveGuardedRegion`) but **not yet** the framing
- command, from the reactor root `rvsec/`:

```
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
mvn test -pl rv-monitor/rv-monitor -Dtest=DispatcherLockReleaseTest
```

## The measurement this test is about

On the frozen control monitor (`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`):

```
$ grep -c 'tryLock' ... ; grep -c 'unlock()' ... ; grep -c 'finally' ...
134 acquisitions   134 releases   0 finally blocks
```

One `static final ReentrantLock` is shared by all 23 specifications. Every acquisition is unprotected, so an exception raised inside the guarded region — the frozen set has a reachable one, `KeyPairGeneratorSpec`'s `switch(null)` — unwinds past the release with the lock still held.

## Why the test uses two threads

The lock is reentrant. The throwing thread re-enters it whatever the generator emits, so two calls on one thread pass with the lock still leaked. The red is only visible from a **second** thread, bounded at 2 s.

## Raw output

```
[INFO] Running com.runtimeverification.rvmonitor.java.rvj.output.combinedoutputcode.event.advice.DispatcherLockReleaseTest
[ERROR] Tests run: 2, Failures: 2, Errors: 0, Skipped: 0, Time elapsed: 2.511 s <<< FAILURE! -- in com.runtimeverification.rvmonitor.java.rvj.output.combinedoutputcode.event.advice.DispatcherLockReleaseTest
java.lang.AssertionError: the advice emitter opens the guarded region
	at com.runtimeverification.rvmonitor.java.rvj.output.combinedoutputcode.event.advice.DispatcherLockReleaseTest.theFramingIsInTheAdviceEmitterAndNotInGlobalLock(DispatcherLockReleaseTest.java:124)
java.lang.AssertionError: a second thread's dispatcher did not complete within 2s: the global lock was never released by the throwing call, so every other thread now spins in the tryLock/Thread.yield loop for ever (INV-INS-129)
	at com.runtimeverification.rvmonitor.java.rvj.output.combinedoutputcode.event.advice.DispatcherLockReleaseTest.aSecondThreadStillDispatchesAfterAHandlerThrows(DispatcherLockReleaseTest.java:95)
[ERROR] Tests run: 2, Failures: 2, Errors: 0, Skipped: 0
```
