package br.unb.cic.rv.grammar;

import br.unb.cic.rv.pointcut.BaseAspectExpander;
import br.unb.cic.rv.pointcut.CombinedPC;
import br.unb.cic.rv.pointcut.NotWithinPC;
import br.unb.cic.rv.pointcut.PointcutExpression;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "named-pointcut reference": {@code BaseAspect.notwithin()} expands via
 * {@link BaseAspectExpander} into an AND-chain of {@link NotWithinPC}, one per
 * {@code baseAspectExclusions} entry (§4.B, Z-decision INV-INS-101). The matcher-level fail-closed
 * behaviour (unrecognised name / empty list) is covered by {@code NamedRefResolverTest} in
 * {@code pointcut-engine}.
 */
class NamedReferenceGrammarTest {

    private static final List<String> CANONICAL_TWELVE = List.of(
            "sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*",
            "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*",
            "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*");

    @Test
    void baseAspectNotwithinExpandsTwelveExclusionsList() {
        // (a) N=12 canonical expansion — every entry is a NotWithinPC leaf in the AND-chain.
        PointcutExpression twelve = BaseAspectExpander.expand(CANONICAL_TWELVE);
        List<String> leaves = notWithinLeaves(twelve);
        assertEquals(CANONICAL_TWELVE, leaves,
                "the expansion must contain one NotWithinPC per exclusion, in order");

        // (b) N=2 smallest non-degenerate AND-chain.
        PointcutExpression two = BaseAspectExpander.expand(List.of("a..*", "b..*"));
        assertInstanceOf(CombinedPC.class, two, "N=2 must produce a CombinedPC AND-chain");
        assertEquals(CombinedPC.Op.AND, ((CombinedPC) two).op());
        assertEquals(List.of("a..*", "b..*"), notWithinLeaves(two));

        // (c) N=1 degenerate — a single NotWithinPC, no AND-of-one.
        PointcutExpression one = BaseAspectExpander.expand(List.of("only..*"));
        assertInstanceOf(NotWithinPC.class, one, "N=1 must return a bare NotWithinPC (no AND-of-one)");
        assertEquals("only..*", ((NotWithinPC) one).typePattern());

        // (d) N=0 empty — the expander rejects it; the matcher path raises LegacyDescriptorException
        //     (covered by NamedRefResolverTest.emptyExclusionsFailsClosed).
        assertThrows(IllegalArgumentException.class, () -> BaseAspectExpander.expand(List.of()));
    }

    /** Collect the {@code typePattern} of every {@link NotWithinPC} leaf, left to right. */
    private static List<String> notWithinLeaves(PointcutExpression e) {
        List<String> out = new ArrayList<>();
        collect(e, out);
        return out;
    }

    private static void collect(PointcutExpression e, List<String> out) {
        if (e instanceof CombinedPC c) {
            assertTrue(c.op() == CombinedPC.Op.AND, "BaseAspect expansion uses AND only");
            collect(c.left(), out);
            collect(c.right(), out);
        } else if (e instanceof NotWithinPC n) {
            out.add(n.typePattern());
        } else {
            throw new AssertionError("unexpected node in BaseAspect expansion: " + e.getClass());
        }
    }
}
