package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Shared helper for building the {@code invoke-static} instruction that calls
 * the generated RuntimeMonitor's event method.
 *
 * <p>Every {@link AdviceEmitter} ultimately emits one such invoke; differences
 * between advice kinds are about placement (before/after/try-catch) and about
 * which registers hold the bound args, not about the invoke shape.
 */
final class MonitorInvokeBuilder {

    private MonitorInvokeBuilder() {}

    /**
     * @return a single-instruction list containing the {@code invoke-static}
     *         call to {@code <monitorOwner>.<monitorCall.method>(<paramTypes>)V}
     *         with arg registers drawn from {@code match.argBindings}.
     */
    static List<BuilderInstruction> buildInvoke(EmitContext ctx) {
        AdviceDescriptor advice = ctx.advice;
        MonitorCallDescriptor call = ctx.primaryMonitorCall();
        if (call == null) return Collections.emptyList();

        String owner = ctx.monitorOwnerDescriptor;
        String eventMethod = shortName(call.getMethod());
        MethodReference ref = buildMethodReference(owner, eventMethod, advice, ctx.typeResolver);

        int[] regs = registersFor(advice, ctx.match);
        return Collections.singletonList(buildInvokeStatic(ref, regs));
    }

    private static String shortName(String fullyQualifiedMethod) {
        if (fullyQualifiedMethod == null) return "";
        int dot = fullyQualifiedMethod.lastIndexOf('.');
        return dot >= 0 ? fullyQualifiedMethod.substring(dot + 1) : fullyQualifiedMethod;
    }

    private static MethodReference buildMethodReference(String owner, String name,
                                                         AdviceDescriptor advice,
                                                         TypeResolver resolver) {
        List<String> paramDescriptors = new ArrayList<>();
        for (ParameterDescriptor p : advice.getParameters()) {
            paramDescriptors.add(resolver.toDescriptor(p.getType()));
        }
        // Monitor event methods return void by MOP convention; RV-Monitor's
        // generated RuntimeMonitor always declares the Event methods as
        // static void.
        return new ImmutableMethodReference(owner, name, paramDescriptors, "V");
    }

    private static int[] registersFor(AdviceDescriptor advice, Match match) {
        int n = advice.getParameters().size();
        int[] regs = new int[n];
        for (int i = 0; i < n; i++) {
            String argKey = String.format("arg%02d", i);
            Integer reg = match.argBindings.get(argKey);
            regs[i] = reg != null ? reg : 0;
        }
        return regs;
    }

    private static BuilderInstruction buildInvokeStatic(MethodReference ref, int[] regs) {
        // Short-form invoke-static/range for ≤5 registers; /range for more.
        if (regs.length <= 5) {
            int[] padded = new int[5];
            System.arraycopy(regs, 0, padded, 0, regs.length);
            return new BuilderInstruction35c(
                    Opcode.INVOKE_STATIC, regs.length,
                    padded[0], padded[1], padded[2], padded[3], padded[4],
                    ref);
        }
        // For >5 args we need contiguous registers; the RegisterAllocator
        // arranges that, so the call is safe here.
        int start = regs[0];
        return new BuilderInstruction3rc(
                Opcode.INVOKE_STATIC_RANGE, start, regs.length, ref);
    }
}
