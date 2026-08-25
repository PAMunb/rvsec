package br.unb.cic.rvsec.crysl.core.calibration;

/**
 * What a calibration target vouches for, and therefore what a mismatch on it stops publishing.
 *
 * <p>A mismatch stops the affected metric and nothing else (task 12.4). One wrong metric must not
 * suppress seven right ones — a gate that fails whole runs teaches its users to disable it — and one
 * right metric must not license a wrong one, which is why suppression is per metric rather than per
 * run and why there is no cascading: {@link #MOP_LIFT} failing does not silence {@link #M3}, because
 * the two are separate claims and a reader is better served by the surviving one plus a named
 * refusal than by nothing.
 */
public enum PublishedMetric {

    /** Reading the five {@code .mop} corpora, including the declared-parameter census. */
    MOP_LIFT,

    /** Reading the 49 upstream {@code .crysl} rules, one fresh reader per rule. */
    ORACLE_LIFT,

    /** Which rule is the oracle of which specification (INV-CONF-11). */
    PAIRING,

    /** Vitality: does the specification index, and can it accuse at all. */
    M0,

    /** The event-signature comparison. */
    M1,

    /** The order comparison. */
    M2,

    /** The constraints census and its denominator. */
    M3,

    /** The predicate-graph comparison. */
    M4
}
