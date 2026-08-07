package br.unb.cic.rv.validator;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

/**
 * Loads every {@code *-oracle.yaml} under a directory, admits the ones whose
 * provenance makes them usable as ground truth, and enforces the
 * minimum-count gate declared by INV-INS-59.
 *
 * <p>The YAML schema is intentionally simple (no external dep): each file is
 * read as raw text. The {@code name:} top-level key identifies the oracle and
 * the {@code provenance:} block decides admission — see {@link OracleProvenance}.
 * Structural validation of the events themselves lives in
 * {@code TraceComparator}, which evaluates each oracle against captured traces.
 *
 * <p><b>Admission, and why it is here rather than in review.</b> The minimum of
 * three is met by provenance, not by volume and not by lowering the threshold
 * (INV-INS-107). That only holds if an inadmissible file cannot pad the count:
 * before gh100 the loader counted files, so a slot carrying an empty event list
 * and a {@code ground_truth_run: pending} provenance counted exactly as much
 * as a populated, hand-validated oracle. Rejected files are still reported, by
 * name and reason, so a rejection is visible rather than a silent shortfall.
 */
public final class OracleLoader {

    /** Minimum admissible oracle count for the Layer-3 / Layer-4 gate (INV-INS-59). */
    public static final int MINIMUM_ORACLES = 3;

    private OracleLoader() {}

    public static LoadResult load(Path oracleDir) throws IOException {
        List<Path> files = new ArrayList<>();
        if (Files.isDirectory(oracleDir)) {
            try (Stream<Path> ls = Files.list(oracleDir)) {
                ls.filter(Files::isRegularFile)
                  .filter(p -> p.getFileName().toString().endsWith("-oracle.yaml"))
                  .sorted()
                  .forEach(files::add);
            }
        }

        List<Path> admitted = new ArrayList<>();
        Map<String, String> rejected = new LinkedHashMap<>();
        for (Path f : files) {
            OracleProvenance provenance = OracleProvenance.parse(f);
            if (provenance == null) {
                rejected.put(f.getFileName().toString(),
                        "no provenance block — every oracle must declare where its expected "
                                + "events came from (INV-INS-107)");
                continue;
            }
            String why = provenance.rejection();
            if (why != null) {
                rejected.put(f.getFileName().toString(), why);
                continue;
            }
            admitted.add(f);
        }
        return new LoadResult(oracleDir, files, admitted, rejected);
    }

    public static Report report(LoadResult loaded) {
        boolean passed = loaded.admitted.size() >= MINIMUM_ORACLES;
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("oracleDir", loaded.dir.toString());
        metrics.put("oracleFilesFound", loaded.files.size());
        metrics.put("oracleCount", loaded.admitted.size());
        metrics.put("oracleNames", loaded.admitted.stream()
                .map(p -> p.getFileName().toString())
                .toList());
        metrics.put("rejectedOracles", loaded.rejected);
        String msg = passed
                ? "≥" + MINIMUM_ORACLES + " admissible oracles present (INV-INS-59 satisfied)"
                : "only " + loaded.admitted.size() + " admissible oracle(s) of "
                        + loaded.files.size() + " file(s); INV-INS-59 requires ≥"
                        + MINIMUM_ORACLES + " — see validator/oracles/ and the rejection "
                        + "reasons under metrics.rejectedOracles";
        return new Report("oracle-loader", passed, msg, metrics);
    }

    /**
     * @param files    every {@code *-oracle.yaml} found
     * @param admitted those whose provenance makes them usable as ground truth
     * @param rejected file name → why it is inadmissible
     */
    public record LoadResult(Path dir, List<Path> files, List<Path> admitted,
                             Map<String, String> rejected) {

        /** The admissible oracles — what the gate counts. */
        public List<Path> oracles() {
            return admitted;
        }
    }
}
