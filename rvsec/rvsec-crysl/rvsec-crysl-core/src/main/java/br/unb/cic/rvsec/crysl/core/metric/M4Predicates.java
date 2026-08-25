package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.emit.CsvEmitter;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.stream.Collectors;

/**
 * M4: the {@code ENSURES}/{@code REQUIRES}/{@code NEGATES} graph of one specification against the
 * graph of the rule it was paired with, compared by arity, polarity and argument position.
 *
 * <h2>What is compared</h2>
 *
 * <p>Three things, and each of them can fail on its own. <b>Arity</b> is {@code arguments().size()}
 * on both sides: a rule clause of arity 2 implemented over one bound object is a projection, not
 * the clause. <b>Polarity</b> is the field on {@link PredicateRef}: {@code REQUIRES !p} demands the
 * predicate be <em>absent</em> and is neither {@code REQUIRES p} nor {@code NEGATES p}, so a
 * specification that writes one where the rule writes the other is implementing the opposite
 * demand. <b>Argument position</b> is compared by index: names do not carry between the two
 * languages - the rule writes {@code output1} where the specification writes {@code output} - so
 * what a position can be compared by is its declared type, when the caller supplies one, and its
 * index otherwise. Two positions holding the same multiset of types in a different order are an
 * inversion; that is the only permutation this metric can see, and it says so rather than implying
 * it checked more.
 *
 * <h2>Three kinds of edge, and one kind of site that is none of them</h2>
 *
 * <p>An edge is <b>present</b> when a site and a clause pair, <b>absent</b> when the rule states a
 * clause no site of the specification implements, and <b>inverted</b> when the two pair on name and
 * section but disagree on polarity or on argument order. A fourth case exists and is deliberately
 * not folded into any of the three: a site that pairs with no clause at all. It is not an inversion
 * and it is not an absence - the specification writes something the rule does not ask for - and
 * calling it either would put two findings under one name. It gets a row, marked
 * {@link CsvEmitter.Origin#INHERITED}, and stays out of the three lists of {@link M4Result}.
 *
 * <h2>Two vocabularies, side by side</h2>
 *
 * <p>Every row carries the site-level vocabulary of {@code predicate_graph.csv} - {@code verdict}
 * and {@code disposition}, which are about <em>where</em> the predicate is read or written and what
 * was decided about that place - and the clause-level {@link CsvEmitter.Fidelity}, which is about
 * how faithfully the <em>clause</em> behind the site is implemented. There is no bijection between
 * the two: one clause is implemented at several sites and one site translates several clauses.
 * Emitting one in place of the other would replace a manual table with an automatic table that
 * measures something else, which is the whole failure this metric exists to avoid.
 *
 * <h2>Derived and inherited (INV-CONF-15)</h2>
 *
 * <p>{@link CsvEmitter.Origin} is about the fidelity class and nothing else. A row is
 * {@code derived} when the pairing was mechanical - the canonical name rule of
 * {@link PredicateGraph} - and the class follows from arity, polarity and position. It is
 * {@code inherited} when a person supplied the pairing (a declared alias) or the class itself, or
 * when there is no clause for the class to be about. The derived fraction is therefore an honest
 * measure of how much of the manual table this component actually replaced, and it does not rise by
 * feeding the component more human judgement.
 *
 * <h2>No refusals</h2>
 *
 * <p>{@link M4Result#refusals()} is always empty, and that is a decision rather than an omission.
 * The {@code Unknown} taxonomy is closed to five tags (INV-CONF-06) and none of them describes what
 * M4 cannot decide: a site with no clause, a name the canonical rule cannot pair, a position with no
 * declared type. Those are not refusals to read - everything was read - they are places where a
 * class cannot be derived, and the mechanism for that is the origin column. Emitting them under a
 * tag meant for something else would make the refusal counts of the other metrics unreadable.
 *
 * <h2>What is not published</h2>
 *
 * <p>The four parcels of the {@code fiéis + fiação + substrato + cobertura} decomposition are
 * emitted as {@link #DECOMPOSITION} - the structure, with the commit and the derived fraction - and
 * <em>not</em> as four scalars. Three of the four depend on the judgement columns, which is exactly
 * what the derived fraction is still resolving; the substrate parcel is the one that is measurably
 * paid. Scalars are emitted only over rows marked derived, through
 * {@link M4Analysis#derivedScalars()}.
 */
public final class M4Predicates {

    /**
     * The rule behind every count this metric emits.
     *
     * <p>It travels with the numbers because the same corpus yields different totals under
     * different rules - rows per site against rows per clause, canonical matching against declared
     * aliases - and an aggregate without its rule is not a measurement (INV-CONF-02).
     */
    public static final String COUNTING_RULE =
            "one row per predicate site of the specification, plus one row per rule clause no site "
                    + "implements; sites are paired with clauses by section and by "
                    + PredicateGraph.CANONICAL_RULE + "; an edge is present when a site and a "
                    + "clause pair, inverted when they pair but disagree on polarity or argument "
                    + "order, absent when a clause pairs with no site; a site that pairs with no "
                    + "clause is none of the three and is counted only as a row; "
                    + "fidelity is derived only where the pairing was mechanical, and the "
                    + "substrate trajectory of jca_android is " + SubstrateTrajectory.rendered()
                    + " under: " + SubstrateTrajectory.COUNTING_RULE;

    /**
     * The four parcels of the M4 decomposition, as structure.
     *
     * <p>Published without three of their four scalars on purpose. The structure is right and the
     * substrate parcel is measurably paid; the other three rest on the judgement columns, and a
     * scalar computed over inherited rows would look like a measurement of the corpus while being a
     * measurement of somebody's table.
     */
    public static final List<Parcel> DECOMPOSITION = List.of(
            new Parcel("fiéis", "clauses implemented as the rule states them", false,
                    "depends on the fidelity column; a scalar is emitted only over rows marked "
                            + "derived, through M4Analysis.derivedScalars()"),
            new Parcel("fiação", "clauses whose producer and consumer are actually wired", false,
                    "depends on the fidelity column and on position types the current lift does "
                            + "not supply; the graph publishes the wiring it can see instead"),
            new Parcel("substrato", "what the predicate substrate costs the specification", true,
                    "measurably paid: the jca_android signature is " + "0/70/21"
                            + " at 5fbe8173 and unchanged at the head this was written against, "
                            + "under " + SubstrateTrajectory.COUNTING_RULE),
            new Parcel("cobertura", "clauses of the rule the specification reaches at all", false,
                    "depends on the fidelity column; the absent edges are emitted individually so "
                            + "a reader can count them under a rule of their own"));

    /**
     * One parcel of the decomposition.
     *
     * @param name    the parcel as the decomposition names it
     * @param meaning what it is, in English
     * @param paid    whether it is measurable today
     * @param status  why it is or is not, stated in full
     */
    public record Parcel(String name, String meaning, boolean paid, String status) {
    }

    /**
     * The human input M4 accepts, and the only place a judgement can enter a row.
     *
     * <p>It is a parameter rather than a table baked into the component because the whole point of
     * the origin column is that a reader can tell derivation from judgement. A default alias map
     * shipped in code would make every row look derived while half of them rested on somebody's
     * pairing.
     *
     * @param aliases           specification predicate name to rule predicate name, for the pairs
     *                          the canonical rule cannot make - {@code MACED} to {@code macced},
     *                          {@code GENERATED_PUBLIC_KEY} to {@code generatedPubkey}
     * @param fidelityBySite    a fidelity class a person decided, keyed by the site's provenance
     */
    public record Judgements(Map<String, String> aliases,
                             Map<Provenance, CsvEmitter.Fidelity> fidelityBySite) {

        public Judgements {
            aliases = Map.copyOf(aliases);
            fidelityBySite = Map.copyOf(fidelityBySite);
        }

        /** No aliases and no supplied classes: everything this run marks derived, it derived. */
        public static Judgements empty() {
            return new Judgements(Map.of(), Map.of());
        }
    }

    /** What the comparison found about one pairing. */
    public enum Edge {
        /** A site and a clause pair, on name, section, polarity and argument order. */
        PRESENT,
        /** The rule states a clause no site of the specification implements. */
        ABSENT,
        /** They pair on name and section and disagree on polarity or on argument order. */
        INVERTED,
        /** A site of the specification pairs with no clause of the rule. */
        UNPAIRED
    }

    /**
     * One site, compared.
     *
     * @param site     the specification's site
     * @param edge     what the comparison found
     * @param clause   the rule clause it paired with, when it paired with one
     * @param fidelity the clause-level class
     * @param origin   whether this metric derived that class or inherited it
     * @param reason   what decided the row, stated in full
     */
    public record ComparedSite(PredicateSiteFacts site, Edge edge, Optional<PredicateRef> clause,
                               CsvEmitter.Fidelity fidelity, CsvEmitter.Origin origin,
                               String reason) {
    }

    /**
     * A rule clause the specification's substrate limits, whatever the specification says.
     *
     * @param clause    the rule clause
     * @param substrate the substrate the specification's file is written on
     * @param ceiling   the limit and its reason
     */
    public record SubstrateCeiling(PredicateRef clause, PredicateSubstrate substrate,
                                   PredicateSubstrate.Ceiling ceiling) {
    }

    /**
     * Everything M4 produced for one specification: the aggregate, the rows behind it, and the
     * findings the aggregate has no field for.
     *
     * <p>The canonical constructor is where the aggregate is held to its own rows. {@link M4Result}
     * carries two row <em>counts</em> and no rows; the emitter is handed the rows and never sees the
     * counts. Nothing joined the two before this, so an aggregate could disagree with the table
     * printed beneath it and no build would notice - which is the failure INV-CONF-15 is about, one
     * level down from the caveat.
     *
     * @param result   the aggregate, as the report carries it
     * @param rows     the rows handed to the emitter, one per site plus one per absent clause
     * @param compared the per-site comparison behind the site rows
     * @param bridges  producer/consumer pairs the graph shows are not about the same object
     * @param ceilings rule clauses the specification's substrate limits
     */
    public record M4Analysis(M4Result result, List<CsvEmitter.M4Row> rows,
                             List<ComparedSite> compared, List<PropagationBridge> bridges,
                             List<SubstrateCeiling> ceilings) {

        public M4Analysis {
            Objects.requireNonNull(result, "M4Analysis.result is mandatory");
            rows = List.copyOf(rows);
            compared = List.copyOf(compared);
            bridges = List.copyOf(bridges);
            ceilings = List.copyOf(ceilings);

            long derived = rows.stream()
                    .filter(row -> row.origin() == CsvEmitter.Origin.DERIVED)
                    .count();
            long inherited = rows.size() - derived;
            if (result.derivedRows() != derived || result.inheritedRows() != inherited) {
                throw new IllegalStateException("M4 aggregate disagrees with its own rows for "
                        + result.specification() + ": the aggregate says " + result.derivedRows()
                        + " derived and " + result.inheritedRows() + " inherited, the "
                        + rows.size() + " rows handed to the emitter say " + derived + " and "
                        + inherited + ". An aggregate that does not describe the table printed "
                        + "beneath it is the failure INV-CONF-15 exists to prevent");
            }
        }

        /**
         * The share of rows whose fidelity class this metric derived.
         *
         * <p>Published beside every aggregate because it is the honest measure of how much of the
         * manual table has actually been replaced. It rises when the comparison gets better and not
         * when the component is handed more judgement.
         */
        public double derivedFraction() {
            return rows.isEmpty() ? 0.0 : (double) result.derivedRows() / rows.size();
        }

        /**
         * The fidelity census, over derived rows only.
         *
         * <p>Restricted on purpose: a census that summed derived and inherited rows would publish a
         * scalar about the corpus that is partly a scalar about somebody's table, which is what the
         * four parcels are waiting on.
         */
        public Map<CsvEmitter.Fidelity, Long> derivedScalars() {
            Map<CsvEmitter.Fidelity, Long> census = new EnumMap<>(CsvEmitter.Fidelity.class);
            for (CsvEmitter.Fidelity fidelity : CsvEmitter.Fidelity.values()) {
                census.put(fidelity, 0L);
            }
            for (CsvEmitter.M4Row row : rows) {
                if (row.origin() == CsvEmitter.Origin.DERIVED) {
                    census.merge(row.fidelity(), 1L, Long::sum);
                }
            }
            return Map.copyOf(census);
        }
    }

    /**
     * Compare one specification's predicate graph with one rule's.
     *
     * @param specification the {@code .mop} file name, as {@code predicate_graph.csv} names it
     * @param rule          the {@code .crysl} file name it was paired with, by declared type
     * @param sites         the specification's predicate sites, in file order
     * @param ruleModel     the lifted rule
     * @param corpus        the graph over every specification being compared, for the reachability
     *                      questions that are not local to one file
     * @param judgements    the human input, or {@link Judgements#empty()}
     */
    public M4Analysis compare(String specification, String rule, List<PredicateSiteFacts> sites,
                              SpecModel ruleModel, PredicateGraph corpus, Judgements judgements) {
        Map<PredicateSiteFacts.Section, Map<String, List<PredicateRef>>> clauses =
                indexClauses(ruleModel);
        Map<String, String> ruleObjects = objectTypes(ruleModel);
        Map<String, Integer> bucketSizes = bucketSizes(sites);
        Map<String, Integer> seen = new LinkedHashMap<>();
        Set<PredicateRef> matched = new LinkedHashSet<>();

        List<ComparedSite> compared = new ArrayList<>(sites.size());
        List<CsvEmitter.M4Row> rows = new ArrayList<>();
        List<PredicateRef> present = new ArrayList<>();
        List<PredicateRef> inverted = new ArrayList<>();

        for (PredicateSiteFacts site : sites) {
            String bucket = bucketKey(site);
            int index = seen.merge(bucket, 1, Integer::sum) - 1;
            ComparedSite comparison = compareSite(site, clauses, ruleObjects, judgements,
                    bucketSizes.getOrDefault(bucket, 1), index, matched);
            compared.add(comparison);
            rows.add(row(comparison, corpus));
            switch (comparison.edge()) {
                case PRESENT -> present.add(site.ref());
                case INVERTED -> inverted.add(site.ref());
                default -> {
                    // UNPAIRED is none of the three edges and ABSENT is never a site's verdict.
                }
            }
        }

        List<PredicateSubstrate> substrates = substratesOf(sites);
        List<SubstrateCeiling> ceilings = ceilings(ruleModel, substrates);
        List<PredicateRef> absent = new ArrayList<>();
        for (PredicateRef clause : allClauses(ruleModel)) {
            if (matched.contains(clause)) {
                continue;
            }
            absent.add(clause);
            rows.add(absenceRow(specification, clause, substrates));
        }

        long derived = rows.stream()
                .filter(row -> row.origin() == CsvEmitter.Origin.DERIVED)
                .count();
        M4Result result = new M4Result(specification, rule, present, absent, inverted,
                (int) derived, rows.size() - (int) derived, List.<Unknown>of(), COUNTING_RULE);
        List<PropagationBridge> bridges = corpus.bridges().stream()
                .filter(bridge -> bridge.producer().specification().equals(specification)
                        || bridge.consumer().specification().equals(specification))
                .toList();
        return new M4Analysis(result, rows, compared, bridges, ceilings);
    }

    // ── comparison ────────────────────────────────────────────────────────────────────────────

    private ComparedSite compareSite(PredicateSiteFacts site,
                                     Map<PredicateSiteFacts.Section, Map<String, List<PredicateRef>>> clauses,
                                     Map<String, String> ruleObjects, Judgements judgements,
                                     int bucketSize, int index, Set<PredicateRef> matched) {
        Map<String, List<PredicateRef>> section =
                clauses.getOrDefault(site.section(), Map.of());
        List<PredicateRef> candidates =
                section.getOrDefault(PredicateGraph.canonical(site.predicate()), List.of());
        boolean viaAlias = false;
        if (candidates.isEmpty()) {
            String alias = judgements.aliases().get(site.predicate());
            if (alias != null) {
                candidates = section.getOrDefault(PredicateGraph.canonical(alias), List.of());
                viaAlias = !candidates.isEmpty();
            }
        }

        if (candidates.isEmpty()) {
            CsvEmitter.Fidelity supplied = judgements.fidelityBySite().get(site.ref().site());
            return new ComparedSite(site, Edge.UNPAIRED, Optional.empty(),
                    supplied == null ? CsvEmitter.Fidelity.AUSENTE : supplied,
                    CsvEmitter.Origin.INHERITED,
                    "no clause named '" + site.predicate() + "' in the rule's " + site.section()
                            + " section, under " + PredicateGraph.CANONICAL_RULE + ". The "
                            + "specification writes something the rule does not ask for, which is "
                            + "neither an inversion nor an absence. The fidelity vocabulary "
                            + "describes a clause and there is none here, so this row's class is "
                            + (supplied == null ? "not derived" : "the one a person supplied"));
        }

        List<PredicateRef> samePolarity = candidates.stream()
                .filter(clause -> clause.polarity() == site.ref().polarity())
                .toList();
        if (samePolarity.isEmpty()) {
            PredicateRef clause = candidates.get(0);
            matched.add(clause);
            return new ComparedSite(site, Edge.INVERTED, Optional.of(clause),
                    CsvEmitter.Fidelity.AUSENTE, origin(viaAlias),
                    "the rule states " + render(clause) + " and the site is "
                            + site.polarityCsv() + ": the specification demands the opposite of "
                            + "what the rule demands. The clause the rule states is not "
                            + "implemented and what is implemented is its inverse; the four-class "
                            + "vocabulary has no cell for an inversion, so the class is AUSENTE "
                            + "and the inverted edge is the finding");
        }

        PredicateRef clause = samePolarity.get(Math.min(index, samePolarity.size() - 1));
        Optional<String> permutation = permutation(site, clause, ruleObjects);
        if (permutation.isPresent()) {
            matched.add(clause);
            return new ComparedSite(site, Edge.INVERTED, Optional.of(clause),
                    CsvEmitter.Fidelity.AUSENTE, origin(viaAlias), permutation.get());
        }

        if (samePolarity.size() > 1 && bucketSize == 1) {
            matched.addAll(samePolarity);
            return new ComparedSite(site, Edge.PRESENT, Optional.of(clause),
                    CsvEmitter.Fidelity.CONFLADO, origin(viaAlias),
                    "the rule states " + samePolarity.size() + " clauses of '" + clause.name()
                            + "' in this section - " + samePolarity.stream()
                                    .map(M4Predicates::render).collect(Collectors.joining("; "))
                            + " - and the specification has one site for all of them, so the site "
                            + "merges them into one check");
        }

        matched.add(clause);
        Optional<PredicateSubstrate.Ceiling> ceiling = site.substrate().ceiling(site.ref());
        if (ceiling.isPresent()
                && ceiling.get().kind() == PredicateSubstrate.Ceiling.Kind.DEGRADED) {
            return new ComparedSite(site, Edge.PRESENT, Optional.of(clause),
                    CsvEmitter.Fidelity.PROJETADO, origin(viaAlias),
                    "the site pairs with " + render(clause) + " and states it under a substrate "
                            + "limit: " + ceiling.get().reason());
        }
        if (clause.arguments().size() != site.arity()) {
            return new ComparedSite(site, Edge.PRESENT, Optional.of(clause),
                    CsvEmitter.Fidelity.PROJETADO, origin(viaAlias),
                    "the rule states " + render(clause) + " at arity " + clause.arguments().size()
                            + " and the site states it at arity " + site.arity() + ", so the "
                            + "specification implements a projection of the clause"
                            + (site.arity() > clause.arguments().size()
                                    ? " over more positions than the rule constrains" : ""));
        }
        return new ComparedSite(site, Edge.PRESENT, Optional.of(clause), CsvEmitter.Fidelity.FIEL,
                origin(viaAlias),
                "the site and " + render(clause) + " agree on arity " + site.arity()
                        + ", on polarity " + site.polarityCsv() + " and on every argument position "
                        + "the two sides both declare a type for");
    }

    /**
     * The one argument-position disagreement this metric can decide: the same multiset of declared
     * types, in a different order.
     *
     * <p>Argument <em>names</em> do not carry between the two languages - the rule writes
     * {@code output1} where the specification writes {@code output} - so a positional comparison
     * over names would call every clause inverted. Types are the positional evidence, and both
     * sides have them: the caller supplies the site's, and the rule's come from its own
     * {@code OBJECTS} section, where each argument name is declared with a type.
     *
     * <p>Only a permutation is reported, never a plain mismatch. The two type vocabularies are not
     * the same vocabulary - one file writes {@code Key} where the other writes
     * {@code javax.crypto.SecretKey} - so a difference at one position is as likely to be a naming
     * difference as an error. Equal multisets in a different order cannot be explained that way,
     * which is why that is the case this metric is willing to call inverted.
     */
    private static Optional<String> permutation(PredicateSiteFacts site, PredicateRef clause,
                                                Map<String, String> ruleObjects) {
        List<String> written = simpleTypes(site.argumentTypes());
        List<String> declared = simpleTypes(clause.arguments().stream()
                .map(argument -> ruleObjects.getOrDefault(argument, ""))
                .toList());
        if (written.size() < 2 || written.size() != declared.size()) {
            return Optional.empty();
        }
        if (written.stream().anyMatch(type -> !PredicateGraph.informativeType(type))
                || declared.stream().anyMatch(type -> !PredicateGraph.informativeType(type))) {
            return Optional.empty();
        }
        if (written.equals(declared)) {
            return Optional.empty();
        }
        List<String> writtenSorted = written.stream().sorted().toList();
        List<String> declaredSorted = declared.stream().sorted().toList();
        if (!writtenSorted.equals(declaredSorted)) {
            return Optional.empty();
        }
        return Optional.of("the site and " + render(clause) + " bind the same types in a different "
                + "order: the rule declares " + declared + " by position and the site binds "
                + written + ". A predicate read at the wrong position is read about the wrong "
                + "object, and no naming difference between the two type vocabularies can produce "
                + "equal multisets in a different order");
    }

    private static List<String> simpleTypes(List<String> types) {
        return types.stream().map(PredicateGraph::simpleName).toList();
    }

    /** The rule's {@code OBJECTS} section as name to declared type. */
    private static Map<String, String> objectTypes(SpecModel rule) {
        Map<String, String> types = new LinkedHashMap<>();
        rule.objects().forEach(object -> types.put(object.name(), object.type()));
        return types;
    }

    private static CsvEmitter.Origin origin(boolean viaAlias) {
        return viaAlias ? CsvEmitter.Origin.INHERITED : CsvEmitter.Origin.DERIVED;
    }

    // ── rows ──────────────────────────────────────────────────────────────────────────────────

    private CsvEmitter.M4Row row(ComparedSite comparison, PredicateGraph corpus) {
        PredicateSiteFacts site = comparison.site();
        return new CsvEmitter.M4Row(site.specification(), site.event(), site.siteKind().csv(),
                site.polarityCsv(), "", String.valueOf(site.arity()), site.predicate(),
                String.join("|", site.argumentTypes()), splitter(site),
                comparison.clause().map(M4Predicates::render).orElse(""),
                site.substrate().mechanism(), verdict(site), disposition(comparison, corpus),
                comparison.reason(), site.siteKind().automatonMembership(), comparison.fidelity(),
                comparison.origin());
    }

    private CsvEmitter.M4Row absenceRow(String specification, PredicateRef clause,
                                        List<PredicateSubstrate> substrates) {
        String reason = "the rule states " + render(clause)
                + " and no site of this specification implements it";
        for (PredicateSubstrate substrate : substrates) {
            Optional<PredicateSubstrate.Ceiling> ceiling = substrate.ceiling(clause);
            if (ceiling.isPresent()) {
                reason = reason + "; " + ceiling.get().reason()
                        + ". That is a property of the substrate this file is written on, not of "
                        + "the specification's author";
            }
        }
        return new CsvEmitter.M4Row(specification, "", "",
                clause.polarity().name().toLowerCase(java.util.Locale.ROOT), "",
                String.valueOf(clause.arguments().size()), clause.name(), "", "", render(clause),
                "", "", "absent", reason, "n/a", CsvEmitter.Fidelity.AUSENTE,
                CsvEmitter.Origin.DERIVED);
    }

    /**
     * The site-level verdict, in the vocabulary the committed table already uses:
     * {@code write:acceptance}, {@code write:body}, {@code read:body}, {@code read-absent:body},
     * {@code negate:body}.
     */
    private static String verdict(PredicateSiteFacts site) {
        String action = switch (site.section()) {
            case ENSURES -> "write";
            case REQUIRES -> site.ref().polarity() == Polarity.NEGATED ? "read-absent" : "read";
            case NEGATES -> "negate";
        };
        String place = site.siteKind() == PredicateSiteFacts.SiteKind.MATCH ? "acceptance" : "body";
        return action + ":" + place;
    }

    /**
     * The site-level disposition, derived only where it is mechanical.
     *
     * <p>{@code omission} is a write nothing in the graph reads: it changes no verdict on any
     * trace. {@code propagation} is a site that translates no clause but sits on a predicate the
     * graph both writes and reads, so all it does is carry the predicate along. The committed table
     * also carries dispositions decided by hand for other reasons; those are not reproduced here,
     * and a disagreement with the committed file is a finding for the calibration gate rather than
     * something to tune this rule until it matches.
     */
    private static String disposition(ComparedSite comparison, PredicateGraph corpus) {
        PredicateSiteFacts site = comparison.site();
        String predicate = site.predicate();
        if (site.section() == PredicateSiteFacts.Section.ENSURES
                && !corpus.hasConsumer(predicate)) {
            return "omission";
        }
        if (comparison.edge() == Edge.UNPAIRED && corpus.hasProducer(predicate)
                && corpus.hasConsumer(predicate)) {
            return "propagation";
        }
        return "";
    }

    /** The argument that applies a splitter, which the committed table detects by {@code .split(}. */
    private static String splitter(PredicateSiteFacts site) {
        return site.ref().arguments().stream()
                .filter(argument -> argument.contains(".split("))
                .findFirst()
                .orElse("");
    }

    // ── rule side ─────────────────────────────────────────────────────────────────────────────

    private static Map<PredicateSiteFacts.Section, Map<String, List<PredicateRef>>> indexClauses(
            SpecModel rule) {
        Map<PredicateSiteFacts.Section, Map<String, List<PredicateRef>>> index =
                new EnumMap<>(PredicateSiteFacts.Section.class);
        index.put(PredicateSiteFacts.Section.ENSURES, group(rule.ensures()));
        index.put(PredicateSiteFacts.Section.REQUIRES, group(rule.requires()));
        index.put(PredicateSiteFacts.Section.NEGATES, group(rule.negates()));
        return index;
    }

    private static Map<String, List<PredicateRef>> group(List<PredicateRef> refs) {
        Map<String, List<PredicateRef>> grouped = new LinkedHashMap<>();
        for (PredicateRef ref : refs) {
            grouped.computeIfAbsent(PredicateGraph.canonical(ref.name()), key -> new ArrayList<>())
                    .add(ref);
        }
        return grouped;
    }

    private static List<PredicateRef> allClauses(SpecModel rule) {
        List<PredicateRef> all = new ArrayList<>(rule.ensures());
        all.addAll(rule.requires());
        all.addAll(rule.negates());
        return all;
    }

    private static List<SubstrateCeiling> ceilings(SpecModel rule,
                                                   List<PredicateSubstrate> substrates) {
        List<SubstrateCeiling> found = new ArrayList<>();
        for (PredicateSubstrate substrate : substrates) {
            for (PredicateRef clause : allClauses(rule)) {
                substrate.ceiling(clause).ifPresent(ceiling ->
                        found.add(new SubstrateCeiling(clause, substrate, ceiling)));
            }
        }
        return found;
    }

    private static List<PredicateSubstrate> substratesOf(List<PredicateSiteFacts> sites) {
        return sites.stream().map(PredicateSiteFacts::substrate).distinct().sorted().toList();
    }

    private static Map<String, Integer> bucketSizes(List<PredicateSiteFacts> sites) {
        Map<String, Integer> sizes = new TreeMap<>();
        for (PredicateSiteFacts site : sites) {
            sizes.merge(bucketKey(site), 1, Integer::sum);
        }
        return sizes;
    }

    private static String bucketKey(PredicateSiteFacts site) {
        return site.section() + "/" + PredicateGraph.canonical(site.predicate());
    }

    /** A clause as the {@code clause} column renders it: {@code Cipher.crysl:137 !encrypted[a, b]}. */
    private static String render(PredicateRef clause) {
        return clause.site() + " " + (clause.polarity() == Polarity.NEGATED ? "!" : "")
                + clause.name() + "[" + String.join(", ", clause.arguments()) + "]";
    }
}
