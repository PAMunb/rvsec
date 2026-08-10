import br.unb.cic.rv.pointcut.*;
import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.*;
import com.android.tools.smali.dexlib2.immutable.instruction.*;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableTypeReference;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.stream.Stream;

/**
 * Constructor-call-site variant of the skill's PointcutBudget. It drives the SAME production
 * PointcutMatcher/PointcutExpressionParser (pointcut-engine target/classes) — nothing about
 * matching is reimplemented. The only difference from the stock harness is the synthetic
 * call site: members named &lt;init&gt; are emitted as NEW_INSTANCE + INVOKE_DIRECT, which is
 * what the matcher's constructor predicate (opcode == INVOKE_DIRECT && name == "&lt;init&gt;",
 * PointcutMatcher.java:433-438) requires and what a real dex contains. Non-&lt;init&gt;
 * members keep the stock INVOKE_VIRTUAL/INVOKE_STATIC shape so neighbours stay comparable.
 *
 * usage: PointcutBudgetCtorB &lt;android.jar&gt; &lt;owner-fqn&gt; &lt;members.tsv&gt; &lt;pointcuts.txt&gt;
 */
public class PointcutBudgetCtorB {

    private static final String CALLER = "Lcom/example/app/Caller;";

    private record Member(String tag, String name, List<String> params,
                          String ret, boolean isStatic) {}

    public static void main(String[] args) throws Exception {
        Path jar = Path.of(args[0]);
        String ownerFqn = args[1];
        List<Member> api = readMembers(Path.of(args[2]));
        List<String[]> candidates = readPointcuts(Path.of(args[3]));

        List<String> imps = (args.length >= 5)
                ? Files.readAllLines(Path.of(args[4])).stream()
                        .map(String::trim).filter(l -> !l.isEmpty() && !l.startsWith("#")).toList()
                : imports(ownerFqn, api);
        PointcutMatcher pm = new PointcutMatcher(
                new TypeResolver(imps),
                new InheritanceResolver(new AndroidClassIndex(jar), List.of()));
        String ownerDesc = "L" + ownerFqn.replace('.', '/') + ";";

        Map<String, List<String>> byMember = new LinkedHashMap<>();
        for (String[] c : candidates) {
            PointcutExpression pe;
            try {
                pe = PointcutExpressionParser.parse(c[1]);
            } catch (RuntimeException e) {
                System.out.printf("%s  PARSE FAILED: %s%n", c[0], e);
                continue;
            }
            List<String> hits = new ArrayList<>();
            for (Member mb : api) {
                if (matches(pm, pe, ownerDesc, mb)) {
                    hits.add(mb.tag());
                    byMember.computeIfAbsent(mb.tag(), k -> new ArrayList<>()).add(c[0]);
                }
            }
            System.out.printf("%-8s  %-70s -> %s%n", c[0], c[1], hits);
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
        boolean ctor = "<init>".equals(mb.name());
        int regs = mb.params().size() + ((mb.isStatic() && !ctor) ? 0 : 1);
        List<ImmutableInstruction> body = new ArrayList<>();
        if (ctor) {
            // new-instance v0, <owner>; invoke-direct {v0, args...} <owner>-><init>(...)
            body.add(new ImmutableInstruction21c(Opcode.NEW_INSTANCE, 0,
                    new ImmutableTypeReference(ownerDesc)));
        }
        ImmutableInstruction call;
        Opcode op = ctor ? Opcode.INVOKE_DIRECT
                : (mb.isStatic() ? Opcode.INVOKE_STATIC : Opcode.INVOKE_VIRTUAL);
        Opcode opRange = ctor ? Opcode.INVOKE_DIRECT_RANGE
                : (mb.isStatic() ? Opcode.INVOKE_STATIC_RANGE : Opcode.INVOKE_VIRTUAL_RANGE);
        if (regs <= 5) {
            int[] r = new int[5];
            for (int i = 0; i < regs; i++) r[i] = i;
            call = new ImmutableInstruction35c(op, regs, r[0], r[1], r[2], r[3], r[4], ref);
        } else {
            call = new ImmutableInstruction3rc(opRange, 0, regs, ref);
        }
        body.add(call);
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        ImmutableMethod m = new ImmutableMethod(CALLER, "callSite", List.of(), "V",
                AccessFlags.PUBLIC.getValue(), null, null,
                new ImmutableMethodImplementation(Math.max(regs, 2), body, List.of(), List.of()));
        ClassDef cd = new ImmutableClassDef(CALLER, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", List.of(), null, null, List.of(), List.of(m));
        List<Instruction> all = new ArrayList<>(body);
        int callIdx = ctor ? 1 : 0;
        return pm.match(pe, cd, m, call, callIdx, all.size(), all).isPresent();
    }

    private static List<String> imports(String ownerFqn, List<Member> api) {
        Set<String> out = new LinkedHashSet<>(List.of(ownerFqn, "java.lang.Object",
                "java.lang.String"));
        for (Member mb : api) {
            Stream.concat(mb.params().stream(), Stream.of(mb.ret()))
                  .forEach(d -> fqnOf(d).ifPresent(out::add));
        }
        return new ArrayList<>(out);
    }

    private static Optional<String> fqnOf(String descriptor) {
        String d = descriptor;
        while (d.startsWith("[")) d = d.substring(1);
        if (!d.startsWith("L") || !d.endsWith(";")) return Optional.empty();
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
