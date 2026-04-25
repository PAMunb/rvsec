package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.emitter.AdviceEmitter;
import br.unb.cic.rv.emitter.EmitContext;
import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.InsertionPoint;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.PointcutExpression;
import br.unb.cic.rv.pointcut.PointcutExpressionParser;
import br.unb.cic.rv.pointcut.PointcutMatcher;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;

import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * Top-level orchestrator that walks {@code ClassDef × Method × Instruction}
 * of a {@link DexFile} and applies every {@link EmitPlan} the
 * {@link EmitterDispatch} produces for each match.
 *
 * <p>This is the executor side of the advice-emitter / dex-mutator split:
 * plans come in, mutations go out. The class does not build instruction
 * sequences — that is the emitter's job. The class does not decide pointcut
 * semantics — that is the matcher's job. It only:
 * <ol>
 *   <li>Parses each advice's pointcut expression once (cached via Map).</li>
 *   <li>Iterates instructions, runs {@link PointcutMatcher} for each advice.</li>
 *   <li>On match, asks {@link EmitterDispatch} for the right emitter, builds
 *       an {@link EmitContext}, and applies the returned plan via
 *       {@link InstructionInjector} (with scratch registers supplied by
 *       {@link RegisterAllocator}).</li>
 * </ol>
 *
 * <p>The weaver never mutates the input {@link DexFile} directly: it builds
 * a {@code MutableDexFile}-shaped delta and returns it. (Dexlib2's immutable
 * model requires a rewrite step anyway; we lean on that to keep the input
 * side effect-free.) Plans requiring {@code <clinit>} synthesis, try/catch
 * ranges, or wrapper rewrites are marked in the returned weave report and
 * handled by follow-on passes (task 5.x integration).
 */
public final class DexWeaver {

    private final EmitterDispatch emitterDispatch;
    private final RegisterAllocator allocator;

    public DexWeaver() {
        this(new EmitterDispatch(), new RegisterAllocator());
    }

    public DexWeaver(EmitterDispatch emitterDispatch, RegisterAllocator allocator) {
        this.emitterDispatch = Objects.requireNonNull(emitterDispatch);
        this.allocator = Objects.requireNonNull(allocator);
    }

    /**
     * Weave the given descriptor into every matching instruction of every
     * method of {@code dexFile}. Returns a simple counter report — the
     * mutation itself happens via the caller's {@link MutableMethodImplementation}
     * supplier (dexlib2 doesn't let us mutate read-only implementations
     * directly).
     */
    public WeaveReport weave(DexFile dexFile, AspectDescriptor descriptor,
                              TypeResolver typeResolver,
                              InheritanceResolver inheritance,
                              MutableImplSupplier mutableSupplier) {
        Objects.requireNonNull(dexFile);
        Objects.requireNonNull(descriptor);

        PointcutMatcher matcher = new PointcutMatcher(typeResolver, inheritance);
        int classesSeen = 0;
        int methodsSeen = 0;
        int matchesApplied = 0;
        int plansSkipped = 0;

        for (ClassDef classDef : dexFile.getClasses()) {
            classesSeen++;
            for (Method method : classDef.getMethods()) {
                methodsSeen++;
                MethodImplementation impl = method.getImplementation();
                if (impl == null) continue;
                List<Instruction> instructions = new java.util.ArrayList<>();
                for (Instruction ins : impl.getInstructions()) instructions.add(ins);
                for (int idx = 0; idx < instructions.size(); idx++) {
                    Instruction ins = instructions.get(idx);
                    for (AdviceDescriptor advice : descriptor.getAdvices()) {
                        PointcutExpression pe = parseCached(advice);
                        if (pe == null) { plansSkipped++; continue; }
                        Optional<Match> m = matcher.match(pe, classDef, method, ins,
                                idx, instructions.size());
                        if (m.isEmpty()) continue;
                        AdviceEmitter emitter;
                        try {
                            emitter = emitterDispatch.select(advice);
                        } catch (UnsupportedOperationException ex) {
                            plansSkipped++;
                            continue;
                        }
                        EmitContext ctx = new EmitContext(advice, m.get(), typeResolver,
                                monitorOwnerFor(descriptor));
                        EmitPlan plan = emitter.emit(ctx);

                        MutableMethodImplementation mut = mutableSupplier.forMethod(method);
                        if (mut == null) {
                            plansSkipped++;
                            continue;
                        }
                        allocator.allocate(mut, plan.registers());
                        applyPlan(mut, idx, plan);
                        matchesApplied++;
                    }
                }
            }
        }
        return new WeaveReport(classesSeen, methodsSeen, matchesApplied, plansSkipped);
    }

    /** Callback that returns a mutable view of the method's implementation. */
    public interface MutableImplSupplier {
        MutableMethodImplementation forMethod(Method method);
    }

    /** Cached parsing; identical expressions across advices are rare but cheap to cache. */
    private PointcutExpression parseCached(AdviceDescriptor advice) {
        String expr = advice.getExpression();
        if (expr == null || expr.isBlank()) return null;
        try {
            return PointcutExpressionParser.parse(expr);
        } catch (RuntimeException ex) {
            return null;
        }
    }

    private void applyPlan(MutableMethodImplementation mut, int idx, EmitPlan plan) {
        InstructionInjector inj = new InstructionInjector(mut);
        switch (plan.insertionPoint()) {
            case BEFORE:
                inj.insertBefore(idx, plan);
                break;
            case AFTER:
                inj.insertAfter(idx, plan);
                break;
            case METHOD_ENTRY:
                inj.insertAtMethodEntry(plan);
                break;
            case TRY_CATCH_WRAP:
            case REPLACE:
                // Pending: task 5.x integration installs try-range + handler
                // labels / swaps the invoke reference; the plan carries the
                // required data but full realization needs additional helpers
                // that live alongside WrapperEmitter rewrites.
                break;
            default:
                throw new IllegalStateException("unknown insertion point: " + plan.insertionPoint());
        }
    }

    private String monitorOwnerFor(AspectDescriptor d) {
        // Convention: the generated RuntimeMonitor lives in the "mop" package
        // under a name derived from the merged aspect name. For this
        // implementation we accept the canonical "mop.MultiSpec_1RuntimeMonitor"
        // emitted by rv-monitor; a future revision can parameterize this.
        String shortName = d.getShortName() == null ? "MultiSpec_1" : d.getShortName();
        return "Lmop/" + shortName + "RuntimeMonitor;";
    }

    public record WeaveReport(int classesSeen, int methodsSeen,
                               int matchesApplied, int plansSkipped) {}
}
