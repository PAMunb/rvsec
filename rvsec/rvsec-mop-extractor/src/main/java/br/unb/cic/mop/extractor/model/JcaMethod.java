package br.unb.cic.mop.extractor.model;

import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.StringJoiner;

public class JcaMethod {

	private String className;
	private String name;
	private List<String> parameters;
	private String signature;

	public JcaMethod(String className, String name, List<String> parameters, String signature) {
		this.className = className;
		this.name = name;
		this.parameters = parameters;
		this.signature = signature;
	}

	public String getClassName() {
		return className;
	}

	public String getName() {
		return name;
	}

	public List<String> getParameters() {
		return Collections.unmodifiableList(parameters);
	}

	public String getParametersAsString() {
		StringJoiner joiner = new StringJoiner(",", "(", ")");
		parameters.forEach(joiner::add);
		return joiner.toString();
	}

	public String getSignature() {
		return signature;
	}

	@Override
	public int hashCode() {
		return Objects.hash(className, name, parameters, signature);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		JcaMethod other = (JcaMethod) obj;
		return Objects.equals(className, other.className) && Objects.equals(name, other.name) && Objects.equals(parameters, other.parameters)
				&& Objects.equals(signature, other.signature);
	}

	@Override
	public String toString() {
		return String.format("JcaMethod [className=%s, name=%s, parameters=%s, signature=%s]", className, name, parameters, signature);
	}

//	@Override
//	public String toString() {
//		return String.format("JcaMethod [%s %s]", className, name);
//	}

}
