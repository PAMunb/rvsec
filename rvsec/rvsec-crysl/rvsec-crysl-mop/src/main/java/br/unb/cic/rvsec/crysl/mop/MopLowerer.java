package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.automata.LabelTransition;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.ObjectDecl;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import java.io.IOException;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Pattern;
import javamop.parser.ast.ImportDeclaration;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.PackageDeclaration;
import javamop.parser.ast.aspectj.BaseTypePattern;
import javamop.parser.ast.expr.NameExpr;
import javamop.parser.ast.mopspec.EventDefinition;
import javamop.parser.ast.mopspec.Formula;
import javamop.parser.ast.mopspec.JavaMOPSpec;
import javamop.parser.ast.mopspec.MOPParameter;
import javamop.parser.ast.mopspec.PropertyAndHandlers;
import javamop.parser.ast.stmt.BlockStmt;
import javamop.parser.ast.visitor.DumpVisitor;
import javamop.parser.main_parser.JavaMOPParser;

/**
 * Writes a lifted specification back out as {@code .mop} text, by building a {@link MOPSpecFile} and
 * handing it to JavaMOP's own {@link DumpVisitor}.
 *
 * <h2>Never a {@code StringBuilder}</h2>
 *
 * <p>The route is {@link MopLift} → {@code MOPSpecFile} → {@code DumpVisitor} → text, and it is that
 * way on purpose. A string builder can emit {@code .mop} text that no {@code MOPSpecFile} could
 * represent — a second {@code ere} line, an event with two pointcuts, a handler outside a property —
 * and such text would still parse often enough to look right. Constructing the tree first makes the
 * AST the arbiter of what is expressible: anything the emitter wants to say that the tree cannot
 * hold fails at construction, here, instead of surviving into a file that a reader would trust.
 *
 * <p>The one place Java source text enters is the body of an event's block, and it enters through
 * {@link JavaMOPParser#Block()} — the same entry {@code JavaParserAdapter} uses for every handler
 * body in the corpus. What lands in the tree is therefore a parsed {@code BlockStmt} and not a
 * string spliced into the output; {@code DumpVisitor} re-prints it from the AST like everything
 * else.
 *
 * <h2>What the model cannot carry, and is therefore lost</h2>
 *
 * <p>{@code SpecModel} is the shape <em>both</em> languages lift to, so it has no field for most of
 * what a {@code .mop} file writes. The losses are declared here rather than discovered by a reader
 * diffing the two files:
 *
 * <ul>
 *   <li><strong>Comments.</strong> Discarded, by the recorded decision that they cannot be
 *       faithfully round-tripped: the lifter blanks them before it scans ({@link SourceText}) and
 *       nothing downstream keeps their text or their attachment point. The one exception is a
 *       comment written <em>inside</em> a pointcut, which survives because {@link
 *       Event#pointcutText()} is the pointcut as written and is emitted verbatim.
 *   <li><strong>Event parameters, {@code returning} and {@code throwing} bindings.</strong>
 *       {@link Event} has no field for them. The generated specification therefore observes the
 *       same calls under the same conditions and binds nothing, which means it does not index —
 *       a real property of the generated tree, not a placeholder, and the reason the round trip is
 *       stated over the six fields it is stated over rather than over the whole file.
 *   <li><strong>Event bodies and handler bodies.</strong> Only the predicate idioms of a body are in
 *       the model, and those are re-emitted (below); the rest of the Java is not. Handlers come back
 *       as {@code @key { }}, so a handler's <em>key</em> survives and its statement count does not.
 *       The key is what the fourth AST check reads, which is why Layer 1 of the gate still works on
 *       generated text.
 *   <li><strong>The advice position.</strong> Every event is written {@code after}, because the
 *       model records no position.
 *   <li><strong>The specification's own name.</strong> It is not a field of {@code SpecModel}, so
 *       the lowered specification is named after the file it came from. {@code RandomStringPassword
 *       .mop} declares {@code RandomStringPasswordSpec} and lowers to {@code RandomStringPassword},
 *       which is a rename and not a corruption — nothing downstream pairs on the specification name
 *       (pairing is by declared type, design D-06).
 * </ul>
 *
 * <h2>Why the formula comes out as {@code fsm}, whatever it went in as</h2>
 *
 * <p>Since design D-20 the preimage {@code h⁻¹(L)} is taken at lift time, so {@code SpecModel.order}
 * is an automaton over real signatures and <strong>cannot be run backwards</strong> into a formula
 * over labels. What can is {@link MopLift#labelOrder()}, retained on the lift result for exactly
 * this purpose, and it is an automaton. {@code fsm} is the syntax that denotes an automaton
 * directly, so the automaton is written as one; regenerating an {@code ere} would mean state
 * elimination, which produces a language-equivalent expression that is not the expression anybody
 * wrote, and the file would then claim a provenance it does not have.
 *
 * <p>The accepting set is written as a single {@code alias match1} line. A specification that
 * declared two aliases over different states ({@code jca_android/KeyManagerFactorySpec.mop} does)
 * comes back with one over their union, because the union is what the model holds; the language is
 * unchanged and the two-alias structure is not.
 */
public final class MopLowerer {

    /** Recorded on every lowered model: comments do not survive, and this says so. */
    public static final String COMMENTS_ARE_DISCARDED =
            "comments are discarded on lower. The lifter blanks them before it scans and no field "
                    + "of the model holds their text or their attachment point, so re-emitting them "
                    + "would mean inventing both; the loss is declared here rather than discovered "
                    + "by a reader diffing the two files";

    /** The formula syntax every lowered specification is written in, and why. */
    public static final String FORMULA_SYNTAX_RULE =
            "the formula is written as fsm regardless of what it was lifted from, because what the "
                    + "lift retains is an automaton (MopLift.labelOrder) and fsm is the syntax that "
                    + "denotes one; the ere is not reconstructible, since h⁻¹(L) is applied at lift "
                    + "time and cannot be run backwards (design D-20)";

    /** A name that could be an {@code import}: dotted, and every segment an identifier. */
    private static final Pattern IMPORTABLE =
            Pattern.compile("(?:[A-Za-z_$][\\w$]*\\.)+[A-Za-z_$][\\w$]*");

    /** The alias the accepting set is written under; see the class comment. */
    private static final String ACCEPTING_ALIAS = "match1";

    /** Named in the alias when the accepting set is empty, so that no state matches it. */
    private static final String NO_ACCEPTING_STATE = "__none";

    /** The package every lowered file declares, matching what all 239 corpus files declare. */
    private static final String PACKAGE = "mop";

    /**
     * Lowers one lifted specification to {@code .mop} text.
     *
     * <p>The argument is the whole {@link MopLift} and not just its {@link SpecModel}, and that is
     * forced by D-20: the model's order automaton is over signatures and the formula is over labels,
     * so the label automaton and the morphism have to come from the lift. The handlers and the
     * predicate sites are on the lift for the same reason — the shared model has no field for
     * either.
     *
     * @param lift the lift result to write back
     * @return the {@code .mop} text, as {@code DumpVisitor} rendered it
     * @throws LowerFailure if the JavaMOP AST refuses to hold what the model says
     */
    public String lower(MopLift lift) throws LowerFailure {
        DumpVisitor visitor = new DumpVisitor();
        specFileOf(lift).accept(visitor, null);
        return visitor.getSource();
    }

    /**
     * Lowers one specification and writes it into {@code directory}, which must not be a corpus
     * directory (INV-CONF-12 — this component never writes where it reads).
     *
     * <p>The file is named after the specification and ends in {@code .mop} because
     * {@code SpecExtractor.parse} consults {@code Tool.isSpecFile} on the name and hands the parser
     * an empty string for anything else, which surfaces as "the file declares no specification"
     * rather than as a naming complaint.
     *
     * @return the file written
     */
    public Path lowerTo(MopLift lift, Path directory) throws LowerFailure, IOException {
        Objects.requireNonNull(directory, "the output directory is mandatory");
        String text = lower(lift);
        Files.createDirectories(directory);
        Path file = directory.resolve(specificationNameOf(lift) + ".mop");
        Files.write(file, text.getBytes(StandardCharsets.UTF_8));
        return file;
    }

    /**
     * The tree, which is the whole of the emitter; everything below it only fills the tree in.
     *
     * <p>Public because the round-trip gate's first layer is a check on the <em>generated tree</em>,
     * and a caller that wants to look at the tree rather than at the text should not have to reparse
     * the text to get one.
     */
    public MOPSpecFile specFileOf(MopLift lift) throws LowerFailure {
        Objects.requireNonNull(lift, "the lift result is mandatory");
        String name = specificationNameOf(lift);
        SpecModel model = lift.model();

        List<Event> declared = orderedEvents(model);
        List<BlockStmt> bodies = bodiesOf(name, lift, declared);
        List<EventDefinition> events = new ArrayList<>();
        for (int i = 0; i < declared.size(); i++) {
            events.add(eventOf(name, declared.get(i), bodies.get(i)));
        }

        List<PropertyAndHandlers> properties = propertiesOf(name, lift);

        JavaMOPSpec spec;
        try {
            spec = new JavaMOPSpec(null, 1, 1, 0, name, parametersOf(model), null, List.of(),
                    events, properties);
        } catch (Exception e) {
            throw new LowerFailure(name, "the JavaMOP AST refused the specification", e);
        }
        return new MOPSpecFile(1, 1,
                new PackageDeclaration(1, 1, List.of(), new NameExpr(1, 1, PACKAGE)),
                importsOf(model), List.of(spec));
    }

    /**
     * The name the lowered specification is declared under: the file's, without its extension.
     *
     * <p>{@code SpecModel} has no field for the specification's own name — it is a MOP-ism the CrySL
     * side has no counterpart for — so the file name is the only identity available. It is also the
     * identity M0 reports every finding under, which keeps the gate's violation lines readable
     * against the file they came from.
     */
    public static String specificationNameOf(MopLift lift) {
        String file = lift.site().file();
        return file.endsWith(".mop") ? file.substring(0, file.length() - ".mop".length()) : file;
    }

    // ── objects ──────────────────────────────────────────────────────────────────────────────

    /**
     * The declared parameters, with the one carrying {@link SpecModel#type()} written first.
     *
     * <p>{@code SpecModel.objects} is a {@code Set}, so declaration order is not in the model — and
     * the order is not decorative: the lifter reads the declared type off the <em>first</em>
     * parameter. What the model does hold is the type itself, so the parameter whose type is the
     * declared type goes first and the rest follow in a canonical order. That reconstructs the one
     * consequence the order has; it does not claim to reconstruct the order.
     */
    private static List<MOPParameter> parametersOf(SpecModel model) {
        List<ObjectDecl> ordered = new ArrayList<>(model.objects());
        ordered.sort(Comparator.comparing(ObjectDecl::type).thenComparing(ObjectDecl::name));
        ordered.stream().filter(object -> object.type().equals(model.type())).findFirst()
                .ifPresent(first -> {
                    ordered.remove(first);
                    ordered.add(0, first);
                });
        List<MOPParameter> parameters = new ArrayList<>();
        for (ObjectDecl object : ordered) {
            parameters.add(new MOPParameter(1, 1, new BaseTypePattern(1, 1, object.type()),
                    object.name()));
        }
        return parameters;
    }

    /**
     * One {@code import} per fully-qualified type any signature names.
     *
     * <p>Not decoration: {@link PointcutExpander} resolves the simple names a pointcut writes
     * through the file's own imports, so a lowered file without them lifts to a different alphabet —
     * {@code SecretKey} instead of {@code javax.crypto.SecretKey} — and the round trip would report
     * every event as changed. The signatures are already resolved, so the imports are recoverable
     * from them exactly. Array suffixes, wildcards and AspectJ's {@code ..} are not importable names
     * and are filtered out; a type the original file never imported arrives here as a simple name,
     * produces no import, and resolves back to itself.
     */
    private static List<ImportDeclaration> importsOf(SpecModel model) {
        Set<String> names = new TreeSet<>();
        for (Event event : model.events()) {
            for (Signature signature : event.signatures()) {
                importable(signature.declaringType(), names);
                importable(signature.returnType(), names);
                signature.paramTypes().forEach(type -> importable(type, names));
            }
        }
        List<ImportDeclaration> imports = new ArrayList<>();
        for (String name : names) {
            imports.add(new ImportDeclaration(1, 1, new NameExpr(1, 1, name), false, false));
        }
        return imports;
    }

    private static void importable(String type, Set<String> out) {
        String base = type;
        while (base.endsWith("[]")) {
            base = base.substring(0, base.length() - 2);
        }
        if (IMPORTABLE.matcher(base).matches()) {
            out.add(base);
        }
    }

    // ── events ───────────────────────────────────────────────────────────────────────────────

    /** The events in declaration order, which is dispatch order (INV-CONF-03). */
    private static List<Event> orderedEvents(SpecModel model) {
        List<Event> ordered = new ArrayList<>(model.events());
        ordered.sort(Comparator.comparingInt(Event::declIndex));
        return ordered;
    }

    /**
     * One {@code event} declaration.
     *
     * <p>The pointcut is {@link Event#pointcutText()} verbatim, which is what makes the alphabet
     * survive: the guard travels inside it as the {@code condition(...)} clause it was written as,
     * and {@code EventDefinition} re-parses the string with the same AspectJ parser the lift used,
     * so a pointcut this constructor accepts is by definition one the lift can read back. A newline
     * is appended because a pointcut ending in a line comment would otherwise swallow the {@code
     * &#123;} that {@code DumpVisitor} prints immediately after it.
     */
    private static EventDefinition eventOf(String specification, Event event, BlockStmt body)
            throws LowerFailure {
        try {
            return new EventDefinition(1, 1, event.label().name(), null, "after", List.of(),
                    event.pointcutText() + "\n", body, false, List.of(), false, List.of(),
                    false, false, false, false);
        } catch (Exception e) {
            throw new LowerFailure(specification, "the pointcut of event '" + event.label().name()
                    + "' did not parse back: " + event.pointcutText(), e);
        }
    }

    /** {@code getStmts() == null} is what the parser itself produces for {@code { }} — trap (a). */
    private static BlockStmt emptyBlock() {
        return new BlockStmt(1, 1, 1, 1, null);
    }

    /**
     * One Java block per event, carrying the predicate idioms that event was written with.
     *
     * <p>Two problems have to be solved together here, and solving either one alone gets the other
     * wrong.
     *
     * <p><strong>Which event a reference belongs to.</strong> {@link SpecModel} records which
     * predicates the specification references, in what order and on which substrate; it does not
     * record which block each reference was written in. What it does carry is a {@code file:line}
     * per reference and a {@code file:line} per event, so each site is attributed to the event whose
     * declaration most recently precedes it — the same attribution rule
     * {@link br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption#RULE} states for {@code addError},
     * and stated here for the same reason: it is a rule, not a guess, and it is written down. A site
     * above the first event goes to the first event, which is the only block that exists before it.
     * Attribution is what keeps the three predicate lists in their original order across the round
     * trip: a reference written in event 3 must not come back out ahead of one written in event 1.
     *
     * <p><strong>Which references are already carried by the pointcut.</strong> Most {@code
     * REQUIRES} references in the corpora are written inside a {@code condition(...)} clause, and
     * the clause travels out with {@link Event#pointcutText()}, which is emitted verbatim. Emitting
     * them again in the block would double them — measured on {@code jca/CipherSpec.mop}, whose
     * three requirements came back as six. So each event's pointcut is scanned with the same
     * {@link PredicateIdioms} the lift uses, and the sites it already carries are consumed from the
     * front of that event's attributed list rather than re-emitted. From the front, because the
     * pointcut is written above the block, so a condition's references are exactly the first the
     * scan meets inside that event.
     */
    private List<BlockStmt> bodiesOf(String specification, MopLift lift, List<Event> events)
            throws LowerFailure {
        List<List<String>> statements = new ArrayList<>();
        List<Integer> locals = new ArrayList<>();
        for (int i = 0; i < events.size(); i++) {
            statements.add(new ArrayList<>());
            locals.add(0);
        }
        if (events.isEmpty()) {
            return List.of();
        }

        List<Deque<String>> carried = new ArrayList<>();
        for (Event event : events) {
            Deque<String> keys = new ArrayDeque<>();
            PredicateIdioms.scan(SourceText.of(specification, event.pointcutText()))
                    .forEach(site -> keys.addLast(keyOf(site)));
            carried.add(keys);
        }

        for (PredicateSite site : lift.predicateSites()) {
            int owner = ownerOf(site.ref().site().line(), lift, events);
            if (!carried.get(owner).isEmpty() && carried.get(owner).peekFirst().equals(keyOf(site))) {
                carried.get(owner).removeFirst();
                continue;
            }
            String call = callOf(site);
            boolean negated = site.ref().polarity() == Polarity.NEGATED && !isAbsenceIdiom(site);
            if (negated || site.verdict().isPresent()) {
                statements.get(owner).add("boolean __p" + locals.get(owner) + " = "
                        + (negated ? "!" : "") + call
                        + site.verdict().map(verdict -> " == " + verdict).orElse("") + ";");
                locals.set(owner, locals.get(owner) + 1);
            } else {
                statements.get(owner).add(call + ";");
            }
        }
        for (PredicateIdioms.AcceptingStateMark mark : lift.acceptingStateMarks()) {
            statements.get(ownerOf(mark.site().line(), lift, events))
                    .add("ExecutionContext.instance()." + (mark.set() ? "set" : "unset")
                            + "ObjectAsInAcceptingState(" + mark.object() + ");");
        }

        List<BlockStmt> blocks = new ArrayList<>();
        for (List<String> body : statements) {
            blocks.add(body.isEmpty() ? emptyBlock() : blockOf(specification, body));
        }
        return blocks;
    }

    /** The index of the event whose declaration most recently precedes {@code line}. */
    private static int ownerOf(int line, MopLift lift, List<Event> events) {
        int owner = 0;
        for (int i = 0; i < events.size(); i++) {
            Provenance site = lift.model().provenance().get(events.get(i));
            if (site != null && site.line() <= line) {
                owner = i;
            }
        }
        return owner;
    }

    /**
     * Everything about a site that the lift can read back, so that a site already carried by a
     * pointcut is recognised as the same site. Provenance is deliberately not in the key: the
     * lowered file is a different file at different lines.
     */
    private static String keyOf(PredicateSite site) {
        return site.kind() + "|" + site.substrate() + "|" + site.ref().polarity() + "|"
                + site.ref().name() + "|" + site.ref().arguments() + "|" + site.verdict();
    }

    /**
     * The block, built by handing the statements to {@link JavaMOPParser#Block()} — the same entry
     * {@code JavaParserAdapter} uses for every handler body in the corpus.
     *
     * <p>So what lands in the tree is a parsed {@code BlockStmt}, and {@code DumpVisitor} re-prints
     * it from the AST like every other node. A statement the AST cannot hold fails here rather than
     * being spliced into the output as text.
     */
    private static BlockStmt blockOf(String specification, List<String> statements)
            throws LowerFailure {
        String block = "{\n" + String.join("\n", statements) + "\n}";
        try {
            return new JavaMOPParser(new StringReader(block)).Block();
        } catch (Exception e) {
            throw new LowerFailure(specification,
                    "the predicate idioms did not parse back as a Java block: " + block, e);
        }
    }

    /** Whether the idiom says "absent" in its own name, so that no {@code !} is needed. */
    private static boolean isAbsenceIdiom(PredicateSite site) {
        return site.substrate() == PredicateSite.Substrate.PREDICATE_STORE
                && site.kind() == PredicateSite.Kind.REQUIRES;
    }

    /** The idiom call of one site, in the substrate it was read on. */
    private static String callOf(PredicateSite site) {
        PredicateRef ref = site.ref();
        String arguments = ref.arguments().isEmpty()
                ? ref.name() : ref.name() + ", " + String.join(", ", ref.arguments());
        if (site.substrate() == PredicateSite.Substrate.EXECUTION_CONTEXT) {
            String method = switch (site.kind()) {
                case ENSURES -> "setProperty";
                case REQUIRES -> "validate";
                case NEGATES -> "remove";
            };
            return "ExecutionContext.instance()." + method + "(" + arguments + ")";
        }
        String method = switch (site.kind()) {
            case ENSURES -> "ensure";
            case REQUIRES -> ref.polarity() == Polarity.NEGATED ? "validateAbsent" : "validate";
            case NEGATES -> "negate";
        };
        return "PredicateStore.instance()." + method + "(" + arguments + ")";
    }

    // ── the formula and the handlers ─────────────────────────────────────────────────────────

    /**
     * The property of the lowered specification: the automaton as {@code fsm}, plus one empty block
     * per declared handler key — or no property at all when the specification declares no handler.
     *
     * <p>The handler keys are what the fourth AST check reads — a {@code @match} family with no
     * {@code @fail} is a violation whatever the bodies contain — so emitting the keys with empty
     * bodies keeps the gate able to catch that failure mode on generated text, which is the whole
     * point of running the checker over the generated tree.
     *
     * <p>A property with no handler cannot be written at all, and that is the grammar's rule rather
     * than a choice made here: {@code getFormula()} reads raw characters until it meets an
     * {@code @}, so a formula with no handler after it runs to end of file and the parser reports
     * {@code Encountered "<EOF>" ... Was expecting "@"}. The seventeen property-less files of
     * {@code generic_new} are exactly that shape; they were lifted with
     * {@link FormulaParser#unconstrained}, and coming back with no property lifts them with it
     * again, so the language survives the round trip precisely because nothing is written.
     *
     * <p>A specification with a real formula and no handler is therefore not writable. It does not
     * occur — the grammar cannot produce one — and if a model ever claims it, this refuses rather
     * than dropping the formula and handing back a specification that admits every word.
     */
    private static List<PropertyAndHandlers> propertiesOf(String specification, MopLift lift)
            throws LowerFailure {
        if (lift.handlers().isEmpty()) {
            if (!admitsEveryWord(lift.labelOrder())) {
                throw new LowerFailure(specification, "the specification declares a formula and no "
                        + "handler, which the JavaMOP grammar cannot express: the formula would run "
                        + "to end of file. Writing it without the formula would hand back a "
                        + "specification that admits every word", null);
            }
            return List.of();
        }
        HashMap<String, BlockStmt> handlers = new HashMap<>();
        for (String key : lift.handlers().keySet()) {
            handlers.put(key, new BlockStmt(1, 1, 1, 1, null));
        }
        return List.of(new PropertyAndHandlers(1, 1,
                new Formula(1, 1, "fsm", fsmOf(lift.labelOrder())), handlers));
    }

    /** The shape {@link FormulaParser#unconstrained} builds: one accepting state, all self-loops. */
    private static boolean admitsEveryWord(LabelAutomaton automaton) {
        return automaton.states().size() == 1 && automaton.accepting().equals(automaton.states())
                && automaton.transitions().stream().allMatch(t -> t.from().equals(t.to()));
    }

    /**
     * The automaton written in {@code fsm} syntax, initial state first.
     *
     * <p>Initial state first is not cosmetic: {@link FormulaParser} takes the first declared block as
     * the initial state, which is JavaMOP's own rule. Every state gets a block, including one that
     * only ever appears as a transition target, so that the state set survives; a state with no
     * outgoing edge comes back as an empty block.
     *
     * <p>The accepting set is written as one {@code alias match1} line. When it is empty the alias
     * names a state that does not exist, which is the only way {@code fsm} can say "nothing here
     * accepts" — the reader's fallback for a specification with no alias at all is "every declared
     * state accepts", and falling into it would hand back a different language.
     */
    private static String fsmOf(LabelAutomaton automaton) {
        Map<String, List<LabelTransition>> byState = new TreeMap<>();
        automaton.states().forEach(state -> byState.put(state, new ArrayList<>()));
        automaton.transitions().forEach(t -> byState.get(t.from()).add(t));

        List<String> blocks = new ArrayList<>();
        blocks.add(stateBlockOf(automaton.initial(), byState.get(automaton.initial())));
        for (Map.Entry<String, List<LabelTransition>> entry : byState.entrySet()) {
            if (!entry.getKey().equals(automaton.initial())) {
                blocks.add(stateBlockOf(entry.getKey(), entry.getValue()));
            }
        }
        String accepting = automaton.accepting().isEmpty() ? NO_ACCEPTING_STATE
                : String.join(" ", new TreeSet<>(automaton.accepting()));
        return "\n" + String.join("\n", blocks)
                + "\n  alias " + ACCEPTING_ALIAS + " = " + accepting + "\n";
    }

    /**
     * One {@code fsm} state block: the state, then one {@code label -> state} line per outgoing
     * edge, in a fixed order so that two runs over the same automaton produce the same text.
     *
     * <p>This leaf is a string and there is no way around that: the {@code fsm} formula is a single
     * opaque field on {@link Formula}, because the JavaMOP grammar captures it as raw characters and
     * never builds a node for it. The prohibition on string building is about the {@code .mop} file,
     * which comes from {@code DumpVisitor} and from nothing else; this string is what the AST hands
     * to it, not a route around it.
     */
    private static String stateBlockOf(String state, List<LabelTransition> outgoing) {
        List<String> edges = outgoing.stream()
                .map(t -> "    " + t.symbol().name() + " -> " + t.to())
                .distinct()
                .sorted()
                .toList();
        return "  " + state + " [\n" + String.join("\n", edges) + "\n  ]";
    }
}
