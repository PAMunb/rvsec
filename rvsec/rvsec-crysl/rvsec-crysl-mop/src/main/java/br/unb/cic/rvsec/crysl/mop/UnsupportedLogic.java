package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import java.nio.file.Path;

/**
 * The formula of a specification is written in a logic this component does not read.
 *
 * <p>A subtype of {@link LiftFailure} because the outcome is the same — the file yields no model
 * and the run records it and continues — and a distinct type because the reason is not "it did not
 * parse": {@code ptltl} is a past-time linear temporal logic, so reading its text with the {@code
 * ere} parser would silently produce an automaton over a language nobody wrote. It has to be
 * refused, and a caller wanting to report *why* the corpus lost a file should not have to match on
 * a message.
 *
 * <p>No specification of the five corpora uses it — measured, the 239 files declare {@code ere} 65
 * times and {@code fsm} 133 times and nothing else, with 17 files declaring no formula at all — so
 * this refusal protects a future specification rather than a present one.
 */
public class UnsupportedLogic extends LiftFailure {

    private static final long serialVersionUID = 1L;

    private final String logic;

    public UnsupportedLogic(Path file, String logic) {
        super(file, "formula logic '" + logic + "' is out of scope; this component reads 'ere' "
                + "and 'fsm' only, and refuses anything else rather than mis-parsing it");
        this.logic = logic;
    }

    /** The logic identifier as the specification declared it, e.g. {@code ptltl}. */
    public String logic() {
        return logic;
    }
}
