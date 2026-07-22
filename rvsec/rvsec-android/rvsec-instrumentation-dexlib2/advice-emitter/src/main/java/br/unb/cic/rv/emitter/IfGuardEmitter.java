package br.unb.cic.rv.emitter;

import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Wraps another {@link AdviceEmitter} with the runtime guard an
 * {@code if(<expr>)} pointcut clause imposes, lowering the guard directly to
 * DEX in the weaver (no fork-side runtime helper).
 *
 * <p>The guard recognises exactly the two expression shapes the corpus
 * contains, each over a variable {@code <bound>} bound by the advice's
 * {@code target(<bound>)} / {@code args(<bound>)} clause (resolved from
 * {@code ctx.match}):
 * <ul>
 *   <li>{@code <bound> == null} → {@link EmitPlan.GuardKind#NULL_CHECK}</li>
 *   <li>{@code !Thread.holdsLock(<bound>)} → {@link EmitPlan.GuardKind#NOT_HOLDS_LOCK}</li>
 * </ul>
 *
 * <p>This wrapper produces the delegate's invoke-plan unchanged and attaches an
 * {@link EmitPlan.GuardSpec} describing the guard. The executor
 * ({@code InstructionInjector.installGuard}) emits the guard check and branches
 * past the delegate's instructions when the guard is false, so the monitor
 * invoke fires exactly when the guard holds. The {@code NOT_HOLDS_LOCK} shape
 * needs one scratch register for {@code move-result vGuard}; the
 * {@code NULL_CHECK} shape needs none (it branches on {@code vBound} directly).
 *
 * <p>Any other expression shape, or a {@code <bound>} the match cannot resolve
 * to a register, raises {@link UnsupportedAspectConstructError} — the guard is
 * never silently dropped to an always-match, which would weave an invoke the
 * source intended to gate.
 */
public final class IfGuardEmitter implements AdviceEmitter {

    /** {@code if( <bound> == null )} — captures the bound variable name. */
    private static final Pattern NULL_CHECK =
            Pattern.compile("^([A-Za-z_$][\\w$.]*)==null$");
    /** {@code if( !Thread.holdsLock(<bound>) )} — captures the bound variable name. */
    private static final Pattern NOT_HOLDS_LOCK =
            Pattern.compile("^!(?:java\\.lang\\.)?Thread\\.holdsLock\\(([A-Za-z_$][\\w$.]*)\\)$");

    private final AdviceEmitter delegate;

    public IfGuardEmitter() { this.delegate = null; }
    private IfGuardEmitter(AdviceEmitter d) { this.delegate = d; }

    public IfGuardEmitter wrapping(AdviceEmitter base) {
        return new IfGuardEmitter(Objects.requireNonNull(base));
    }

    @Override
    public EmitPlan emit(EmitContext ctx) {
        if (delegate == null) {
            throw new IllegalStateException(
                    "IfGuardEmitter must be used via wrapping(base); raw emit() is unsupported");
        }
        EmitPlan inner = delegate.emit(ctx);

        String guardExpr = extractIfExpression(ctx.advice.getExpression());
        if (guardExpr == null) {
            throw new UnsupportedAspectConstructError(
                    "IfGuardEmitter selected but no if(...) clause found in expression: "
                            + ctx.advice.getExpression());
        }
        String normalized = guardExpr.replaceAll("\\s+", "");

        Matcher nullM = NULL_CHECK.matcher(normalized);
        if (nullM.matches()) {
            int boundReg = resolveBound(ctx, nullM.group(1), normalized);
            EmitPlan.GuardSpec spec =
                    new EmitPlan.GuardSpec(EmitPlan.GuardKind.NULL_CHECK, boundReg);
            // NULL_CHECK branches on vBound directly — no scratch needed.
            return new EmitPlan(inner.toInsert(), inner.insertionPoint(),
                    inner.registers(), inner.tryCatchSpec(), spec);
        }

        Matcher lockM = NOT_HOLDS_LOCK.matcher(normalized);
        if (lockM.matches()) {
            int boundReg = resolveBound(ctx, lockM.group(1), normalized);
            EmitPlan.GuardSpec spec =
                    new EmitPlan.GuardSpec(EmitPlan.GuardKind.NOT_HOLDS_LOCK, boundReg);
            // NOT_HOLDS_LOCK needs one scratch for the move-result holding the
            // holdsLock(...) result; stack it on top of the delegate's demand.
            RegisterRequest req = new RegisterRequest(
                    inner.registers().scratchCount() + 1,
                    inner.registers().needsWidePair(),
                    inner.registers().mustBeLowRange());
            return new EmitPlan(inner.toInsert(), inner.insertionPoint(),
                    req, inner.tryCatchSpec(), spec);
        }

        throw new UnsupportedAspectConstructError(
                "unsupported if(...) guard shape: '" + guardExpr
                        + "' — only '<bound> == null' and '!Thread.holdsLock(<bound>)' are lowered");
    }

    /**
     * Resolve {@code boundName} to its DEX register via the advice's
     * {@code target}/{@code args} bindings, or fail loud. A guard variable that
     * is not a resolvable binding cannot be gated correctly in-weaver, so we
     * refuse rather than weave an ungated invoke.
     */
    private int resolveBound(EmitContext ctx, String boundName, String normalized) {
        Integer reg = MonitorInvokeBuilder.resolveBindingRegister(
                ctx.advice, ctx.match, boundName);
        if (reg == null) {
            throw new UnsupportedAspectConstructError(
                    "if(...) guard '" + normalized + "' references '" + boundName
                            + "', which is not a resolvable target/args binding for this match");
        }
        return reg;
    }

    /**
     * Extract the raw text inside the first {@code if(...)} pointcut clause of
     * {@code expression}, honouring nested parentheses (e.g.
     * {@code if(!Thread.holdsLock(o))}). Returns {@code null} when no
     * {@code if(} clause is present.
     */
    private static String extractIfExpression(String expression) {
        if (expression == null) return null;
        int idx = findIfClause(expression);
        if (idx < 0) return null;
        int open = idx + 3; // past "if("
        int depth = 1;
        for (int i = open; i < expression.length(); i++) {
            char c = expression.charAt(i);
            if (c == '(') depth++;
            else if (c == ')') {
                depth--;
                if (depth == 0) return expression.substring(open, i);
            }
        }
        return null;
    }

    /**
     * Index of the {@code if(} that opens a pointcut clause — i.e. {@code if}
     * not preceded by an identifier character (so {@code notify(}/{@code endif(}
     * style tokens are not mistaken for the PCD).
     */
    private static int findIfClause(String expression) {
        int from = 0;
        while (true) {
            int idx = expression.indexOf("if(", from);
            if (idx < 0) {
                idx = expression.indexOf("if (", from);
                if (idx < 0) return -1;
            }
            if (idx == 0 || !isIdentPart(expression.charAt(idx - 1))) {
                return idx;
            }
            from = idx + 2;
        }
    }

    private static boolean isIdentPart(char c) {
        return Character.isLetterOrDigit(c) || c == '_' || c == '$';
    }

    @Override
    public String kind() { return "if-guarded[" + (delegate == null ? "-" : delegate.kind()) + "]"; }
}
