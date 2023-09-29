package br.unb.cic.mop.defsuses;

import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;


import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.expr.FieldAccessExpr;
import javamop.parser.ast.expr.MethodCallExpr;
import javamop.parser.ast.mopspec.EventDefinition;
import javamop.parser.ast.mopspec.JavaMOPSpec;
import javamop.parser.ast.mopspec.PropertyAndHandlers;
import javamop.parser.ast.stmt.BlockStmt;
import javamop.parser.ast.stmt.ExpressionStmt;
import javamop.parser.ast.stmt.Statement;

public class UseDefVisitor extends VoidVisitorAdapter<Object> {
	private static final String METHOD_PREFIX = "ExecutionContext.instance()";
	private static final String METHOD_SET = "setProperty";
	private static final String METHOD_GET = "validate";

	private Map<String, MOPSpecDefsUses> specs = new HashMap<>();
	private String currentSpec;

	/* visit functions for JavaMOP components */

	@Override
	public void visit(MOPSpecFile f, Object arg) {
		if (f.getSpecs() != null) {
			f.getSpecs().forEach(i -> i.accept(this, arg));
		}
	}

	@Override
	public void visit(JavaMOPSpec s, Object arg) {
		currentSpec = s.getName();
		specs.putIfAbsent(currentSpec, new MOPSpecDefsUses(currentSpec));
		if (s.getEvents() != null) {
			for (EventDefinition e : s.getEvents()) {
				e.accept(this, arg);
			}			
		}
		if(s.getPropertiesAndHandlers() != null) {
			for(PropertyAndHandlers pah: s.getPropertiesAndHandlers()) {
				pah.accept(this, arg);
			}
		}
	}

	@Override
	public void visit(EventDefinition e, Object arg) {
		if (!Objects.isNull(e.getAction())) {
			e.getAction().accept(this, arg);
		}
		if (!Objects.isNull(e.getCondition()) && !"".equals(e.getCondition())) {
			PropertyExtractor ext = new PropertyExtractor(METHOD_PREFIX, METHOD_GET);
			List<String> propsUsed = ext.parse(e.getCondition());
			propsUsed.forEach(p -> specs.get(currentSpec).addUse(p));
		}
	}
	
	@Override
	public void visit(PropertyAndHandlers pah, Object arg) {
		HashMap<String, BlockStmt> handlers = pah.getHandlers();
		if (!Objects.isNull(handlers)) {
			handlers.values().forEach(b -> b.accept(this, arg));			
		}
	}

	@Override
	public void visit(BlockStmt b, Object arg) {
		if (!Objects.isNull(b.getStmts())) {
			for (Statement stmt : b.getStmts()) {
				stmt.accept(this, arg);
			}
		}
	}

	@Override
	public void visit(ExpressionStmt stmt, Object arg) {
		if (!Objects.isNull(stmt.getExpression())) {
			stmt.getExpression().accept(this, arg);
		}
	}

	@Override
	public void visit(MethodCallExpr e, Object arg) {
		if (!Objects.isNull(e.getScope()) && METHOD_PREFIX.equals(e.getScope().toString())) {
			if (METHOD_SET.equals(e.getName())) {
				FieldAccessExpr exp = (FieldAccessExpr) e.getArgs().get(0);
				specs.get(currentSpec).addDef(exp.getField());
			}
			if (METHOD_GET.equals(e.getName())) {
				FieldAccessExpr exp = (FieldAccessExpr) e.getArgs().get(0);
				specs.get(currentSpec).addUse(exp.getField());
			}
		}
	}

	public Collection<MOPSpecDefsUses> getSpecs() {
		return specs.values();
	}
}
