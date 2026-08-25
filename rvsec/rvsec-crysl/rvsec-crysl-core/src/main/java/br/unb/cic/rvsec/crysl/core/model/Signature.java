package br.unb.cic.rvsec.crysl.core.model;

import java.util.List;
import java.util.Objects;

/**
 * A concrete method signature: the alphabet the comparison actually runs over.
 *
 * <p>Both sides of the comparison are reduced to signatures - the MOP side by resolving each
 * pointcut, the CrySL side from {@code CrySLMethod} - so that the two automata speak one language.
 * Labels are a MOP-side naming convention and never enter the alphabet (INV-CONF-03).
 *
 * @param declaringType fully-qualified declaring type
 * @param name          method name, or the declaring type's simple name for a constructor
 * @param paramTypes    fully-qualified parameter types, in declaration order
 * @param returnType    fully-qualified return type
 */
public record Signature(String declaringType, String name, List<String> paramTypes, String returnType) {

    public Signature {
        Objects.requireNonNull(declaringType, "Signature.declaringType is mandatory");
        Objects.requireNonNull(name, "Signature.name is mandatory");
        Objects.requireNonNull(returnType, "Signature.returnType is mandatory");
        paramTypes = List.copyOf(paramTypes);
    }
}
