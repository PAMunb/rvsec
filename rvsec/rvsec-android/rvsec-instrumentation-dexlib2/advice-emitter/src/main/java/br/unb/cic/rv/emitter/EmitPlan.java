package br.unb.cic.rv.emitter;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;

import java.util.Collections;
import java.util.List;

/**
 * A concrete plan for injecting a single advice occurrence into a host method.
 *
 * <p>Fields:
 * <ul>
 *   <li>{@code toInsert} — the ordered list of {@link BuilderInstruction}s the
 *       executor writes into the method implementation.</li>
 *   <li>{@code insertionPoint} — where the instructions land relative to the
 *       matched site ({@link InsertionPoint}).</li>
 *   <li>{@code registers} — scratch-register demand for the allocator.</li>
 *   <li>{@code tryCatchSpec} — populated only for
 *       {@link InsertionPoint#TRY_CATCH_WRAP} plans; describes the try range
 *       and the catch-type the executor must wire to a handler that runs the
 *       plan's instructions.</li>
 *   <li>{@code guardSpec} — populated only when an {@code if(<expr>)} pointcut
 *       clause gates this advice. Describes the runtime guard the executor
 *       installs around {@code toInsert}: the executor emits the guard check,
 *       branches past {@code toInsert} when the guard is false, so the monitor
 *       invoke fires exactly when the guard holds (see {@link GuardSpec} and
 *       {@code InstructionInjector.installGuard}).</li>
 * </ul>
 *
 * <p>The plan is intentionally dexlib2-flavored (uses {@code BuilderInstruction})
 * because the {@code dex-mutator} executor consumes them directly without any
 * further translation.
 */
public record EmitPlan(
        List<BuilderInstruction> toInsert,
        InsertionPoint insertionPoint,
        RegisterRequest registers,
        TryCatchSpec tryCatchSpec,
        GuardSpec guardSpec
) {

    public EmitPlan {
        toInsert = toInsert == null ? Collections.emptyList() : List.copyOf(toInsert);
        if (registers == null) registers = RegisterRequest.NONE;
        // tryCatchSpec is nullable by design — only populated for TRY_CATCH_WRAP.
        // guardSpec is nullable by design — only populated for if(...)-gated advice.
    }

    /** Four-arg overload retained for plans that carry no guard. */
    public EmitPlan(List<BuilderInstruction> toInsert, InsertionPoint insertionPoint,
                    RegisterRequest registers, TryCatchSpec tryCatchSpec) {
        this(toInsert, insertionPoint, registers, tryCatchSpec, null);
    }

    public static EmitPlan of(List<BuilderInstruction> ins, InsertionPoint pt) {
        return new EmitPlan(ins, pt, RegisterRequest.NONE, null, null);
    }

    public static EmitPlan of(List<BuilderInstruction> ins, InsertionPoint pt,
                              RegisterRequest req) {
        return new EmitPlan(ins, pt, req, null, null);
    }

    public static EmitPlan tryCatch(List<BuilderInstruction> handler,
                                     RegisterRequest req,
                                     TryCatchSpec spec) {
        return new EmitPlan(handler, InsertionPoint.TRY_CATCH_WRAP, req, spec, null);
    }

    /**
     * Shape of the try/catch the executor must install around the matched
     * instruction. {@code catchType} is the DEX type descriptor of the caught
     * exception; {@code catchAny} flags the conventional catch-all on
     * {@code Ljava/lang/Throwable;} that plain {@code after() throwing(...)}
     * without a declared type produces.
     *
     * <p>{@code throwingOperandIndex} is the position (in the monitor invoke's
     * operand list) of the {@code throwing(<name>)}-bound exception argument, or
     * {@code -1} when the advice binds no exception parameter. The
     * {@code MonitorInvokeBuilder} emits a placeholder register at that slot
     * (it cannot know the caught-exception register until the executor allocates
     * one); the executor rewrites that slot to the register written by
     * {@code move-exception} when it materialises the handler block (§4.T). A
     * dedicated index avoids guessing which operand is the exception when the
     * monitor event also takes args/target bindings (the corpus's sole site
     * passes {@code (o, e)} — two operands, only the second is the exception).
     */
    public record TryCatchSpec(String catchType, boolean catchAny, int throwingOperandIndex) {
        public static TryCatchSpec catchAll() {
            return new TryCatchSpec("Ljava/lang/Throwable;", true, -1);
        }
        public static TryCatchSpec catchAll(int throwingOperandIndex) {
            return new TryCatchSpec("Ljava/lang/Throwable;", true, throwingOperandIndex);
        }
        public static TryCatchSpec specific(String catchType) {
            return new TryCatchSpec(catchType, false, -1);
        }
        public static TryCatchSpec specific(String catchType, int throwingOperandIndex) {
            return new TryCatchSpec(catchType, false, throwingOperandIndex);
        }
    }

    /**
     * Runtime guard an {@code if(<expr>)} pointcut clause imposes on this
     * advice. The executor installs the guard around {@code toInsert} so the
     * monitor invoke fires only when the guard holds.
     *
     * <p>{@code boundRegister} is the DEX register holding the {@code <bound>}
     * variable referenced inside the guard, resolved from the match's
     * {@code target(<bound>)} / {@code args(<bound>)} binding. The two
     * supported shapes lower as:
     * <ul>
     *   <li>{@link GuardKind#NULL_CHECK} ({@code <bound> == null}):
     *       {@code if-nez vBound, :skip} — the monitor invoke is skipped when
     *       {@code vBound} is non-null (guard false).</li>
     *   <li>{@link GuardKind#NOT_HOLDS_LOCK} ({@code !Thread.holdsLock(<bound>)}):
     *       {@code invoke-static {vBound}, Thread.holdsLock(Object)Z} +
     *       {@code move-result vGuard} + {@code if-nez vGuard, :skip} — the
     *       invoke is skipped when the current thread DOES hold the lock
     *       (guard false). {@code vGuard} is the scratch register the executor
     *       allocates for this plan.</li>
     * </ul>
     */
    public record GuardSpec(GuardKind kind, int boundRegister) {}

    /** Shape of the {@code if(<expr>)} guard the executor lowers in-weaver. */
    public enum GuardKind {
        /** {@code <bound> == null} — branch past the invoke when non-null. */
        NULL_CHECK,
        /** {@code !Thread.holdsLock(<bound>)} — branch past the invoke when the lock is held. */
        NOT_HOLDS_LOCK
    }
}
