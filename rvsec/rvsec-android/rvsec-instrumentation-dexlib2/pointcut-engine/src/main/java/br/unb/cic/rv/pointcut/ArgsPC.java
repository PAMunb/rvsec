package br.unb.cic.rv.pointcut;

import java.util.List;

/**
 * {@code args(name1, name2, ...)} — binds each argument of the matched join point
 * to a parameter name declared in the advice signature.
 *
 * <p>Names match the {@code AdviceDescriptor.parameters} list by name, not by position.
 */
public record ArgsPC(List<String> names) implements PointcutExpression {
    public ArgsPC {
        names = List.copyOf(names);
    }
}
