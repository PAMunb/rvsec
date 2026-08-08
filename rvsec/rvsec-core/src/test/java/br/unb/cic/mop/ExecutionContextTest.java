package br.unb.cic.mop;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import javax.crypto.spec.SecretKeySpec;

import org.junit.Before;
import org.junit.Test;

/**
 * The predicate store identifies objects the way the monitor index does.
 *
 * <p>JavaMOP gives every monitored instance its own monitor, keyed by
 * {@code System.identityHashCode} and confirmed with {@code ==}, so it never
 * confuses two alike instances. The store where those monitors record what they
 * observed has to agree, or the two halves of one mechanism disagree about what
 * "the same object" means.
 *
 * <p>{@link SecretKeySpec} is the witness used here because its {@code equals}
 * compares the key material and the algorithm, so two independently constructed
 * keys with the same bytes are equal and not identical -- exactly the shape an
 * application produces when it builds the same hardcoded key twice, one through
 * a conforming sequence and one through a violating branch.
 */
public class ExecutionContextTest {

    private SecretKeySpec first;
    private SecretKeySpec second;

    @Before
    public void setUp() {
        ExecutionContext.instance().reset();
        byte[] material = new byte[] { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 };
        first = new SecretKeySpec(material, "AES");
        second = new SecretKeySpec(material.clone(), "AES");
        assertTrue("the witness is only meaningful if the two keys are equal", first.equals(second));
        assertFalse("...and not the same object", first == second);
    }

    @Test
    public void marksOnlyTheObjectItWasGiven() {
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, first);

        assertTrue(ExecutionContext.instance().validate(Property.GENERATED_KEY, first));
        assertFalse(ExecutionContext.instance().validate(Property.GENERATED_KEY, second));
    }

    @Test
    public void removingOneLeavesTheOtherMarked() {
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, first);
        ExecutionContext.instance().setProperty(Property.GENERATED_KEY, second);

        ExecutionContext.instance().remove(Property.GENERATED_KEY, first);

        assertFalse(ExecutionContext.instance().validate(Property.GENERATED_KEY, first));
        assertTrue(ExecutionContext.instance().validate(Property.GENERATED_KEY, second));
    }

    @Test
    public void acceptingStateIsPerObject() {
        ExecutionContext.instance().setObjectAsInAcceptingState(first);

        assertTrue(ExecutionContext.instance().isInAcceptingState(first));
        assertFalse(ExecutionContext.instance().isInAcceptingState(second));

        ExecutionContext.instance().unsetObjectAsInAcceptingState(first);
        assertFalse(ExecutionContext.instance().isInAcceptingState(first));
    }

    @Test
    public void ensuredPredicateScanIsPerObject() {
        ExecutionContext.instance().setProperty(Property.RANDOMIZED, first);

        assertTrue(ExecutionContext.instance().hasEnsuredPredicate(first));
        assertFalse(ExecutionContext.instance().hasEnsuredPredicate(second));
    }
}
