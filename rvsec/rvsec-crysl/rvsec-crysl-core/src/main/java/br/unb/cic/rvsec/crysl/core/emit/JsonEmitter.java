package br.unb.cic.rvsec.crysl.core.emit;

import br.unb.cic.rvsec.crysl.core.metric.ConformanceReport;
import br.unb.cic.rvsec.crysl.core.metric.M4Result;
import br.unb.cic.rvsec.crysl.core.metric.MetricResult;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonPrimitive;
import com.google.gson.JsonSerializer;
import com.google.gson.TypeAdapter;
import com.google.gson.TypeAdapterFactory;
import com.google.gson.reflect.TypeToken;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonWriter;
import java.io.IOException;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.nio.file.Path;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Serializes the canonical model and the conformance report to JSON.
 *
 * <p><b>This JSON is an output, not an interchange format.</b> The component is one JVM and one
 * process (D-01): the two lifters and the comparison run in the same heap, and a model never
 * travels between processes as text. The rejected alternative was three processes stitched by JSON,
 * and one of its costs was that a read error becomes an exit code instead of a typed
 * {@code Unknown} item - which contradicts the design's own non-negotiable. There is deliberately
 * no reader for what this class writes. Writing one would reintroduce that seam through the back
 * door: the moment a JSON document is parsed back into a model, the wire format acquires a
 * compatibility contract, the state numbering of an automaton becomes a cross-boundary agreement,
 * and lift errors stop being typed. If some future consumer needs the model, it should call the
 * lifters, which are on the classpath.
 *
 * <p>INV-CONF-01 is enforced here rather than trusted: a model or a report whose stamp is absent or
 * a placeholder raises {@link MissingVersionError} and nothing is written. The stamp occupies a
 * fixed position - the first member of every document - so a reader can tell at a glance which
 * corpus state the numbers describe (task 4.7).
 */
public final class JsonEmitter {

    private static final Gson GSON = new GsonBuilder()
            .setPrettyPrinting()
            .disableHtmlEscaping()
            .serializeNulls()
            .registerTypeAdapter(Instant.class,
                    (JsonSerializer<Instant>) (src, type, ctx) -> new JsonPrimitive(src.toString()))
            .registerTypeAdapterFactory(new OptionalAdapterFactory())
            .create();

    /**
     * The document for one lifted specification or rule.
     *
     * @throws MissingVersionError when the model's stamp is absent or a placeholder
     */
    public String toJson(SpecModel model) {
        if (model == null) {
            throw new MissingVersionError(
                    "INV-CONF-01: no model to serialize, so no stamp to serialize it under");
        }
        Map<String, Object> document = new LinkedHashMap<>();
        document.put("stamp", stampOf(model.version(), "model"));
        document.put("model", model);
        return GSON.toJson(document);
    }

    /**
     * The document for one comparison run.
     *
     * <p>Both stamps are in the header (D-17): the specifications and the oracle come from
     * different git repositories, and a single commit beside a rule-derived number would name a
     * repository that did not produce it. The pairing rule is there too, because a number published
     * under the older by-name pairing has to be re-stamped before it can be reused (INV-CONF-11).
     *
     * @throws MissingVersionError    when either stamp is absent or a placeholder
     * @throws IllegalArgumentException when a result reports counts under a blank counting rule
     */
    public String toJson(ConformanceReport report) {
        if (report == null) {
            throw new MissingVersionError(
                    "INV-CONF-01: no report to serialize, so no stamp to serialize it under");
        }
        Map<String, Object> stamp = new LinkedHashMap<>();
        stamp.put("mop", stampOf(report.mopVersion(), "mop"));
        stamp.put("oracle", stampOf(report.oracleVersion(), "oracle"));
        stamp.put("pairingRule", report.pairingRule());

        boolean hasM4 = false;
        for (MetricResult result : report.results()) {
            if (result.countingRule() == null || result.countingRule().isBlank()) {
                throw new IllegalArgumentException("INV-CONF-02: " + result.metric() + " on "
                        + result.specification() + " reports counts and names no counting rule");
            }
            hasM4 |= result instanceof M4Result;
        }

        Map<String, Object> document = new LinkedHashMap<>();
        document.put("stamp", stamp);
        if (hasM4) {
            document.put("m4JudgementCaveat", CsvSchema.M4_JUDGEMENT_CAVEAT);
        }
        document.put("results", report.results());
        return GSON.toJson(document);
    }

    /**
     * Write a rendered document under {@code outputDir}, and answer where it went.
     *
     * <p>The write goes through {@link StampedTable#write}, which is the package's only filesystem
     * access: an emitter that could open a file of its own could publish an unstamped one.
     */
    public Path write(Path outputDir, String fileName, String json) {
        Path target = outputDir.resolve(fileName);
        StampedTable.write(target, json);
        return target;
    }

    private static Map<String, String> stampOf(Version version, String side) {
        if (version == null) {
            throw new MissingVersionError("INV-CONF-01: the " + side + " version is absent");
        }
        SourceStamp source = version.source();
        requireIdentifying(version.corpus(), side + " corpus");
        requireIdentifying(source.repository(), side + " repository");
        requireIdentifying(source.commit(), side + " commit");
        Map<String, String> stamp = new LinkedHashMap<>();
        stamp.put("corpus", version.corpus());
        stamp.put("repository", source.repository());
        stamp.put("commit", source.commit());
        stamp.put("readAt", source.data().toString());
        return stamp;
    }

    /**
     * A stamp field that identifies nothing is an absent stamp.
     *
     * <p>The model's records reject {@code null}, so the reachable failure is the placeholder: an
     * empty commit, or {@code "unknown"}, type-checks and still leaves the reader unable to say
     * which corpus state the document describes.
     */
    private static void requireIdentifying(String value, String what) {
        if (value == null || value.isBlank() || "unknown".equalsIgnoreCase(value.trim())
                || "TODO".equalsIgnoreCase(value.trim())) {
            throw new MissingVersionError("INV-CONF-01: the " + what + " is a placeholder ("
                    + value + "); serialization is refused rather than emitting a document no "
                    + "reader can attribute to a corpus state");
        }
    }

    /**
     * Serializes {@code Optional} as its value or as null.
     *
     * <p>Gson has no built-in support for it, and its reflective fallback would reach into
     * {@code java.util}, which the module system refuses. The model uses {@code Optional} wherever
     * absence is a modelled state - a witness with no harness, a transition with no guard - so this
     * is not an optional convenience.
     */
    private static final class OptionalAdapterFactory implements TypeAdapterFactory {

        @Override
        @SuppressWarnings("unchecked")
        public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type) {
            if (type.getRawType() != Optional.class) {
                return null;
            }
            Type valueType = type.getType() instanceof ParameterizedType parameterized
                    ? parameterized.getActualTypeArguments()[0]
                    : Object.class;
            TypeAdapter<Object> valueAdapter =
                    (TypeAdapter<Object>) gson.getAdapter(TypeToken.get(valueType));
            return (TypeAdapter<T>) new TypeAdapter<Optional<Object>>() {

                @Override
                public void write(JsonWriter out, Optional<Object> value) throws IOException {
                    if (value == null || value.isEmpty()) {
                        out.nullValue();
                    } else {
                        valueAdapter.write(out, value.get());
                    }
                }

                @Override
                public Optional<Object> read(JsonReader in) {
                    throw new UnsupportedOperationException(
                            "D-01: this JSON is an output of the canonical model, never an "
                                    + "interchange format; there is no reader for it on purpose");
                }
            };
        }
    }
}
