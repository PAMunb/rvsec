/*
 * JimpleDefUtils — shared def-use helpers extracted from MenuExtractor and
 * SpinnerItemExtractor (gh60 C1g). The three primitives below were copy-
 * pasted between the two extractors with identical semantics; centralising
 * them keeps future fixes (e.g. tightening the multi-def policy) in one
 * place instead of forcing parallel edits across consumers.
 */
package presto.android.util;

import java.util.List;

import soot.Local;
import soot.Unit;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.IntConstant;
import soot.jimple.Stmt;
import soot.jimple.StringConstant;
import soot.toolkits.scalar.SimpleLocalDefs;

public final class JimpleDefUtils {

	private JimpleDefUtils() {
		// utility class
	}

	/**
	 * Returns the RHS of the latest unique definition of {@code local}
	 * reaching {@code useSite}, or {@code null} when there are zero or
	 * multiple reaching defs. The conservative choice — emitting the
	 * wrong value would mis-attribute the consumer's extracted item
	 * (menu entry, spinner string, …).
	 *
	 * Also returns {@code null} when SimpleLocalDefs throws on a
	 * malformed body, so callers do not need a separate try/catch.
	 */
	public static Value definitionRhs(Local local, Stmt useSite, SimpleLocalDefs defs) {
		try {
			List<Unit> reaching = defs.getDefsOfAt(local, useSite);
			if (reaching.size() != 1) return null;
			Unit def = reaching.get(0);
			if (def instanceof AssignStmt) {
				return ((AssignStmt) def).getRightOp();
			}
		} catch (RuntimeException ex) {
			// SimpleLocalDefs throws on malformed bodies; treat as unresolved.
		}
		return null;
	}

	/**
	 * Resolves an IntConstant argument, walking one def-use step when the
	 * argument is a Local. Returns {@code null} when the value is not an
	 * int literal at the use site.
	 */
	public static Integer resolveInt(Value arg, Stmt useSite, SimpleLocalDefs defs) {
		Value v = (arg instanceof Local) ? definitionRhs((Local) arg, useSite, defs) : arg;
		return (v instanceof IntConstant) ? ((IntConstant) v).value : null;
	}

	/**
	 * Resolves a StringConstant argument, walking one def-use step when
	 * the argument is a Local. Returns {@code null} when the value is not
	 * a string literal at the use site.
	 */
	public static String resolveStr(Value arg, Stmt useSite, SimpleLocalDefs defs) {
		Value v = (arg instanceof Local) ? definitionRhs((Local) arg, useSite, defs) : arg;
		return (v instanceof StringConstant) ? ((StringConstant) v).value : null;
	}
}
