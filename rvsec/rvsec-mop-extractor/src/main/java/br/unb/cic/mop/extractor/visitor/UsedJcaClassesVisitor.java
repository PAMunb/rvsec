package br.unb.cic.mop.extractor.visitor;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import javamop.parser.ast.ImportDeclaration;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.aspectj.CombinedPointCut;
import javamop.parser.ast.aspectj.MethodPointCut;
import javamop.parser.ast.aspectj.PointCut;
import javamop.parser.ast.mopspec.EventDefinition;
import javamop.parser.ast.mopspec.JavaMOPSpec;

public class UsedJcaClassesVisitor extends VoidVisitorAdapter<Object> {
	private Set<String> classes = new HashSet<>();
	private Map<String, String> imports = new HashMap<>();

	/* visit functions for JavaMOP components */

	@Override
	public void visit(MOPSpecFile f, Object arg) {
		if (f.getSpecs() != null) {
			f.getImports().forEach(i -> i.accept(this, arg));
			f.getSpecs().forEach(i -> i.accept(this, arg));
		}
	}

	@Override
	public void visit(ImportDeclaration n, Object arg) {
		if(n.isAsterisk()) {
			return;
		}
		String clazz = n.getName().toString();
		String key = clazz.substring(clazz.lastIndexOf('.') + 1);
		imports.put(key, clazz);
	}


	@Override
	public void visit(JavaMOPSpec s, Object arg) {
		if (s.getEvents() != null) {
			for (EventDefinition e : s.getEvents()) {
				e.accept(this, arg);
			}
		}
	}

	@Override
	public void visit(EventDefinition e, Object arg) {
		if (!Objects.isNull(e.getPointCut())) {
			e.getPointCut().accept(this, arg);
		}
	}

	@Override
	public void visit(CombinedPointCut p, Object arg) {
		for (PointCut subP : p.getPointcuts()) {
			subP.accept(this, arg);
		}
	}

	@Override
	public void visit(MethodPointCut p, Object arg) {
		String clazzName = p.getSignature().getOwner().toString();
		if (imports.containsKey(clazzName)) {
			getClasses().add(imports.get(clazzName));
		}
	}

	public Set<String> getClasses() {
		return classes;
	}

}


