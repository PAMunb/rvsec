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

		return new ErrorSummary(spec, type, clazz, method, loc);
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
	 * One consequence is worth knowing where dedup happens: {@code expecting} is not part of the
	 * identity, so two reports of the same violation that differ only in the expected value are
	 * one record, and which of the two survives an in-JVM {@code HashSet} is arrival order.
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
