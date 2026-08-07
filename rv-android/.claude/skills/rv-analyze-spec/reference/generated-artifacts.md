# What the generated files tell you that the `.mop` does not

## Contents

- [The three artefacts](#the-three-artefacts)
- [The `.rvm`: the specification without its pointcuts](#the-rvm-the-specification-without-its-pointcuts)
- [The aspect: where binding has to happen](#the-aspect-where-binding-has-to-happen)
- [The monitor: fields, transitions and the coenable residue](#the-monitor-fields-transitions-and-the-coenable-residue)
- [Six things only the generated output tells you](#six-things-only-the-generated-output-tells-you)
- [Editing the `.rvm` directly](#editing-the-rvm-directly)

## The three artefacts

```
Spec.mop  --javamop-->  Spec.rvm            (specification, pointcuts removed)
                        SpecMonitorAspect.aj (pointcuts + advice)
Spec.rvm  --rv-monitor-> SpecRuntimeMonitor.java
```

With `-merge`, the last two become `MultiSpec_1MonitorAspect.aj` and
`MultiSpec_1RuntimeMonitor.java` for the whole set.

Read all three before reasoning about what a `.mop` means. The habit costs a minute and
settles most arguments.

## The `.rvm`: the specification without its pointcuts

The `.rvm` keeps the events, the property block and the handlers, but every event's pointcut
is gone — reduced to a parameter list. A `condition(...)` becomes an early `return false`
guard at the top of the body:

```java
event g1(String transformation, Cipher c){
    if ( ! (isValid(transformation)) ) {
        return false;
    }
    { currentTransformation = transformation; cipher = c; }
}
```

That guard is the mechanism behind a subtle behaviour: when a condition is false the event
does **not** fire at all. The automaton does not advance, and a later call that expected the
advance becomes a sequence violation instead. If a specification reports
`InvalidSequenceOfMethodCalls` where you expected something more specific, look for a
condition that silently suppressed an event.

The `.rvm` is also the cheapest place to run experiments — see the last section.

## The aspect: where binding has to happen

The aspect holds the woven pointcuts:

```java
pointcut CipherSpec_g2(String transformation, Object provider) :
    (call(public static Cipher Cipher.getInstance(String, Object+))
     && args(transformation, provider)) && MOP_CommonPointCut();
```

What it does **not** hold is the event body. The body is compiled out of the advice into a
static method of the runtime monitor class. Three consequences follow, and all three have
cost someone time:

- **`thisJoinPoint` is not available in an event body.** Anything you need from the join point
  must be bound in the pointcut.
- **Binding a new argument therefore costs at least one new event** whenever the overloads
  differ in arity, because `args(a, b, third, ..)` requires arity ≥ 3 and drops the shorter
  overload out of the automaton entirely.
- **`__LOC` expands only in an event body.** To use it in a helper, pass it in as a `String`
  parameter; each call site then gets its own line number.

A `private` method declared in the specification block *is* emitted into the monitor class, so
shared logic between event bodies is possible — just not shared access to the join point.

## The monitor: fields, transitions and the coenable residue

Three things to look for in `…RuntimeMonitor.java`.

**Variables declared in the specification block become fields of the monitor instance**, one
instance per monitored object. This is what makes `remove(Property, field)` per-monitor and
plain `remove(Property)` global — the one-argument form deletes a predicate's whole set, so
one monitor's `@fail` erases every other monitor's mark. Grep for one-argument `remove(` calls
when auditing.

**The transition table** is emitted as rows of state numbers. An event whose row is entirely
`fail` is declared but never placed in the automaton, which turns a legitimate API call into a
reported sequence violation. This is worth checking mechanically across a whole set rather
than by eye.

**The coenable residue** is one line, and it is a useful sanity check:

```java
//alive_parameters_0 = [Cipher c]
boolean alive_parameters_0 = true;
```

If you have just spent a minute of CPU and three gigabytes on a specification with a single
parameter, that comment is what you bought. See `generator-pipeline.md`.

## Six things only the generated output tells you

Collected because each was discovered the hard way.

1. **`thisJoinPoint` is unavailable in event bodies** — the body is not in the advice.
2. **`(..)` matches zero arguments too.** A pointcut written `doFinal(..)` matches
   `doFinal()`, so if a separate `doFinal()` event also exists, one call takes two
   transitions. Visible in the aspect, invisible in the `.mop`.
3. **The return type in a pointcut discriminates overloads.** `byte[] doFinal(..)` and
   `int doFinal(..)` reach disjoint sets of methods.
4. **A false `condition(...)` suppresses the event entirely**, it does not fail it.
5. **Spec-block variables are per-monitor fields**, which is why the two `remove` overloads
   behave completely differently.
6. **The accepting category's name comes from the alias**, so an `fsm` with
   `alias match1 = end` and the equivalent `ere` (whose plugin emits `alias match = …`)
   produce monitors that differ in exactly that identifier and nothing else.

## Editing the `.rvm` directly

For experiments about the *alphabet* or the *automaton* — cost measurements, ceiling probing,
comparing two formalisations of the same language — skip javamop and edit the `.rvm`. It is
plain text, rv-monitor consumes it directly, and it removes the pointcut layer from the
variables under test.

Swapping the property block between notations is a two-line edit:

```python
i, j = src.index("\tfsm:"), src.index("\t@fail")
ere  = "\tere: g3* (g1|g2) (i1|i2) ( ... )+\n\n"
out  = (src[:i] + ere + src[j:]).replace("@match1", "@match")
```

Two cautions. Event bodies in such an experiment are placeholders, so what you are validating
is the alphabet and the language, **not** the specification — say so explicitly when
reporting. And when you swap `fsm` for `ere`, the accepting category is renamed, so the
handler name has to change with it or the generator will not find a handler for the category.
