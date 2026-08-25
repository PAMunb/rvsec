package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Version;
import java.util.List;
import java.util.Objects;

/**
 * Everything one comparison run produced, with the header INV-CONF-02 and INV-CONF-11 require.
 *
 * <p>Both versions are held, never one: the specifications and the oracle come from different git
 * repositories, so a report that carried a single commit would attribute an oracle-derived number
 * to the repository that did not produce it. {@code pairingRule} is in the header because pairing is
 * by declared type and never by file name, and any number published under the older by-name pairing
 * has to be re-stamped before it can be reused.
 *
 * @param mopVersion    corpus and commit of the {@code .mop} side
 * @param oracleVersion corpus and commit of the CrySL side
 * @param pairingRule   how specifications were paired with rules, stated in full
 * @param results       one entry per metric per specification
 */
public record ConformanceReport(Version mopVersion, Version oracleVersion, String pairingRule,
                                List<MetricResult> results) {

    public ConformanceReport {
        Objects.requireNonNull(mopVersion, "ConformanceReport.mopVersion is mandatory (INV-CONF-01)");
        Objects.requireNonNull(oracleVersion, "ConformanceReport.oracleVersion is mandatory (INV-CONF-01)");
        Objects.requireNonNull(pairingRule, "ConformanceReport.pairingRule is mandatory (INV-CONF-11)");
        results = List.copyOf(results);
    }
}
