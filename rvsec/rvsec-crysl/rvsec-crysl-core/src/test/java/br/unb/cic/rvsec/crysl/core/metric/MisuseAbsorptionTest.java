package br.unb.cic.rvsec.crysl.core.metric;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.model.Label;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * The "absorbs misuse" rule, on text small enough to read.
 *
 * <p>The rule is the independent probe's, verbatim, so that the corpus test in {@code -crysl} and
 * {@code scripts/absorve.py} answer the same question. What these check is the three places where a
 * naive reading of it goes wrong: an {@code addError} after the {@code ere} line is a handler and
 * not absorption; an {@code addError} inside a comment is not code; and a {@code //} inside a string
 * literal does not start a comment.
 */
class MisuseAbsorptionTest {

    @Test
    @DisplayName("an addError in an event body before the ere line is absorption")
    void test_add_error_in_an_event_body_counts() {
        MisuseAbsorption absorption = MisuseAbsorption.scan("""
                Spec(Key k) {
                   event c1 after(): call(* p.K.a()) {
                     ErrorCollector.instance().addError(new ErrorDescription("x"));
                   }
                   ere : c1
                   @fail { }
                }
                """);

        assertTrue(absorption.absorbs());
        assertEquals(List.of(new Label("c1")), absorption.events(),
                "the call is attributed to the event whose declaration precedes it");
        assertEquals(MisuseAbsorption.RULE, absorption.rule(),
                "INV-CONF-02: the rule travels with the answer");
    }

    @Test
    @DisplayName("an addError in @fail is not absorption: it fires when the word is rejected")
    void test_add_error_after_the_formula_does_not_count() {
        MisuseAbsorption absorption = MisuseAbsorption.scan("""
                Spec(Key k) {
                   event c1 after(): call(* p.K.a()) { }
                   ere : c1
                   @fail {
                     ErrorCollector.instance().addError(new ErrorDescription("x"));
                   }
                }
                """);

        assertFalse(absorption.absorbs(), "a @fail accuses when the automaton rejects the word; "
                + "absorption is the specification reporting without the word ever leaving the "
                + "language, and merging the two would count every specification that accuses");
        assertTrue(absorption.events().isEmpty());
    }

    @Test
    @DisplayName("an addError inside a comment is not code")
    void test_commented_out_calls_do_not_count() {
        MisuseAbsorption absorption = MisuseAbsorption.scan("""
                Spec(Key k) {
                   // the seed called addError(new ErrorDescription("x")) here and no longer does
                   /* an older revision also had addError(...) in this block */
                   event c1 after(): call(* p.K.a()) { }
                   ere : c1
                   @fail { }
                }
                """);

        assertFalse(absorption.absorbs(), "the corpus carries prose that names the idioms it "
                + "removed; counting a comment would report a repair as if it had not happened");
    }

    @Test
    @DisplayName("a slash inside a string literal does not start a comment")
    void test_literals_are_tracked() {
        MisuseAbsorption absorption = MisuseAbsorption.scan("""
                Spec(Key k) {
                   List<String> algorithms = Arrays.asList("HMAC/SHA256"); addError(x);
                   event c1 after(): call(* p.K.a()) { }
                   ere : c1
                   @fail { }
                }
                """);

        assertTrue(absorption.absorbs(), "the corpus writes message literals with slashes in them, "
                + "and a scan that blanked from the first slash would lose the rest of the line");
    }

    @Test
    @DisplayName("a file with no formula line is scanned whole")
    void test_a_specification_without_a_formula() {
        MisuseAbsorption absorption = MisuseAbsorption.scan("""
                Spec(Key k) {
                   event c1 after(): call(* p.K.a()) { addError(x); }
                }
                """);

        assertTrue(absorption.absorbs(), "seventeen files of generic_new declare no property at "
                + "all; there is no ere line to cut at, so the whole file is the head");
        assertEquals(List.of(new Label("c1")), absorption.events());
    }
}
