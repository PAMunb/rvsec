import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.DescriptorReader;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.WrapperEmitter;
import br.unb.cic.rv.mutator.DexFileMutator;
import br.unb.cic.rv.mutator.DexWeaver;
import br.unb.cic.rv.mutator.RegisterAllocator;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.*;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableTypeReference;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * Set-phase weave probe (copy of batchD beta_BetaWeaveProbeB.java, class renamed only): drives the PRODUCTION dexlib2 pipeline exactly as
 * BatchRunner.java wires it (DescriptorReader -> TypeResolver(descriptor
 * imports) -> AndroidClassIndex(android-30 jar) -> WrapperEmitter.generate ->
 * DexWeaver(+wrappers) -> expandWrapperReplacementsForApk(InheritanceResolver)
 * -> weave) over a synthetic DEX that contains one call site per scenario.
 * Nothing about matching, wrapper enumeration or substitution is reimplemented.
 *
 * usage: SetExecWeaveProbe &lt;android.jar&gt; &lt;descriptor.json&gt; &lt;scenarios.tsv&gt;
 * scenario row (tab-separated): tag  ownerFqn  method|&lt;init&gt;  paramDescs(comma or -)  retDesc  kind(V|I|D|S)
 */
public class SetExecWeaveProbe {

    private static final String PROBE = "Lcom/example/probe/Probe;";
    private static final String MYKEY = "Lcom/example/probe/MyKey;";

    record Scenario(String tag, String ownerFqn, String name, List<String> params,
                    String ret, char kind) {}

    public static void main(String[] args) throws Exception {
        Path jar = Path.of(args[0]);
        Path descriptorPath = Path.of(args[1]);
        List<Scenario> scenarios = readScenarios(Path.of(args[2]));

        AspectDescriptor descriptor = DescriptorReader.read(descriptorPath);
        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex androidIndex = new AndroidClassIndex(jar);

        Path wrapperOut = Files.createTempDirectory("betawrap");
        List<WrapperEmitter.WrapperEntry> wrappers =
                WrapperEmitter.generate(descriptor, wrapperOut, androidIndex);
        System.out.println("== WrapperEmitter entries (" + wrappers.size() + ") for "
                + descriptorPath.getFileName());
        for (WrapperEmitter.WrapperEntry w : wrappers) {
            System.out.printf("  wrapper %-55s %s.%s(%s)%s static=%s%n", w.wrapperName,
                    w.originalClassFqn, w.originalMethodName,
                    String.join(",", w.originalParamFqn), ":" + w.originalReturnFqn,
                    w.isStatic);
        }

        DexFile dex = buildDex(scenarios);
        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator(), wrappers);
        InheritanceResolver inheritance = new InheritanceResolver(androidIndex, List.of(dex));
        weaver.expandWrapperReplacementsForApk(inheritance);

        DexFileMutator mutator = new DexFileMutator(dex);
        DexWeaver.MutableImplSupplier supplier = new DexWeaver.MutableImplSupplier() {
            @Override public com.android.tools.smali.dexlib2.builder.MutableMethodImplementation
                    forMethod(Method m) { return mutator.forMethod(m); }
            @Override public void replaceImpl(Method m,
                    com.android.tools.smali.dexlib2.builder.MutableMethodImplementation impl) {
                mutator.replaceImpl(m, impl); }
            @Override public void addSynthesizedMethod(String cls, Method m) {
                mutator.addSynthesizedMethod(cls, m); }
        };
        DexWeaver.WeaveReport wr = weaver.weave(dex, descriptor, typeResolver, inheritance, supplier);
        System.out.println("== WeaveReport " + wr);

        DexFile woven = mutator.toDexFile();
        Map<String, List<String>> results = new LinkedHashMap<>();
        for (ClassDef cd : woven.getClasses()) {
            for (Method m : cd.getMethods()) {
                if (!m.getName().startsWith("site_")) continue;
                String tag = m.getName().substring(5);
                MethodImplementation impl = m.getImplementation();
                List<String> hits = new ArrayList<>();
                if (impl != null) {
                    for (Instruction ins : impl.getInstructions()) {
                        if (ins instanceof ReferenceInstruction ri
                                && ri.getReference() instanceof MethodReference mr) {
                            String dc = mr.getDefiningClass();
                            if (dc.startsWith("Lmop/MonitorWrappers")) {
                                hits.add("WRAPPED:" + mr.getName());
                            } else if (dc.endsWith("RuntimeMonitor;")) {
                                hits.add("INLINE:" + mr.getName());
                            }
                        }
                    }
                }
                results.put(tag, hits);
            }
        }
        System.out.println("== Site capture results");
        for (Scenario s : scenarios) {
            List<String> hits = results.getOrDefault(s.tag(), List.of());
            System.out.printf("  %-14s %-42s -> %s%n", s.tag(),
                    s.ownerFqn + "." + s.name + "(" + String.join(",", s.params) + ")",
                    hits.isEmpty() ? "UNTOUCHED" : hits);
        }
    }

    private static List<Scenario> readScenarios(Path p) throws Exception {
        List<Scenario> out = new ArrayList<>();
        for (String line : Files.readAllLines(p)) {
            if (line.isBlank() || line.startsWith("#")) continue;
            String[] f = line.split("\t");
            List<String> params = "-".equals(f[3].trim()) ? List.of()
                    : List.of(f[3].trim().split(","));
            out.add(new Scenario(f[0].trim(), f[1].trim(), f[2].trim(), params,
                    f[4].trim(), f[5].trim().charAt(0)));
        }
        return out;
    }

    private static int width(String desc) {
        return ("J".equals(desc) || "D".equals(desc)) ? 2 : 1;
    }

    private static DexFile buildDex(List<Scenario> scenarios) {
        List<ImmutableMethod> methods = new ArrayList<>();
        for (Scenario s : scenarios) {
            String ownerDesc = "L" + s.ownerFqn().replace('.', '/') + ";";
            ImmutableMethodReference ref = new ImmutableMethodReference(
                    ownerDesc, s.name(), s.params(), s.ret());
            boolean ctor = s.kind() == 'D' && "<init>".equals(s.name());
            boolean isStatic = s.kind() == 'S';
            int argWidth = s.params().stream().mapToInt(SetExecWeaveProbe::width).sum();
            int regs = argWidth + (isStatic ? 0 : 1);
            List<ImmutableInstruction> body = new ArrayList<>();
            if (ctor) {
                body.add(new ImmutableInstruction21c(Opcode.NEW_INSTANCE, 0,
                        new ImmutableTypeReference(ownerDesc)));
            }
            Opcode op = ctor ? Opcode.INVOKE_DIRECT
                    : switch (s.kind()) {
                        case 'I' -> Opcode.INVOKE_INTERFACE;
                        case 'S' -> Opcode.INVOKE_STATIC;
                        default -> Opcode.INVOKE_VIRTUAL;
                    };
            ImmutableInstruction call;
            if (regs <= 5) {
                int[] r = new int[5];
                for (int i = 0; i < regs; i++) r[i] = i;
                call = new ImmutableInstruction35c(op, regs, r[0], r[1], r[2], r[3], r[4], ref);
            } else {
                Opcode opr = switch (op) {
                    case INVOKE_DIRECT -> Opcode.INVOKE_DIRECT_RANGE;
                    case INVOKE_INTERFACE -> Opcode.INVOKE_INTERFACE_RANGE;
                    case INVOKE_STATIC -> Opcode.INVOKE_STATIC_RANGE;
                    default -> Opcode.INVOKE_VIRTUAL_RANGE;
                };
                call = new ImmutableInstruction3rc(opr, 0, regs, ref);
            }
            body.add(call);
            if (!ctor && !"V".equals(s.ret())) {
                Opcode mr = s.ret().startsWith("L") || s.ret().startsWith("[")
                        ? Opcode.MOVE_RESULT_OBJECT
                        : (width(s.ret()) == 2 ? Opcode.MOVE_RESULT_WIDE : Opcode.MOVE_RESULT);
                body.add(new ImmutableInstruction11x(mr, 0));
            }
            body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
            methods.add(new ImmutableMethod(PROBE, "site_" + s.tag(), List.of(), "V",
                    AccessFlags.PUBLIC.getValue(), null, null,
                    new ImmutableMethodImplementation(Math.max(regs + 2, 4), body,
                            List.of(), List.of())));
        }
        ClassDef probe = new ImmutableClassDef(PROBE, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", List.of(), null, null, List.of(), methods);

        // App-internal SecretKey implementor: declares getEncoded()/destroy() so
        // call sites with the subtype as static receiver exist in a realistic APK.
        List<ImmutableMethod> myKeyMethods = new ArrayList<>();
        for (String[] mm : new String[][]{{"getEncoded", "[B"}, {"destroy", "V"},
                {"getAlgorithm", "Ljava/lang/String;"}, {"getFormat", "Ljava/lang/String;"}}) {
            List<ImmutableInstruction> b = new ArrayList<>();
            if (!"V".equals(mm[1])) {
                b.add(new ImmutableInstruction21c(Opcode.CONST_CLASS, 0,
                        new ImmutableTypeReference("Ljava/lang/Object;")));
                b.add(new ImmutableInstruction10x(Opcode.RETURN_VOID)); // body irrelevant
            } else {
                b.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
            }
            myKeyMethods.add(new ImmutableMethod(MYKEY, mm[0], List.of(), mm[1],
                    AccessFlags.PUBLIC.getValue(), null, null,
                    new ImmutableMethodImplementation(2, b, List.of(), List.of())));
        }
        ClassDef myKey = new ImmutableClassDef(MYKEY, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", List.of("Ljavax/crypto/SecretKey;"), null, null,
                List.of(), myKeyMethods);
        return new ImmutableDexFile(Opcodes.forApi(30), List.of(probe, myKey));
    }
}
