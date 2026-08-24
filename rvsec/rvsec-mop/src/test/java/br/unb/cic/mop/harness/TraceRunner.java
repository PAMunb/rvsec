package br.unb.cic.mop.harness;

import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.PredicateStore;
import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.mop.eh.ErrorDescription;

import javax.tools.JavaCompiler;
import javax.tools.ToolProvider;
import java.io.IOException;
import java.io.PrintWriter;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Replays a trace of API calls through one generated monitor snapshot and records what it
 * accuses.
 *
 * <p>
 * It exists because a structural gate measures the artefact and not its behaviour. gh100's
 * wrapper merge removed twelve silently discarded wrappers and created advices of incompatible
 * arity firing at the same site, and the count that was reported as success
 * ({@code wrappersGenerated 96 -> 84}) was blind to it; gh101's automaton repairs removed
 * eighteen all-{@code fail} rows and moved the accusation to the next call, and no gate that
 * counts rows could see that either. This replays the calls and reads the accusations.
 *
 * <h2>Why the static dispatchers, and not the wrappers</h2>
 *
 * <p>
 * Each trace line resolves against the snapshot's generated <em>static event dispatchers</em>,
 * {@code MultiSpec_1RuntimeMonitor.<Spec>_<event>Event(...)}, and never against
 * {@code mop/MonitorWrappers.java}. The wrappers exist only for {@code after} advices
 * ({@code WrapperEmitter.shouldWrap}), so replaying through them would make every {@code before}
 * advice invisible -- {@code MessageDigestSpec.reset} among them, which is precisely the event
 * the automata repairs are measured on.
 *
 * <h2>Why traces are keyed by API call and not by event name</h2>
 *
 * <p>
 * The two snapshots of a comparison need not share an alphabet: a repair may rename
 * {@code c1} to {@code c2} or delete {@code reset} outright. A trace keyed by event name would
 * silently stop resolving on one side and the harness would report "not accused" where the
 * truth is "not replayed". So a trace names API calls, and each snapshot's own pointcuts --
 * read from the {@code MultiSpec_1MonitorAspect.json} descriptor the generator writes beside
 * the monitor -- map them to that snapshot's dispatchers.
 *
 * <h2>Trace grammar</h2>
 *
 * <pre>
 * # comment, or a blank line
 * bind md = MessageDigest.getInstance("SHA-256")   # create the object, fire nothing
 * MessageDigest.getInstance("MD5") -&gt; md           # create it and fire the advices of the call
 * new PBEKeySpec(chars) -&gt; spec                    # a constructor call
 * md.update(bytes)                                 # a call on a bound object
 * </pre>
 *
 * <p>
 * The {@code bind} form is what makes the guard-on-field sites observable: it produces a real
 * object with a real algorithm whose {@code getInstance} the monitor never saw, which is the
 * situation in which a guard reading the monitor's own field reads the empty string while the
 * object itself carries {@code SHA-256}.
 *
 * <p>
 * Arguments are string literals, integers, {@code null}, a previously bound name, or one of the
 * placeholders {@code bytes}, {@code bytes(n)}, {@code chars}, {@code chars(n)} for the array
 * arguments no trace needs to spell out.
 *
 * <h2>A limitation worth knowing</h2>
 *
 * <p>
 * {@link ErrorCollector} deduplicates: it keeps a {@link java.util.Set} of
 * {@link ErrorDescription}, so a second accusation identical to the first is dropped. The
 * outcome therefore records the accusations as a set and, separately, the dispatcher calls that
 * produced no new one, so a repeated accusation is visible as a firing without a new error
 * rather than being lost.
 */
public final class TraceRunner implements AutoCloseable {

    /** What one trace did on one snapshot. */
    public static final class Outcome {
        public final String trace;
        public final boolean accused;
        public final List<String> accusingEvents = new ArrayList<>();
        public final List<String> envelopes = new ArrayList<>();
        public final List<String> unresolved = new ArrayList<>();

        Outcome(String trace, boolean accused) {
            this.trace = trace;
            this.accused = accused;
        }
    }

    private final URL classes;
    private final List<Advice> advices;
    private final Map<String, String> imports;
    private final Map<String, Object> bindings = new HashMap<>();

    private URLClassLoader loader;
    private Class<?> runtimeMonitor;

    private TraceRunner(URL classes, List<Advice> advices, Map<String, String> imports) {
        this.classes = classes;
        this.advices = advices;
        this.imports = imports;
    }

    /**
     * A monitor snapshot with no state carried over from the previous trace.
     *
     * <p>
     * The generated monitor keeps its indexing tables in {@code static} fields, so two traces
     * replayed through one loaded copy are one long trace: a legitimate
     * {@code getInstance("PKIX"); init(ks); getTrustManagers()} came back accused only because
     * the automaton was still in the state a previous trace had left it in. Each trace therefore
     * gets its own class loader, which is the only way to reset a static.
     */
    private void reload() throws Exception {
        if (loader != null) {
            loader.close();
        }
        loader = new URLClassLoader(new URL[] {classes}, TraceRunner.class.getClassLoader());
        runtimeMonitor = loader.loadClass("mop.MultiSpec_1RuntimeMonitor");
    }

    // ---------------------------------------------------------------- loading

    /**
     * Compiles a generated monitor directory into {@code workDir} and loads it.
     *
     * <p>
     * Compilation happens here rather than in the build because the harness must load two
     * snapshots in one run, and only one of them is ever the committed one. The classpath is
     * this JVM's own, so the monitor resolves {@code ErrorCollector} from the parent loader and
     * the accusations it records are the ones this class reads.
     */
    public static TraceRunner of(Path monitorDir, Path workDir) throws Exception {
        Path classes = workDir.resolve("classes");
        Files.createDirectories(classes);

        List<String> sources;
        try (Stream<Path> walk = Files.walk(monitorDir)) {
            sources = walk.filter(path -> path.toString().endsWith(".java"))
                    // `mop/Coverage.java` is the Android coverage helper: it imports
                    // android.util.Log and cannot compile off a device. It contributes no
                    // event dispatcher, so leaving it out costs the replay nothing.
                    .filter(path -> !path.getFileName().toString().equals("Coverage.java"))
                    .map(Path::toString)
                    .collect(Collectors.toList());
        }
        if (sources.isEmpty()) {
            throw new IllegalArgumentException("no generated .java under " + monitorDir);
        }

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException(
                    "no system Java compiler; the harness needs a JDK, not a JRE");
        }
        List<String> options = new ArrayList<>(Arrays.asList(
                "-classpath", System.getProperty("java.class.path"),
                "-d", classes.toString(),
                "-nowarn", "-proc:none"));
        options.addAll(sources);
        int status = compiler.run(null, null, System.err, options.toArray(new String[0]));
        if (status != 0) {
            throw new IllegalStateException("the generated monitor of " + monitorDir
                    + " did not compile; see the messages above");
        }

        Path descriptor = monitorDir.resolve("MultiSpec_1MonitorAspect.json");
        if (!Files.isRegularFile(descriptor)) {
            throw new IllegalArgumentException("no aspect descriptor beside the monitor: "
                    + descriptor + "; the pointcuts are what resolve a trace line");
        }
        List<Advice> advices = Advice.readAll(descriptor);
        Map<String, String> imports =
                readImports(monitorDir.resolve("MultiSpec_1RuntimeMonitor.java"));

        return new TraceRunner(classes.toUri().toURL(), advices, imports);
    }

    /** Simple class name to fully-qualified name, read off the monitor's own import list. */
    private static Map<String, String> readImports(Path monitor) throws IOException {
        Map<String, String> imports = new LinkedHashMap<>();
        for (String line : Files.readAllLines(monitor, StandardCharsets.UTF_8)) {
            String text = line.trim();
            if (!text.startsWith("import ")) {
                if (text.startsWith("class ") || text.startsWith("public ")) {
                    break;
                }
                continue;
            }
            String qualified = text.substring("import ".length()).replace("static ", "")
                    .replace(";", "").trim();
            if (qualified.endsWith(".*")) {
                continue;
            }
            imports.put(qualified.substring(qualified.lastIndexOf('.') + 1), qualified);
        }
        return imports;
    }

    @Override
    public void close() throws IOException {
        if (loader != null) {
            loader.close();
        }
    }

    // ---------------------------------------------------------------- replay

    /** Replays one trace file and reports what the snapshot accused. */
    public Outcome replay(Path traceFile) throws Exception {
        bindings.clear();
        reload();
        // Everything a trace can leave behind is cleared here, and the predicate substrate is
        // part of that. `reload()` builds a fresh loader for the monitor classes, but both
        // stores sit on `java.class.path`, so parent-first delegation resolves the same
        // singleton for every trace of a directory replay -- exactly why the error sink already
        // needed an explicit reset. Left alone, a satisfying trace's `ensure` silently satisfies
        // the violating trace that follows it, and the pair reports a pass it did not earn.
        ErrorCollector.instance().reset();
        PredicateStore.instance().reset();
        ExecutionContext.instance().reset();

        List<String> accusing = new ArrayList<>();
        List<String> envelopes = new ArrayList<>();
        List<String> unresolved = new ArrayList<>();

        for (String raw : Files.readAllLines(traceFile, StandardCharsets.UTF_8)) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }
            Call call = Call.parse(line);
            Object receiver = call.receiver == null ? null : bindings.get(call.receiver);
            Object[] arguments = new Object[call.arguments.size()];
            for (int index = 0; index < arguments.length; index++) {
                arguments[index] = literal(call.arguments.get(index));
            }

            Object produced = null;
            if (call.method == null) {
                // `bind buf = bytes(16)`: a value the trace needs to name, so that the same
                // array can be randomised by one call and read by the next.
                bindings.put(call.binding, literal(call.type));
                continue;
            }
            if (call.binding != null) {
                produced = call.receiver != null
                        ? produce(receiver, call.method, arguments)
                        : instantiate(call.type, call.method, arguments);
                bindings.put(call.binding, produced);
            }
            if (call.silent) {
                continue;
            }
            // The generated dispatchers key their monitor map on the monitored object, and a
            // null key is a NullPointerException inside the indexing tree rather than a
            // "no monitor" answer. A line whose object the platform could not produce is
            // therefore recorded as unreplayed, never replayed with a null.
            if (call.receiver != null && receiver == null) {
                unresolved.add(line + "  (no instance of the monitored object could be produced)");
                continue;
            }

            List<Advice> matched =
                    match(call, receiver != null ? receiver : produced, arguments);
            if (matched.isEmpty()) {
                unresolved.add(line);
                continue;
            }
            Object target = receiver != null ? receiver : produced;
            for (Advice advice : matched) {
                for (MonitorCall monitorCall : advice.calls) {
                    Set<ErrorDescription> before =
                            new HashSet<>(ErrorCollector.instance().getErrors());
                    try {
                        invoke(advice, monitorCall, arguments, target, produced);
                    } catch (Exception | StackOverflowError raised) {
                        // A guard or a handler can throw -- KeyPairGeneratorSpec's validate()
                        // switched on a null field until gh104 task 8.4 -- and in the woven
                        // application the exception propagates into the caller's frame,
                        // leaving the dispatcher's lock held (INV-INS-129, design D-14). A
                        // snapshot that throws is a result about that snapshot, so it is
                        // recorded against the trace and the replay continues; letting it end
                        // the run would mean the side that throws produces no verdict at all
                        // and the side that does not could never be compared with it.
                        Throwable cause = raised instanceof java.lang.reflect.InvocationTargetException
                                ? ((java.lang.reflect.InvocationTargetException) raised).getCause()
                                : raised;
                        unresolved.add(line + "  (" + advice.specName + "."
                                + monitorCall.eventId + " raised " + cause + ")");
                        continue;
                    }
                    Set<ErrorDescription> after = ErrorCollector.instance().getErrors();
                    if (after.size() > before.size()) {
                        accusing.add(advice.specName + "." + monitorCall.eventId);
                        envelopes.addAll(
                                envelopes(after, before, advice.specName, monitorCall.eventId));
                    }
                }
            }
        }

        Outcome outcome = new Outcome(traceFile.getFileName().toString(), !accusing.isEmpty());
        outcome.accusingEvents.addAll(accusing);
        outcome.envelopes.addAll(envelopes);
        outcome.unresolved.addAll(unresolved);
        return outcome;
    }

    /**
     * The envelopes of the accusations <em>this event added</em>, one per accusation.
     *
     * <p>
     * The set is diffed rather than scanned. {@link ErrorCollector} accumulates over the whole
     * trace and hands back a {@link HashSet}, so a scan returns an arbitrary error of the
     * specification -- in practice one raised at an earlier event -- and any second accusation
     * at one event is invisible. Both cost real evidence: an event body that raises a value
     * accusation beside a predicate one (SignatureSpec's {@code i1} raises
     * {@code SIGNATURE-ALG-00} and {@code SIGNATURE-NOBS-00} from two independent {@code if}s)
     * reported only one of the two, so re-anchoring a value list showed up as no change at all.
     *
     * <p>
     * The order is the message's, so that two snapshots of the same trace are comparable: a
     * {@code HashSet}'s iteration order is not a property of the run being measured.
     */
    private List<String> envelopes(Set<ErrorDescription> after, Set<ErrorDescription> before,
            String spec, String event) {
        List<ErrorDescription> added = new ArrayList<>();
        for (ErrorDescription error : after) {
            if (spec.equals(error.getSpec()) && !before.contains(error)) {
                added.add(error);
            }
        }
        added.sort((left, right) -> String.valueOf(left.getExpecting())
                .compareTo(String.valueOf(right.getExpecting())));
        List<String> written = new ArrayList<>();
        for (ErrorDescription error : added) {
            written.add("spec=" + error.getSpec() + ",ev=" + event + ",type=" + error.getType()
                    + ",msg=" + error.getExpecting());
        }
        if (written.isEmpty()) {
            // The event moved the counter but added nothing of this specification: the
            // accusation belongs to another spec woven over the same call. The event is still
            // an accusing one, so it keeps an envelope, and the envelope says only that.
            written.add("spec=" + spec + ",ev=" + event);
        }
        return written;
    }

    // ---------------------------------------------------------------- matching

    /**
     * The advices of this snapshot whose pointcut this line matches.
     *
     * <p>
     * A line written on a bound name ({@code kg.init(256)}) does not name its type, and half a
     * dozen JCA classes declare an {@code init} of one argument. The receiver's runtime class is
     * what separates them: {@code Mac.init(Key)} does not match a {@code KeyGenerator}. Matching
     * on the method name alone would fire another specification's dispatcher with a monitored
     * object of the wrong type.
     */
    private List<Advice> match(Call call, Object receiver, Object[] arguments) {
        List<Advice> matched = new ArrayList<>();
        for (Advice advice : advices) {
            for (Pointcut pointcut : advice.pointcuts) {
                if (!pointcut.matchesShape(call) || !advice.arityAdmits(call.arguments.size())) {
                    continue;
                }
                if (!fitsPointcut(pointcut, arguments)) {
                    continue;
                }
                if (call.type != null) {
                    if (!pointcut.type.equals(call.type)) {
                        continue;
                    }
                } else {
                    Class<?> owner = resolve(pointcut.type);
                    if (owner == null || !owner.isInstance(receiver)) {
                        continue;
                    }
                }
                if (!returnTypeAdmits(pointcut)) {
                    continue;
                }
                matched.add(advice);
                break;
            }
        }
        return matched;
    }

    /**
     * Whether the type the pointcut declares is the one the method actually returns.
     *
     * <p>
     * Both weavers gate this exactly -- AspectJ by construction, and the dexlib2 engine in
     * code with a test that spells it out ({@code PointcutMatcher.java:361-363},
     * {@code PointcutMatcherTest.java:603-612}, "concrete return-type gate MUST be exact") --
     * so a pointcut that names the wrong return type matches nothing and its advice, though
     * generated, never fires. Replaying such an advice would make the harness report that a
     * specification accuses where the woven application is silent, and would make a repair
     * that corrects a return type read as no difference at all. That is what it did before
     * this check: gh104 task 8.5 repairs {@code SignatureSpec}'s two {@code sign()} pointcuts,
     * which declared {@code byte} where android-30 declares {@code byte[]} and {@code int},
     * and the before/after replay classified the trace {@code unchanged} because both sides
     * fired {@code s1}.
     *
     * <p>
     * The platform consulted is this JVM's, not android-30's. The two agree on every signature
     * the set names -- the JCA classes are the same API -- and a type the harness cannot
     * resolve carries no gate rather than a false negative.
     */
    private boolean returnTypeAdmits(Pointcut pointcut) {
        if (pointcut.returnType == null) {
            return true;
        }
        Class<?> owner = resolve(pointcut.type);
        if (owner == null) {
            return true;
        }
        int fixed = 0;
        for (String declared : pointcut.paramTypes) {
            if (!declared.contains("..")) {
                fixed++;
            }
        }
        for (Method method : owner.getMethods()) {
            if (!method.getName().equals(pointcut.method)) {
                continue;
            }
            if (!pointcut.variadic && method.getParameterCount() != fixed) {
                continue;
            }
            if (method.getReturnType().getSimpleName().equals(pointcut.returnType)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Whether the pointcut's declared parameter types accept these arguments.
     *
     * <p>
     * {@code KeyPairGenerator.initialize(int)} and {@code initialize(AlgorithmParameterSpec)}
     * are one name at one arity, and the specification treats them as different events -- one
     * of which is an orphan that accuses on sight. Matching without the types fires the wrong
     * one. A {@code null} argument matches any reference type, as the weaver's static typing
     * would.
     *
     * <p>
     * The discrimination between those two is done by the assignability test at the end, and
     * only by it. A blanket rule stood in front of that test -- an {@code Integer} argument was
     * refused against every declared reference type -- on the strength of the same
     * {@code initialize} example, which the assignability test already decides:
     * {@code AlgorithmParameterSpec} is not assignable from {@code Integer}. The blanket rule
     * therefore changed the outcome only where the declared type genuinely does accept an
     * {@code Integer} -- {@code Object}, {@code Number}, {@code Integer}, {@code Comparable},
     * {@code Serializable} -- and in the whole {@code jca_android} set exactly one pointcut of
     * the 112 declares such a type: {@code RandomStringPasswordSpec.vo}'s
     * {@code String.valueOf(Object)}. So the rule protected nothing and blocked the one
     * conversion the set exists to model, making a replayable program report "not accused" for
     * the one reason this class must never report it: it was not replayed. Removing it moves no
     * outcome of the 92 committed traces on either snapshot of the differential comparison.
     */
    private boolean fitsPointcut(Pointcut pointcut, Object[] arguments) {
        for (int index = 0; index < pointcut.paramTypes.size() && index < arguments.length;
                index++) {
            String declared = pointcut.paramTypes.get(index).trim();
            if (declared.contains("..") || declared.contains("*") || declared.endsWith("+")) {
                return true;
            }
            Object argument = arguments[index];
            if (argument == null) {
                if ("int".equals(declared) || "long".equals(declared)
                        || "boolean".equals(declared)) {
                    return false;
                }
                continue;
            }
            if ("int".equals(declared) || "long".equals(declared)) {
                if (!(argument instanceof Integer)) {
                    return false;
                }
                continue;
            }
            Class<?> owner = resolve(declared.replace("[]", ""));
            if (declared.endsWith("[]")) {
                if (!argument.getClass().isArray()) {
                    return false;
                }
                continue;
            }
            if (owner != null && !owner.isInstance(argument)) {
                return false;
            }
        }
        return true;
    }

    private void invoke(Advice advice, MonitorCall monitorCall, Object[] arguments, Object target,
            Object produced) throws Exception {
        Map<String, Object> values = advice.bind(arguments, target, produced);
        Object[] actual = new Object[monitorCall.args.size()];
        for (int index = 0; index < actual.length; index++) {
            actual[index] = values.get(monitorCall.args.get(index));
        }

        String name = monitorCall.method.substring(monitorCall.method.lastIndexOf('.') + 1);
        Method dispatcher = null;
        for (Method candidate : runtimeMonitor.getMethods()) {
            if (candidate.getName().equals(name)
                    && candidate.getParameterCount() == actual.length) {
                dispatcher = candidate;
                break;
            }
        }
        if (dispatcher == null) {
            throw new NoSuchMethodException("no dispatcher " + name + " of arity " + actual.length
                    + " in this snapshot");
        }
        Class<?>[] declared = dispatcher.getParameterTypes();
        for (int index = 0; index < actual.length; index++) {
            actual[index] = coerce(actual[index], declared[index]);
        }
        dispatcher.invoke(null, actual);
    }

    private Object coerce(Object value, Class<?> declared) {
        if (value == null) {
            if (declared == int.class) {
                return 0;
            }
            if (declared == long.class) {
                return 0L;
            }
            if (declared == boolean.class) {
                return Boolean.FALSE;
            }
            return null;
        }
        if (declared == int.class && value instanceof String) {
            return Integer.parseInt((String) value);
        }
        if (declared == long.class && value instanceof Integer) {
            return ((Integer) value).longValue();
        }
        if (declared.isInstance(value) || declared.isPrimitive()) {
            return value;
        }
        return declared.isAssignableFrom(value.getClass()) ? value : null;
    }

    // ---------------------------------------------------------------- values

    private Object literal(String token) {
        if ("null".equals(token)) {
            return null;
        }
        if (token.startsWith("\"") && token.endsWith("\"") && token.length() >= 2) {
            return token.substring(1, token.length() - 1);
        }
        if (token.matches("-?\\d+")) {
            return Integer.valueOf(token);
        }
        if (token.startsWith("bytes")) {
            return new byte[size(token, 16)];
        }
        if (token.startsWith("chars")) {
            char[] password = new char[size(token, 8)];
            Arrays.fill(password, 'a');
            return password;
        }
        return bindings.get(token);
    }

    private static int size(String token, int fallback) {
        int open = token.indexOf('(');
        if (open < 0 || !token.endsWith(")")) {
            return fallback;
        }
        return Integer.parseInt(token.substring(open + 1, token.length() - 1).trim());
    }

    /**
     * Produces the object a trace line binds.
     *
     * <p>
     * The real API call is attempted first, because the guard-on-field traces need an object
     * whose {@code getAlgorithm()} really answers what the trace named. When the platform has no
     * such algorithm -- {@code TrustManagerFactory.getInstance("X509")} is an Android name and
     * this is a JVM -- the call falls back to any instance of the type, which still serves as
     * the monitor's identity key, and the algorithm the specification sees is the string from
     * the trace either way.
     */
    private Object instantiate(String type, String method, Object[] arguments) {
        Class<?> target = resolve(type);
        if (target == null) {
            return null;
        }
        try {
            if ("new".equals(method)) {
                Constructor<?> chosen = null;
                for (Constructor<?> constructor : target.getConstructors()) {
                    if (constructor.getParameterCount() == arguments.length
                            && (chosen == null || fits(constructor.getParameterTypes(), arguments))) {
                        chosen = constructor;
                        if (fits(constructor.getParameterTypes(), arguments)) {
                            break;
                        }
                    }
                }
                return chosen == null ? null
                        : chosen.newInstance(adapt(chosen.getParameterTypes(), arguments));
            }
            Method chosen = null;
            for (Method candidate : target.getMethods()) {
                if (!candidate.getName().equals(method)
                        || candidate.getParameterCount() != arguments.length) {
                    continue;
                }
                if (fits(candidate.getParameterTypes(), arguments)) {
                    chosen = candidate;
                    break;
                }
                if (chosen == null) {
                    chosen = candidate;
                }
            }
            if (chosen != null) {
                return chosen.invoke(null, adapt(chosen.getParameterTypes(), arguments));
            }
        } catch (Exception first) {
            // fall through to the fallback below
        }
        try {
            for (Method candidate : target.getMethods()) {
                if (candidate.getName().equals("getInstance")
                        && candidate.getParameterCount() == 1
                        && candidate.getParameterTypes()[0] == String.class) {
                    for (String fallback : FALLBACKS) {
                        try {
                            return candidate.invoke(null, fallback);
                        } catch (Exception ignored) {
                            // try the next name
                        }
                    }
                }
            }
        } catch (Exception ignored) {
            // an object the platform cannot produce; null is still a usable identity
        }
        return null;
    }

    /** Invokes an instance method to produce the object a trace line binds. */
    private Object produce(Object receiver, String method, Object[] arguments) {
        if (receiver == null) {
            return null;
        }
        try {
            Method chosen = null;
            for (Method candidate : receiver.getClass().getMethods()) {
                if (!candidate.getName().equals(method)
                        || candidate.getParameterCount() != arguments.length) {
                    continue;
                }
                if (fits(candidate.getParameterTypes(), arguments)) {
                    chosen = candidate;
                    break;
                }
                if (chosen == null) {
                    chosen = candidate;
                }
            }
            if (chosen != null) {
                chosen = onPublicOwner(chosen);
                chosen.setAccessible(true);
                return chosen.invoke(receiver, adapt(chosen.getParameterTypes(), arguments));
            }
        } catch (Exception ignored) {
            // the platform refused the call; the binding stays null and the line is recorded
        }
        return null;
    }

    /**
     * The same method, re-looked-up on a public owner when the runtime class is not public.
     *
     * <p>
     * {@code getMethods()} answers with the {@code Method} of the class that declares the
     * override, and several JCA factories hand back a package-private delegate:
     * {@code KeyPairGenerator.getInstance("RSA")} is a {@code KeyPairGenerator$Delegate}, which
     * overrides {@code generateKeyPair()}. {@code setAccessible} on that {@code Method} throws
     * {@code InaccessibleObjectException} -- {@code java.base} does not open
     * {@code java.security} to the unnamed module -- the call is refused, and the binding
     * silently becomes {@code null}. A trace that names a real key pair then replays with a
     * null key and measures nothing, which is worse than failing: the line is not recorded as
     * unresolved, because {@code bind} lines never are.
     *
     * <p>
     * Looking the same signature up on the nearest public supertype gives a {@code Method}
     * whose declaring class is exported, and virtual dispatch still runs the delegate's body.
     * Measured on this JVM, {@code KeyPairGenerator} is the only factory of the set the defect
     * reaches, and only on the two methods its delegate overrides; the non-public delegates of
     * {@code MessageDigest} and {@code Signature} override none of the methods the corpus
     * calls, so they resolved to a public owner already.
     */
    private static Method onPublicOwner(Method method) {
        if (Modifier.isPublic(method.getDeclaringClass().getModifiers())) {
            return method;
        }
        for (Class<?> owner = method.getDeclaringClass(); owner != null;
                owner = owner.getSuperclass()) {
            for (Class<?> face : owner.getInterfaces()) {
                if (!Modifier.isPublic(face.getModifiers())) {
                    continue;
                }
                try {
                    return face.getMethod(method.getName(), method.getParameterTypes());
                } catch (NoSuchMethodException ignored) {
                    // the interface does not declare it; try the next one
                }
            }
            Class<?> parent = owner.getSuperclass();
            if (parent == null || !Modifier.isPublic(parent.getModifiers())) {
                continue;
            }
            try {
                return parent.getMethod(method.getName(), method.getParameterTypes());
            } catch (NoSuchMethodException ignored) {
                // keep climbing
            }
        }
        return method;
    }

    /** Whether an overload's declared parameters accept these arguments as they stand. */
    private boolean fits(Class<?>[] declared, Object[] arguments) {
        for (int index = 0; index < declared.length; index++) {
            Object argument = index < arguments.length ? arguments[index] : null;
            if (argument == null) {
                if (declared[index].isPrimitive()) {
                    return false;
                }
                continue;
            }
            if (declared[index] == int.class && argument instanceof Integer) {
                continue;
            }
            if (declared[index] == long.class && argument instanceof Integer) {
                continue;
            }
            if (!declared[index].isInstance(argument)) {
                return false;
            }
        }
        return true;
    }

    private static final String[] FALLBACKS = {"PKIX", "SunX509", "SHA-256", "AES", "RSA",
            "SHA1PRNG", "HmacSHA256", "PKCS12", "TLS", "SHA256withRSA"};

    private Object[] adapt(Class<?>[] declared, Object[] arguments) {
        Object[] adapted = new Object[declared.length];
        for (int index = 0; index < declared.length; index++) {
            adapted[index] = coerce(index < arguments.length ? arguments[index] : null,
                    declared[index]);
        }
        return adapted;
    }

    private Class<?> resolve(String simpleName) {
        String qualified = imports.get(simpleName);
        String[] candidates = qualified != null
                ? new String[] {qualified}
                : new String[] {"java.security." + simpleName, "javax.crypto." + simpleName,
                        "javax.crypto.spec." + simpleName, "javax.net.ssl." + simpleName,
                        "java.lang." + simpleName};
        for (String candidate : candidates) {
            try {
                return Class.forName(candidate);
            } catch (ClassNotFoundException ignored) {
                // try the next package
            }
        }
        return null;
    }

    // ---------------------------------------------------------------- entry point

    /** {@code TraceRunner <monitorDir> <tracesDir> <workDir> <outJson>} */
    public static void main(String[] args) throws Exception {
        if (args.length < 4) {
            System.err.println("usage: TraceRunner <monitorDir> <tracesDir> <workDir> <outJson>");
            System.exit(2);
        }
        Path monitorDir = Paths.get(args[0]);
        Path tracesDir = Paths.get(args[1]);
        Path workDir = Paths.get(args[2]);
        Path out = Paths.get(args[3]);

        List<Path> traces;
        try (Stream<Path> list = Files.list(tracesDir)) {
            traces = list.filter(path -> path.toString().endsWith(".txt")).sorted()
                    .collect(Collectors.toList());
        }

        List<Outcome> outcomes = new ArrayList<>();
        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir)) {
            for (Path trace : traces) {
                outcomes.add(runner.replay(trace));
            }
        }

        Files.createDirectories(out.toAbsolutePath().getParent());
        try (PrintWriter writer = new PrintWriter(Files.newBufferedWriter(out,
                StandardCharsets.UTF_8))) {
            writer.println("[");
            for (int index = 0; index < outcomes.size(); index++) {
                Outcome outcome = outcomes.get(index);
                writer.println("  {");
                writer.println("    \"trace\": " + quote(outcome.trace) + ",");
                writer.println("    \"accused\": " + outcome.accused + ",");
                writer.println("    \"accusingEvents\": " + array(outcome.accusingEvents) + ",");
                writer.println("    \"envelopes\": " + array(outcome.envelopes) + ",");
                writer.println("    \"unresolved\": " + array(outcome.unresolved));
                writer.println("  }" + (index + 1 < outcomes.size() ? "," : ""));
            }
            writer.println("]");
        }
    }

    private static String array(List<String> values) {
        return values.stream().map(TraceRunner::quote)
                .collect(Collectors.joining(", ", "[", "]"));
    }

    private static String quote(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
                + "\"";
    }

    // ---------------------------------------------------------------- model

    /** One line of a trace, already split into its parts. */
    static final class Call {
        String type;
        String receiver;
        String method;
        String binding;
        boolean silent;
        final List<String> arguments = new ArrayList<>();

        static Call parse(String line) {
            Call call = new Call();
            String text = line;
            if (text.startsWith("bind ")) {
                call.silent = true;
                text = text.substring("bind ".length()).trim();
                int equals = text.indexOf('=');
                call.binding = text.substring(0, equals).trim();
                text = text.substring(equals + 1).trim();
            } else {
                int arrow = text.indexOf("->");
                if (arrow >= 0) {
                    call.binding = text.substring(arrow + 2).trim();
                    text = text.substring(0, arrow).trim();
                }
            }
            int open0 = text.indexOf('(');
            int dot0 = open0 < 0 ? text.lastIndexOf('.') : text.lastIndexOf('.', open0);
            if (!text.startsWith("new ") && dot0 < 0) {
                // `bind buf = bytes(16)` -- a value, not a call.
                call.type = text;
                return call;
            }
            if (text.startsWith("new ")) {
                text = text.substring("new ".length()).trim();
                int open = text.indexOf('(');
                call.type = text.substring(0, open).trim();
                call.method = "new";
                call.arguments.addAll(split(text.substring(open + 1, text.lastIndexOf(')'))));
                return call;
            }
            int open = text.indexOf('(');
            String head = text.substring(0, open).trim();
            int dot = head.lastIndexOf('.');
            String qualifier = head.substring(0, dot).trim();
            call.method = head.substring(dot + 1).trim();
            if (Character.isUpperCase(qualifier.charAt(0))) {
                call.type = qualifier;
            } else {
                call.receiver = qualifier;
            }
            call.arguments.addAll(split(text.substring(open + 1, text.lastIndexOf(')'))));
            return call;
        }

        private static List<String> split(String body) {
            List<String> parts = new ArrayList<>();
            int depth = 0;
            boolean quoted = false;
            StringBuilder buffer = new StringBuilder();
            for (char character : body.toCharArray()) {
                if (quoted) {
                    buffer.append(character);
                    if (character == '"') {
                        quoted = false;
                    }
                    continue;
                }
                if (character == '"') {
                    quoted = true;
                    buffer.append(character);
                } else if (character == '(') {
                    depth++;
                    buffer.append(character);
                } else if (character == ')') {
                    depth--;
                    buffer.append(character);
                } else if (character == ',' && depth == 0) {
                    parts.add(buffer.toString().trim());
                    buffer.setLength(0);
                } else {
                    buffer.append(character);
                }
            }
            if (buffer.toString().trim().length() > 0) {
                parts.add(buffer.toString().trim());
            }
            return parts;
        }
    }

    /** A {@code call(...)} of an advice's pointcut expression. */
    static final class Pointcut {
        final String type;
        final String method;
        final String returnType;
        final List<String> paramTypes;
        final boolean variadic;

        /** Words a signature may carry ahead of the return type. */
        private static final List<String> MODIFIERS = Arrays.asList(
                "public", "protected", "private", "static", "final", "abstract",
                "synchronized", "native", "strictfp");

        Pointcut(String type, String method, String returnType, List<String> paramTypes,
                boolean variadic) {
            this.type = type;
            this.method = method;
            this.returnType = returnType;
            this.paramTypes = paramTypes;
            this.variadic = variadic;
        }

        /**
         * The return type a signature declares, or {@code null} where it declares none --
         * a constructor, or a wildcard the weaver does not gate on.
         */
        static String returnTypeOf(String[] words, String method) {
            if ("new".equals(method) || words.length < 2) {
                return null;
            }
            String candidate = words[words.length - 2];
            if (MODIFIERS.contains(candidate) || candidate.contains("*")) {
                return null;
            }
            return candidate;
        }

        /** Name and arity; the owning type is checked by the caller, which knows the receiver. */
        boolean matchesShape(Call call) {
            if (!method.equals(call.method)) {
                return false;
            }
            if (call.receiver != null && "new".equals(method)) {
                return false;
            }
            int fixed = 0;
            for (String declared : paramTypes) {
                if (!declared.contains("..")) {
                    fixed++;
                }
            }
            return variadic ? call.arguments.size() >= fixed
                    : paramTypes.size() == call.arguments.size();
        }

        /** {@code call(public static MessageDigest MessageDigest.getInstance(String))} */
        static List<Pointcut> readAll(String expression) {
            List<Pointcut> pointcuts = new ArrayList<>();
            int index = 0;
            while ((index = expression.indexOf("call(", index)) >= 0) {
                int depth = 0;
                int end = index + 4;
                for (; end < expression.length(); end++) {
                    if (expression.charAt(end) == '(') {
                        depth++;
                    } else if (expression.charAt(end) == ')') {
                        depth--;
                        if (depth == 0) {
                            break;
                        }
                    }
                }
                String body = expression.substring(index + 5, end);
                index = end;

                int open = body.indexOf('(');
                if (open < 0) {
                    continue;
                }
                String signature = body.substring(0, open).trim();
                String parameters = body.substring(open + 1, body.lastIndexOf(')')).trim();
                String[] words = signature.split("\\s+");
                String qualified = words[words.length - 1];
                int dot = qualified.lastIndexOf('.');
                if (dot < 0) {
                    continue;
                }
                String owner = qualified.substring(0, dot);
                owner = owner.substring(owner.lastIndexOf('.') + 1);
                String method = qualified.substring(dot + 1);
                List<String> declared = parameters.isEmpty()
                        ? new ArrayList<String>()
                        : Call.split(parameters);
                boolean variadic = parameters.contains("..");
                pointcuts.add(new Pointcut(owner, method, returnTypeOf(words, method), declared,
                        variadic));
            }
            return pointcuts;
        }
    }

    /** One dispatcher an advice calls, with the advice-formal names it passes. */
    static final class MonitorCall {
        String method;
        String eventId;
        final List<String> args = new ArrayList<>();
    }

    /** One advice of the snapshot's descriptor. */
    static final class Advice {
        String name;
        String specName;
        String expression;
        final List<String> parameters = new ArrayList<>();
        String returning;
        String target;
        final List<String> argsBound = new ArrayList<>();
        final List<MonitorCall> calls = new ArrayList<>();
        List<Pointcut> pointcuts = new ArrayList<>();

        /**
         * Whether this advice's {@code args(...)} clause admits a call of this many arguments.
         *
         * <p>
         * {@code call(getInstance(String, ..)) && args(alg, *)} is a two-argument event and
         * {@code call(getInstance(String, ..)) && args(alg)} a one-argument one -- the same
         * pointcut, separated only by the binding clause. Reading the arity off the
         * {@code call(...)} alone fires both on every {@code getInstance}, and the legitimate
         * PKIX sequence comes back accused.
         */
        boolean arityAdmits(int size) {
            if (argsBound.isEmpty()) {
                return true;
            }
            for (String name : argsBound) {
                if ("..".equals(name)) {
                    return size >= argsBound.size() - 1;
                }
            }
            return size == argsBound.size();
        }

        /**
         * The value each advice formal takes for this trace line.
         *
         * <p>
         * {@code args(alg)} binds the formal {@code alg} to the call's first argument,
         * {@code target(k)} to the receiver and {@code returning(digest)} to whatever the call
         * produced -- so a formal with no binding in the pointcut resolves to {@code null},
         * which is what the woven code would pass as well.
         */
        Map<String, Object> bind(Object[] arguments, Object target, Object produced) {
            Map<String, Object> values = new HashMap<>();
            int position = 0;
            for (String name : argsBound) {
                if ("..".equals(name) || "*".equals(name)) {
                    position++;
                    continue;
                }
                values.put(name, position < arguments.length ? arguments[position] : null);
                position++;
            }
            if (this.target != null) {
                values.put(this.target, target);
            }
            if (returning != null) {
                values.put(returning, produced != null ? produced : target);
            }
            for (String parameter : parameters) {
                values.putIfAbsent(parameter, null);
            }
            return values;
        }

        static List<Advice> readAll(Path descriptor) throws IOException {
            String text = new String(Files.readAllBytes(descriptor), StandardCharsets.UTF_8);
            Object parsed = Json.parse(text);
            List<Advice> advices = new ArrayList<>();
            @SuppressWarnings("unchecked")
            List<Object> raw = (List<Object>) ((Map<String, Object>) parsed).get("advices");
            for (Object element : raw) {
                @SuppressWarnings("unchecked")
                Map<String, Object> entry = (Map<String, Object>) element;
                Advice advice = new Advice();
                advice.name = (String) entry.get("name");
                advice.specName = (String) entry.get("specName");
                advice.expression = (String) entry.get("expression");
                advice.pointcuts = Pointcut.readAll(advice.expression);
                Object parameters = entry.get("parameters");
                if (parameters instanceof List) {
                    for (Object parameter : (List<?>) parameters) {
                        advice.parameters.add((String) ((Map<?, ?>) parameter).get("name"));
                    }
                }
                Object returning = entry.get("returning");
                if (returning instanceof List && !((List<?>) returning).isEmpty()) {
                    advice.returning =
                            (String) ((Map<?, ?>) ((List<?>) returning).get(0)).get("name");
                }
                advice.argsBound.addAll(names(advice.expression, "args"));
                List<String> targets = names(advice.expression, "target");
                if (!targets.isEmpty()) {
                    advice.target = targets.get(0);
                }
                Object monitorCalls = entry.get("monitorCalls");
                if (monitorCalls instanceof List) {
                    for (Object element2 : (List<?>) monitorCalls) {
                        Map<?, ?> call = (Map<?, ?>) element2;
                        MonitorCall monitorCall = new MonitorCall();
                        monitorCall.method = (String) call.get("method");
                        monitorCall.eventId = (String) call.get("eventId");
                        Object callArgs = call.get("args");
                        if (callArgs instanceof List) {
                            for (Object argument : (List<?>) callArgs) {
                                monitorCall.args.add((String) argument);
                            }
                        }
                        advice.calls.add(monitorCall);
                    }
                }
                advices.add(advice);
            }
            return advices;
        }

        private static List<String> names(String expression, String keyword) {
            List<String> found = new ArrayList<>();
            int index = expression.indexOf(keyword + "(");
            while (index >= 0) {
                boolean standalone = index == 0
                        || !Character.isJavaIdentifierPart(expression.charAt(index - 1));
                int end = expression.indexOf(')', index);
                if (standalone && end > 0) {
                    for (String part : expression.substring(index + keyword.length() + 1, end)
                            .split(",")) {
                        found.add(part.trim());
                    }
                    return found;
                }
                index = expression.indexOf(keyword + "(", index + 1);
            }
            return found;
        }
    }

    /**
     * Enough JSON to read a generated descriptor.
     *
     * <p>
     * The module has no dependencies today and this file is the only reader of that descriptor,
     * so a parser of sixty lines is a smaller commitment than a JSON library on the test
     * classpath of a module that ships specification text.
     */
    static final class Json {
        private final String text;
        private int position;

        private Json(String text) {
            this.text = text;
        }

        static Object parse(String text) {
            Json json = new Json(text);
            json.skip();
            return json.value();
        }

        private void skip() {
            while (position < text.length() && Character.isWhitespace(text.charAt(position))) {
                position++;
            }
        }

        private Object value() {
            char character = text.charAt(position);
            switch (character) {
                case '{':
                    return object();
                case '[':
                    return array();
                case '"':
                    return string();
                case 't':
                    position += 4;
                    return Boolean.TRUE;
                case 'f':
                    position += 5;
                    return Boolean.FALSE;
                case 'n':
                    position += 4;
                    return null;
                default:
                    return number();
            }
        }

        private Map<String, Object> object() {
            Map<String, Object> map = new LinkedHashMap<>();
            position++;
            skip();
            if (text.charAt(position) == '}') {
                position++;
                return map;
            }
            while (true) {
                skip();
                String key = string();
                skip();
                position++; // ':'
                skip();
                map.put(key, value());
                skip();
                char character = text.charAt(position++);
                if (character == '}') {
                    return map;
                }
            }
        }

        private List<Object> array() {
            List<Object> list = new ArrayList<>();
            position++;
            skip();
            if (text.charAt(position) == ']') {
                position++;
                return list;
            }
            while (true) {
                skip();
                list.add(value());
                skip();
                char character = text.charAt(position++);
                if (character == ']') {
                    return list;
                }
            }
        }

        private String string() {
            StringBuilder buffer = new StringBuilder();
            position++;
            while (true) {
                char character = text.charAt(position++);
                if (character == '"') {
                    return buffer.toString();
                }
                if (character == '\\') {
                    char escaped = text.charAt(position++);
                    switch (escaped) {
                        case 'n':
                            buffer.append('\n');
                            break;
                        case 't':
                            buffer.append('\t');
                            break;
                        case 'r':
                            buffer.append('\r');
                            break;
                        case 'u':
                            buffer.append((char) Integer.parseInt(
                                    text.substring(position, position + 4), 16));
                            position += 4;
                            break;
                        default:
                            buffer.append(escaped);
                    }
                } else {
                    buffer.append(character);
                }
            }
        }

        private Object number() {
            int start = position;
            while (position < text.length()
                    && "-+.eE0123456789".indexOf(text.charAt(position)) >= 0) {
                position++;
            }
            String literal = text.substring(start, position);
            return literal.toLowerCase(Locale.ROOT).contains(".")
                    ? (Object) Double.valueOf(literal)
                    : (Object) Long.valueOf(literal);
        }
    }
}
