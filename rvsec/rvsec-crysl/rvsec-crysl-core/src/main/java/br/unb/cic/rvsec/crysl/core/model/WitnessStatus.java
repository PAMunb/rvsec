package br.unb.cic.rvsec.crysl.core.model;

/**
 * Whether a witness is a word over the alphabet or a trace that was actually executed.
 *
 * <p>The distinction is not pedantry. A word accepted by an automaton need not be a runnable Java
 * trace: {@code javax.crypto.Cipher} carries a mode state machine that neither the {@code .mop} nor
 * the rule models, so {@code wrap} after {@code ENCRYPT_MODE} throws {@code IllegalStateException}
 * before any monitor sees it. INV-CONF-08.
 */
public enum WitnessStatus {
    /** A word over the alphabet, produced by product search and never run. */
    ABSTRACT,
    /** A trace that was executed, with the harness that executed it named. */
    CONCRETE
}
