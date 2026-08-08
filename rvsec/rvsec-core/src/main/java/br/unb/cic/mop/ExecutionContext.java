package br.unb.cic.mop;

import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.Set;

/**
 * This class allows us to setup an execution
 * context, stating that an object is in an accepting
 * state or that an object has a property associated to it.
 *
 * We use it to "mimic" the ensures / requires
 * clauses of CrySL and to execute the unit
 * test cases.
 *
 * <p>Objects are identified <b>by identity</b>, which is how JavaMOP identifies
 * the object a monitor belongs to: it keys a monitor by
 * {@code System.identityHashCode} and confirms the match with {@code ==}. A
 * store keyed by {@code equals} would disagree with that on every type whose
 * {@code equals} is value-based -- {@code SecretKeySpec}, {@code String}, boxed
 * primitives -- and the disagreement is silent in all three directions: a write
 * over an object equal to a stored one adds nothing, so two monitors share one
 * mark; a {@code validate} succeeds for an object no monitored sequence ever
 * produced, provided an equal one was; and a removal in one monitor's
 * {@code @fail} takes another monitor's mark.
 */
public class ExecutionContext {

    private Map<Property, Set<Object>> context;

    private Set<Object> acceptingState;

    private static ExecutionContext instance;

    /*
     * A private constructor according to the
     * Singleton design pattern.
     */
    private ExecutionContext() {
        context = new HashMap<>();
        acceptingState = identitySet();
    }

    /*
     * A set that holds objects by identity rather than by equals.
     * IdentityHashMap is Java 1.4 and Android API 1; Collections.newSetFromMap
     * is Java 6 and Android API 9, which is the floor this imposes on an
     * instrumented application.
     */
    private static Set<Object> identitySet() {
        return Collections.newSetFromMap(new IdentityHashMap<Object, Boolean>());
    }

    /**
     * The unique way to obtain an instance to the
     * Execution context.
     *
     * @return the singleton ExecutionContext instance.
     */
    public static ExecutionContext instance() {
        if(instance == null) {
            instance = new ExecutionContext();
        }
        return instance;
    }

    /**
     * Remove a property from the ExecutionContext. We will
     * typically call this method in a <code>@fail</code>
     * clause of an MOP specification.
     */
    @Deprecated
    public void remove(Property property) {
        if(context.containsKey(property)) {
            context.remove(property);
        }
    }

    public void remove(Property property, Object obj) {
        if(context.containsKey(property)) {
            context.get(property).remove(obj);
        }
        if(context.get(property) != null && context.get(property).isEmpty()) {
            context.remove(property);
        }
    }

    /**
     * We should call this method in the advice bodies,
     * whenever we want to ensure that an object satisfies
     * a given property.
     *
     * Take a look at the ensures clause of a CrySL rule,
     * which often ensures a property of an object (after
     * a call to a method).
     *
     * @param property property we want to relate to an object
     * @param value object that will have a property assigned to
     */
    public void setProperty(Property property, Object value) {
        Set<Object> objects = identitySet();
        if(context.containsKey(property)) {
            objects = context.get(property);
        }
        objects.add(value);
        context.put(property, objects);
    }

    /**
     * Returns true if the object <code>obj</code> has
     * been assigned to the <code>property</code>.
     *
     * @return A boolean indicating if a mapping between
     * a property and a value exists.
     */
    public boolean validate(Property property, Object obj) {
        return context.containsKey(property) && context.get(property).contains(obj);
    }

    /**
     * Returns true if <code>obj</code> is in accepting state.
     */
    public boolean isInAcceptingState(Object obj) {
        return acceptingState.contains(obj);
    }

    /**
     * Setup that <code>obj</code> is in an accepting state.
     * We should call this method in a <code>@match</code>
     * clause o an MOP specification.
     */
    public void setObjectAsInAcceptingState(Object obj) {
        acceptingState.add(obj);
    }

    /**
     * Use this method to indicate that an <code>obj</code>
     * is not in accepting state anymore. We should call
     * this method in a <code>@fail</code> clause of an MOP
     * specification.
     */
    public void unsetObjectAsInAcceptingState(Object obj) { acceptingState.remove(obj); }

    /**
     * Checks if <code>obj</code> has a property related
     * to it (not mattering which one).

     * @return <code>true</code> if <code>obj</code> has a
     * property related to it.
     */
    public boolean hasEnsuredPredicate(Object obj) {
        for(Set<Object> objects: context.values()) {
            if(objects.contains(obj)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Reset the ExecutionContext to its initial state.
     */
    public void reset() {
        acceptingState.clear();
        context.clear();
    }
}
