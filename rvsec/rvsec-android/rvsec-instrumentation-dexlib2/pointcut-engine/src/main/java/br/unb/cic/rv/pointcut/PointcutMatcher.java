package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction3rc;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/**
 * Matches a {@link PointcutExpression} AST against a DEX
 * (class, method, instruction) tuple and extracts argument/target bindings.
 *
 * <p>Scope of this class (task 3.6):
 * <ul>
 *   <li>Matches {@link CallPC} against {@code invoke-*} instructions by resolving
 *       the call target signature through {@link TypeResolver}.</li>
 *   <li>Matches {@link ExecutionPC} at method entry (first instruction only) —
 *       used by the {@code coverage-weaver} catch-all.</li>
 *   <li>Matches {@link StaticInitPC} against {@code <clinit>} methods when the
 *       class matches the pattern via {@link InheritanceResolver} (supports
 *       {@code T+} semantics).</li>
 *   <li>{@link CombinedPC} implements logical {@code AND} / {@code OR} with
 *       merged bindings.</li>
 *   <li>{@link ArgsPC} / {@link TargetPC} are handled as binding collectors on
 *       an established call-site match — they never fail a match in isolation.</li>
 *   <li>{@link NotWithinPC} filters by class type pattern (prefix match on
 *       {@code com.foo..*}; literal match otherwise).</li>
 *   <li>{@link IfPC} and {@link NamedRefPC} are treated as match-true; the weaver
 *       emits guards ({@code IfGuardEmitter}) or ignores named refs at injection
 *       time.</li>
 * </ul>
 *
 * <p>CPS-aware pass (INV-INS-24): when {@link CpsDetector#isStateMachine(ClassDef)}
 * returns true and the current method is {@code invokeSuspend}, the matcher
 * accepts calls that would normally be matched against the user-facing suspend
 * fun — it unwraps the enclosing state-machine class to the owner reported by
 * {@code @DebugMetadata} (when present) so naming-based matchers see the right
 * owner. Patterns the detector cannot lower surface no match (weaver records
 * the miss and LIMITATIONS.md documents unsupported suspend shapes).
 */
public final class PointcutMatcher {

    private final TypeResolver typeResolver;
    private final InheritanceResolver inheritance;

    public PointcutMatcher(TypeResolver typeResolver, InheritanceResolver inheritance) {
        this.typeResolver = Objects.requireNonNull(typeResolver);
        this.inheritance = Objects.requireNonNull(inheritance);
    }

    /**
     * @return a {@link Match} when the pointcut matches the tuple (with any
     *         bindings inferred), {@code Optional.empty()} otherwise.
     */
    public Optional<Match> match(PointcutExpression pe, ClassDef classDef,
                                 Method method, Instruction instruction,
                                 int instructionIndex, int totalInstructions) {
        return matchInternal(pe, new Context(classDef, method, instruction,
                instructionIndex, totalInstructions));
    }

    // --- internal ------------------------------------------------------------

    private Optional<Match> matchInternal(PointcutExpression pe, Context ctx) {
        if (pe instanceof CombinedPC) {
            return matchCombined((CombinedPC) pe, ctx);
        }
        if (pe instanceof NotWithinPC) {
            return matchNotWithin((NotWithinPC) pe, ctx);
        }
        if (pe instanceof CallPC) {
            return matchCall((CallPC) pe, ctx);
        }
        if (pe instanceof ExecutionPC) {
            return matchExecution((ExecutionPC) pe, ctx);
        }
        if (pe instanceof StaticInitPC) {
            return matchStaticInit((StaticInitPC) pe, ctx);
        }
        if (pe instanceof ArgsPC) {
            // Standalone args() is inert — binding happens on a CallPC match.
            return Optional.of(Match.empty(pe));
        }
        if (pe instanceof TargetPC) {
            return Optional.of(Match.empty(pe));
        }
        if (pe instanceof IfPC || pe instanceof NamedRefPC || pe instanceof WithinPC) {
            // Treated as always-match at this layer; the weaver decides filtering
            // for WithinPC (rarely emitted in the rv-monitor corpus).
            return Optional.of(Match.empty(pe));
        }
        return Optional.empty();
    }

    private Optional<Match> matchCombined(CombinedPC c, Context ctx) {
        if (c.op() == CombinedPC.Op.AND) {
            Optional<Match> left = matchInternal(c.left(), ctx);
            if (left.isEmpty()) return Optional.empty();
            Optional<Match> right = matchInternal(c.right(), ctx);
            if (right.isEmpty()) return Optional.empty();
            return Optional.of(mergeBindings(left.get(), right.get(), c));
        }
        // OR: first side that succeeds wins.
        Optional<Match> left = matchInternal(c.left(), ctx);
        if (left.isPresent()) return left;
        return matchInternal(c.right(), ctx);
    }

    private Optional<Match> matchNotWithin(NotWithinPC nw, Context ctx) {
        String classFqn = fromDescriptor(ctx.classDef.getType());
        if (matchesTypePattern(classFqn, nw.typePattern())) {
            return Optional.empty();
        }
        return Optional.of(Match.empty(nw));
    }

    private Optional<Match> matchCall(CallPC cp, Context ctx) {
        if (!(ctx.instruction instanceof ReferenceInstruction)) {
            return Optional.empty();
        }
        ReferenceInstruction ri = (ReferenceInstruction) ctx.instruction;
        if (!(ri.getReference() instanceof MethodReference)) return Optional.empty();
        MethodReference mr = (MethodReference) ri.getReference();

        // Owner resolution — exact owner match, with a CPS-aware fallback: if
        // the enclosing class is a Kotlin state machine and we are inside
        // invokeSuspend, also accept the match when the owner declared by
        // @DebugMetadata("c") equals the pointcut's declaring type (the source
        // suspend fun's owner, before the compiler lifted it into the
        // continuation class).
        String expectedOwner = typeResolver.toDescriptor(cp.declaringType());
        String actualOwner = mr.getDefiningClass();
        if (!expectedOwner.equals(actualOwner)
                && !cpsAwareOwnerMatch(expectedOwner, ctx)) {
            return Optional.empty();
        }

        // Method name
        String expectedName = cp.isConstructor() ? "<init>" : cp.methodName();
        if (!expectedName.equals(mr.getName())) return Optional.empty();

        // Return type (non-constructor)
        if (!cp.isConstructor()) {
            String expectedReturn = typeResolver.toDescriptor(cp.returnType());
            if (!expectedReturn.equals(mr.getReturnType())) return Optional.empty();
        }

        // Parameter types — varargs short-circuits
        List<? extends CharSequence> actualParams = mr.getParameterTypes();
        if (!cp.varargs()) {
            if (actualParams.size() != cp.paramTypes().size()) return Optional.empty();
            for (int i = 0; i < actualParams.size(); i++) {
                String expected = typeResolver.toDescriptor(cp.paramTypes().get(i));
                if (!expected.contentEquals(actualParams.get(i))) return Optional.empty();
            }
        }

        // Register operands of the invoke; positions depend on static-ness and
        // constructor-ness of the resolved MethodReference. The advice-emitter
        // consumes these to satisfy args()/target() bindings at injection time
        // (task 4.x).
        int[] regs = extractInvokeRegisters(ctx.instruction);
        return Optional.of(buildCallMatch(cp, mr, regs));
    }

    private static Match buildCallMatch(CallPC cp, MethodReference mr, int[] regs) {
        boolean isStatic = cp.isConstructor() ? false : isLikelyStatic(cp);
        int baseOffset = (cp.isConstructor() || isStatic) ? 0 : 1;
        int targetRegister = cp.isConstructor() || isStatic ? -1
                : (regs.length > 0 ? regs[0] : -1);
        Map<String, Integer> paramRegs = new LinkedHashMap<>();
        List<String> paramTypes = cp.paramTypes();
        for (int i = 0; i < paramTypes.size() && baseOffset + i < regs.length; i++) {
            // Positional key — advice-emitter joins this with args(...) names
            // when a sibling ArgsPC is present. Using zero-padded positional
            // keys keeps iteration order stable.
            paramRegs.put(String.format("arg%02d", i), regs[baseOffset + i]);
        }
        return new Match(paramRegs, targetRegister, cp);
    }

    /**
     * The AspectJ modifier prefix (public/static/...) was stripped at parse
     * time, so the AST alone cannot tell us whether a call is static. The
     * advice-emitter reconciles static-ness from the matched
     * {@code MethodReference}'s {@code ACC_STATIC} flag at injection time —
     * here we conservatively return {@code false} and let the emitter shift
     * registers when needed. The register mapping is always recomputed
     * downstream, so this heuristic never silently misplaces a binding.
     */
    private static boolean isLikelyStatic(CallPC cp) {
        return false;
    }

    private Optional<Match> matchExecution(ExecutionPC ex, Context ctx) {
        // execution(..) is matched at method entry in our corpus; the pattern
        // is opaque here — the coverage-weaver applies the same expression
        // semantics via its own filter pipeline.
        if (ctx.instructionIndex != 0) return Optional.empty();
        return Optional.of(Match.empty(ex));
    }

    private Optional<Match> matchStaticInit(StaticInitPC si, Context ctx) {
        if (!"<clinit>".equals(ctx.method.getName())) return Optional.empty();
        if (ctx.instructionIndex != 0) return Optional.empty();
        String classFqn = fromDescriptor(ctx.classDef.getType());
        String pattern = si.typePattern();
        if (pattern.endsWith("+")) {
            String parent = pattern.substring(0, pattern.length() - 1);
            if (!inheritance.isAssignableFrom(parent, classFqn)) return Optional.empty();
        } else {
            if (!matchesTypePattern(classFqn, pattern)) return Optional.empty();
        }
        return Optional.of(Match.empty(si));
    }

    // --- helpers -------------------------------------------------------------

    private boolean cpsAwareOwnerMatch(String expectedOwner, Context ctx) {
        if (!CpsDetector.isStateMachine(ctx.classDef)) return false;
        if (!CpsDetector.isInvokeSuspend(ctx.method)) return false;
        String dmOwner = CpsDetector.debugMetadataOwner(ctx.classDef);
        if (dmOwner == null) return false;
        // DebugMetadata.c is a source FQN like "com.example.Foo"; expectedOwner
        // is a DEX descriptor. Convert.
        String asDescriptor = "L" + dmOwner.replace('.', '/') + ";";
        return expectedOwner.equals(asDescriptor);
    }

    /** Pattern match for {@code com.foo..*} / {@code com.foo..Bar+} / exact. */
    static boolean matchesTypePattern(String classFqn, String pattern) {
        if (pattern == null || pattern.isEmpty()) return false;
        String p = pattern.trim();
        if (p.endsWith("+")) p = p.substring(0, p.length() - 1);
        // Package wildcard: "com.foo..*" matches anything under com.foo.
        if (p.endsWith("..*")) {
            String prefix = p.substring(0, p.length() - "..*".length());
            return classFqn.equals(prefix) || classFqn.startsWith(prefix + ".");
        }
        if (p.endsWith(".*")) {
            String prefix = p.substring(0, p.length() - ".*".length());
            if (!classFqn.startsWith(prefix + ".")) return false;
            return classFqn.indexOf('.', prefix.length() + 1) < 0;
        }
        return classFqn.equals(p);
    }

    private static int[] extractInvokeRegisters(Instruction inst) {
        if (inst instanceof Instruction35c) {
            Instruction35c i = (Instruction35c) inst;
            int count = i.getRegisterCount();
            int[] regs = new int[count];
            if (count > 0) regs[0] = i.getRegisterC();
            if (count > 1) regs[1] = i.getRegisterD();
            if (count > 2) regs[2] = i.getRegisterE();
            if (count > 3) regs[3] = i.getRegisterF();
            if (count > 4) regs[4] = i.getRegisterG();
            return regs;
        }
        if (inst instanceof Instruction3rc) {
            Instruction3rc i = (Instruction3rc) inst;
            int count = i.getRegisterCount();
            int start = i.getStartRegister();
            int[] regs = new int[count];
            for (int k = 0; k < count; k++) regs[k] = start + k;
            return regs;
        }
        return new int[0];
    }

    /** Convert a DEX type descriptor ({@code "Lcom/example/Foo;"}) to a Java FQN. */
    private static String fromDescriptor(String desc) {
        if (desc == null) return "";
        if (desc.startsWith("L") && desc.endsWith(";")) {
            return desc.substring(1, desc.length() - 1).replace('/', '.');
        }
        return desc;
    }

    private static Map<String, Integer> emptyMap() {
        return new LinkedHashMap<>();
    }

    private static Match mergeBindings(Match left, Match right, PointcutExpression pe) {
        Map<String, Integer> args = new LinkedHashMap<>(left.argBindings);
        args.putAll(right.argBindings);
        int target = left.targetRegister >= 0 ? left.targetRegister : right.targetRegister;
        return new Match(args, target, pe);
    }

    // --- context + Match helpers --------------------------------------------

    private static final class Context {
        final ClassDef classDef;
        final Method method;
        final Instruction instruction;
        final int instructionIndex;
        final int totalInstructions;

        Context(ClassDef classDef, Method method, Instruction instruction,
                int instructionIndex, int totalInstructions) {
            this.classDef = classDef;
            this.method = method;
            this.instruction = instruction;
            this.instructionIndex = instructionIndex;
            this.totalInstructions = totalInstructions;
        }
    }
}
