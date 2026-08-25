package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.metric.ClauseFamily;
import br.unb.cic.rvsec.crysl.core.metric.ClauseVerdict;
import br.unb.cic.rvsec.crysl.core.metric.CountingRule;
import br.unb.cic.rvsec.crysl.core.metric.M3Ceilings;
import br.unb.cic.rvsec.crysl.core.metric.M3Constraints;
import br.unb.cic.rvsec.crysl.core.metric.M3Result;
import br.unb.cic.rvsec.crysl.core.metric.SpecificationIdioms;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.UnrecognizedConstraint;
import br.unb.cic.rvsec.crysl.core.model.UntranslatableConstraint;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.mop.MopLifter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * M3 over the real corpus: the 24 {@code jca_android} specifications against the upstream oracle.
 *
 * <h2>The stamp, and why it is not the one the task list was written against</h2>
 *
 * <p>Every number here is measured at {@link #MEASURED_AT}, and that is a different commit from the
 * one the change's targets were pinned at. The pinned stamp is {@code 5fbe8173}; between it and
 * this one, {@code 5bc5c893} rewrote the {@code Arrays.asList(…)} value lists of 13 of the 24
 * specifications — which is <em>exactly</em> M3's subject, idiom A. A numerator carried forward from
 * {@code 5fbe8173} would describe a corpus that no longer exists.
 *
 * <p>The denominator is a different matter: it comes from the oracle, which lives in another
 * repository on its own clock, and the value-list rewrite could not touch it. So the two halves of
 * the fraction carry two stamps, and this class keeps them apart on purpose.
 *
 * <p>A disagreement between these numbers and the change's pinned targets is a <strong>finding</strong>
 * — reported with both measurements and both counting rules — and never a reason to adjust the rule
 * until it agrees (INV-CONF-14).
 */
class M3ConstraintsCorpusTest {

    /**
     * The {@code rvsec} commit the {@code .mop} numerator was measured at.
     *
     * <p>{@code git status --porcelain} over {@code rvsec-mop/src/main/resources} is empty at this
     * commit, so on-disk is committed and the stamp describes the bytes that were read.
     */
    private static final String MEASURED_AT = "86a8f178";

    /**
     * Pairing by declared type, from {@code docs/20260824_mapeamento_mop_crysl.md} §2.2.
     *
     * <p>Written out rather than computed, for two reasons. Pairing by file name is forbidden and
     * ambiguous — {@code SecretKeySpec.mop} matches {@code SecretKey.crysl} and {@code
     * SecretKeySpec.crysl}, both of which exist, and it is the type of the specification's parameter
     * that separates them. And this test measures M3, not the pairing: taking the pairing from the
     * component under construction would make a defect in it invisible here.
     *
     * <p>Two of the 24 specifications have no rule and are absent from this map:
     * {@code IvChainJunction} (a junction, translating no rule) and {@code RandomStringPassword}
     * ({@code String} has no rule).
     */
    private static final Map<String, String> PAIRS = pairs();

    private static Map<String, String> pairs() {
        Map<String, String> map = new LinkedHashMap<>();
        map.put("CipherInputStreamSpec.mop", "CipherInputStream");
        map.put("CipherOutputStreamSpec.mop", "CipherOutputStream");
        map.put("CipherSpec.mop", "Cipher");
        map.put("DHGenParameterSpecSpec.mop", "DHGenParameterSpec");
        map.put("GCMParameterSpecSpec.mop", "GCMParameterSpec");
        map.put("HMACParameterSpecSpec.mop", "HMACParameterSpec");
        map.put("IvParameterSpec.mop", "IvParameterSpec");
        map.put("KeyGeneratorSpec.mop", "KeyGenerator");
        map.put("KeyManagerFactorySpec.mop", "KeyManagerFactory");
        map.put("KeyPairGeneratorSpec.mop", "KeyPairGenerator");
        map.put("KeyPairSpec.mop", "KeyPair");
        map.put("KeyStoreSpec.mop", "KeyStore");
        map.put("MacSpec.mop", "Mac");
        map.put("MessageDigestSpec.mop", "MessageDigest");
        map.put("PBEKeySpecSpec.mop", "PBEKeySpec");
        map.put("PBEParameterSpecSpec.mop", "PBEParameterSpec");
        map.put("SSLContextSpec.mop", "SSLContext");
        map.put("SecretKeySpec.mop", "SecretKey");
        map.put("SecretKeySpecSpec.mop", "SecretKeySpec");
        map.put("SecureRandomSpec.mop", "SecureRandom");
        map.put("SignatureSpec.mop", "Signature");
        map.put("TrustManagerFactorySpec.mop", "TrustManagerFactory");
        return Map.copyOf(map);
    }

    private static Path mopDirectory() {
        return Paths.get("..", "..", "rvsec-mop", "src", "main", "resources", "jca_android")
                .normalize();
    }

    private static Version mopVersion() {
        return new Version("jca_android", new SourceStamp("rvsec", MEASURED_AT, Instant.EPOCH));
    }

    // ── the denominator ───────────────────────────────────────────────────────────────────────

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("8.9: the M3 denominator under R1 is 80 in the 22 paired rules, 119 across all 49")
    void test_denominator_under_r1() throws Exception {
        Path rules = OracleCorpus.cryslRules();

        int all = 0;
        int paired = 0;
        for (Path rule : cryslFiles(rules)) {
            int clauses = CountingRule.countClauses(Files.readString(rule));
            all += clauses;
            if (PAIRS.containsValue(name(rule))) {
                paired += clauses;
            }
        }

        assertEquals(119, all,
                "R1 over the 49 upstream rules, by the text route. " + CountingRule.R1);
        assertEquals(80, paired,
                "R1 over the 22 rules a jca_android specification pairs with. " + CountingRule.R1);
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("8.6/8.9: the text route and the façade route agree, rule by rule")
    void test_the_two_r1_routes_agree() throws Exception {
        Path rules = OracleCorpus.cryslRules();
        CryslLifter lifter = new CryslLifter();
        CryslLifter.CorpusLift lift = lifter.liftCorpus(rules, OracleCorpus.version());

        assertEquals(47, lift.ok(), "the corpus baseline: 47 of 49 rules load with a fresh reader");

        int facade = 0;
        Map<String, int[]> disagreements = new TreeMap<>();
        for (SpecModel model : lift.models()) {
            String simple = simpleName(model.type());
            Path file = rules.resolve(simple + ".crysl");
            if (!Files.exists(file)) {
                continue;
            }
            int byText = CountingRule.countClauses(Files.readString(file));
            int byFacade = model.constraints().size();
            facade += byFacade;
            if (byText != byFacade) {
                disagreements.put(simple, new int[] {byText, byFacade});
            }
        }

        assertTrue(disagreements.isEmpty(),
                "R1 must give the same answer whether it is applied to the text or read off the "
                        + "façade; a rule where it does not is a finding about that rule, not a "
                        + "licence to pick a total. Disagreements (text, façade): " + render(disagreements));
        assertEquals(114, facade,
                "the façade can only count the rules that parse: 119 under R1 minus the 5 clauses "
                        + "of OAEPParameterSpec (2) and SSLEngine (3), which do not load and are "
                        + "recorded as findings about the upstream files (D-08)");
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("8.6: the denominator really does move under another rule — measured, not asserted from memory")
    void test_the_denominator_is_rule_dependent() throws Exception {
        int splittingConjunctions = 0;
        int splittingImplications = 0;
        int splittingConjunctionsPaired = 0;
        int splittingImplicationsPaired = 0;
        for (Path rule : cryslFiles(OracleCorpus.cryslRules())) {
            String section = constraintsSectionOf(Files.readString(rule));
            int conjunctions = countTopLevel(section, "&&");
            int implications = countTopLevel(section, "=>");
            int clauses = CountingRule.countClauses(Files.readString(rule));
            splittingConjunctions += clauses + conjunctions;
            splittingImplications += clauses + implications;
            if (PAIRS.containsValue(name(rule))) {
                splittingConjunctionsPaired += clauses + conjunctions;
                splittingImplicationsPaired += clauses + implications;
            }
        }

        assertEquals(125, splittingConjunctions,
                "R1 plus the 6 top-level '&&' of Cipher.crysl. Under this rule the same corpus "
                        + "answers 125, not 119 — which is why no total may be published without "
                        + "its rule beside it");
        assertEquals(86, splittingConjunctionsPaired, "the same rule over the 22 paired rules");
        assertEquals(145, splittingImplications,
                "R1 plus the 26 implications across 6 rules");
        assertEquals(99, splittingImplicationsPaired, "the same rule over the 22 paired rules");
    }

    /** Occurrences of a two-character operator outside a {@code {…}} value list. */
    private static int countTopLevel(String section, String operator) {
        int depth = 0;
        int count = 0;
        for (int i = 0; i < section.length() - 1; i++) {
            char c = section.charAt(i);
            if (c == '{') {
                depth++;
            } else if (c == '}') {
                depth--;
            } else if (depth == 0 && section.startsWith(operator, i)) {
                count++;
                i++;
            }
        }
        return count;
    }

    // ── the numerator ─────────────────────────────────────────────────────────────────────────

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("8.1/8.3/8.5: the census over jca_android, measured and stamped at " + MEASURED_AT)
    void test_the_census_over_the_paired_corpus() throws Exception {
        List<M3Result> results = run();

        int denominator = results.stream().mapToInt(M3Result::denominator).sum();
        int implemented = results.stream().mapToInt(M3Result::implemented).sum();
        int absent = results.stream().mapToInt(M3Result::absent).sum();
        int refused = results.stream().mapToInt(result -> result.refusals().size()).sum();

        assertEquals(80, denominator, "the denominator is the rule's, under " + CountingRule.R1);
        assertEquals(denominator, implemented + absent + refused,
                "every clause lands in exactly one of implemented, absent or refused");

        assertEquals(31, implemented,
                "the numerator, measured at rvsec@" + MEASURED_AT + " against the upstream oracle. "
                        + "It is lower as a fraction than the historical 25/55 = 45,5 % because the "
                        + "denominator grew: the upstream rules demand more than the abandoned "
                        + "api30 generation did. The specifications did not change to make it drop");
        assertEquals(36, absent, "clauses the specification does not implement");
        assertEquals(13, refused, "clauses this reader declined to decide, of two kinds");

        Map<M3Result.Idiom, Integer> byIdiom = new TreeMap<>();
        for (M3Result result : results) {
            result.byIdiom().forEach((idiom, count) -> byIdiom.merge(idiom, count, Integer::sum));
        }
        assertEquals(12, byIdiom.get(M3Result.Idiom.A_ALIAS_TABLE), "idiom A: the allow-lists");
        assertEquals(7, byIdiom.get(M3Result.Idiom.B_INLINE_ARITHMETIC), "idiom B: inline arithmetic");
        assertEquals(4, byIdiom.get(M3Result.Idiom.C_LOCAL_HELPER),
                "idiom C: the four key-size clauses of KeyPairGenerator, in its validate(int)");
        assertEquals(8, byIdiom.get(M3Result.Idiom.D_EXTERNAL_HELPER),
                "idiom D: the eight transformation clauses of Cipher, in CipherTransformationUtil");
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("8.3/8.5: the 13 refusals split into untranslatable and unrecognised, never absent")
    void test_the_refusals_are_typed_and_counted() throws Exception {
        List<M3Result> results = run();

        Map<String, Integer> untranslatable = new TreeMap<>();
        int unrecognised = 0;
        for (M3Result result : results) {
            for (var refusal : result.refusals()) {
                if (refusal instanceof UntranslatableConstraint clause) {
                    untranslatable.merge(clause.family(), 1, Integer::sum);
                } else if (refusal instanceof UnrecognizedConstraint) {
                    unrecognised++;
                }
            }
        }

        assertEquals(6, untranslatable.get("neverTypeOf"),
                "6 of the corpus's 7 neverTypeOf clauses are in paired rules; the seventh is in "
                        + "PasswordAuthentication, which has no specification");
        assertEquals(3, untranslatable.get("notHardCoded"),
                "3 of 4; the fourth is in PasswordAuthentication");
        assertEquals(1, untranslatable.get("callTo"),
                "Cipher.crysl's callTo[IV] — a liveness obligation with no end-of-trace instant. "
                        + "Its four noCallTo siblings are NOT here: a prohibition is safety");
        assertEquals(3, unrecognised,
                "the three Cipher clauses whose consequent is a noCallTo over ORDER symbols; the "
                        + "reader does not follow the CONSTRAINTS/ORDER coupling and says so");

        M3Ceilings ceilings = M3Constraints.ceilings(results, unpairedRules());
        assertEquals(34, ceilings.subject(),
                "clauses of loaded upstream rules that no specification pairs with. The 5 clauses "
                        + "of the two rules that do not parse are NOT in this number: they are a "
                        + "lift failure, reported on its own line (34 + 5 = 119 - 80)");
        assertEquals(3, ceilings.instrument(),
                "clauses this reader cannot follow. It falls when the reader learns a shape, and "
                        + "the subject ceiling does not — which is why they are never summed");
    }

    // ── the two findings the change asked for by name ─────────────────────────────────────────

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("8.11: a specification faithful to upstream is not accused")
    void test_dh_gen_parameter_spec_is_implemented_and_not_accused() throws Exception {
        M3Result result = censusOf("DHGenParameterSpecSpec.mop");

        assertEquals(1, result.denominator(),
                "DHGenParameterSpec.crysl states one clause, exponentSize < primeSize. The "
                        + "abandoned api30 generation had deleted it, so against that oracle the "
                        + "specification's condition() had no base and was reported MOP-SEM-BASE");
        assertEquals(1, result.implemented(), "the specification implements it");
        assertEquals(0, result.absent());
        assertTrue(result.refusals().isEmpty(),
                "with the upstream rule as the single oracle (D-06), a clause implemented exactly "
                        + "as upstream writes it can never be counted against the specification. "
                        + "The accusation mode the api30 verdicts produced is gone by construction");

        ClauseVerdict row = result.rows().get(0);
        assertEquals(ClauseFamily.ARITHMETIC, row.family());
        assertEquals(java.util.Optional.of(M3Result.Idiom.B_INLINE_ARITHMETIC), row.idiom());
        assertTrue(row.evidence().orElseThrow().contains("exponentSize < primeSize"));
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("8.9: the four api30 MOP-SEM-BASE rows all had a base upstream")
    void test_the_mop_sem_base_rows_re_examined() throws Exception {
        // The four rows of constraint_table.csv at 5fbe8173 that read MOP-SEM-BASE — "the
        // specification checks something the rule does not state" — were an artefact of the oracle,
        // not of the specifications. Each is re-examined here against the rule the upstream states.
        assertEquals(1, censusOf("DHGenParameterSpecSpec.mop").implemented(),
                "row 2 of 4: DHGenParameterSpec.crysl:15 states exponentSize < primeSize");
        assertEquals(3, censusOf("IvParameterSpec.mop").implemented(),
                "row 3 of 4: IvParameterSpec.crysl:17-19 states all three offset/length clauses, "
                        + "and the specification implements all three");
        assertEquals(2, censusOf("SecretKeySpecSpec.mop").implemented(),
                "row 4 of 4: SecretKeySpec.crysl:18 states the keyAlgorithm allow-list the api30 "
                        + "rule had lost, and :19 the length clause");

        M3Result gcm = censusOf("GCMParameterSpecSpec.mop");
        assertEquals(3, gcm.absent(),
                "row 1 of 4: GCMParameterSpec.crysl:19-21 does state the offset/length clauses, so "
                        + "the api30 verdict 'no base' was wrong about the rule. The specification "
                        + "has since deleted those conjuncts on a measured argument, so today they "
                        + "are absent — a different verdict, reached for a different reason");
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("historical reconciliation with constraint_table.csv — labelled, not asserted as the vector")
    void test_reconciliation_with_the_committed_table() throws Exception {
        // The committed table is human judgement, re-anchored to .crysl by the gh104 lineage. It is
        // read here as history, never as the calibration vector: the component remeasures. The
        // arithmetic below is the whole difference, itemised, so that a change on either side fails
        // loudly with a reason instead of drifting.
        List<M3Result> results = run();
        int implemented = results.stream().mapToInt(M3Result::implemented).sum();

        int humanImplemented = 24;   // 22 IGUAL + 2 MOP-MAIS-PERMISSIVO
        int cipherNotDerived = 8;    // the table declined a verdict on 14 Cipher rows; 8 are idiom D
        int ivLenGreaterThanZero = 1; // the table called it unimplemented; the spec writes len >= 0
        int gcmDeleted = 2;          // the table called two GCM clauses IGUAL; the spec deleted them

        assertEquals(implemented,
                humanImplemented + cipherNotDerived + ivLenGreaterThanZero - gcmDeleted,
                "the component's 31 against the table's 24, itemised: +8 Cipher clauses the table "
                        + "left NAO-DERIVADO and this census routes to idiom D; +1 IvParameterSpec "
                        + "len > 0, which the specification implements as len >= 0 (weaker, and the "
                        + "row carries the matched text so the weakening is visible); -2 "
                        + "GCMParameterSpec clauses the table marks IGUAL that the specification "
                        + "deleted, with its reason written in its own comment");
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("8.4: the families api30 erased do occur upstream, in the numbers their route assumes")
    void test_the_erased_families_occur_upstream() throws Exception {
        // Counted over the CONSTRAINTS sections of the 49 upstream rules as textual occurrences,
        // which is a different rule from R1 and is stated as such: R1 counts clauses, and one clause
        // can carry three instanceOf and two transformation parts. The routes ClauseFamily declares
        // rest on these numbers, so they are asserted rather than quoted.
        Map<String, Integer> occurrences = constraintOccurrences();

        assertEquals(4, occurrences.get("instanceOf["),
                "instanceOf, all four in Cipher.crysl. api30 had erased the family; the route is a "
                        + "runtime instanceof, which is exact — the dynamic monitor is stronger "
                        + "than the static analyser here, so its absence is a real absence");
        assertEquals(26, occurrences.get("alg(") + occurrences.get("mode(")
                        + occurrences.get("pad("),
                "the transformation string parts (11 alg + 10 mode + 5 pad), all in Cipher.crysl. "
                        + "api30 had erased them; the route is idiom D, the splitting helper");
        assertEquals(4, occurrences.get("notHardCoded["),
                "notHardCoded, in 4 rules. api30 had erased it; the route is "
                        + "Unknown{UntranslatableConstraint}, like neverTypeOf — a property of the "
                        + "source code, not of a value");

        assertEquals(7, occurrences.get("neverTypeOf["), "the seven neverTypeOf, across 5 rules");
        assertEquals(4, occurrences.get("noCallTo["), "four prohibitions — safety, and they map");
        assertEquals(1, occurrences.get("callTo["),
                "exactly one obligation, Cipher.crysl's callTo[IV] — and this count needs no "
                        + "correction for its four noCallTo siblings, because CrySL capitalises the "
                        + "C in noCallTo and 'callTo[' is therefore not a substring of 'noCallTo['. "
                        + "The asymmetry is the whole point: 4 map and 1 does not");
    }

    private static Map<String, Integer> constraintOccurrences() throws IOException {
        Map<String, Integer> occurrences = new TreeMap<>();
        for (String marker : List.of("instanceOf[", "neverTypeOf[", "notHardCoded[", "noCallTo[",
                "callTo[", "alg(", "mode(", "pad(")) {
            occurrences.put(marker, 0);
        }
        for (Path rule : cryslFiles(OracleCorpus.cryslRules())) {
            String section = constraintsSectionOf(Files.readString(rule));
            for (String marker : occurrences.keySet()) {
                int count = 0;
                int from = 0;
                while ((from = section.indexOf(marker, from)) >= 0) {
                    count++;
                    from += marker.length();
                }
                occurrences.merge(marker, count, Integer::sum);
            }
        }
        return occurrences;
    }

    /** The {@code CONSTRAINTS} section, comments removed — the same cut R1 makes. */
    private static String constraintsSectionOf(String source) {
        List<String> sections = List.of("SPEC", "OBJECTS", "EVENTS", "ORDER", "CONSTRAINTS",
                "REQUIRES", "ENSURES", "NEGATES", "FORBIDDEN");
        StringBuilder collected = new StringBuilder();
        boolean inside = false;
        for (String raw : source.replaceAll("(?s)/\\*.*?\\*/", "").split("\r?\n", -1)) {
            String line = raw.replaceAll("//.*", "");
            String head = line.strip().split("\\s+", 2)[0];
            if (!line.isEmpty() && !Character.isWhitespace(line.charAt(0)) && sections.contains(head)) {
                inside = "CONSTRAINTS".equals(head);
                continue;
            }
            if (inside) {
                collected.append(line).append('\n');
            }
        }
        return collected.toString();
    }

    // ── the alias table, which is part of the semantics of idiom A ────────────────────────────

    @Test
    @DisplayName("8.2: the alias-table dependency, and how unevenly it is distributed")
    void test_alias_table_rows_per_service() throws Exception {
        Map<String, Integer> rows = aliasTableRows();

        assertEquals(169, rows.values().stream().mapToInt(Integer::intValue).sum(),
                "the table as it stands. It was 158 until task 11.6 (D-15) added the eleven "
                        + "multi-line Alg.Alias registrations a single-line extraction had missed, "
                        + "so any number published from it needs the commit beside it");

        assertEquals(61, rows.getOrDefault("Signature", 0), "Signature carries the most aliases");
        assertEquals(34, rows.getOrDefault("Cipher", 0), "then Cipher");
        assertEquals(24, rows.getOrDefault("Mac", 0), "then Mac");

        for (String service : List.of("KeyStore", "SSLContext", "SecureRandom", "KeyManagerFactory",
                "SecretKeySpec")) {
            assertEquals(0, rows.getOrDefault(service, 0),
                    service + " has no alias row at all: its platform names come from providers "
                            + "this table does not extract (AndroidKeyStore, Bouncy Castle), or "
                            + "from behavioural equivalence rather than an Alg.Alias registration");
        }
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("8.2: every idiom-A clause says whether the alias table widens it")
    void test_every_allow_list_clause_declares_its_alias_dependency() throws Exception {
        List<M3Result> results = run();
        Map<String, Integer> rows = aliasTableRows();

        List<String> withDependency = new ArrayList<>();
        List<String> withoutDependency = new ArrayList<>();
        for (M3Result result : results) {
            for (ClauseVerdict row : result.rows()) {
                if (row.idiom().orElse(null) != M3Result.Idiom.A_ALIAS_TABLE) {
                    continue;
                }
                (row.widenedByAliasTable() ? withDependency : withoutDependency)
                        .add(result.specification());
            }
        }

        assertEquals(11, withDependency.size(),
                "eleven of the twelve allow-lists are read through ConscryptAliasTable.matches(…), "
                        + "so a list textually identical to the rule's is in fact more permissive — "
                        + "which a literal extractor would report as conformant");
        assertEquals(List.of("GCMParameterSpecSpec.mop"), withoutDependency,
                "the tag-length list is the one allow-list of the set compared literally");

        // The dependency and its weight are different facts, and the corpus separates them: three
        // specifications consult a service the table has no row for, so the call is a dependency
        // with no effect. Recording only "uses the table" would overstate those three; recording
        // only the row counts would miss them entirely.
        assertEquals(0, rows.getOrDefault("KeyStore", 0));
        assertTrue(withDependency.contains("KeyStoreSpec.mop"),
                "KeyStoreSpec calls matches(\"KeyStore\", …) against zero rows");
    }

    // ── plumbing ──────────────────────────────────────────────────────────────────────────────

    private List<M3Result> run() throws Exception {
        List<M3Result> results = new ArrayList<>();
        for (String specification : PAIRS.keySet()) {
            results.add(censusOf(specification));
        }
        return results;
    }

    private M3Result censusOf(String specification) throws Exception {
        Path rules = OracleCorpus.cryslRules();
        Path mopFile = mopDirectory().resolve(specification);
        SpecModel rule = new CryslLifter()
                .lift(rules.resolve(PAIRS.get(specification) + ".crysl"), OracleCorpus.version());
        SpecModel mop = new MopLifter().lift(mopFile, mopVersion());
        return M3Constraints.census(mop, rule,
                SpecificationIdioms.of(specification, Files.readString(mopFile)));
    }

    private List<SpecModel> unpairedRules() throws Exception {
        CryslLifter.CorpusLift lift = new CryslLifter()
                .liftCorpus(OracleCorpus.cryslRules(), OracleCorpus.version());
        List<SpecModel> unpaired = new ArrayList<>();
        for (SpecModel model : lift.models()) {
            if (!PAIRS.containsValue(simpleName(model.type()))) {
                unpaired.add(model);
            }
        }
        return unpaired;
    }

    /**
     * The alias table, counted from the class the monitors actually run.
     *
     * <p>Read from {@code rvsec-core} in the working tree rather than from the auditable CSV beside
     * it: the CSV is the registry, the class is what a woven monitor consults, and it is the class
     * whose rows widen a specification's allow-list.
     */
    private static Map<String, Integer> aliasTableRows() throws IOException {
        Path table = Paths.get("..", "..", "rvsec-core", "src", "main", "java", "br", "unb", "cic",
                "mop", "jca", "util", "ConscryptAliasTable.java").normalize();
        assertTrue(Files.isReadable(table), "the alias table was not found at " + table.toAbsolutePath());
        Map<String, Integer> rows = new TreeMap<>();
        Matcher matcher = Pattern.compile("^\\s*\\{\\s*\"([A-Za-z]+)\"", Pattern.MULTILINE)
                .matcher(Files.readString(table));
        while (matcher.find()) {
            rows.merge(matcher.group(1), 1, Integer::sum);
        }
        assertFalse(rows.isEmpty(), "no rows were recognised in " + table.toAbsolutePath());
        return rows;
    }

    private static List<Path> cryslFiles(Path directory) throws IOException {
        try (var entries = Files.list(directory)) {
            return entries.filter(path -> path.getFileName().toString().endsWith(".crysl"))
                    .sorted().toList();
        }
    }

    private static String name(Path rule) {
        String file = rule.getFileName().toString();
        return file.substring(0, file.length() - ".crysl".length());
    }

    private static String simpleName(String type) {
        int dot = type.lastIndexOf('.');
        return dot < 0 ? type : type.substring(dot + 1);
    }

    private static String render(Map<String, int[]> disagreements) {
        StringBuilder text = new StringBuilder();
        disagreements.forEach((rule, counts) ->
                text.append(rule).append("=(").append(counts[0]).append(",").append(counts[1])
                        .append(") "));
        return text.toString();
    }
}
