/**
 * The JavaMOP side of the component: lift one {@code .mop} file into the shared model, and write a
 * lifted model back out as {@code .mop} text.
 *
 * <h2>What is here</h2>
 *
 * <p>{@link br.unb.cic.rvsec.crysl.mop.MopLifter} reads a file into a
 * {@link br.unb.cic.rvsec.crysl.mop.MopLift} — the canonical
 * {@link br.unb.cic.rvsec.crysl.core.model.SpecModel} plus the MOP-side facts the shared model has
 * no field for. {@link br.unb.cic.rvsec.crysl.mop.MopLowerer} is the inverse, through JavaMOP's own
 * {@code DumpVisitor}, and {@link br.unb.cic.rvsec.crysl.mop.RoundTripGate} validates what it
 * emitted in two layers with different standing (design D-12).
 *
 * <h2>There is deliberately no {@code crysl.lower}</h2>
 *
 * <p>The symmetry a reader expects — a lowerer on each side — is absent on purpose, and the reason
 * is recorded here so that its absence is not read as an oversight and repaired.
 *
 * <p>A {@code .crysl} pretty-printer would cost around four hundred lines and has <strong>no
 * consumer</strong> — no consumer anywhere, not one that is merely inconvenient to reach. The
 * CrySL project ships no formatter, so nothing upstream reads generated rule text; nothing in this
 * component reads it either, because the comparison runs over the shared model and never over rule
 * syntax. The single oracle is the upstream {@code CrySL-Rules} repository and not a generated
 * {@code MetaCrySL} corpus (design D-06), and it is read and never written, so this component has
 * no rule text to produce.
 *
 * <p>{@code mop.lower} is not in the same position, and that asymmetry is the point. It has a
 * consumer: the round-trip gate. Writing a model back as {@code .mop} and lifting it again is what
 * proves the lift keeps what it claims to keep, and JavaMOP <em>does</em> ship the writer — {@code
 * DumpVisitor} — so the emitter costs a tree walk rather than a pretty-printer. The two sides are
 * not symmetric because the technologies are not.
 *
 * <h2>Read-only over every corpus</h2>
 *
 * <p>Nothing in this package writes to a path it read (INV-CONF-12). {@code MopLowerer.lowerTo}
 * takes the output directory from its caller and is the only write path here.
 */
package br.unb.cic.rvsec.crysl.mop;
