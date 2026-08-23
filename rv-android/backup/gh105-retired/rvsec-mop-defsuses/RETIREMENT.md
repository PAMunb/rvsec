# `rvsec-mop-defsuses`, retired at task 7.3 of gh105-predicate-wiring

The module read a `.mop` with JavaParser and printed which events define and which
use each monitor field — a def/use graph over the specification's own Java, written
while the predicate wiring was still being designed by hand.

**Why it is here.** Nothing calls it. It was never a dependency of any module of the
reactor: the only two places that named it were `rvsec/pom.xml`'s `<modules>` list,
which built it, and the skip list of `rv-android/scripts/check_no_legacy_mop.py`,
which excluded it from a grep. What it computed by reading source, this change now
derives from the specifications themselves and keeps under version control —
`data/jca_android/predicate_graph.csv` carries one row per predicate site with its
clause, its mechanism and its disposition, and four gates decide against it.

**What it contains.** Five Java files (1735 lines), of which `UseDefVisitor.java` and
`VoidVisitorAdapter.java` are 1528 — a vendored JavaParser visitor and its
specialisation. `DefsUsesGraph.java:65-66` holds a hard-coded absolute path to one
developer's home directory, which is the shape of tool this was.

It is kept whole, buildable as it stood, so that a reader who wants the def/use view
can run it without recovering it from history.
