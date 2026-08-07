# The monitor generator: a rewriting pipeline, and where its wall is

## Contents

- [The three stages](#the-three-stages)
- [The logic repository is a rewriting system](#the-logic-repository-is-a-rewriting-system)
- [Which logic you write barely matters](#which-logic-you-write-barely-matters)
- [The `fsm` back end, and the coenable blow-up](#the-fsm-back-end-and-the-coenable-blow-up)
- [What all that work produces](#what-all-that-work-produces)
- [The two failure modes](#the-two-failure-modes)
- [The ceiling, and why it cannot be raised from outside](#the-ceiling-and-why-it-cannot-be-raised-from-outside)
- [Reproducible measurements](#reproducible-measurements)
- [A latent defect worth knowing about](#a-latent-defect-worth-knowing-about)

Paths below are relative to `$RVSEC_HOME/rv-monitor/`.

## The three stages

A `.mop` file becomes a runtime monitor in three hops.

**javamop** reads the `.mop` and emits two files: a `.rvm` — the same specification with the
AspectJ pointcuts stripped out and the event bodies normalised — and a `.aj` aspect holding
the pointcuts and the advice. It writes the `.rvm` into the *source* directory, not into
`-d`. Always copy the `.mop` to a scratch directory first.

**rv-monitor** reads the `.rvm`. For the property block it calls out to the **logic
repository**, a separate subsystem with one plugin per logic. The plugin turns the property
into a transition table plus, sometimes, two pieces of derived information — *enable sets* and
*coenable sets* — which rv-monitor uses to decide when a monitor instance can be
garbage-collected.

**rv-monitor** then emits `…RuntimeMonitor.java`. This last stage is the one that fails, and
it fails on the derived information, not on the automaton.

## The logic repository is a rewriting system

This is the part worth internalising, because it explains why the notation you choose has far
less effect than it looks like it should.

`LogicPluginFactory.process`
(`logicrepository/…/plugins/LogicPluginFactory.java:289-310`) does not simply call a plugin
and return. It inspects the plugin's output. If the messages contain `"done"`, it returns.
Otherwise it reads the `logic` name the plugin wrote onto its own output and **calls itself
again** with that name. The comment in the source calls this *transitive processing*.

So the repository is a rewriting system: a property is rewritten from logic to logic until
some plugin declares itself terminal. Here is the whole landscape, read out of the plugin
sources:

| logic | rewrites into | terminal? | computes enable/coenable sets |
|---|---|---|---|
| `ere` | **`fsm`** | no | no — the `fsm` stage does it |
| `ltl` | **`fsm`** | no | no — the `fsm` stage does it |
| `ptltl` | **`fsm`** | no | no — the `fsm` stage does it |
| `fsm` | — | **yes** | **yes** (`FSMEnables`, `FSMCoenables`) |
| `tfsm` | — | yes | yes (its own coenables) |
| `cfg` | — | yes | enable sets only |
| `pda` | — | yes | no |
| `po` | — | yes | no |
| `ptcaret` | — | yes | no |
| `srs` | — | yes | no |

Three of the ten logics funnel into `fsm`. The JCA specification sets use only two of them:
18 specifications written as `ere`, 5 written as `fsm`. **Both end up in the same back end.**

## Which logic you write barely matters

`EREPlugin.process` (`plugins_logicrepository/ere/…/EREPlugin.java:19-48`) is the clearest
example of the pattern. It parses the regular expression, builds a DFA from it with
Brzozowski derivatives (`ere/…/FSM.java`), prints that DFA in `fsm` syntax, sets
`logic = "fsm"`, and returns **without** the `"done"` message. `LTLPlugin` and `PTLTLPlugin`
do the same thing from a different starting notation.

Then `FSMPlugin.process` runs on the result: `FSMMin` → `FSMEnables` → `FSMCoenables` →
`setEnableSets(…)` (`fsm/…/FSMPlugin.java:67-78`), and emits `"done"` (`:74`).

**The `ere` notation is a front end, not an alternative back end.** Measured on the same
language with the same 17-event alphabet: five states after minimisation on both paths,
2,228,207 `fail` coenable sets on both paths, 53.5 s against 53.6 s, and the same
`StackOverflowError` at 18 events on both paths. The generated monitors differ only in the
name of the accepting category (`match1` for a hand-written alias, `match` for the one the
`ere` plugin emits).

So choose the notation for readability, not for cost. What *would* change the cost profile is
moving to a logic with a different terminal plugin — `pda`, `srs`, `po`, `ptcaret` compute no
enable sets at all — but that changes the expressiveness and the semantics, and is a design
decision, not a workaround.

Two grammar facts, established by reading the parsers:

- The `ere` grammar (`ere/src/main/javacc/…/EREParser.jj`) accepts `*`, `+`, `~`, `&`, `|`,
  `^<digit>`, `epsilon` and `empty`. **There is no `?`.** A rule's `ORDER ge*, d?` is written
  `e1* (d | epsilon)`, which is the same language.
- The `fsm` grammar (`fsm/src/main/javacc/…/FSMParser.jj`) has a `DEF` token, giving
  `default -> <state>`. No specification in the JCA sets uses it, which is why every
  undeclared pair ends up in `fail` — see the next section.

## The `fsm` back end, and the coenable blow-up

Four things compose into an exponential. Each is reasonable on its own.

**1. The transition table is completed with `fail`.**
`FSMCoenables.getFullTransition` (`fsm/…/FSMCoenables.java:260-292`) walks every event and,
for any `(state, event)` pair the specification did not declare, inserts a transition to the
state `fail`. With no `default ->` in use, that is a lot of pairs.

**2. `fail` is a category.**
Categories come from the specification's handlers. A `.mop` with an `@fail` block — nearly
every one of them — makes `fail` a category the generator must produce coenable information
for.

**3. The coenable walk goes backwards, accumulating a set.**
`computeCoenables` (`FSMCoenables.java:114-160`) inverts the transition map and walks
backwards from every state in each category, accumulating a `HashSet` of the events seen on
the path, memoised on the pair `(state, set)`.

**4. From `fail`, everything is co-reachable.**
Because step 1 made `fail` the destination of most pairs, the backward walk from `fail`
reaches every state by almost every event, and the accumulated sets are eventually *every
subset of the alphabet*.

The result is exact, not asymptotic:

```
coenable sets recorded for the `fail` category  =  n × (2ⁿ − 1)
```

`n` events, each mapping to every non-empty subset of the alphabet. Verified to the unit by
running the production `FSMCoenables` class:

| n | formula | measured |
|---:|---:|---:|
| 17 | 2,228,207 | **2,228,207** |
| 18 | 4,718,574 | **4,718,574** |

The number of *states* is irrelevant: 5 after minimisation at 14, 17 and 18 events alike, and
identical for `fsm` and `ere`. **The alphabet is the only lever.**

## What all that work produces

`FSMPlugin` concatenates the enable and coenable strings and hands them back
(`FSMPlugin.java:78`). At 17 events that string is **82,448,990 characters**; at 18 it is
**184,036,772**.

On the rv-monitor side, `EnableSet.parseSets`
(`rv-monitor/…/java/rvj/output/EnableSet.java:66-119`) parses it and maps each event name to
the **specification parameters** that event carries (`EnableSet.java:102-105`).
`OptimizedCoenableSet.optimize` (`…/output/OptimizedCoenableSet.java:17-33`) reduces that to a
DNF over the specification's parameters, and `MonitorTermination` emits one
`alive_parameters_<j>` flag per resulting group.

Now look at the specifications. Every one of the 23 JCA specifications has **at most one**
parameter, and in `CipherSpec` every event carries that same parameter (`Cipher c`). So all
2,228,207 sets map to the same single parameter set, `RVMParameterSet` de-duplicates them, and
the generated monitor contains:

```java
//alive_parameters_0 = [Cipher c]
boolean alive_parameters_0 = true;
```

**82 MB of string, 2.2 million sets, 53 seconds and 3.3 GB of RAM, to produce one line.** And
`OptimizedCoenableSet.optimize` already has the fallback that yields the same value for free:
`if (enables == null) enables = getFullEnable()`.

Two reasons to know this. It says the computation is degenerate for this family of
specifications, so a repair in the generator would be verifiable by byte-diffing the generated
monitor. And it says not to look for meaning in coenable sets when debugging: there is none.

## The two failure modes

They are different, and confusing them wastes a lot of time.

**At 18 events — `StackOverflowError`.** Not slowness. `parseSets` matches a pattern with
nested quantifiers — `(...)(\s*,\s*[...])*` — against the whole 184 MB string. Java's
`Matcher` recurses once per repetition, so the stack dies. The trace is unmistakable:

```
Exception in thread "main" java.lang.StackOverflowError
    at java.base/java.util.regex.Pattern$GroupTail.match(Pattern.java:5000)
    at java.base/java.util.regex.Pattern$BmpCharPropertyGreedy.match(Pattern.java:4509)
    at java.base/java.util.regex.Pattern$Loop.match(Pattern.java:5078)
    ...
```

**At 24 events — impossible in principle.** 402,653,160 sets at roughly 37 characters each is
about 1.5 × 10¹⁰ characters. Java's maximum `String` length is 2³¹ − 1, about 2.1 × 10⁹. The
string cannot be built. A run that appears to hang at 27 GB is not slow; it was never going to
finish.

## The ceiling, and why it cannot be raised from outside

**17 events**, for any specification whose logic funnels into `fsm` and that has an `@fail`
handler.

The launcher (`target/release/rv-monitor/bin/rv-monitor`) already passes `-Xss1g`. Raising it
is not an option: the JVM refuses to start with `-Xss2g`, `-Xss4g` or `-Xss8g` — each fails in
0.1 s with "A fatal exception has occurred". One gigabyte is effectively the cap for the main
thread's stack, and 18 events overflows it.

Nothing you can do in the `.mop` moves this line except reducing the alphabet.

Also worth recording: `EnableSet.java` and `FSMCoenables.java` have **never been modified**
since the initial commit of the vendored `rv-monitor`. The ceiling has been in the same place
for the entire life of the project, which is why a specification's own history is often the
best evidence of where someone hit it before.

## Reproducible measurements

**Generate one specification and time it.** Always copy first.

```bash
mkdir -p $S/one && cp $MOP/jca/CipherSpec.mop $S/one/ && cd $S/one
nice -n 15 $RVSEC_HOME/javamop/bin/javamop -d $S/one CipherSpec.mop
/usr/bin/time -v timeout 900 nice -n 15 \
  $RVSEC_HOME/rv-monitor/bin/rv-monitor -d $S/one $S/one/CipherSpec.rvm 2>&1 \
  | grep -Ei 'is generated|Exception in|Elapsed|Maximum resident|Exit status'
```

**Generate a whole set** (`-merge`), then check the transition rows:

```bash
rm -rf $S/gen && mkdir -p $S/gen/specs $S/gen/out
cp $MOP/jca_android/*.mop $S/gen/specs/
nice -n 15 $RVSEC_HOME/javamop/bin/javamop -d $S/gen/out -merge $S/gen/specs/*.mop
mv $S/gen/specs/*.rvm $S/gen/out/          # javamop leaves .rvm in the SOURCE dir
nice -n 15 $RVSEC_HOME/rv-monitor/bin/rv-monitor -d $S/gen/out -merge $S/gen/out/*.rvm
uv run python scripts/gh101_monitor_transition_check.py \
  $S/gen/out/MultiSpec_1RuntimeMonitor.java
```

**Watch a run that seems stuck.** The stack tells you which of the two mechanisms you are in.

```bash
jstack $(pgrep -f logicrepository.Main | head -1) | grep -A 25 '"main"'
ps -o rss= -p $(pgrep -f logicrepository.Main | head -1)
free -g
```

Do not `pkill -f logicrepository.Main` while your own shell command line contains that
string — you will kill your own wrapper.

**Count coenables without generating code.** `scripts/CoenableProbe.java` calls the real
`FSMCoenables`; see `scripts/README.md`. It reports states after minimisation, milliseconds
per phase, the set count per category, and the size of the resulting string — and it takes an
`fsm` body or an `ere` expression, so you can compare the two notations directly.

**Reference measurements** (loaded workstation, `nice -n 15`, JDK 25):

| variant | events | states | `fail` coenables | outcome |
|---|---:|---:|---:|---|
| `fsm`, frozen `CipherSpec` | 17 | 5 | 2,228,207 | 53.5 s, 3.3 GB |
| `ere`, same language | 17 | 5 | 2,228,207 | 53.6 s, 3.0 GB |
| `fsm` + one event | 18 | 5 | 4,718,574 | `StackOverflowError` |
| `ere` + one event | 18 | 5 | 4,718,574 | `StackOverflowError` |
| historical 18-event `CipherSpec` | 18 | 5 | 4,718,574 | `StackOverflowError`, 1 m 02 s, 5.4 GB |
| re-budgeted alphabet | 14 | 5 | 229,362 | **6.1 s, 1.0 GB** |

## A latent defect worth knowing about

`computeCoenables` (`FSMCoenables.java:114-127`) creates the `eventsSeen` memo **once** and
shares it across all categories. Whichever category is processed first consumes the memo
entries, so later categories are systematically under-computed, and the result depends on
category order.

You can see it in the numbers above: with `fail` processed first, the accepting category got
354 sets on the `fsm` path and 6,864 on the `ere` path — same language, different alias
membership, wildly different counts. It does not affect the JCA specifications, because
everything collapses to one parameter anyway, but do not build an argument on a coenable count
for a non-first category.
