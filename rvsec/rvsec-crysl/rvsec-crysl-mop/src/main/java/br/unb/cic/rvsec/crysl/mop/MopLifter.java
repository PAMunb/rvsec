package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.automata.InverseMorphism;
import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.model.Constraint;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Guard;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.ObjectDecl;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.io.File;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javamop.parser.SpecExtractor;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.mopspec.EventDefinition;
import javamop.parser.ast.mopspec.Formula;
import javamop.parser.ast.mopspec.JavaMOPSpec;
import javamop.parser.ast.mopspec.MOPParameter;
import javamop.parser.ast.mopspec.MOPParameters;
import javamop.parser.ast.mopspec.PropertyAndHandlers;
import javamop.parser.ast.stmt.BlockStmt;
import javamop.util.MOPNameSpace;

/**
 * Lifts one {@code .mop} file into the canonical {@link SpecModel} the five metrics compare.
 *
 * <h2>Not thread-safe, and no batch entry point</h2>
 *
 * <p>This class must be used from one thread at a time, and so must every other instance of it: the
 * hazard is not in this object but in the parser underneath. {@code JavaMOPParser} keeps its parser
 * in a {@code private static JavaMOPParser parser} field and {@code MOPNameSpace} is a static map
 * of identifiers, so two parses in flight at once share both. Two instances of this class do not
 * help; a lock inside it would not help either, because nothing stops another caller from reaching
 * the parser directly.
 *
 * <p>What does help is the shape of the API: {@link #lift(Path, Version)} takes <strong>one</strong>
 * path, and there is deliberately no overload taking a collection or a directory. A batch overload
 * is how a caller ends up writing {@code paths.parallelStream().map(lifter::lift)}, which compiles,
 * runs, and produces a corpus census that is wrong in a way no assertion catches. A caller that
 * wants a corpus writes the loop itself, and a sequential loop is what it will write.
 *
 * <h2>What the model gets and what it does not</h2>
 *
 * <p>{@code SpecModel.order} is an automaton over <strong>real signatures</strong>, symmetric with
 * the CrySL side, and it is built here rather than in the comparison (design D-20). The formula
 * names labels, so {@link FormulaParser} necessarily reads it into a {@link LabelAutomaton} first;
 * what turns that into the model's field is the inverse morphism, and that step is emphatically
 * <em>not</em> a substitution of each label by its signatures.
 *
 * <p>It is not a substitution because the alphabet is not disjoint. In {@code IvChainJunction} the
 * labels {@code use} and {@code useRandomSpec} both match one
 * {@code Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)} call, with no
 * {@code condition} on either side, so that one call emits two letters and drives the monitor
 * through two transitions. Replacing each label by its signatures would presuppose one letter per
 * observed call, which is false in the corpus; the honest step is {@code h⁻¹(L)}, where {@code h}
 * carries a signature to the <em>concatenation</em>, in declaration order, of every label matching
 * it (design D-02, {@link InverseMorphism}).
 *
 * <p>{@code SpecModel.forbidden} is always empty. JavaMOP has no counterpart to CrySL's {@code
 * FORBIDDEN} section — a prohibition is expressed by leaving a call out of the {@code ere}, which is
 * a property of the language and not a separate list — so inventing entries here would manufacture
 * agreement with the rule.
 *
 * <p>{@code SpecModel.constraints} holds the {@code condition(...)} clauses of the events, one per
 * event that declares one, with the text as written. That is the lift-level notion of a constraint:
 * the clause the specification evaluates before it lets an event fire. Classifying those clauses by
 * idiom, and deciding which CrySL {@code CONSTRAINTS} clause each one implements, is M3's work and
 * not the lifter's. Note that a clause can be both a constraint and a predicate reference — {@code
 * condition(ExecutionContext.instance().validate(Property.GENERATED_KEY, key))} is counted once in
 * {@code constraints} and once in {@code requires} — because it is genuinely both, and dropping
 * either would understate one of the two metrics.
 */
public final class MopLifter {

    private static final Pattern SPEC_HEADER = Pattern.compile("^\\s*([A-Za-z_$][\\w$]*)\\s*\\(",
            Pattern.MULTILINE);

    private static final Pattern CONDITION_CLAUSE = Pattern.compile("\\bcondition\\s*\\(");

    /**
     * Lifts one file.
     *
     * @param mopFile the {@code .mop} file, read and never written (INV-CONF-12)
     * @param version the corpus stamp; mandatory, because an unstamped model cannot reach emission
     * @return the canonical model
     * @throws LiftFailure if the file does not parse or its formula is out of scope
     */
    public SpecModel lift(Path mopFile, Version version) throws LiftFailure {
        return read(mopFile, version).model();
    }

    /**
     * Lifts one file and keeps the MOP-side facts {@link SpecModel} has no field for.
     *
     * <p>Same parse, same cost; {@link #lift(Path, Version)} is this method with everything but the
     * model dropped. M0 needs the handlers and M4 needs the substrate of each predicate site, so
     * throwing them away and re-parsing later would mean parsing every file twice.
     */
    public MopLift read(Path mopFile, Version version) throws LiftFailure {
        // INV-CONF-05. MOPNameSpace is a static global with three accumulating lists - the user
        // identifiers, the generated ones and the map between them - and a "used" flag that
        // getMOPVar() raises the first time a name is generated. init() clears the flag and
        // NOTHING ELSE: read it (javamop.util.MOPNameSpace) before assuming otherwise. The three
        // lists survive it, so a lift is NOT made independent of what was lifted before it in this
        // JVM; what the call restores is the ability to register further user identifiers, which
        // addUserVariable() refuses once the flag is up ("Cannot update MOPNameSpace after once
        // used"). Without it, the first lift that generates a name would make every later file's
        // parse throw.
        //
        // Its measured effect on these corpora is NIL. Probed over all five with the call and
        // without it, both runs give ok=215 fail=0 eventos=905 parametros=381 - identical in all
        // three aggregates, because nothing on this path generates a name. The call is kept anyway:
        // it costs one field write, it is the only reset the class offers, and a corpus that did
        // reach getMOPVar() would fail loudly without it. This comment exists so that a later
        // reader who measures the same nil does not conclude the line is dead and delete it, and
        // so that nobody credits it with a per-file isolation it does not provide. Design D-07.
        MOPNameSpace.init();

        MOPSpecFile specFile;
        try {
            specFile = SpecExtractor.parse(new File(mopFile.toString()));
        } catch (Exception e) {
            throw new LiftFailure(mopFile, "SpecExtractor.parse failed", e);
        }
        if (specFile.getSpecs() == null || specFile.getSpecs().isEmpty()) {
            throw new LiftFailure(mopFile, "the file declares no specification");
        }
        if (specFile.getSpecs().size() > 1) {
            // Measured: no file of the five corpora declares more than one specification. Refusing
            // is the honest answer if one ever does, because SpecModel describes one artifact and
            // silently lifting only the first would drop events out of every aggregate downstream.
            throw new LiftFailure(mopFile, "the file declares " + specFile.getSpecs().size()
                    + " specifications; the model describes one artifact and this component does "
                    + "not choose between them");
        }

        JavaMOPSpec spec = specFile.getSpecs().get(0);
        SourceText source = SourceText.read(mopFile);
        Provenance specSite = specSite(source, spec.getName());

        List<ObjectDecl> objects = objectsOf(spec);
        PointcutExpander expander = new PointcutExpander(specFile.getImports(),
                objects.stream().map(ObjectDecl::type).toList());

        List<EventDefinition> definitions = spec.getEvents() == null
                ? List.of() : spec.getEvents();
        Map<Object, Provenance> provenance = new LinkedHashMap<>();
        List<Event> events = new ArrayList<>();
        List<Constraint> constraints = new ArrayList<>();
        int cursor = 0;
        for (int i = 0; i < definitions.size(); i++) {
            EventDefinition definition = definitions.get(i);
            int offset = source.find(eventDeclaration(definition.getId()), cursor);
            Provenance site = offset < 0 ? specSite : source.at(offset);
            cursor = offset < 0 ? cursor : offset + 1;

            String condition = definition.getCondition();
            // declIndex is the AST index, which is the order the events are written in: declaration
            // order is dispatch order, so an event that lost its index has lost the information the
            // morphism h needs to say which letters a call emits (design D-02).
            Event event = new Event(new Label(definition.getId()),
                    definition.getPointCutString() == null ? "" : definition.getPointCutString(),
                    expander.expand(definition.getPointCut()),
                    condition == null || condition.isBlank()
                            ? Optional.empty() : Optional.of(new Guard(condition.trim())),
                    i);
            events.add(event);
            provenance.put(event, site);

            if (condition != null && !condition.isBlank()) {
                int clause = source.find(CONDITION_CLAUSE, offset < 0 ? 0 : offset);
                Constraint constraint = new Constraint(condition.trim(),
                        clause < 0 ? site : source.at(clause));
                constraints.add(constraint);
                provenance.put(constraint, constraint.site());
            }
        }

        List<PredicateSite> predicateSites = PredicateIdioms.scan(source);
        List<PredicateRef> ensures = new ArrayList<>();
        List<PredicateRef> requires = new ArrayList<>();
        List<PredicateRef> negates = new ArrayList<>();
        for (PredicateSite site : predicateSites) {
            switch (site.kind()) {
                case ENSURES -> ensures.add(site.ref());
                case REQUIRES -> requires.add(site.ref());
                case NEGATES -> negates.add(site.ref());
            }
            provenance.put(site.ref(), site.ref().site());
        }

        Map<String, HandlerBlock> handlers = handlersOf(spec, source, specSite);
        LabelAutomaton labelOrder = orderOf(mopFile, spec, events);
        InverseMorphism morphism = InverseMorphism.of(events, specSite);
        Automaton order = preimage(labelOrder, morphism);

        SpecModel model = new SpecModel(version,
                declaredTypeOf(spec, objects, events, expander, definitions, mopFile),
                Set.copyOf(objects), events, order, constraints, ensures, requires, negates,
                Set.<Signature>of(), provenance);

        MOPParameters parameters = spec.getParameters();
        return new MopLift(model, labelOrder, morphism, specSite, handlers, predicateSites,
                PredicateIdioms.acceptingStateMarks(source),
                definitions.size(), parameters == null ? 0 : parameters.size(),
                eventsBindingParameters(definitions));
    }

    /**
     * How many events bind at least one declared specification parameter.
     *
     * <p>{@code getMOPParametersOnSpec()} is the intersection JavaMOP itself computes between an
     * event's parameters and the specification's, and it is what decides whether the generated
     * monitor indexes: with the intersection empty for every event the monitor has nothing to key a
     * slice on and compiles to one monitor for the whole program. It cannot be recovered from the
     * text, which is why M0 gets it from the lift rather than re-deriving it.
     *
     * <p>The null guard is the same one {@code objectsOf} needs and for the same reason:
     * {@code JavaParserAdapter.convertParameters} swallows every exception from the parameter
     * bubble and returns {@code null} instead of reporting.
     */
    private static int eventsBindingParameters(List<EventDefinition> definitions) {
        int binding = 0;
        for (EventDefinition definition : definitions) {
            MOPParameters bound = definition.getMOPParametersOnSpec();
            if (bound != null && bound.size() > 0) {
                binding++;
            }
        }
        return binding;
    }

    /**
     * The declared objects, in declaration order.
     *
     * <p>{@code getParameters()} can be {@code null}: {@code JavaParserAdapter.convertParameters}
     * catches every exception from the parameter bubble and returns {@code null} rather than
     * reporting. No file of the five corpora reaches that branch, and the guard stays because the
     * alternative is a {@code NullPointerException} at a call site that says nothing about which
     * file caused it.
     */
    private static List<ObjectDecl> objectsOf(JavaMOPSpec spec) {
        List<ObjectDecl> objects = new ArrayList<>();
        MOPParameters parameters = spec.getParameters();
        if (parameters == null) {
            return objects;
        }
        for (MOPParameter parameter : parameters) {
            String type = parameter.getType() == null ? "*" : parameter.getType().getOp();
            objects.add(new ObjectDecl(type, parameter.getName()));
        }
        return objects;
    }

    /**
     * The type the specification is about, in three steps, each one used only when the one before
     * it finds nothing.
     *
     * <ol>
     *   <li>the type of the first declared parameter — 198 of the 215 files;</li>
     *   <li>for a parameterless specification, the declaring type of the first signature its events
     *       name. The {@code jca} sets contain exactly two such specifications, which is why design
     *       D-06 states this fallback explicitly;</li>
     *   <li>for a specification that names no method either, the type its pointcut names directly.
     *       Three files of {@code generic_new} are of that shape: they observe
     *       {@code staticinitialization(Collection+)} and never a {@code call(...)}.</li>
     * </ol>
     *
     * <p>This is the field pairing runs on, and pairing is <strong>by declared type</strong> and
     * never by file name: {@code SecretKeySpec.mop} and {@code SecretKeySpecSpec.mop} pair with
     * {@code SecretKey.crysl} and {@code SecretKeySpec.crysl} respectively, which name-matching gets
     * backwards (design D-06).
     */
    private String declaredTypeOf(JavaMOPSpec spec, List<ObjectDecl> objects, List<Event> events,
                                  PointcutExpander expander, List<EventDefinition> definitions,
                                  Path mopFile) throws LiftFailure {
        if (!objects.isEmpty()) {
            return objects.get(0).type();
        }
        for (Event event : events) {
            Optional<Signature> first = event.signatures().stream().findFirst();
            if (first.isPresent()) {
                return first.get().declaringType();
            }
        }
        for (EventDefinition definition : definitions) {
            List<String> named = expander.namedTypes(definition.getPointCut());
            if (!named.isEmpty()) {
                return named.get(0);
            }
        }
        throw new LiftFailure(mopFile, "specification '" + spec.getName() + "' declares no "
                + "parameter and no pointcut naming a type, so it has no declared type to pair on");
    }

    /**
     * The handlers, keyed exactly as {@code getHandlers()} reports them.
     *
     * <p>Two guards here, both measured:
     *
     * <ul>
     *   <li>trap (e) — the keys arrive <strong>lowercased</strong>, because the grammar writes
     *       {@code handlers.put(id.toLowerCase(), handler)}. The four keys the corpora produce are
     *       {@code fail}, {@code match}, {@code match1} and {@code match2}, so a lookup written as
     *       {@code "@match1"} or {@code "Match1"} finds nothing and reports the handler absent;
     *   <li>traps (a) and (d) — a {@code null} {@code BlockStmt} means the body did not parse and a
     *       {@code null} {@code getStmts()} means the body is {@code { }}. See {@link HandlerBlock}.
     * </ul>
     */
    private static Map<String, HandlerBlock> handlersOf(JavaMOPSpec spec, SourceText source,
                                                        Provenance specSite) {
        Map<String, HandlerBlock> handlers = new LinkedHashMap<>();
        List<PropertyAndHandlers> properties = spec.getPropertiesAndHandlers();
        if (properties == null) {
            return handlers;
        }
        for (PropertyAndHandlers property : properties) {
            Map<String, BlockStmt> declared = property.getHandlers();
            if (declared == null) {
                continue;
            }
            for (Map.Entry<String, BlockStmt> entry : declared.entrySet()) {
                String key = entry.getKey();
                // Trap (f): this BlockStmt is javamop.parser.ast.stmt.BlockStmt, the internal fork
                // of the 2006 Java 1.5 parser, and NOT com.github.javaparser.ast.stmt.BlockStmt.
                // The two share a simple name and nothing else - no common supertype, no shared
                // visitor - so an IDE that completes the import to the modern one produces code
                // that does not compile, and a mixed pipeline produces code that compiles and never
                // matches. Nothing here needs the modern parser; a caller that does should re-parse
                // block.toString() with it rather than trying to bridge the two type hierarchies.
                BlockStmt block = entry.getValue();
                HandlerBlock.Status status;
                int statements = 0;
                if (block == null) {
                    status = HandlerBlock.Status.UNPARSED;
                } else if (block.getStmts() == null) {
                    // Trap (a): getStmts() is null, not empty, for "{ }". 543 blocks of the five
                    // corpora are in this state; treating null as "no handler" would report a
                    // present-and-empty @match as absent, which is exactly the distinction M0 needs.
                    status = HandlerBlock.Status.EMPTY;
                } else {
                    statements = block.getStmts().size();
                    status = statements == 0
                            ? HandlerBlock.Status.EMPTY : HandlerBlock.Status.NON_EMPTY;
                }
                int offset = source.find(handlerDeclaration(key), 0);
                handlers.put(key, new HandlerBlock(key, status, statements,
                        offset < 0 ? specSite : source.at(offset)));
            }
        }
        return handlers;
    }

    /**
     * The language the formula denotes, over the labels the formula is written in.
     *
     * <p>A specification may declare no property at all — seventeen files of {@code generic_new} do
     * — in which case there is no order to violate and the language is every word over the
     * specification's own alphabet. See {@link FormulaParser#unconstrained}.
     */
    private static LabelAutomaton orderOf(Path mopFile, JavaMOPSpec spec, List<Event> events)
            throws LiftFailure {
        List<PropertyAndHandlers> properties = spec.getPropertiesAndHandlers();
        if (properties != null) {
            for (PropertyAndHandlers property : properties) {
                if (property.getProperty() instanceof Formula formula) {
                    return FormulaParser.parse(mopFile, formula.getType(), formula.getFormula());
                }
            }
        }
        Set<Label> labels = new LinkedHashSet<>();
        events.forEach(event -> labels.add(event.label()));
        return FormulaParser.unconstrained(labels);
    }

    /**
     * {@code h⁻¹(labelOrder)}: the model's order automaton, over real signatures.
     *
     * <p>{@link InverseMorphism#preimage} refuses to run at all when the morphism carries a
     * refusal, which is right for a caller that would otherwise publish a language built over an
     * admitted gap — but the lift is not that caller. A refusal is a typed result and not a lift
     * failure: a specification whose {@code Cipher.getInstance(String)} is claimed by two labels
     * separated by a {@code condition} still has 16 other events, a declared type, handlers and
     * predicate sites, and throwing here would drop all of that on the floor and cost the corpus
     * census a file. So the preimage is taken over the part of {@code h} that <em>is</em> resolved,
     * and the refusals travel out on {@link MopLift#morphism()}.
     *
     * <p>What that costs is stated here rather than left for a reader to infer: a refused signature
     * has no image, so it is not a letter of the result and no word containing it is in the
     * language. That narrowing is an artefact of the refusal and not a claim of the specification,
     * which is exactly why the refusal has to be read. A consumer of {@code SpecModel.order} that
     * does not also read {@code morphism().refusals()} is reading a language narrower than the file
     * it came from; 42 of the 215 files of the five corpora carry at least one such refusal,
     * 56 refusals between them.
     */
    private static Automaton preimage(LabelAutomaton labelOrder, InverseMorphism morphism) {
        if (morphism.refusals().isEmpty()) {
            return morphism.preimage(labelOrder);
        }
        // The same morphism minus its refusals, which is what preimage() insists on being given.
        // Nothing is discarded by this: the refused signatures are already absent from images(),
        // because InverseMorphism.of declines to invent an image for them, and the refusals
        // themselves are on their way out on MopLift.morphism().
        return new InverseMorphism(morphism.images(), List.of()).preimage(labelOrder);
    }

    private static Provenance specSite(SourceText source, String name) {
        Matcher matcher = SPEC_HEADER.matcher(source.code());
        while (matcher.find()) {
            if (matcher.group(1).equals(name)) {
                return source.at(matcher.start(1));
            }
        }
        return new Provenance(source.file(), 1);
    }

    private static Pattern eventDeclaration(String id) {
        return Pattern.compile("\\bevent\\s+" + Pattern.quote(id) + "\\b");
    }

    private static Pattern handlerDeclaration(String key) {
        return Pattern.compile("@\\s*" + Pattern.quote(key) + "\\b", Pattern.CASE_INSENSITIVE);
    }
}
