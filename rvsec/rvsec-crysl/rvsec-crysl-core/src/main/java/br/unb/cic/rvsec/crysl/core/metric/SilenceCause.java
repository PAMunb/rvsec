package br.unb.cic.rvsec.crysl.core.metric;

/**
 * Why a specification can observe a violating trace and say nothing, and what each cause is worth.
 *
 * <p>The three constants are not a taxonomy invented at the desk. The behavioural run of
 * 2026-08-24 replayed thirteen traces against the generated monitors of the five specifications
 * that do not index, with four negative controls whose predictions were written down before the run,
 * and measured that "does not build a {@code MapOfMonitor}" fuses three different phenomena
 * (design D-04). Only one of them is a repairable defect of a file. Collapsing them would report a
 * limit of the formalism as a defect of a specification, which is the error the whole capability
 * exists to prevent.
 *
 * <p>All three describe a <strong>live</strong> monitor. There is no constant here for a dead one,
 * and that absence is the point: the corpus contains no dead monitor, and reporting any of these
 * three as death would be the mistake the run was paid for. Where a genuinely dead monitor is ever
 * measured, it gets its own constant and its own disposition, and adding one is a visible change
 * of contract.
 */
public enum SilenceCause {

    /**
     * The monitor is live and cannot see the end of the trace.
     *
     * <p>{@code CipherInputStreamSpec} declares {@code ere : c1 (r1|r2)+ cl1}. The word
     * {@code c1 r1} — the stream opened and read and never closed — is a live prefix of an accepted
     * word, and JavaMOP fires {@code @fail} only when the word leaves the language. There is no
     * end-of-trace event in the formalism, so "opened and never closed" is undetectable
     * <em>by construction</em>. The negative control confirms the monitor is alive: {@code c1 cl1},
     * which does leave the language, accuses at {@code cl1} in both corpora.
     *
     * <p>This is CrySL's {@code IncompleteOperationError} blind spot. It is a property of JavaMOP,
     * not of the file, so it is recorded as a divergence and never as a refusal.
     */
    LIVE_BLIND_TO_END_OF_TRACE(Disposition.DIVERGENCE_RECORD,
            "the monitor is live: the ere accepts the observed word as a live prefix, and JavaMOP "
                    + "fires @fail only when the word leaves the language. There is no end-of-trace "
                    + "event in the formalism, so this class of violation is undetectable by "
                    + "construction. It is a limit of JavaMOP and not a defect of the "
                    + "specification, so it belongs in divergence_record.csv"),

    /**
     * The monitor is live and its target class is absent from the platform.
     *
     * <p>{@code HMACParameterSpecSpec} monitors {@code javax.xml.crypto.dsig.spec.HMACParameterSpec},
     * which exists in the host JDK and in no verified Android API level (26, 30, 33, 35): Android
     * carries no {@code javax.xml.crypto} at all. The monitor accuses on the JSE, where the negative
     * control {@code c c} does fire; on device the pointcut can never match.
     *
     * <p>The report must say the monitor is live and the target is absent. "The monitor is dead" is
     * a different finding about a different subject, and the death here is the platform's.
     */
    LIVE_TARGET_ABSENT(Disposition.TYPED_UNKNOWN,
            "the monitor is live and the class its pointcut names is absent from the platform, so "
                    + "the pointcut can never match on device. This is a defect of the pointcut, "
                    + "not a dead monitor: the two are different findings and the report keeps "
                    + "them apart"),

    /**
     * The monitor is live and has nowhere to report from.
     *
     * <p>{@code RandomStringPassword} declares {@code ere : vo gb}, an empty {@code @match} and no
     * {@code @fail}. Its automaton still changes state; no trace can make it accuse. Its own header
     * says why the empty handler is there: the JavaMOP grammar requires at least one handler after
     * the {@code ere} ({@code RVParser.propertyHandler}), and a file without one does not parse, so
     * an empty handler is the only way to state an automaton with nothing to report.
     *
     * <p>This is the only one of the three that is an M0 refusal, and it is a property of the file
     * rather than of any corpus.
     */
    LIVE_WITHOUT_ACCUSATION_SITE(Disposition.REFUSAL,
            "the monitor is live and has no accusation site: no @fail with a body, and no "
                    + "addError reachable in an event body that the formula admits. No trace can "
                    + "make it accuse. This is a property of the file and not of any corpus, and "
                    + "the corpus states it in its own words: \"the JavaMOP grammar requires at "
                    + "least one handler after the `ere` (RVParser.propertyHandler), and a file "
                    + "without one does not parse, so an empty handler is the only way to state an "
                    + "automaton with nothing to report\" (jca_android/RandomStringPassword.mop)");

    private final Disposition disposition;
    private final String reason;

    SilenceCause(Disposition disposition, String reason) {
        this.disposition = disposition;
        this.reason = reason;
    }

    /** What the report does with this cause. */
    public Disposition disposition() {
        return disposition;
    }

    /** The written reason, emitted beside every finding of this cause. */
    public String reason() {
        return reason;
    }

    /** Where a silence of a given cause is reported, which is what separates the three. */
    public enum Disposition {

        /** A row of {@code divergence_record.csv}. The specification is not accused of anything. */
        DIVERGENCE_RECORD,

        /** A typed {@code Unknown} item, counted with the other refusals of its metric. */
        TYPED_UNKNOWN,

        /** An M0 refusal: M1-M4 emit no verdict for this specification (INV-CONF-09). */
        REFUSAL
    }
}
