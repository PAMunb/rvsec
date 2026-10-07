package presto.android.gui;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import presto.android.Hierarchy;
import presto.android.Logger;
import soot.Body;
import soot.Local;
import soot.RefType;
import soot.SootClass;
import soot.SootMethod;
import soot.Type;
import soot.Unit;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.InstanceInvokeExpr;
import soot.jimple.InvokeExpr;
import soot.jimple.ReturnStmt;
import soot.jimple.Stmt;

/**
 * Connects a fragment's view, as its {@code onCreateView} returns it, to the two
 * places the fragment reads that view back: the {@code view} parameter of its
 * {@code onViewCreated(View, Bundle)}, and the result of {@code getView()} /
 * {@code requireView()} called on the fragment.
 *
 * <p>The framework makes both connections at run time, so the flow graph has no
 * edge for them. Without the edges, a fragment that looks its widgets up in
 * {@code onViewCreated} ({@code view.findViewById(id).setOnClickListener(l)}) or
 * through {@code getView()} registers listeners on views the solver cannot see,
 * and those listeners are lost. Adding plain value-flow edges before the solver
 * runs lets the existing {@code findViewById} and {@code setXListener} models do
 * the rest.
 *
 * <p>The edges are per class, not per instance: every {@code getView()} on a
 * fragment of class F receives every view F's {@code onCreateView} can return.
 */
public final class FragmentViewFlow {

  private static final Set<String> FRAGMENT_BASES = Set.of(
          "android.app.Fragment",
          "android.support.v4.app.Fragment",
          "androidx.fragment.app.Fragment");

  private static final Set<String> VIEW_GETTERS = Set.of("getView", "requireView");

  private static final String ON_CREATE_VIEW =
          "android.view.View onCreateView(android.view.LayoutInflater,android.view.ViewGroup,android.os.Bundle)";

  private static final String ON_VIEW_CREATED =
          "void onViewCreated(android.view.View,android.os.Bundle)";

  private FragmentViewFlow() {
  }

  /** Adds the edges to {@code g}; returns how many were added. */
  public static int link(Flowgraph g, Hierarchy hier) {
    Map<SootClass, List<Local>> returned = new HashMap<>();
    int edges = 0;
    for (SootClass c : new ArrayList<>(hier.appClasses)) {
      if (c.isInterface() || c.isPhantom()) {
        continue;
      }
      boolean fragment = isFragment(c);
      for (SootMethod m : new ArrayList<>(c.getMethods())) {
        if (!m.isConcrete()) {
          continue;
        }
        Body body;
        try {
          body = m.retrieveActiveBody();
        } catch (RuntimeException e) {
          continue;
        }
        if (fragment && ON_VIEW_CREATED.equals(m.getSubSignature())) {
          edges += connect(g, returnedViews(c, hier, returned), body.getParameterLocal(0));
        }
        for (Unit u : body.getUnits()) {
          if (!(u instanceof AssignStmt) || !((Stmt) u).containsInvokeExpr()) {
            continue;
          }
          InvokeExpr ie = ((Stmt) u).getInvokeExpr();
          if (!(ie instanceof InstanceInvokeExpr) || ie.getArgCount() != 0
                  || !VIEW_GETTERS.contains(ie.getMethodRef().getName())) {
            continue;
          }
          Type t = ((InstanceInvokeExpr) ie).getBase().getType();
          Value lhs = ((AssignStmt) u).getLeftOp();
          if (!(t instanceof RefType) || !(lhs instanceof Local)) {
            continue;
          }
          SootClass receiver = ((RefType) t).getSootClass();
          if (hier.appClasses.contains(receiver) && isFragment(receiver)) {
            edges += connect(g, returnedViews(receiver, hier, returned), (Local) lhs);
          }
        }
      }
    }
    Logger.verb("FragmentViewFlow", "fragment view edges added: " + edges);
    return edges;
  }

  /** Value flow {@code source -> target}, the edge the flow graph builds for {@code target = source}. */
  private static int connect(Flowgraph g, List<Local> sources, Local target) {
    int added = 0;
    for (Local source : sources) {
      if (source != target) {
        g.varNode(source).addEdgeTo(g.varNode(target));
        added++;
      }
    }
    return added;
  }

  /** Locals returned by the nearest application {@code onCreateView} in {@code c}'s superclass chain. */
  private static List<Local> returnedViews(SootClass c, Hierarchy hier,
                                           Map<SootClass, List<Local>> memo) {
    List<Local> cached = memo.get(c);
    if (cached != null) {
      return cached;
    }
    List<Local> result = new ArrayList<>();
    SootClass cur = c;
    while (cur != null && hier.appClasses.contains(cur)) {
      SootMethod m = cur.getMethodUnsafe(ON_CREATE_VIEW);
      if (m != null && m.isConcrete()) {
        try {
          for (Unit u : m.retrieveActiveBody().getUnits()) {
            if (u instanceof ReturnStmt && ((ReturnStmt) u).getOp() instanceof Local) {
              result.add((Local) ((ReturnStmt) u).getOp());
            }
          }
        } catch (RuntimeException e) {
          // no body: nothing returned that the analysis can see
        }
        break;
      }
      cur = cur.getSuperclassUnsafe();
    }
    memo.put(c, result);
    return result;
  }

  static boolean isFragment(SootClass c) {
    SootClass cur = c;
    int guard = 0;
    while (cur != null && guard++ < 32) {
      if (FRAGMENT_BASES.contains(cur.getName())) {
        return true;
      }
      cur = cur.getSuperclassUnsafe();
    }
    return false;
  }
}
