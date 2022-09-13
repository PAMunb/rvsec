package br.unb.cic.mop;

import java.util.*;

/**
 * This class allows us to setup an execution
 * context, stating that an object is in an accepting
 * state or that an object has a property associated to it.
 *
 * We use it to "mimic" the ensures / requires
 * clauses of CrySL and to execute the unit
 * test cases.
 */
public class ExecutionContext {
    /*
     * The properties that we are interested in.
     */
    public enum Property {
        GENERATED_KEY,
        DIGESTED,
        ENCRYPTED,
        GENERATED_MAC,
        GENERATED_PRIVATE_KEY,
        GENERATED_PUBLIC_KEY,
        GENERATE_SSL_CONTEXT,
        GENERATE_SSL_ENGINE,
        GENERATED_KEY_MANAGERS,
        GENERATED_KEY_PAIR,
        GENERATED_TRUST_MANAGER,
        GENERATED_TRUST_MANAGERS,
        GENERATED_KEY_STORE,
        PREPARED_DH,
        PREPARED_GCM,
        PREPARED_HMAC,
        PREPARED_PBE,
        PREPARED_IV,
        RANDOMIZED,
        SIGNED,
        SPECCED_KEY,
        VERIFIED,
        WRAPPED_KEY
    }

    private Map<Property, Set<Object>> context;

    private Set<Object> acceptingState;

    private static ExecutionContext instance;

    /*
     * A private constructor according to the
     * Singleton design pattern.
     */
    private ExecutionContext() {
        context = new HashMap<>();
        acceptingState = new HashSet<>();
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
        Set<Object> objects = context.getOrDefault(property, new HashSet<>());
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
