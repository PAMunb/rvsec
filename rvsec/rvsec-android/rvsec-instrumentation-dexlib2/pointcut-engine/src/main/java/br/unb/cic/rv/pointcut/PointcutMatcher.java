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
 *   <li>{@link ArgsPC} and the binding form of {@link TargetPC} ({@code target(o)})
 *       are inert collectors on an established call-site match — they never fail a
 *       match in isolation. The type form of {@link TargetPC} ({@code target(Cipher)})
 *       constrains the call receiver's declared type via {@link InheritanceResolver}
 *       (§4.TT, subtype-aware).</li>
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

    /**
     * §4.D overload: carries the active aspect's pre-expanded {@code baseAspectExclusions} and name
     * so {@code matchNamedRef} can resolve {@code BaseAspect.notwithin()} when a composed
     * {@code commonPointcut} (§4.D.0) is matched. The weaver supplies these from the
     * {@code AspectDescriptor}.
     */
    public Optional<Match> match(PointcutExpression pe, ClassDef classDef,
                                 Method method, Instruction instruction,
                                 int instructionIndex, int totalInstructions,
                                 List<? extends Instruction> instructions,
                                 List<String> baseAspectExclusions, String aspectName) {
        return matchInternal(pe, new Context(classDef, method, instruction,
                instructionIndex, totalInstructions,
                instructions == null ? Collections.emptyList() : instructions,
                baseAspectExclusions, aspectName));
    }

    // --- internal ------------------------------------------------------------

    private Optional<Match> matchInternal(PointcutExpression pe, Context ctx) {
        if (pe instanceof CombinedPC) {
            return matchCombined((CombinedPC) pe, ctx);
        }
        if (pe instanceof NotWithinPC) {
            return matchNotWithin((NotWithinPC) pe, ctx);
        }
        if (pe instanceof NegationPC) {
            return matchNegation((NegationPC) pe, ctx);
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
            return matchArgs((ArgsPC) pe, ctx);
        }
        if (pe instanceof TargetPC) {
            return matchTarget((TargetPC) pe, ctx);
        }
        if (pe instanceof NamedRefPC) {
            return matchNamedRef((NamedRefPC) pe, ctx);
        }
        if (pe instanceof IfPC || pe instanceof WithinPC) {
            // Treated as always-match at this layer; the weaver decides filtering
            // for WithinPC (rarely emitted in the rv-monitor corpus).
            return Optional.of(Match.empty(pe));
        }
        return Optional.empty();
    }

    /**
     * §4.D: resolve a {@link NamedRefPC}. {@code BaseAspect.notwithin()} expands against the
     * descriptor's {@code baseAspectExclusions} (via {@link BaseAspectExpander}); an empty list
     * fails closed ({@link LegacyDescriptorException}). The {@code adviceexecution()} family is
     * vacuously true (deferred.md Entry C — advice-body executions are not separate join points in
     * the dexlib2 inline-call model). Any other name fails closed
     * ({@link UnresolvedNamedRefException}, G-decision) rather than silently matching everything.
     */
    private Optional<Match> matchNamedRef(NamedRefPC nr, Context ctx) {
        String name = nr.name();
        if ("BaseAspect.notwithin()".equals(name)) {
            if (ctx.baseAspectExclusions.isEmpty()) {
                throw new LegacyDescriptorException(ctx.aspectName);
            }
            return matchInternal(BaseAspectExpander.expand(ctx.baseAspectExclusions), ctx);
        }
        if (name.contains("adviceexecution")) {
            return Optional.of(Match.empty(nr));
        }
        throw new UnresolvedNamedRefException(ctx.aspectName, name);
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

    /**
     * §4.N: {@code !target(Type)} / {@code !args(Type)}. Evaluate the inner
     * {@link TargetPC} / {@link ArgsPC} and invert: a present inner verdict
     * (the type matched) yields no match; an empty inner verdict (the type did
     * not match, or the join point is a static invoke / non-{@code MethodReference})
     * yields a match. A negation carries no bindings — the same shape as
     * {@link #matchNotWithin}.
     */
    private Optional<Match> matchNegation(NegationPC neg, Context ctx) {
        Optional<Match> inner = matchInternal(neg.inner(), ctx);
        if (inner.isPresent()) {
            return Optional.empty();
        }
        return Optional.of(Match.empty(neg));
    }

    /**
     * §4.TT: {@code target(...)} has two forms.
     *
     * <p>The binding form ({@code target(o)}, {@code type == null}) is inert — the
     * receiver is bound to the advice parameter at injection time, never filtered
     * here; it stays an always-match collector exactly like {@link ArgsPC}.
     *
     * <p>The type form ({@code target(Cipher)} / {@code target(Cipher+)}) constrains
     * the call receiver. In the dexlib2 inline-call model the receiver's declared
     * type is the invoke's owner ({@code MethodReference.getDefiningClass()} of the
     * current instruction). We match iff the pattern type is assignable from that
     * declared owner (declared-type, subtype-aware per the V-decision — not a runtime
     * {@code instanceof}). A trailing {@code +} is accepted but redundant: subtype
     * checking is unconditional. FQN conversion mirrors the §4.O owner-subtype path
     * ({@code fromDescriptor(toDescriptor(x))}, since {@code resolveFqn} mangles
     * already-qualified names). A static invoke (or any non-{@code ReferenceInstruction})
     * has no receiver, so a {@code target(Type)} cannot match it.
     */
    private Optional<Match> matchTarget(TargetPC tp, Context ctx) {
        if (tp.type() == null) {
            return Optional.of(Match.empty(tp));
        }
        if (!(ctx.instruction instanceof ReferenceInstruction)) {
            return Optional.empty();
        }
        ReferenceInstruction ri = (ReferenceInstruction) ctx.instruction;
        if (!(ri.getReference() instanceof MethodReference)) return Optional.empty();
        if (isStaticInvocation(ctx.instruction)) {
            return Optional.empty();
        }
        MethodReference mr = (MethodReference) ri.getReference();

        String patternType = tp.type();
        if (patternType.endsWith("+")) {
            patternType = patternType.substring(0, patternType.length() - 1);
        }
        // Derive the expected FQN through the descriptor (toDescriptor handles both
        // qualified types like "javax.crypto.Cipher" AND simple names via imports).
        String expectedFqn = fromDescriptor(typeResolver.toDescriptor(patternType));
        String receiverFqn = fromDescriptor(mr.getDefiningClass());
        if (inheritance.isAssignableFrom(expectedFqn, receiverFqn)) {
            return Optional.of(Match.empty(tp));
        }
        return Optional.empty();
    }

    /**
     * §4.AT: {@code args(...)} is the argument-list analogue of {@code target(...)}.
     *
     * <p>The binding/wildcard form ({@code args(o)}, {@code args(*, enc)},
     * {@code args(key, ..)} — no concrete Type at any position) is inert: arguments
     * are bound to advice parameters at injection time, never filtered here. It stays
     * an always-match collector exactly like the legacy behaviour.
     *
     * <p>The type form ({@code args(String)}, {@code args(CharSequence)} — at least
     * one position is a concrete Type) constrains the matched call's actual argument
     * descriptors POSITIONALLY. We walk the {@code MethodReference} parameter types
     * (declared types, subtype-aware per the V-decision — NOT a runtime
     * {@code instanceof}). A {@code null} position (binding name) or {@code "*"}
     * accepts any single argument; a trailing {@code ".."} accepts any remaining
     * arguments. Without a trailing {@code ".."} the actual arity must equal the
     * positional count; with it the arity must be at least the head count. FQN
     * conversion mirrors §4.TT/§4.O ({@code fromDescriptor(toDescriptor(x))}, since
     * {@code resolveFqn} mangles already-qualified names). A non-{@code MethodReference}
     * invoke cannot have argument types, so a type-form {@code args(...)} cannot match.
     */
    private Optional<Match> matchArgs(ArgsPC ap, Context ctx) {
        if (!ap.hasTypeConstraint()) {
            return Optional.of(Match.empty(ap));
        }
        if (!(ctx.instruction instanceof ReferenceInstruction)) {
            return Optional.empty();
        }
        ReferenceInstruction ri = (ReferenceInstruction) ctx.instruction;
        if (!(ri.getReference() instanceof MethodReference)) return Optional.empty();
        MethodReference mr = (MethodReference) ri.getReference();

        List<String> positions = ap.types();
        boolean trailingRest = !positions.isEmpty()
                && "..".equals(positions.get(positions.size() - 1));
        int headCount = trailingRest ? positions.size() - 1 : positions.size();

        List<? extends CharSequence> actualArgs = mr.getParameterTypes();
        if (trailingRest ? actualArgs.size() < headCount
                         : actualArgs.size() != headCount) {
            return Optional.empty();
        }
        for (int i = 0; i < headCount; i++) {
            String expected = positions.get(i);
            // A binding-name position (null) or "*" accepts any single argument.
            if (expected == null || "*".equals(expected)) {
                continue;
            }
            String patternType = expected;
            if (patternType.endsWith("+")) {
                patternType = patternType.substring(0, patternType.length() - 1);
            }
            String expectedFqn = fromDescriptor(typeResolver.toDescriptor(patternType));
            String actualFqn = fromDescriptor(actualArgs.get(i).toString());
            if (!inheritance.isAssignableFrom(expectedFqn, actualFqn)) {
                return Optional.empty();
            }
        }
        return Optional.of(Match.empty(ap));
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
        // §4.O: T+ in owner position — when the source spelled the owner as `T+`, the trailing
        // `+` is retained in declaringType() (unlike ParamSpec, where it is stripped to a flag).
        // Match the declared owner OR any subtype via InheritanceResolver (FQN form, mirroring the
        // param-position subtype path below). The exact-equals path is preserved for non-`+` owners.
        String ownerType = cp.declaringType();
        boolean ownerSubtype = ownerType != null && ownerType.endsWith("+");
        if (ownerSubtype) {
            ownerType = ownerType.substring(0, ownerType.length() - 1);
        }
        String expectedOwner = typeResolver.toDescriptor(ownerType);
        String actualOwner = mr.getDefiningClass();
        boolean ownerOk;
        if (ownerSubtype) {
            // Derive the FQN from the descriptor (toDescriptor handles both qualified owners
            // like "javax.crypto.Cipher" AND simple names resolved via imports); resolveFqn is
            // for simple names only and would mangle an already-qualified owner.
            String expectedFqn = fromDescriptor(expectedOwner);
            String actualFqn = fromDescriptor(actualOwner);
            ownerOk = inheritance.isAssignableFrom(expectedFqn, actualFqn)
                    || cpsAwareOwnerMatch(expectedOwner, ctx);
        } else {
            ownerOk = expectedOwner.equals(actualOwner) || cpsAwareOwnerMatch(expectedOwner, ctx);
        }
        if (!ownerOk) {
            return Optional.empty();
        }

        // Method name (§4.X: a trailing `*` is a prefix glob — `add*` matches add/addAll/addLast).
        String expectedName = cp.isConstructor() ? "<init>" : cp.methodName();
        if (!nameMatches(expectedName, mr.getName())) return Optional.empty();

        // Return type (non-constructor). §4.RW: a `*` return-type pattern (the
        // dominant generic-corpus form `call(* Owner.name(..))`) matches ANY
        // return descriptor — symmetric to the `*` handling already in place for
        // args positions (matchArgs `"*".equals(expected)`) and method names
        // (nameMatches trailing `*`). Without this skip, toDescriptor("*") falls
        // through to the last-resort `Ljava/lang/*;`, which never equals a real
        // return descriptor, so every `call(* ...)` site silently fails to match.
        // The exact-equality gate is preserved for concrete return types.
        if (!cp.isConstructor() && !"*".equals(cp.returnType().trim())) {
            String expectedReturn = typeResolver.toDescriptor(cp.returnType());
            if (!expectedReturn.equals(mr.getReturnType())) return Optional.empty();
        }

        // Parameter types. paramSpecs() is the fixed positional head; varargs()
        // marks a trailing `..` (§4.V). Exact lists require the actual arity to
        // equal the head; trailing varargs require it to be at least the head
        // size — standalone `(..)` has an empty head (match-anything) while
        // `(String, ..)` pins the head and accepts any tail.
        List<? extends CharSequence> actualParams = mr.getParameterTypes();
        int headSize = cp.paramSpecs().size();
        if (cp.varargs() ? actualParams.size() < headSize
                         : actualParams.size() != headSize) {
            return Optional.empty();
        }
        for (int i = 0; i < headSize; i++) {
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

    /**
     * §4.X: method-name match. A trailing {@code *} in the pointcut's method name is a prefix glob
     * ({@code add*} matches {@code add}/{@code addAll}/{@code addLast} but not {@code remove});
     * otherwise the names must be equal.
     */
    private static boolean nameMatches(String expectedName, String actualName) {
        if (expectedName.endsWith("*")) {
            return actualName.startsWith(expectedName.substring(0, expectedName.length() - 1));
        }
        return expectedName.equals(actualName);
    }

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
        // §4.D: the active aspect's pre-expanded BaseAspect exclusions + name, read by
        // matchNamedRef to resolve BaseAspect.notwithin(). Empty list + null name for callers
        // that do not compose a commonPointcut (the legacy 7-arg match path / unit fixtures).
        final List<String> baseAspectExclusions;
        final String aspectName;

        Context(ClassDef classDef, Method method, Instruction instruction,
                int instructionIndex, int totalInstructions,
                List<? extends Instruction> instructions) {
            this(classDef, method, instruction, instructionIndex, totalInstructions,
                    instructions, Collections.emptyList(), null);
        }

        Context(ClassDef classDef, Method method, Instruction instruction,
                int instructionIndex, int totalInstructions,
                List<? extends Instruction> instructions,
                List<String> baseAspectExclusions, String aspectName) {
            this.classDef = classDef;
            this.method = method;
            this.instruction = instruction;
            this.instructionIndex = instructionIndex;
            this.totalInstructions = totalInstructions;
            this.instructions = instructions;
            this.baseAspectExclusions = baseAspectExclusions == null
                    ? Collections.emptyList() : baseAspectExclusions;
            this.aspectName = aspectName;
        }
    }
}
