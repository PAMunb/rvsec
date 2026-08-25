package br.unb.cic.rvsec.crysl.crysl;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.model.Constraint;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.ObjectDecl;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import crysl.parsing.CrySLModelReader;
import crysl.parsing.CrySLParserException;
import crysl.rule.CrySLForbiddenMethod;
import crysl.rule.CrySLMethod;
import crysl.rule.CrySLPredicate;
import crysl.rule.CrySLRule;
import crysl.rule.ICrySLPredicateParameter;
import crysl.rule.ISLConstraint;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Stream;

/**
 * Reads one {@code .crysl} rule into the canonical {@link SpecModel}, with a
 * {@link CrySLModelReader} constructed for that rule and discarded with it.
 *
 * <h2>Why a fresh reader, and why there is no way to ask for anything else</h2>
 *
 * <p>{@code CrySLModelReader} accumulates {@code OBJECTS} scope across the rules it reads, in both
 * directions, and the leak is measured on the upstream corpus itself. {@code Signature.crysl} uses
 * {@code offset} and {@code len} without declaring them, and loads only if {@code GCMParameterSpec},
 * {@code IvParameterSpec} or {@code Mac} was read first in the same reader. {@code SecretKey.crysl}
 * read before {@code Key.crysl} <em>breaks</em> {@code Key.crysl}. Under one shared reader the set
 * of rules that load is therefore a function of read order: forty random orders gave the histogram
 * {@code {29:3, 30:15, 31:22}}. Under a fresh reader the answer is 47 of 49, every time.
 *
 * <p>So INV-CONF-04 is not a recommendation this class follows. No method of this class accepts a
 * reader, no field of this module holds one — an ArchUnit rule in the test sources checks that — and
 * no flag turns sharing back on. A flag that reintroduces non-determinism is a flag that will
 * eventually be set, most likely by someone chasing the cost of constructing 49 readers, which is
 * not the expensive part of anything here.
 *
 * <h2>The rules are read as they stand</h2>
 *
 * <p>There is <strong>no lexical normalization</strong>, of any kind, anywhere in this class. The
 * file goes to the reader byte for byte. The five-substitution normalizer that existed in this
 * project belonged to the abandoned {@code api30} corpus and has no consumer; reintroducing it "just
 * in case" would mean the oracle the comparison cites is not the oracle on disk.
 *
 * <p>The two rules that do not load are consequently findings about the upstream files —
 * {@code OAEPParameterSpec} uses the grammar's reserved word {@code alg} as an object name and
 * {@code SSLEngine}'s {@code ORDER} references an event {@code cp1} that is declared {@code ep1} —
 * and INV-CONF-12 forbids repairing them in place. They are reported, not fixed.
 */
public final class CryslLifter {

    /** The file extension of a CrySL rule. */
    public static final String RULE_EXTENSION = ".crysl";

    /**
     * The outcome of reading a whole directory: what lifted and what did not.
     *
     * @param models   one model per rule that lifted, in file-name order
     * @param failures one failure per rule that did not, in file-name order
     */
    public record CorpusLift(List<SpecModel> models, List<LiftFailure> failures) {

        public CorpusLift {
            models = List.copyOf(models);
            failures = List.copyOf(failures);
        }

        /** Number of rules that lifted. */
        public int ok() {
            return models.size();
        }

        /** Number of rules that did not, which is a finding count and not an error count. */
        public int failed() {
            return failures.size();
        }
    }

    /**
     * Lifts one rule.
     *
     * <p>The {@code version} is the corpus identity, supplied by the caller and stamped verbatim
     * onto the model (INV-CONF-01). It is a parameter rather than a constant of this class on
     * purpose: a model that carried a corpus identity this class chose for itself could be
     * attributed to a corpus that did not produce it, and the whole point of the stamp is that a
     * number lifted from {@code CrySL-Rules} at one commit can never be read as a number from
     * anywhere else.
     *
     * @param cryslRule the rule file, read as it stands
     * @param version   which corpus this rule came from, and at which commit
     * @return the canonical model
     * @throws LiftFailure if the rule does not parse; the failure carries the parser's exception
     *                     and the EMF diagnostics that say where and why
     */
    public SpecModel lift(Path cryslRule, Version version) throws LiftFailure {
        Objects.requireNonNull(cryslRule, "cryslRule is mandatory");
        Objects.requireNonNull(version, "version is mandatory (INV-CONF-01)");

        // Provenance first: it is also the only route that can say what is wrong with a rule the
        // facade will refuse, and the facade's own message never says.
        CryslProvenance provenance = CryslProvenance.read(cryslRule);

        CrySLRule rule;
        try {
            // A NEW reader, for this rule alone. INV-CONF-04.
            rule = new CrySLModelReader().readRule(cryslRule.toFile());
        } catch (CrySLParserException | RuntimeException e) {
            throw new LiftFailure(cryslRule, "the CrySL reader refused the rule",
                    provenance.errors(), e);
        }
        if (rule == null) {
            throw new LiftFailure(cryslRule, "the CrySL reader returned no rule",
                    provenance.errors(),
                    new CrySLParserException("the reader returned no rule for " + cryslRule));
        }
        return toModel(cryslRule, rule, provenance, version);
    }

    /**
     * Lifts every {@code .crysl} file of a directory, in file-name order.
     *
     * <p>A rule that does not lift does not abort the run: it becomes an entry of
     * {@link CorpusLift#failures()} and the reading continues. That is the difference between a
     * finding and an incident, and the upstream corpus depends on it — two of its 49 rules have
     * never parsed.
     *
     * @param directory the corpus directory, never written to (INV-CONF-12)
     * @param version   the corpus identity stamped on every model produced
     * @return what lifted and what did not
     * @throws IOException if the directory cannot be listed
     */
    public CorpusLift liftCorpus(Path directory, Version version) throws IOException {
        Objects.requireNonNull(directory, "directory is mandatory");
        Objects.requireNonNull(version, "version is mandatory (INV-CONF-01)");
        if (!Files.isDirectory(directory)) {
            throw new IOException("not a corpus directory: " + directory.toAbsolutePath());
        }

        List<Path> rules;
        try (Stream<Path> entries = Files.list(directory)) {
            rules = entries.filter(path -> path.getFileName().toString().endsWith(RULE_EXTENSION))
                    .sorted(Comparator.comparing(path -> path.getFileName().toString()))
                    .toList();
        }

        List<SpecModel> models = new ArrayList<>();
        List<LiftFailure> failures = new ArrayList<>();
        for (Path rule : rules) {
            try {
                models.add(lift(rule, version));
            } catch (LiftFailure failure) {
                failures.add(failure);
            }
        }
        return new CorpusLift(models, failures);
    }

    private SpecModel toModel(Path file, CrySLRule rule, CryslProvenance provenance, Version version) {
        String fileName = file.getFileName().toString();
        Map<Object, Provenance> sites = new HashMap<>();

        Set<ObjectDecl> objects = new LinkedHashSet<>();
        for (Map.Entry<String, String> declared : rule.getObjects()) {
            // CrySL writes an OBJECTS entry as "type name"; the facade hands it over as
            // name -> type, so the key is the identifier and the value is the type.
            ObjectDecl object = new ObjectDecl(declared.getValue(), declared.getKey());
            objects.add(object);
            sites.put(object, at(fileName, provenance.objectLines().get(declared.getKey()),
                    provenance, CryslProvenance.Section.OBJECTS));
        }

        List<Event> events = liftEvents(rule, provenance, fileName, sites);

        Automaton order = StateMachineAdapter.toAutomaton(rule.getUsagePattern());

        Provenance constraintSite = section(fileName, provenance, CryslProvenance.Section.CONSTRAINTS);
        List<Constraint> constraints = new ArrayList<>();
        for (ISLConstraint clause : rule.getConstraints()) {
            // The clause is kept as the facade renders it. M3 classifies by idiom over this text,
            // and it can only do that over what was written rather than over a summary of it.
            Constraint constraint = new Constraint(String.valueOf(clause), constraintSite);
            constraints.add(constraint);
            sites.put(constraint, constraintSite);
        }

        List<PredicateRef> ensures = liftPredicates(rule.getPredicates(), fileName, provenance,
                CryslProvenance.Section.ENSURES, sites);
        List<PredicateRef> negates = liftPredicates(rule.getNegatedPredicates(), fileName, provenance,
                CryslProvenance.Section.NEGATES, sites);
        List<PredicateRef> requires = liftRequired(rule, fileName, provenance, sites);

        Set<Signature> forbidden = new LinkedHashSet<>();
        Provenance forbiddenSite = section(fileName, provenance, CryslProvenance.Section.FORBIDDEN);
        for (CrySLForbiddenMethod method : rule.getForbiddenMethods()) {
            Signature signature = StateMachineAdapter.toSignature(method.getMethod());
            forbidden.add(signature);
            sites.put(signature, forbiddenSite);
        }

        return new SpecModel(version, rule.getClassName(), objects, events, order, constraints,
                ensures, requires, negates, forbidden, sites);
    }

    /**
     * The rule's {@code EVENTS}, one model event per declared method.
     *
     * <p>Two decisions are visible here and both come from D-19.
     *
     * <p><strong>The label is synthetic.</strong> The façade does not expose the names the rule was
     * written with — {@code TransitionEdge.getLabel()} answers method signatures, not {@code g1} or
     * {@code Get} — and those names are deliberately kept out of the comparison: the alphabet is
     * {@code Signature} and never {@code Label} (INV-CONF-03). A positional {@code crysl:n} says
     * plainly that this side has no label to offer, where borrowing a method name would invite a
     * name-matching heuristic that D-19 rejected. The declared names are available, for reports and
     * for a human reading a finding, through {@link CryslProvenance#eventNames()}.
     *
     * <p><strong>The order is canonical, not declaration order.</strong> The façade returns the
     * events in an unspecified iteration order, so declaration order is not recoverable from it at
     * all; sorting by signature gives an order that is at least the same on every JVM and every run.
     * Nothing is lost: {@code declIndex} exists because on the MOP side declaration order is
     * dispatch order when two labels match one call, and on the CrySL side no such dispatch exists —
     * one event is one method.
     */
    private List<Event> liftEvents(CrySLRule rule, CryslProvenance provenance, String fileName,
                                   Map<Object, Provenance> sites) {
        Provenance eventsSite = section(fileName, provenance, CryslProvenance.Section.EVENTS);
        List<CrySLMethod> methods = rule.getEvents().stream()
                .sorted(Comparator.comparing(CrySLMethod::getDeclaringClassName)
                        .thenComparing(CrySLMethod::getShortMethodName)
                        .thenComparing(method -> String.join(",", method.getParameters().stream()
                                .map(Map.Entry::getValue).toList())))
                .toList();

        List<Event> events = new ArrayList<>();
        for (int index = 0; index < methods.size(); index++) {
            CrySLMethod method = methods.get(index);
            Signature signature = StateMachineAdapter.toSignature(method);
            Event event = new Event(new Label("crysl:" + index), method.getSignature(),
                    Set.of(signature), Optional.empty(), index);
            events.add(event);
            sites.put(event, eventsSite);
            sites.put(signature, eventsSite);
        }
        return events;
    }

    /**
     * The {@code ENSURES} and {@code NEGATES} blocks, which are read the same way and differ only in
     * the list they land in.
     *
     * <p>Both are {@link Polarity#POSITIVE}. The façade reports {@code isNegated() == true} for
     * every entry of a {@code NEGATES} block, but that flag is the block and not the reference:
     * {@code CrySLModelReader.getTimedPredicates} is called with a hard-coded {@code false} for
     * {@code ENSURES} and a hard-coded {@code true} for {@code NEGATES}, so it restates which
     * collection the entry came from and carries no per-reference fact. The corpus agrees — its two
     * {@code NEGATES} entries, {@code PBEKeySpec.crysl} and {@code SecretKey.crysl}, name their
     * predicate with no {@code !} on it. Copying the flag here would make every {@code NEGATES}
     * pair read as inverted against a {@code .mop} {@code remove(...)}, which writes no {@code !}
     * either. Polarity is a per-reference fact, and the one block where it is one is
     * {@code REQUIRES}.
     */
    private List<PredicateRef> liftPredicates(Iterable<CrySLPredicate> predicates, String fileName,
                                              CryslProvenance provenance,
                                              CryslProvenance.Section sectionId,
                                              Map<Object, Provenance> sites) {
        Provenance site = section(fileName, provenance, sectionId);
        List<PredicateRef> refs = new ArrayList<>();
        for (CrySLPredicate predicate : predicates) {
            PredicateRef ref = toRef(predicate, Polarity.POSITIVE, site);
            refs.add(ref);
            sites.put(ref, site);
        }
        return refs;
    }

    /**
     * The {@code REQUIRES} block.
     *
     * <p>Every entry of the upstream corpus is a {@code CrySLPredicate} — 56 of them, measured — so
     * the loop is written for that and nothing else; an entry of any other shape would be a change
     * in the corpus worth noticing rather than a case to absorb silently.
     *
     * <p>Three of those 56 are negated in place — {@code Cipher.crysl:137} requires
     * {@code !macced[_, plainText]} and {@code Mac.crysl:51} and {@code :52} require
     * {@code !encrypted[...]}. They stay in {@code requires}, which is their section: a negated
     * requirement demands the predicate be <em>absent</em>, whereas {@code NEGATES} says the event
     * withdraws a predicate, and moving them would claim a clause the rule does not have. The
     * {@code !} rides on {@link PredicateRef#polarity()} instead, read from the grammar through
     * {@code CrySLPredicate.isNegated()} — here, unlike in the other two blocks, the flag is a fact
     * of the reference: {@code CrySLModelReader.getRequiredPredicate} takes it from
     * {@code RequiredPredicate.isNegated()} on the parse tree.
     */
    private List<PredicateRef> liftRequired(CrySLRule rule, String fileName,
                                            CryslProvenance provenance, Map<Object, Provenance> sites) {
        Provenance site = section(fileName, provenance, CryslProvenance.Section.REQUIRES);
        List<PredicateRef> refs = new ArrayList<>();
        for (ISLConstraint required : rule.getRequiredPredicates()) {
            if (required instanceof CrySLPredicate predicate) {
                PredicateRef ref = toRef(predicate, polarityOf(predicate), site);
                refs.add(ref);
                sites.put(ref, site);
            }
        }
        return refs;
    }

    private PredicateRef toRef(CrySLPredicate predicate, Polarity polarity, Provenance site) {
        List<String> arguments = predicate.getParameters().stream()
                .map(ICrySLPredicateParameter::getName)
                .map(String::valueOf)
                .toList();
        return new PredicateRef(predicate.getPredName(), arguments, polarity, site);
    }

    /**
     * The polarity of a {@code REQUIRES} entry.
     *
     * <p>{@code isNegated()} is declared to return a boxed {@code Boolean}, so a {@code null} is
     * reachable through the type even though the 4.0.6 constructors always set it. It is refused
     * out loud rather than read as {@code POSITIVE}: an unknown polarity silently taken as positive
     * is exactly the inversion this field exists to catch, and it would be invisible in the report.
     */
    private Polarity polarityOf(CrySLPredicate predicate) {
        Boolean negated = predicate.isNegated();
        if (negated == null) {
            throw new IllegalStateException("CrySLPredicate.isNegated() returned null for '"
                    + predicate.getPredName() + "'; the polarity of a REQUIRES entry cannot be "
                    + "guessed, and defaulting it to POSITIVE would invert the requirement");
        }
        return negated ? Polarity.NEGATED : Polarity.POSITIVE;
    }

    /**
     * The position of an item the façade handed over without one.
     *
     * <p>The façade has no position API at all, so an item's site is the line of the section it was
     * declared in, and the line of the section comes from the EMF route. Where even that is missing
     * — a rule whose parse recovered without a node model for that block — the site is line 1, the
     * file itself. It is never guessed from text: {@link Provenance} is stamped at read time, and
     * recovering positions from emitted text would make the report its own source of truth.
     */
    private Provenance section(String fileName, CryslProvenance provenance,
                               CryslProvenance.Section sectionId) {
        return at(fileName, provenance.lineOf(sectionId).orElse(null), provenance, sectionId);
    }

    private Provenance at(String fileName, Integer line, CryslProvenance provenance,
                          CryslProvenance.Section fallback) {
        if (line != null && line >= 1) {
            return new Provenance(fileName, line);
        }
        Integer sectionLine = provenance.lineOf(fallback).orElse(null);
        return new Provenance(fileName, sectionLine != null && sectionLine >= 1 ? sectionLine : 1);
    }
}
