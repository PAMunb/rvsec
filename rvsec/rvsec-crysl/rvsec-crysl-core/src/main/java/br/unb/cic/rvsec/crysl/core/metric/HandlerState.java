package br.unb.cic.rvsec.crysl.core.metric;

/**
 * What the parser found where a {@code @match} or {@code @fail} body was expected, in the model
 * module's vocabulary.
 *
 * <p>It mirrors {@code mop.HandlerBlock.Status} one-for-one and it is a separate type because it has
 * to be: M0 lives in the model module, the model module may not depend on the {@code javamop} lifter
 * (design D-16), and the distinction between {@link #EMPTY} and {@link #ABSENT} is the one M0's
 * refusal of {@code RandomStringPassword} rests on. Losing it on the way across the boundary would
 * turn "declared with nothing in it" into "not declared", which are different claims about the file.
 *
 * <p>{@link #UNPARSED} is carried for the same reason the lifter carries it: {@code
 * JavaParserAdapter} swallows every exception from a handler body and leaves a {@code null} block
 * behind, so a malformed handler is indistinguishable from an empty one at the block level. Reading
 * it as {@link #EMPTY} would make M0 refuse a healthy specification the day it happens.
 */
public enum HandlerState {

    /** No handler with this key is declared. */
    ABSENT,

    /** Declared, and its body contains no statement. */
    EMPTY,

    /** Declared, with at least one statement. */
    NON_EMPTY,

    /** Declared, and its body did not parse, so its content is unknown. */
    UNPARSED
}
