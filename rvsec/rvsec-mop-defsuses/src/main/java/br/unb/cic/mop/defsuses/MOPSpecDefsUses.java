package br.unb.cic.mop.defsuses;

import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

public class MOPSpecDefsUses {
	private String name;
	private Set<String> defs;
	private Set<String> uses;

	public MOPSpecDefsUses(String name) {
		this(name, new HashSet<>(), new HashSet<>());
	}

	public MOPSpecDefsUses(String name, Set<String> defs, Set<String> uses) {
		this.name = name;
		this.defs = defs;
		this.uses = uses;
	}

	public void addDef(String prop) {
		defs.add(prop);
	}
	public void addUse(String prop) {
		uses.add(prop);
	}

	public String getName() {
		return name;
	}

	public Set<String> getDefs() {
		return defs;
	}

	public Set<String> getUses() {
		return uses;
	}

	@Override
	public int hashCode() {
		return Objects.hash(defs, name, uses);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if (obj == null)
			return false;
		if (getClass() != obj.getClass())
			return false;
		MOPSpecDefsUses other = (MOPSpecDefsUses) obj;
		return Objects.equals(defs, other.defs) && Objects.equals(name, other.name) && Objects.equals(uses, other.uses);
	}

	@Override
	public String toString() {
		return String.format("MOPSpecDefsUses [name=%s, defs=%s, uses=%s]", name, defs, uses);
	}

}
