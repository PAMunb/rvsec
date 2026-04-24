package br.unb.cic.rv.pointcut;

/**
 * Typed AST for AspectJ pointcut expressions emitted by JavaMOP.
 *
 * <p>Shape covered (task 3.2):
 * <pre>
 *   expr   := or
 *   or     := and ('||' and)*
 *   and    := unary ('&amp;&amp;' unary)*
 *   unary  := '!' unary | primary
 *   primary := 'call' '(' methodSig ')'
 *           | 'execution' '(' sigPattern ')'
 *           | 'args' '(' name (',' name)* ')'
 *           | 'target' '(' name ')'
 *           | 'within' '(' typePattern ')'
 *           | 'staticinitialization' '(' typePattern ')'
 *           | 'if' '(' javaExpr ')'
 *           | 'adviceexecution' '(' ')'
 *           | namedRef   // e.g. BaseAspect.notwithin(), emitted by rv-monitor templates
 * </pre>
 *
 * <p>Concrete nodes are records; the sealed hierarchy lets consumers use exhaustive
 * {@code switch} over the AST without a visitor.
 */
public sealed interface PointcutExpression
        permits CallPC, ExecutionPC, ArgsPC, TargetPC, WithinPC, NotWithinPC,
                StaticInitPC, IfPC, CombinedPC, NamedRefPC {
}
