package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.model.Provenance;
import java.util.Objects;

/**
 * One {@code @match} / {@code @fail} handler of a specification, in the only form that keeps
 * "present and empty" apart from "absent".
 *
 * <p>The distinction is load-bearing and easy to lose. M0 asks whether a specification has an
 * accusation site at all: a specification whose {@code @match} is {@code { }} and which declares no
 * {@code @fail} cannot accuse under any trace, and that is an M0 refusal — it is the reason G06
 * refuses {@code RandomStringPassword}. A specification that simply declares no {@code @match} is a
 * different artifact making a different claim.
 *
 * <p>Two measured parser behaviours conspire to erase that difference:
 *
 * <ul>
 *   <li>trap (a) — {@code BlockStmt.getStmts()} returns {@code null}, not an empty list, for
 *       {@code { }}. Over the five corpora 543 blocks are in that state, so a reader that treats
 *       {@code null} as "no block" mislabels a large part of the corpus and a reader that
 *       dereferences it dies on the first {@code generic} file;
 *   <li>trap (d) — {@code JavaParserAdapter.convert(PropertyHandler)} catches every exception from
 *       parsing a handler body and leaves the {@code BlockStmt} {@code null}, with no warning
 *       anywhere. A malformed handler is therefore indistinguishable from an empty one at the
 *       {@code BlockStmt} level. What still separates them is the map: the handler's key is put
 *       into {@code getHandlers()} either way, so an absent key means the handler was not written
 *       and a present key with a {@code null} value means it was written and did not parse.
 * </ul>
 *
 * <p>{@link Status#UNPARSED} does not occur in the five corpora today — all 239 files parse every
 * handler body — so the guard is written from the code that produces it rather than from a witness,
 * and it is kept because the alternative is that the day it does occur, the file reads as
 * accusation-free and M0 refuses a healthy specification.
 *
 * @param key         the handler key as {@code getHandlers()} reports it, which is
 *                    <strong>lowercased</strong> — trap (e), {@code @match1} arrives as
 *                    {@code "match1"} — so callers must not compare against {@code "@match1"}
 * @param status      what the parser found
 * @param statements  number of statements in the block; 0 for every status but
 *                    {@link Status#NON_EMPTY}
 * @param site        where the handler was declared, or the specification's own site when the
 *                    handler is absent
 */
public record HandlerBlock(String key, Status status, int statements, Provenance site) {

    public HandlerBlock {
        Objects.requireNonNull(key, "HandlerBlock.key is mandatory");
        Objects.requireNonNull(status, "HandlerBlock.status is mandatory");
        Objects.requireNonNull(site, "HandlerBlock.site is mandatory");
    }

    /** Whether the specification declares this handler at all. */
    public boolean present() {
        return status != Status.ABSENT;
    }

    /** Whether the handler is declared and its body contains no statement. */
    public boolean presentAndEmpty() {
        return status == Status.EMPTY;
    }

    /** What the parser found where a handler body was expected. */
    public enum Status {
        /** No handler with this key is declared. */
        ABSENT,
        /** Declared, and its body is {@code { }} — {@code getStmts()} returned {@code null}. */
        EMPTY,
        /** Declared, with at least one statement. */
        NON_EMPTY,
        /**
         * Declared, and its body did not parse. {@code JavaParserAdapter} swallowed the exception
         * and left a {@code null} {@code BlockStmt} behind, so the body's content is unknown.
         */
        UNPARSED
    }
}
