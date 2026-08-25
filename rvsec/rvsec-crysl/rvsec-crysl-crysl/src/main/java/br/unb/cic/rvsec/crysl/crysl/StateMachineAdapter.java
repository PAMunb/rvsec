package br.unb.cic.rvsec.crysl.crysl;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.automata.Transition;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import crysl.rule.CrySLMethod;
import crysl.rule.StateMachineGraph;
import crysl.rule.StateNode;
import crysl.rule.TransitionEdge;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/**
 * The rule's {@code ORDER}, as the façade already compiled it, turned into the automaton the
 * comparison runs on.
 *
 * <p>The alphabet is {@link Signature} and nothing else (INV-CONF-03). A {@code TransitionEdge}
 * carries a <em>collection</em> of {@code CrySLMethod} — one edge of {@code Cipher.crysl} labelled
 * {@code Inits} holds eight overloads of {@code init} — and each of those methods becomes one
 * transition of its own between the same two states. Two facts follow, and both are wanted: the
 * aggregate name {@code Inits} disappears, because names are a rule-side convention the {@code .mop}
 * side does not share; and the eight overloads stay distinct, because they are eight different
 * calls on device and a comparison that merged them would be comparing something no program can
 * execute.
 *
 * <p>The result may be non-deterministic. {@code Cipher.crysl} has {@code init} edges out of state
 * {@code 0} and out of state {@code 1}, and rules of the form {@code con, a?, a} are genuinely
 * ambiguous under a Glushkov construction. Determinizing is M2's job; assuming determinism here
 * would quietly assume something the corpus does not provide.
 */
public final class StateMachineAdapter {

    private StateMachineAdapter() {
    }

    /**
     * @param usagePattern the {@code ORDER} state machine the façade built for a rule
     * @return the same language, over signatures
     */
    public static Automaton toAutomaton(StateMachineGraph usagePattern) {
        Objects.requireNonNull(usagePattern, "usagePattern is mandatory");

        Set<String> states = new LinkedHashSet<>();
        for (StateNode node : usagePattern.getNodes()) {
            states.add(node.getName());
        }
        // getStartNode() is the artificial "-1" the builder prepends; it is a node of the graph, but
        // an automaton whose initial state is not among its states cannot be constructed at all, so
        // adding it defensively is cheaper than trusting the builder's invariant.
        String initial = usagePattern.getStartNode().getName();
        states.add(initial);

        Set<String> accepting = new LinkedHashSet<>();
        for (StateNode node : usagePattern.getAcceptingStates()) {
            accepting.add(node.getName());
            states.add(node.getName());
        }

        List<Transition> transitions = new ArrayList<>();
        for (TransitionEdge edge : usagePattern.getAllTransitions()) {
            String from = edge.getLeft().getName();
            String to = edge.getRight().getName();
            states.add(from);
            states.add(to);
            for (CrySLMethod method : edge.getLabel()) {
                // No guard: CrySL puts side conditions in CONSTRAINTS, not on ORDER transitions,
                // so an Optional.empty() here states a fact about the language rather than hiding
                // something the rule declared.
                transitions.add(new Transition(from, toSignature(method), Optional.empty(), to));
            }
        }
        return new Automaton(states, initial, accepting, transitions);
    }

    /**
     * One {@code CrySLMethod} as a {@link Signature}.
     *
     * <p>Three conversions matter. The <em>name</em> is the short name, so a constructor comes out
     * as the declaring type's simple name ({@code SecretKeySpec}), which is the convention
     * {@code Signature} declares and the convention the MOP side resolves pointcuts to. The
     * <em>parameter types</em> are the values of the parameter entries: CrySL writes each parameter
     * as {@code name -> type} and it is the type that is part of the signature; the names are the
     * rule's binding, not the call's shape. The <em>return type</em> is the value of the return
     * entry, {@code void} being written as such by the façade.
     */
    public static Signature toSignature(CrySLMethod method) {
        Objects.requireNonNull(method, "method is mandatory");
        List<String> paramTypes = method.getParameters().stream()
                .map(java.util.Map.Entry::getValue)
                .toList();
        String returnType = method.getRetObject() == null
                ? CrySLMethod.VOID
                : method.getRetObject().getValue();
        return new Signature(method.getDeclaringClassName(), method.getShortMethodName(),
                paramTypes, returnType);
    }
}
