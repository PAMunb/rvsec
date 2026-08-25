package br.unb.cic.rvsec.crysl.core.emit;

import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.time.Instant;

/**
 * The two stamps every emitter test needs.
 *
 * <p>They are two rather than one on purpose: the specifications come from {@code rvsec} and the
 * oracle from {@code rvsec-cognicrypt}, and a test that used one stamp for both would pass against
 * an emitter that had collapsed them (D-17).
 */
final class Fixtures {

    static final Version MOP = new Version("jca_android",
            new SourceStamp("rvsec", "39b000ce", Instant.parse("2026-08-24T10:00:00Z")));

    static final Version ORACLE = new Version("CrySL-Rules",
            new SourceStamp("rvsec-cognicrypt", "a1b2c3d4", Instant.parse("2026-08-24T10:00:01Z")));

    private Fixtures() {
    }
}
