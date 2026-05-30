package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;

import java.util.Collections;
import java.util.List;

/**
 * Builds a synthesized {@code <clinit>} ({@code static constructor})
 * {@link Method} for a class that has none, so a
 * {@code staticinitialization(T+)} advice can fire (§4.Y).
 *
 * <p>The {@link br.unb.cic.rv.pointcut.PointcutMatcher staticinit matcher}
 * gates on {@code "<clinit>".equals(method.getName())}, so a class without a
 * class initializer is never visited by {@code DexWeaver}'s per-method loop.
 * The weaver's staticinit pre-pass detects this case and calls
 * {@link #synthesize} to construct a fresh {@code <clinit>} whose body is the
 * advice's delivery sequence followed by {@code return-void}, then registers
 * it via {@link DexFileMutator#addSynthesizedMethod}.
 *
 * <h2>Register frame</h2>
 * The synthesized {@code <clinit>} takes no parameters, so its frame is fully
 * private. The caller emits the advice body against a known low base and
 * passes the matching {@code registerCount} (e.g. 2 for the §4.Y Signature
 * delivery, which uses v0/v1), so the ART verifier accepts the frame.
 */
public final class StaticInitSynthesizer {

    private StaticInitSynthesizer() {}

    /** Access flags of a class initializer: {@code static constructor}. */
    private static final int CLINIT_FLAGS =
            AccessFlags.STATIC.getValue() | AccessFlags.CONSTRUCTOR.getValue();

    /**
     * Construct a synthesized {@code <clinit>} for {@code definingClassDesc}
     * whose implementation runs {@code body} then returns.
     *
     * @param definingClassDesc DEX descriptor of the owning class ({@code Lcls;}).
     * @param body              the advice delivery instructions (without the
     *                          trailing {@code return-void}); every register
     *                          they reference must be {@code < registerCount}.
     * @param registerCount     frame size covering the highest register
     *                          {@code body} uses (≥ 1).
     * @return an {@link ImmutableMethod} ready to register via
     *         {@link DexFileMutator#addSynthesizedMethod}.
     */
    public static Method synthesize(String definingClassDesc,
                                    List<BuilderInstruction> body,
                                    int registerCount) {
        MutableMethodImplementation impl =
                new MutableMethodImplementation(Math.max(1, registerCount));
        int i = 0;
        for (BuilderInstruction ins : body) {
            impl.addInstruction(i++, ins);
        }
        impl.addInstruction(i, new BuilderInstruction10x(Opcode.RETURN_VOID));

        return new ImmutableMethod(
                definingClassDesc,
                "<clinit>",
                Collections.emptyList(),
                "V",
                CLINIT_FLAGS,
                null,
                null,
                impl);
    }
}
