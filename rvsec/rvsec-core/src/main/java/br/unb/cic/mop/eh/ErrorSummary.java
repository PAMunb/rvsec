package br.unb.cic.mop.eh;

import java.io.Serializable;

/**
 * One reported specification violation, reduced to the fields that identify it on the device:
 * specification, error kind, class, method, source position, failure code and event.
 *
 * <p>
 * <b>{@code location} participates in {@link #equals(Object)} and {@link #hashCode()}, and that
 * is intentional.</b> In-JVM deduplication is therefore line-granular: a method violated at two
 * different lines emits two records. Two reasons make this the right rule. It bounds logcat
 * volume for a hot violated method without collapsing anything a reader would want back, and it
 * is what makes the reported position carry information at all — a per-method record could only
 * name one arbitrary line out of many.
 *
 * <p>
 * <b>{@code code} and {@code event} participate too, and {@code event} is the one that earns its
 * place.</b> Every specification of the set has at most one {@code @fail} handler, so the failure
 * code of a sequence violation is a function of the specification name and would refine nothing
 * on its own; it is the event that names <em>which</em> transition failed. Without it two
 * different causes reported at one call site are one record, and which of them survives the
 * {@code HashSet} is arrival order — measured on the differential-harness corpus, six such
 * identities split in two once the event enters, three of them with the code identical on both
 * sides (see {@code rv-android/data/gh104/identity_discontinuity.md}).
 *
 * <p>
 * Both values are read from the reported message envelope and are the sentinel
 * {@code UNSPECIFIED} when the message carries none, so a report from a specification set that
 * emits no envelope keeps a readable identity instead of a null one. The consequence is a
 * declared discontinuity, not a side effect: a deduplicated count taken under this identity is
 * not comparable to one taken under the five-field identity that preceded it, and a published
 * count must say which of the two it belongs to.
 *
 * <p>
 * The coarser identity — {@code (apk, class, method, spec)}, one <em>unique misuse</em> — is
 * deliberately <em>not</em> computed here. It is applied downstream, where the records are
 * aggregated. Coarsening inside the monitor would discard the line data before anyone could use
 * it, and would not save the downstream aggregation anyway.
 */
public class ErrorSummary implements Serializable {
	private static final long serialVersionUID = 1L;

	private String spec;
	private String error;
	private String classQualifiedName;
	private String methodName;
	private String location;
	private String code;
	private String event;

	public ErrorSummary(String spec, ErrorType error, String classQualifiedName, String methodName, String location,
			String code, String event) {
		this(spec, error.toString(), classQualifiedName, methodName, location, code, event);
	}

	public ErrorSummary(String spec, String error, String classQualifiedName, String methodName, String location,
			String code, String event) {
		this.spec = spec;
		this.error = error;
		this.classQualifiedName = classQualifiedName;
		this.methodName = methodName;
		this.location = location;
		this.code = code;
		this.event = event;
	}

	public String getSpec() {
		return spec;
	}

	public String getError() {
		return error;
	}

	public String getClassQualifiedName() {
		return classQualifiedName;
	}

	public String getMethodName() {
		return methodName;
	}

	public String getLocation() {
		return location;
	}

	public String getCode() {
		return code;
	}

	public String getEvent() {
		return event;
	}

	private String className() {
		String res = classQualifiedName;
//        if(classQualifiedName.contains("$")) {
//            int idx = classQualifiedName.indexOf("$");
//            res =  res.substring(0, idx);
//        }
		return res.substring(res.lastIndexOf(".") + 1);
	}

	@Override
	public int hashCode() {
		final int prime = 31;
		int result = 1;
		result = prime * result + ((classQualifiedName == null) ? 0 : classQualifiedName.hashCode());
		result = prime * result + ((code == null) ? 0 : code.hashCode());
		result = prime * result + ((error == null) ? 0 : error.hashCode());
		result = prime * result + ((event == null) ? 0 : event.hashCode());
		result = prime * result + ((location == null) ? 0 : location.hashCode());
		result = prime * result + ((methodName == null) ? 0 : methodName.hashCode());
		result = prime * result + ((spec == null) ? 0 : spec.hashCode());
		return result;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if (obj == null)
			return false;
		if (getClass() != obj.getClass())
			return false;
		ErrorSummary other = (ErrorSummary) obj;
		if (classQualifiedName == null) {
			if (other.classQualifiedName != null)
				return false;
		} else if (!classQualifiedName.equals(other.classQualifiedName))
			return false;
		if (code == null) {
			if (other.code != null)
				return false;
		} else if (!code.equals(other.code))
			return false;
		if (event == null) {
			if (other.event != null)
				return false;
		} else if (!event.equals(other.event))
			return false;
		if (error == null) {
			if (other.error != null)
				return false;
		} else if (!error.equals(other.error))
			return false;
		if (location == null) {
			if (other.location != null)
				return false;
		} else if (!location.equals(other.location))
			return false;
		if (methodName == null) {
			if (other.methodName != null)
				return false;
		} else if (!methodName.equals(other.methodName))
			return false;
		if (spec == null) {
			if (other.spec != null)
				return false;
		} else if (!spec.equals(other.spec))
			return false;
		return true;
	}

	/**
	 * The six comma-separated fields of the reported line — unchanged by the arrival of
	 * {@code code} and {@code event}, and deliberately so.
	 *
	 * <p>
	 * The two new fields are already on the line: they are read out of the message envelope,
	 * which the collector appends as the seventh field. Emitting them a second time would widen
	 * a positional record every downstream parser splits by count, for no information gained.
	 */
	@Override
	public String toString() {
		return String.format("%s,%s,%s,%s,%s,%s", spec, classQualifiedName, className(), methodName, location, error);
	}

}
