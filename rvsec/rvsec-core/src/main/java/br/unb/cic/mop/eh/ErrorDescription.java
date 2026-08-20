package br.unb.cic.mop.eh;

import java.io.Serializable;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ErrorDescription implements Serializable {
	private static final long serialVersionUID = 1L;

	/**
	 * Trailing source position of a stack frame: {@code (<file>:<line>)}.
	 *
	 * <p>
	 * The pattern describes only what a frame reliably <em>ends</em> with, and places no
	 * constraint whatsoever on what precedes it. That is deliberate. A method name cannot be
	 * described by a character class: Kotlin mangles internals and lambdas with {@code $},
	 * inline classes with {@code -}, Robolectric shadows carry {@code $$robo$$}, and backtick
	 * test names contain spaces and even their own parenthesis pairs. Every attempt to
	 * enumerate those shapes fails again the next time a toolchain invents one.
	 *
	 * <p>
	 * Two properties of the group matter. It contains no nested parenthesis, and it must end
	 * in {@code :<digits>} — that is what distinguishes a source position from a parenthesis
	 * belonging to the name, so a well-formed value can never be truncated by accident.
	 */
	static final Pattern FRAME_SUFFIX = Pattern.compile("\\(([^()]+:\\d+)\\)$");

	/**
	 * What a report carries for {@code code} and {@code event} when its message has no envelope.
	 *
	 * <p>
	 * A sentinel and not {@code null}, and not the empty string either. Both new fields are part
	 * of the identity, so their absence has to be a value a reader can see and a
	 * {@code HashSet} can compare: every record of a specification set that emits no envelope
	 * then shares one readable identity, distinguishable at a glance from a record whose event
	 * was actually named.
	 */
	static final String UNSPECIFIED = "UNSPECIFIED";

	/**
	 * The marker that opens the v1 message envelope.
	 *
	 * <p>
	 * Presence of this marker — not presence of the keys — is what decides whether a message is
	 * an envelope. A pre-envelope sentence that happened to contain the characters {@code ev=}
	 * must yield the sentinel, or the two identity eras would not be distinguishable in the
	 * record, which is the one thing a declared discontinuity has to keep true.
	 */
	private static final String ENVELOPE_MARKER = "v=1 ";

	/**
	 * The two identity keys of the envelope, matched on a whitespace boundary and running to the
	 * next space.
	 *
	 * <p>
	 * The boundary is what keeps the free-text {@code msg='...'} tail from supplying a value: the
	 * grammar puts {@code code} and {@code ev} second and third, immediately after the marker, so
	 * the first match is always the record's own. The Python reader that measured the identity
	 * discontinuity applies the same two rules to the same field
	 * ({@code rv-android/scripts/gh104_identity_discontinuity.py}); one grammar read two ways
	 * drifts unless both readers are written from it.
	 */
	private static final Pattern ENVELOPE_CODE = Pattern.compile("(?:^|\\s)code=(\\S+)");

	private static final Pattern ENVELOPE_EVENT = Pattern.compile("(?:^|\\s)ev=(\\S+)");

	private ErrorType type;
	private String spec;
	private String location;
	private String expecting;
	private ErrorSummary summary;

	public ErrorDescription(ErrorType type, String spec, String location) {
		this(type, spec, location, "unknown");
	}

	public ErrorDescription(ErrorType type, String spec, String location, String expecting) {
		this.type = type;
		this.spec = spec;
		this.location = location;
		this.expecting = expecting;
		summary = createErrorSummary();
	}

	public ErrorType getType() {
		return type;
	}

	public String getSpec() {
		return spec;
	}

	public String getLocation() {
		return location;
	}

	public String getExpecting() {
		return expecting;
	}

	public ErrorSummary getErrorSummary() {
		return summary;
	}

	/**
	 * Splits the reported {@link StackTraceElement} string into a class, a method and a source
	 * position.
	 *
	 * <p>
	 * The split is what makes a violation record name <em>where</em> a specification was
	 * violated, and it feeds the {@code (apk, class, method, spec)} key every downstream
	 * analysis uses to identify one unique misuse. When it fails, the fallback below leaves the
	 * whole frame — source position included — in both the class and the method field, so the
	 * line number silently joins that key and a single misuse is counted once per line it
	 * occurs at.
	 *
	 * <p>
	 * The algorithm therefore avoids predicting what a method name looks like. It strips the
	 * trailing {@link #FRAME_SUFFIX} group and splits the remainder at its <b>last</b> dot: the
	 * class part is a dotted path and a method name never contains a dot, so the last dot is
	 * always the separator no matter what the name is made of.
	 *
	 * <p>
	 * The fallback is kept for input that is genuinely not a stack frame — no trailing position
	 * group, or nothing dotted in front of it. Mangling such a value on a guess would be worse
	 * than leaving it intact for a human to read.
	 */
	private ErrorSummary createErrorSummary() {
		String clazz = location;
		String method = location;
		String loc = location;

		Matcher matcher = FRAME_SUFFIX.matcher(location);
		if (matcher.find()) {
			String remainder = location.substring(0, matcher.start());
			int lastDot = remainder.lastIndexOf('.');
			if (lastDot != -1) {
				clazz = remainder.substring(0, lastDot);
				method = remainder.substring(lastDot + 1);
				loc = matcher.group(1);
			}
		}

		return new ErrorSummary(spec, type, clazz, method, loc, envelopeValue(ENVELOPE_CODE),
				envelopeValue(ENVELOPE_EVENT));
	}

	/**
	 * Reads one identity key out of the message envelope, or returns {@link #UNSPECIFIED}.
	 *
	 * <p>
	 * The value is taken from {@code expecting} rather than passed in beside it because that is
	 * where the monitor already puts it: the specification writes one envelope, the collector
	 * appends it to the line whole, and every consumer downstream reads the same characters. A
	 * second channel for the same two values would be a second thing to keep in agreement.
	 */
	private String envelopeValue(Pattern key) {
		if (expecting == null || !expecting.contains(ENVELOPE_MARKER)) {
			return UNSPECIFIED;
		}
		Matcher matcher = key.matcher(expecting);
		return matcher.find() ? matcher.group(1) : UNSPECIFIED;
	}

	@Override
	public boolean equals(Object o) {
		if (this == o)
			return true;
		if (o == null || getClass() != o.getClass())
			return false;
		ErrorDescription that = (ErrorDescription) o;
		return getErrorSummary().equals(that.getErrorSummary());
	}

	/**
	 * Hashes exactly what {@link #equals(Object)} compares — the {@link ErrorSummary}, and
	 * nothing else.
	 *
	 * <p>
	 * Every other field is excluded, including {@code location}. It is tempting to keep the raw
	 * location for hash spread on the grounds that the summary is derived from it, but that
	 * argument requires {@code createErrorSummary} to be injective and it is not: {@code "F:1"}
	 * takes the fallback and lands in all three summary fields, while {@code "F:1.F:1(F:1)"}
	 * takes the split branch and produces exactly the same triple. Two equal descriptions would
	 * then hash differently — the very contract violation this hashCode exists to avoid. Hashing
	 * the summary alone needs no such argument.
	 *
	 * <p>
	 * One consequence is worth knowing where dedup happens: the <em>free text</em> of
	 * {@code expecting} is not part of the identity, so two reports that differ only in the
	 * expected value are one record and which of them survives an in-JVM {@code HashSet} is
	 * arrival order. What is <em>not</em> outside the identity any more is the {@code code=} and
	 * {@code ev=} pair the same field carries when the message is an envelope: those two are
	 * read out of it and enter the summary, so two reports that name different events are two
	 * records even at one location.
	 */
	@Override
	public int hashCode() {
		return (summary == null) ? 0 : summary.hashCode();
	}

	@Override
	public String toString() {
		return String.format("[%s] %s at %s expecting %s", spec, type, location, expecting);
	}

}
