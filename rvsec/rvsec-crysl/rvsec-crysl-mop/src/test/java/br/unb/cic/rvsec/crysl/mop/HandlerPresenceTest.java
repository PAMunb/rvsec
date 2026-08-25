package br.unb.cic.rvsec.crysl.mop;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * "Handler present and empty" is not "handler absent".
 *
 * <p>The witness is {@code jca/RandomStringPassword.mop}, whose whole handler section is
 * {@code @match { }} — declared, and containing nothing. It declares no {@code @fail}. A monitor
 * built from it can never accuse under any trace, which is what makes it the specification G06
 * refuses, and the refusal is only available to G06 if the lift keeps the two facts apart:
 * {@code @match} present and empty, {@code @fail} absent.
 *
 * <p>Both facts are easy to lose to the parser. {@code getStmts()} answers {@code null} rather than
 * an empty list for {@code { }} (trap a), so a reader that tests {@code getStmts() != null} calls
 * the handler absent; and {@code JavaParserAdapter} swallows the exception from a handler body that
 * does not parse and leaves the {@code BlockStmt} {@code null} too (trap d), so the two have to be
 * separated by something other than the block, namely by whether the key is in the map at all.
 */
class HandlerPresenceTest {

    private final MopLifter lifter = new MopLifter();

    @Test
    @DisplayName("@match { } lifts to present-and-empty, and @fail to absent")
    void test_empty_match_is_present_and_empty() throws LiftFailure {
        MopLift lift = lifter.read(Corpora.file("jca", "RandomStringPassword.mop"),
                Corpora.version("jca"));

        HandlerBlock match = lift.handler("match");
        assertTrue(match.present(), "@match is written in the file, so it is present");
        assertTrue(match.presentAndEmpty(), "its body is { }, so it is present and empty");
        assertEquals(HandlerBlock.Status.EMPTY, match.status());
        assertEquals(0, match.statements());
        assertEquals(27, match.site().line(),
                "the handler's provenance is the line @match is written on");

        HandlerBlock fail = lift.handler("fail");
        assertFalse(fail.present(), "the file declares no @fail at all");
        assertEquals(HandlerBlock.Status.ABSENT, fail.status());
    }

    @Test
    @DisplayName("trap (e): handler keys arrive lowercased, so the lookup is case-insensitive")
    void test_handler_keys_are_lowercased() throws LiftFailure {
        MopLift lift = lifter.read(Corpora.file("jca", "SecureRandomSpec.mop"),
                Corpora.version("jca"));

        // The file writes "@match1"; the grammar stores it as "match1" via
        // handlers.put(id.toLowerCase(), handler). A caller comparing against "@match1" or
        // "Match1" would find nothing and conclude the handler is absent.
        assertTrue(lift.handlers().containsKey("match1"));
        assertFalse(lift.handlers().containsKey("@match1"));
        assertTrue(lift.handler("Match1").present(), "the lookup normalises the key for the caller");
        assertEquals(HandlerBlock.Status.NON_EMPTY, lift.handler("match1").status());
    }

    @Test
    @DisplayName("a handler with statements is NON_EMPTY and counts them")
    void test_non_empty_handler() throws LiftFailure {
        MopLift lift = lifter.read(Corpora.file("jca", "MacSpec.mop"), Corpora.version("jca"));

        HandlerBlock match = lift.handler("match");
        assertEquals(HandlerBlock.Status.NON_EMPTY, match.status());
        assertEquals(1, match.statements(),
                "@match holds the single setObjectAsInAcceptingState call");

        HandlerBlock fail = lift.handler("fail");
        assertEquals(HandlerBlock.Status.NON_EMPTY, fail.status());
        assertTrue(fail.statements() >= 2, "@fail accuses, withdraws the predicate and resets");
    }
}
