package br.unb.cic.rv.mutator;

import br.unb.cic.rv.pointcut.InheritanceResolver;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.FiveRegisterInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.RegisterRangeInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;

/**
 * Handler-stamp weaver: routes every {@code invoke-virtual} (or
 * {@code invoke-virtual/range}) of
 * {@code setOnClickListener(View$OnClickListener)},
 * {@code setOnLongClickListener(View$OnLongClickListener)} and
 * {@code setAccessibilityDelegate(View$AccessibilityDelegate)} on
 * {@code android.view.View} or any subtype to the static method of the same
 * name in {@code mop.RvsecStamp} (INV-INS-176). A site is a candidate by the
 * exact name and descriptor of one of these setters; the owner decides
 * whether it is rewritten.
 *
 * <p>The helper takes the receiver as its first parameter, so the rewrite keeps
 * the register list and only swaps the opcode and the reference
 * ({@link InstructionInjector#replaceInvoke}); the method's size, branch
 * targets and try ranges are untouched (INV-INS-175). The helper performs the
 * original call through virtual dispatch, so an app subclass that overrides
 * one of these setters still runs its override.
 *
 * <h2>Compose virtual nodes</h2>
 * A Compose screen has no view per widget: its nodes are virtual, and Compose's
 * {@code AndroidComposeViewAccessibilityDelegateCompat} fills each one from a
 * {@code SemanticsNode} in the private method
 * {@code populateAccessibilityNodeInfoProperties(int, AccessibilityNodeInfoCompat, SemanticsNode)}.
 * Being private, that call cannot be routed through a helper, so the weaver
 * inserts {@code invoke-static mop.RvsecStamp.composeNode(info, node)} right
 * after it, reusing the call's own info and node registers: the call returns
 * void, so both registers still hold their values. The match is on the exact
 * owner, name and signature; a library whose names R8 renamed has no match and
 * is left alone.
 *
 * <h2>What is left alone</h2>
 * <ul>
 *   <li>{@code invoke-super} and {@code invoke-super/range}: they name an
 *       implementation, not a dispatch, and the helper can only dispatch
 *       virtually. These sites are counted in
 *       {@link StampReport#invokeSuperSkipped}.</li>
 *   <li>A call whose static owner is not assignable to {@code android.view.View}
 *       through the APK and framework hierarchy, including an owner the
 *       hierarchy cannot resolve. Counted in {@link StampReport#ownerNotView}.</li>
 *   <li>A candidate invoked with any other opcode ({@code invoke-interface},
 *       {@code invoke-direct}, {@code invoke-static} or their range forms):
 *       left alone and not counted.</li>
 *   <li>Classes of the {@code mop} package, which hold the helper itself.</li>
 * </ul>
 *
 * <p>The weaver is independent of the MOP descriptor: it adds no monitor event
 * and changes no site the advice weave touches.
 */
public final class StampWeaver {

    /** DEX descriptor of the helper class the call sites are routed to. */
    public static final String STAMP_CLASS_DESC = "Lmop/RvsecStamp;";
    private static final String VIEW_DESC = "Landroid/view/View;";
    private static final String VIEW_FQN = "android.view.View";

    /** The three stamped setters. */
    public enum Kind { CLICK, LONG_CLICK, DELEGATE }

    private record Target(Kind kind, MethodReference helper) {}

    /** {@code name(params)return} of an original setter → its helper. */
    private static final Map<String, Target> TARGETS = Map.of(
            "setOnClickListener(Landroid/view/View$OnClickListener;)V",
            new Target(Kind.CLICK, helper("setOnClickListener", "Landroid/view/View$OnClickListener;")),
            "setOnLongClickListener(Landroid/view/View$OnLongClickListener;)V",
            new Target(Kind.LONG_CLICK, helper("setOnLongClickListener", "Landroid/view/View$OnLongClickListener;")),
            "setAccessibilityDelegate(Landroid/view/View$AccessibilityDelegate;)V",
            new Target(Kind.DELEGATE, helper("setAccessibilityDelegate", "Landroid/view/View$AccessibilityDelegate;")));

    private static final String COMPOSE_DELEGATE_DESC =
            "Landroidx/compose/ui/platform/AndroidComposeViewAccessibilityDelegateCompat;";
    private static final String COMPOSE_POPULATE =
            "populateAccessibilityNodeInfoProperties(ILandroidx/core/view/accessibility/"
                    + "AccessibilityNodeInfoCompat;Landroidx/compose/ui/semantics/SemanticsNode;)V";
    private static final MethodReference COMPOSE_HELPER = new ImmutableMethodReference(
            STAMP_CLASS_DESC, "composeNode",
            List.of("Ljava/lang/Object;", "Ljava/lang/Object;"), "V");

    private final InheritanceResolver inheritance;
    /** Owner descriptor → whether it is assignable to {@code android.view.View}. */
    private final Map<String, Boolean> ownerIsView = new HashMap<>();

    public StampWeaver(InheritanceResolver inheritance) {
        this.inheritance = Objects.requireNonNull(inheritance);
    }

    private static MethodReference helper(String name, String listenerDesc) {
        return new ImmutableMethodReference(STAMP_CLASS_DESC, name,
                List.of(VIEW_DESC, listenerDesc), "V");
    }

    /**
     * Rewrite the stamped call sites of {@code dex}.
     *
     * <p>A method is materialised through {@code forMethod} only when its
     * original body holds a candidate call, and the rewrite then runs over the
     * materialised body, so it sees whatever an earlier weave already put
     * there.
     *
     * @param forMethod the mutable body of a method, shared with the other
     *     weaves of the same DEX
     * @return the per-kind counters for this DEX
     */
    public StampReport weave(DexFile dex, Function<Method, MutableMethodImplementation> forMethod) {
        int click = 0;
        int longClick = 0;
        int delegate = 0;
        int invokeSuperSkipped = 0;
        int ownerNotView = 0;
        int composeSites = 0;
        for (ClassDef classDef : dex.getClasses()) {
            if (classDef.getType().startsWith("Lmop/")) continue;
            for (Method method : classDef.getMethods()) {
                MethodImplementation impl = method.getImplementation();
                if (impl == null || !hasCandidate(impl.getInstructions())) continue;
                MutableMethodImplementation mut = forMethod.apply(method);
                if (mut == null) continue;
                InstructionInjector injector = new InstructionInjector(mut);
                List<BuilderInstruction> instructions = mut.getInstructions();
                for (int idx = 0; idx < instructions.size(); idx++) {
                    Instruction ins = instructions.get(idx);
                    if (isComposePopulate(ins)) {
                        mut.addInstruction(idx + 1, composeCall(ins));
                        instructions = mut.getInstructions();
                        idx++;
                        composeSites++;
                        continue;
                    }
                    MethodReference ref = candidateRef(ins);
                    if (ref == null) continue;
                    Target target = TARGETS.get(signature(ref));
                    Opcode op = ins.getOpcode();
                    if (op == Opcode.INVOKE_SUPER || op == Opcode.INVOKE_SUPER_RANGE) {
                        invokeSuperSkipped++;
                        continue;
                    }
                    if (op != Opcode.INVOKE_VIRTUAL && op != Opcode.INVOKE_VIRTUAL_RANGE) continue;
                    if (!isView(ref.getDefiningClass())) {
                        ownerNotView++;
                        continue;
                    }
                    injector.replaceInvoke(idx, target.helper());
                    switch (target.kind()) {
                        case CLICK -> click++;
                        case LONG_CLICK -> longClick++;
                        case DELEGATE -> delegate++;
                    }
                }
            }
        }
        return new StampReport(click, longClick, delegate, composeSites,
                invokeSuperSkipped, ownerNotView);
    }

    private static boolean hasCandidate(Iterable<? extends Instruction> instructions) {
        for (Instruction ins : instructions) {
            if (candidateRef(ins) != null || isComposePopulate(ins)) return true;
        }
        return false;
    }

    /** Whether {@code ins} invokes Compose's node-population method. */
    private static boolean isComposePopulate(Instruction ins) {
        if (!(ins instanceof ReferenceInstruction ri)) return false;
        if (!(ri.getReference() instanceof MethodReference ref)) return false;
        Opcode op = ins.getOpcode();
        if (op != Opcode.INVOKE_DIRECT && op != Opcode.INVOKE_DIRECT_RANGE
                && op != Opcode.INVOKE_VIRTUAL && op != Opcode.INVOKE_VIRTUAL_RANGE) return false;
        return ref.getName().equals("populateAccessibilityNodeInfoProperties")
                && ref.getDefiningClass().equals(COMPOSE_DELEGATE_DESC)
                && signature(ref).equals(COMPOSE_POPULATE);
    }

    /**
     * {@code invoke-static composeNode(info, node)} over the registers of the
     * population call {@code populate}: its operands are the receiver, the
     * virtual id, the info and the node, so the info and the node are its third
     * and fourth registers (contiguous in the range form).
     */
    private static BuilderInstruction composeCall(Instruction populate) {
        if (populate instanceof RegisterRangeInstruction r) {
            return new BuilderInstruction3rc(Opcode.INVOKE_STATIC_RANGE,
                    r.getStartRegister() + 2, 2, COMPOSE_HELPER);
        }
        FiveRegisterInstruction f = (FiveRegisterInstruction) populate;
        return new BuilderInstruction35c(Opcode.INVOKE_STATIC, 2,
                f.getRegisterE(), f.getRegisterF(), 0, 0, 0, COMPOSE_HELPER);
    }

    /** The method reference of {@code ins} when it invokes one of the stamped setters. */
    private static MethodReference candidateRef(Instruction ins) {
        if (!(ins instanceof ReferenceInstruction ri)) return null;
        if (!(ri.getReference() instanceof MethodReference ref)) return null;
        String name = ref.getName();
        if (!name.equals("setOnClickListener") && !name.equals("setOnLongClickListener")
                && !name.equals("setAccessibilityDelegate")) return null;
        return TARGETS.containsKey(signature(ref)) ? ref : null;
    }

    private static String signature(MethodReference ref) {
        StringBuilder sb = new StringBuilder(ref.getName()).append('(');
        for (CharSequence p : ref.getParameterTypes()) sb.append(p);
        return sb.append(')').append(ref.getReturnType()).toString();
    }

    private boolean isView(String ownerDesc) {
        return ownerIsView.computeIfAbsent(ownerDesc, d -> {
            if (!d.startsWith("L") || !d.endsWith(";")) return false;
            String fqn = d.substring(1, d.length() - 1).replace('/', '.');
            return inheritance.isAssignableFrom(VIEW_FQN, fqn);
        });
    }

    /**
     * Counters of one {@link #weave} call.
     *
     * @param clickSites {@code setOnClickListener} sites rewritten
     * @param longClickSites {@code setOnLongClickListener} sites rewritten
     * @param delegateSites {@code setAccessibilityDelegate} sites rewritten
     * @param composeSites Compose node-population calls followed by the
     *     inserted {@code composeNode} call
     * @param invokeSuperSkipped candidate sites left alone because they are
     *     {@code invoke-super}
     * @param ownerNotView candidate sites left alone because their owner is not
     *     a {@code View} subtype the hierarchy resolves
     */
    public record StampReport(int clickSites, int longClickSites, int delegateSites,
                              int composeSites, int invokeSuperSkipped, int ownerNotView) {}
}
