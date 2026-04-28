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
        TryCatchSpec tryCatchSpec
) {

    public EmitPlan {
        toInsert = toInsert == null ? Collections.emptyList() : List.copyOf(toInsert);
        if (registers == null) registers = RegisterRequest.NONE;
        // tryCatchSpec is nullable by design — only populated for TRY_CATCH_WRAP.
    }

    public static EmitPlan of(List<BuilderInstruction> ins, InsertionPoint pt) {
        return new EmitPlan(ins, pt, RegisterRequest.NONE, null);
    }

    public static EmitPlan of(List<BuilderInstruction> ins, InsertionPoint pt,
                              RegisterRequest req) {
        return new EmitPlan(ins, pt, req, null);
    }

    public static EmitPlan tryCatch(List<BuilderInstruction> handler,
                                     RegisterRequest req,
                                     TryCatchSpec spec) {
        return new EmitPlan(handler, InsertionPoint.TRY_CATCH_WRAP, req, spec);
    }

    /**
     * Shape of the try/catch the executor must install around the matched
     * instruction. {@code catchType} is the DEX type descriptor of the caught
     * exception; {@code catchAny} flags the conventional catch-all on
     * {@code Ljava/lang/Throwable;} that plain {@code after() throwing(...)}
     * without a declared type produces.
     */
    public record TryCatchSpec(String catchType, boolean catchAny) {
        public static TryCatchSpec catchAll() {
            return new TryCatchSpec("Ljava/lang/Throwable;", true);
        }
        public static TryCatchSpec specific(String catchType) {
            return new TryCatchSpec(catchType, false);
        }
    }
}
