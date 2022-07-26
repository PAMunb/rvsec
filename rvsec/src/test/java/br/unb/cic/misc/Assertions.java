package br.unb.cic.misc;

import org.junit.Assert;

import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.eh.ErrorCollector;

public class Assertions extends Assert {

    public static void mustBeInAcceptingState(Object obj) {
        if(ExecutionContext.instance().isInAcceptingState(obj)) {
            assertTrue(true);
        }
        else {
            fail("Object is not in accepting state.");
        }
    }

    public static void mustNotBeInAcceptingState(Object obj) {
        if(ExecutionContext.instance().isInAcceptingState(obj)) {
            fail("Object is in a final state.");
        }
        else {
            assertTrue(true);
        }
    }

    public static void hasEnsuredPredicate(Object obj) {
        if(ExecutionContext.instance().hasEnsuredPredicate(obj)) {
            assertTrue(true);
        }
        else {
            fail("Object has not ensured predicate.");
        }
    }

    public static void notHasEnsuredPredicate(Object obj) {
        if(ExecutionContext.instance().hasEnsuredPredicate(obj)) {
            fail("Object has an ensured predicate.");
        }
        else {
            assertTrue(true);
        }
    }

    public static void hasEnsuredPredicate(ExecutionContext.Property property, Object obj) {
        if(ExecutionContext.instance().validate(property, obj)) {
            assertTrue(true);
        }
        else {
            fail("Object has not an ensured predicate of " + property);
        }
    }

    public static void expectingEmptySetOfErrors() {
        if(ErrorCollector.instance().getErrors().isEmpty()) {
            assertTrue(true);
        }
        else {
            fail("Expecting no error in the test case, but found " + ErrorCollector.instance().getErrors().size());
        }
    }

    public static void expectingNonEmptySetOfErrors() {
        if(!ErrorCollector.instance().getErrors().isEmpty()) {
            assertTrue(true);
        }
        else {
            fail("Expecting a non empty set of errors, but found " + ErrorCollector.instance().getErrors().size()
                    + " errors");
        }
    }
    public static void expectingNonEmptySetOfErrors(int numberOfErrors) {
        if(ErrorCollector.instance().getErrors().size() == numberOfErrors) {
            assertTrue(true);
        }
        else {
            fail("Expecting " + numberOfErrors + ", but found " + ErrorCollector.instance().getErrors().size() + " errors");
        }
    }

}
