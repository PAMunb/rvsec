import br.unb.cic.rv.pointcut.*;
import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.*;
import com.android.tools.smali.dexlib2.immutable.instruction.*;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.stream.Stream;

/**
 * Answers "what does this pointcut actually match?" by running the production
 * {@link PointcutMatcher} over every overload of a real class, instead of reasoning about it.
 *
 * <p>Two properties are what you are usually checking. <b>Coverage</b>: the union of the
 * candidates reaches every overload the CrySL rule names. <b>Disjointness</b>: no overload is
 * matched by two candidates — overlap is exactly what makes one call take two transitions.
 * Include the neighbouring members (updateAAD, unwrap, getIV) in the member table so leakage
 * shows up too.
 *
 * <pre>
 * java -cp "$CP" PointcutBudget &lt;android.jar&gt; &lt;owner-fqn&gt; &lt;members.tsv&gt; &lt;pointcuts.txt&gt;
 * </pre>
 *
 * members.tsv   tag \t name \t paramDescriptors(comma-sep) \t returnDescriptor \t 0|1(static)
 *               produced by api_members.py
 * pointcuts.txt label \t pointcut-expression        (blank lines and #-comments ignored)
 *
 * Type names in the pointcuts are resolved against imports derived automatically from the
 * member table, so `Object+`, `Key` and `ByteBuffer` all work unqualified.
 */
public class PointcutBudget {

    private static final String CALLER = "Lcom/example/app/Caller;";

    private record Member(String tag, String name, List<String> params,
                          String ret, boolean isStatic) {}

    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            System.err.println("usage: PointcutBudget <android.jar> <owner-fqn> "
                    + "<members.tsv> <pointcuts.txt>");
            System.exit(2);
        }
        Path jar = Path.of(args[0]);
        String ownerFqn = args[1];
        List<Member> api = readMembers(Path.of(args[2]));
        List<String[]> candidates = readPointcuts(Path.of(args[3]));

        PointcutMatcher pm = new PointcutMatcher(
                new TypeResolver(imports(ownerFqn, api)),
                new InheritanceResolver(new AndroidClassIndex(jar), List.of()));
        String ownerDesc = "L" + ownerFqn.replace('.', '/') + ";";

        int width = candidates.stream().mapToInt(c -> c[0].length()).max().orElse(8);
        for (String[] c : candidates) {
            PointcutExpression pe;
            try {
                pe = PointcutExpressionParser.parse(c[1]);
            } catch (RuntimeException e) {
                System.out.printf("%-" + width + "s  PARSE FAILED: %s%n", c[0], e);
                continue;
            }
            List<String> hits = new ArrayList<>();
            for (Member mb : api) {
                if (matches(pm, pe, ownerDesc, mb)) hits.add(mb.tag());
            }
            System.out.printf("%-" + width + "s  %-58s -> %s%n", c[0], c[1], hits);
        }

        // Disjointness: any member reached by more than one candidate is reported explicitly,
        // because an overlap is a double transition at runtime and is easy to miss by eye.
        Map<String, List<String>> byMember = new LinkedHashMap<>();
        for (String[] c : candidates) {
            PointcutExpression pe;
            try { pe = PointcutExpressionParser.parse(c[1]); } catch (RuntimeException e) { continue; }
            for (Member mb : api) {
                if (matches(pm, pe, ownerDesc, mb)) {
                    byMember.computeIfAbsent(mb.tag(), k -> new ArrayList<>()).add(c[0]);
                }
            }
        }
        System.out.println();
        boolean clean = true;
        for (var e : byMember.entrySet()) {
            if (e.getValue().size() > 1) {
                System.out.printf("OVERLAP  %-28s matched by %s%n", e.getKey(), e.getValue());
                clean = false;
            }
        }
        List<String> unmatched = api.stream().map(Member::tag)
                .filter(t -> !byMember.containsKey(t)).toList();
        if (!unmatched.isEmpty()) System.out.println("UNMATCHED " + unmatched);
        if (clean) System.out.println("DISJOINT  no member is matched by two candidates");
    }

    private static boolean matches(PointcutMatcher pm, PointcutExpression pe,
                                   String ownerDesc, Member mb) {
        ImmutableMethodReference ref =
                new ImmutableMethodReference(ownerDesc, mb.name(), mb.params(), mb.ret());
        // A static invoke passes only the arguments; an instance invoke passes the receiver
        // first. Register count drives the 35c/3rc choice, exactly as a real dex would.
        int regs = mb.params().size() + (mb.isStatic() ? 0 : 1);
        ImmutableInstruction call;
        if (regs <= 5) {
            int[] r = new int[5];
            for (int i = 0; i < regs; i++) r[i] = i;
            call = new ImmutableInstruction35c(
                    mb.isStatic() ? Opcode.INVOKE_STATIC : Opcode.INVOKE_VIRTUAL,
                    regs, r[0], r[1], r[2], r[3], r[4], ref);
        } else {
            call = new ImmutableInstruction3rc(
                    mb.isStatic() ? Opcode.INVOKE_STATIC_RANGE : Opcode.INVOKE_VIRTUAL_RANGE,
                    0, regs, ref);
        }
        List<ImmutableInstruction> body =
                List.of(call, new ImmutableInstruction10x(Opcode.RETURN_VOID));
        ImmutableMethod m = new ImmutableMethod(CALLER, "callSite", List.of(), "V",
                AccessFlags.PUBLIC.getValue(), null, null,
                new ImmutableMethodImplementation(Math.max(regs, 2), body, List.of(), List.of()));
        ClassDef cd = new ImmutableClassDef(CALLER, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", List.of(), null, null, List.of(), List.of(m));
        List<Instruction> all = new ArrayList<>(body);
        return pm.match(pe, cd, m, call, 0, all.size(), all).isPresent();
    }

    /** Imports for the TypeResolver, derived from every reference type the API mentions. */
    private static List<String> imports(String ownerFqn, List<Member> api) {
        Set<String> out = new LinkedHashSet<>(List.of(ownerFqn, "java.lang.Object",
                "java.lang.String"));
        for (Member mb : api) {
            Stream.concat(mb.params().stream(), java.util.stream.Stream.of(mb.ret()))
                  .forEach(d -> fqnOf(d).ifPresent(out::add));
        }
        return new ArrayList<>(out);
    }

    private static Optional<String> fqnOf(String descriptor) {
        String d = descriptor;
        while (d.startsWith("[")) d = d.substring(1);
        if (!d.startsWith("L") || !d.endsWith(";")) return Optional.empty();   // primitive
        return Optional.of(d.substring(1, d.length() - 1).replace('/', '.'));
    }

    private static List<Member> readMembers(Path p) throws Exception {
        List<Member> out = new ArrayList<>();
        for (String line : Files.readAllLines(p)) {
            if (line.isBlank() || line.startsWith("#")) continue;
            String[] f = line.split("\t", -1);
            if (f.length < 5) throw new IllegalArgumentException("bad member row: " + line);
            List<String> params = f[2].isBlank() ? List.of() : List.of(f[2].split(","));
            out.add(new Member(f[0].trim(), f[1].trim(), params, f[3].trim(), "1".equals(f[4].trim())));
        }
        return out;
    }

    private static List<String[]> readPointcuts(Path p) throws Exception {
        List<String[]> out = new ArrayList<>();
        for (String line : Files.readAllLines(p)) {
            if (line.isBlank() || line.startsWith("#")) continue;
            String[] f = line.split("\t", 2);
            out.add(f.length == 2 ? new String[]{f[0].trim(), f[1].trim()}
                                  : new String[]{"pc" + out.size(), f[0].trim()});
        }
        return out;
    }
}
