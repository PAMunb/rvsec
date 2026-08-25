package br.unb.cic.rvsec.crysl.core.metric;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * R1, applied to text.
 *
 * <p>The rule is executable and not only documented because the metric's denominator comes from the
 * CrySL façade — one {@code ISLConstraint} per clause — and a counting rule that could only be
 * checked by reading a comment could not be checked at all. Two routes to the same number is what
 * makes {@code 80} a measurement rather than an assertion; the corpus test in
 * {@code rvsec-crysl-crysl} runs both over the upstream oracle and compares them rule by rule.
 */
class CountingRuleTest {

    @Test
    @DisplayName("8.6: one clause per ';' inside CONSTRAINTS")
    void test_counts_one_clause_per_semicolon() {
        String rule = """
                SPEC java.security.KeyGenerator

                OBJECTS
                	java.lang.String algorithm;
                	int keysize;

                CONSTRAINTS
                	algorithm in {"AES", "HmacSHA256"};
                	algorithm in {"AES"} => keysize in {128, 192, 256};

                REQUIRES
                	randomized[this];
                """;
        assertEquals(2, CountingRule.countClauses(rule),
                "OBJECTS and REQUIRES also end their entries with ';' and must not be counted; "
                        + "only the CONSTRAINTS section is the denominator");
    }

    @Test
    @DisplayName("8.6: '&&' conjunctions are not split")
    void test_conjunctions_are_not_split() {
        String rule = """
                SPEC javax.crypto.Cipher

                CONSTRAINTS
                	alg(transformation) in {"RSA"} && mode(transformation) in {"ECB"} => pad(transformation) in {"NoPadding"};
                """;
        assertEquals(1, CountingRule.countClauses(rule),
                "a compound antecedent is one obligation; splitting it would make the denominator "
                        + "a function of how the author phrased the antecedent");
    }

    @Test
    @DisplayName("8.6: comments are removed before anything is counted")
    void test_comments_do_not_add_clauses() {
        String rule = """
                SPEC demo.Demo

                CONSTRAINTS
                	// the clause below replaced an older one: keysize in {1024};
                	keysize in {2048};
                	/* and this block mentions another; and another; */
                """;
        assertEquals(1, CountingRule.countClauses(rule),
                "a ';' inside a comment is not a clause; a comment is not countable and does not "
                        + "enter a metric");
    }

    @Test
    @DisplayName("8.6: a rule with no CONSTRAINTS section counts zero")
    void test_no_section_is_zero_not_an_error() {
        String rule = """
                SPEC java.security.KeyPair

                ENSURES
                	generatedKeyPair[this];
                """;
        assertEquals(0, CountingRule.countClauses(rule),
                "11 of the 49 upstream rules state no CONSTRAINTS at all; that is a zero, not a "
                        + "failure to read");
    }

    @Test
    @DisplayName("R1 prints itself, so it can travel beside a number")
    void test_rule_renders_with_its_statement() {
        assertTrue(CountingRule.R1.toString().startsWith("R1: "));
        assertTrue(CountingRule.R1.statement().contains("comments removed"));
    }
}
