package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.OneRegisterInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction3rc;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;

import java.util.Collections;
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
 * <p>CPS-aware pass (INV-INS-61): when {@link CpsDetector#isStateMachine(ClassDef)}
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
     *
     * <p>The {@code instructions} parameter is the surrounding instruction
     * list of the current method; {@code buildCallMatch} reads it to peek
     * {@code instructions[invokeIndex + 1]} for a trailing {@code move-result*}
     * (synthetic {@code $return} binding, INV-INS-72). The list is typed as
     * {@code List<? extends Instruction>} to accept both the immutable read
     * side of {@code Method.getImplementation().getInstructions()} and the
     * in-flight builder side without coupling {@code pointcut-engine} to the
     * {@code dexlib2-builder} module.
     */
    public Optional<Match> match(PointcutExpression pe, ClassDef classDef,
                                 Method method, Instruction instruction,
                                 int instructionIndex, int totalInstructions,
                                 List<? extends Instruction> instructions) {
        return matchInternal(pe, new Context(classDef, method, instruction,
                instructionIndex, totalInstructions,
                instructions == null ? Collections.emptyList() : instructions));
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
            if (actualParams.size() != cp.paramSpecs().size()) return Optional.empty();
            for (int i = 0; i < actualParams.size(); i++) {
                CallPC.ParamSpec spec = cp.paramSpecs().get(i);
                CharSequence actual = actualParams.get(i);
                boolean ok;
                if (spec.isSubtype()) {
                    // InheritanceResolver.isAssignableFrom takes FQNs (e.g.
                    // "java.lang.Object", "java.security.Provider"), not DEX
                    // descriptors, because of the fast-path for
                    // superFqn == "java.lang.Object" at
                    // InheritanceResolver.java:66 which returns
                    // !isPrimitive(subFqn) (FQN form). Convert both sides.
                    String expectedFqn = typeResolver.resolveFqn(spec.descriptor());
                    String actualFqn = fromDescriptor(actual.toString());
                    ok = inheritance.isAssignableFrom(expectedFqn, actualFqn);
                } else {
                    String expectedDesc = typeResolver.toDescriptor(spec.descriptor());
                    ok = expectedDesc.contentEquals(actual);
                }
                if (!ok) return Optional.empty();
            }
        }

        // Register operands of the invoke; positions depend on static-ness and
        // constructor-ness of the resolved MethodReference. The advice-emitter
        // consumes these to satisfy args()/target() bindings at injection time
        // (task 4.x).
        int[] regs = extractInvokeRegisters(ctx.instruction);
        boolean isStaticInvoke = isStaticInvocation(ctx.instruction);
        return Optional.of(buildCallMatch(cp, mr, regs, isStaticInvoke,
                ctx.instructions, ctx.instructionIndex));
    }

    // Package-private to allow direct unit testing (see
    // PointcutMatcherConstructorTest). The full match() flow remains the
    // public API; this method is the canonical seat of the gh56 fix and
    // is exercised in isolation.
    static Match buildCallMatch(CallPC cp, MethodReference mr, int[] regs,
                                          boolean isStaticInvoke,
                                          List<? extends Instruction> instructions,
                                          int invokeIndex) {
        // Static-ness comes from the actual invoke opcode, not the AspectJ
        // modifier (which is stripped at parse time). For invoke-static* the
        // first register operand is the first arg; for invoke-virtual /
        // -direct / -super / -interface the first register is the receiver
        // and args start at offset 1.
        //
        // Constructors (invoke-direct to <init>) place the freshly-allocated
        // instance in regs[0] — same shape as a virtual instance invoke. The
        // previous implementation treated constructors as static (offset 0),
        // shifting every argument binding by one register and losing the
        // receiver. The fix collapses the predicate to isStaticInvoke alone.
        int baseOffset = isStaticInvoke ? 0 : 1;
        int targetRegister = isStaticInvoke
                ? -1
                : (regs.length > 0 ? regs[0] : -1);
        // Two-predicate constructor gate (D3, defence in depth): the descriptor
        // predicate (cp.isConstructor()) AND the method-name predicate
        // (mr.getName().equals("<init>")) must agree. invoke-direct is also
        // used for private non-constructor methods and super-<init> chaining
        // outside the advice contract — relying on either predicate alone
        // would capture an unintended receiver.
        boolean isConstructor = cp.isConstructor()
                && "<init>".equals(mr.getName());
        Map<String, Integer> paramRegs = new LinkedHashMap<>();
        // Wide-slot accounting (gh59): `long` and `double` occupy two
        // consecutive register slots in the DEX invoke operand list, while
        // all other types (refs, int, float, boolean, byte, short, char)
        // occupy one. Iterating with a naive `regs[baseOffset + i]` would
        // map every arg after the first wide to the wide's high half (typed
        // `Long (Low/High Half)` by the verifier) or to a downstream slot
        // belonging to the next parameter — producing VerifyError at install
        // time on the affected `<init>` body. We read widths from the
        // MethodReference param descriptors (JVM form, e.g. "J"/"D") because
        // that's the authoritative shape of the actual DEX invoke.
        List<? extends CharSequence> paramDescriptors = mr.getParameterTypes();
        int regOffset = baseOffset;
        for (int i = 0; i < paramDescriptors.size(); i++) {
            if (regOffset >= regs.length) break;
            // Positional key — advice-emitter joins this with args(...) names
            // when a sibling ArgsPC is present. Using zero-padded positional
            // keys keeps iteration order stable.
            paramRegs.put(String.format("arg%02d", i), regs[regOffset]);
            CharSequence pt = paramDescriptors.get(i);
            boolean wide = pt.length() == 1
                    && (pt.charAt(0) == 'J' || pt.charAt(0) == 'D');
            regOffset += wide ? 2 : 1;
        }
        // Synthetic "$return" binding (INV-INS-72): for non-constructor
        // invokes, peek the next instruction; if it's move-result* the
        // destination register is recorded so MonitorInvokeBuilder can
        // resolve returning(name) without falling back to literal 0. Skipped
        // for constructors (no move-result* after <init>) — constructor
        // advice consumes targetRegister directly through resolveReturningRegister.
        if (!isConstructor && invokeIndex + 1 < instructions.size()) {
            Instruction next = instructions.get(invokeIndex + 1);
            Opcode op = next.getOpcode();
            if ((op == Opcode.MOVE_RESULT
                    || op == Opcode.MOVE_RESULT_OBJECT
                    || op == Opcode.MOVE_RESULT_WIDE)
                    && next instanceof OneRegisterInstruction) {
                int dest = ((OneRegisterInstruction) next).getRegisterA();
                // For MOVE_RESULT_WIDE the destination occupies the pair
                // (vN, vN+1); the synthetic key stores the low register vN.
                // Wide-pair contiguity is the caller's responsibility
                // (RegisterShifter INV-INS-26 guarantees it for emitted code).
                paramRegs.put("$return", dest);
            }
        }
        return new Match(paramRegs, targetRegister, cp, isConstructor);
    }

    /**
     * Returns whether the matched invoke instruction is one of the static-
     * invocation opcodes ({@code invoke-static} / {@code invoke-static/range}).
     * For static invokes the register operand list is the argument list with
     * no implicit receiver; for non-static invokes the first register is the
     * receiver. This determines the `argBindings` offset in
     * {@link #buildCallMatch}, which had previously defaulted to assuming a
     * receiver and was silently mis-binding `args()` for static calls
     * (cryptoapp `String.valueOf(Object)` regression — INV-INS-65).
     */
    private static boolean isStaticInvocation(
            com.android.tools.smali.dexlib2.iface.instruction.Instruction instr) {
        if (instr == null) return false;
        switch (instr.getOpcode()) {
            case INVOKE_STATIC:
            case INVOKE_STATIC_RANGE:
                return true;
            default:
                return false;
        }
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

    /**
     * Convert a DEX type descriptor ({@code "Lcom/example/Foo;"}, {@code "I"},
     * {@code "J"}, …) to a Java FQN form ({@code "com.example.Foo"},
     * {@code "int"}, {@code "long"}). Single-letter primitive descriptors are
     * mapped to their FQN spellings because {@code InheritanceResolver.isPrimitive}
     * matches on the FQN form — without this conversion,
     * {@code isAssignableFrom("java.lang.Object", "I")} would hit the
     * {@code Object} fast-path with {@code !isPrimitive("I") = true} and
     * erroneously accept primitives under {@code Object+}. Array descriptors
     * ({@code "[I"}, {@code "[Ljava/lang/String;"}) are out of scope for gh61
     * — no JCA {@code .mop} uses {@code Array+} as a subtype marker.
     */
    private static String fromDescriptor(String desc) {
        if (desc == null) return "";
        if (desc.startsWith("L") && desc.endsWith(";")) {
            return desc.substring(1, desc.length() - 1).replace('/', '.');
        }
        if (desc.length() == 1) {
            switch (desc.charAt(0)) {
                case 'V': return "void";
                case 'Z': return "boolean";
                case 'B': return "byte";
                case 'S': return "short";
                case 'C': return "char";
                case 'I': return "int";
                case 'J': return "long";
                case 'F': return "float";
                case 'D': return "double";
                default:  break;
            }
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
        // Constructor classification under AND: today only one side of a CombinedPC
        // produces a constructor classification (the CallPC side; ArgsPC, TargetPC,
        // ExecutionPC, StaticInitPC, NotWithinPC, etc. all return Match.empty(pe)
        // with isConstructor=false). OR-merging is therefore equivalent to "the
        // side that knows the invoke kind wins". If a future combinator ever
        // produces a Match with mixed kind agreement on both sides, this collapses
        // to constructor semantics — re-evaluate then.
        boolean isConstructor = left.isConstructor || right.isConstructor;
        return new Match(args, target, pe, isConstructor);
    }

    // --- context + Match helpers --------------------------------------------

    private static final class Context {
        final ClassDef classDef;
        final Method method;
        final Instruction instruction;
        final int instructionIndex;
        final int totalInstructions;
        final List<? extends Instruction> instructions;

        Context(ClassDef classDef, Method method, Instruction instruction,
                int instructionIndex, int totalInstructions,
                List<? extends Instruction> instructions) {
            this.classDef = classDef;
            this.method = method;
            this.instruction = instruction;
            this.instructionIndex = instructionIndex;
            this.totalInstructions = totalInstructions;
            this.instructions = instructions;
        }
    }
}
