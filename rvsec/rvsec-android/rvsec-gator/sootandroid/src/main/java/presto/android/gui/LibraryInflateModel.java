package presto.android.gui;

import presto.android.gui.graph.NAddView2OpNode;
import presto.android.gui.graph.NInflate1OpNode;
import presto.android.gui.graph.NInflate2OpNode;
import presto.android.gui.graph.NNode;
import presto.android.gui.graph.NOpNode;
import presto.android.gui.graph.NVarNode;
import soot.Local;
import soot.Scene;
import soot.SootMethod;
import soot.Value;
import soot.jimple.IntConstant;
import soot.jimple.InvokeExpr;
import soot.jimple.Jimple;
import soot.jimple.SpecialInvokeExpr;
import soot.jimple.Stmt;
import soot.toolkits.scalar.Pair;

/**
 * Models library entry points that inflate a layout without going through
 * {@code LayoutInflater.inflate} or {@code Activity.setContentView(int)} at the
 * application call site: DataBinding, the content-layout constructor of AndroidX
 * activities, and the layout-id {@code setView(int)} of the AndroidX and
 * Material alert dialog builders. ViewBinding is not handled
 * here: its generated class inflates through {@code LayoutInflater.inflate},
 * which the flowgraph already models, and its {@code findChildViewById} binding
 * step is a separate FindView1 model.
 *
 * <p>These libraries live outside the analysed application classes, so
 * the flowgraph never sees the {@code inflate}/{@code setContentView} calls they
 * make internally. Each recognised call is rewritten into the operation node the
 * solver already understands:
 * <ul>
 *   <li>{@code DataBindingUtil.setContentView(activity, layout[, component])}
 *       becomes Inflate2 on the activity argument, so the layout lands in the
 *       activity's roots exactly like {@code activity.setContentView(layout)};</li>
 *   <li>{@code DataBindingUtil.inflate(inflater, layout, parent, attach[, c])} and
 *       {@code ViewDataBinding.inflateInternal(inflater, layout, parent, attach, c)}
 *       (what a generated {@code XxxBinding.inflate(...)} calls) become Inflate1.
 *       The call returns a binding, not a view, so the inflated root is bound to
 *       a fresh local: the solver records it as the operation's result, which is
 *       what the client reads to attribute the layout to a host activity;</li>
 *   <li>{@code super(layout)} in an activity constructor, the
 *       {@code ComponentActivity(int contentLayoutId)} family of AndroidX
 *       constructors, becomes Inflate2 on {@code this}: the library calls
 *       {@code setContentView(layout)} itself during {@code onCreate};</li>
 *   <li>{@code builder.setView(layout)} on {@code androidx.appcompat} /
 *       support {@code AlertDialog$Builder} and {@code MaterialAlertDialogBuilder}
 *       becomes Inflate1 with a fresh result local. The dialog itself stays
 *       unmodelled; the inflated body is attributed to the activity running the
 *       code by the client. {@code android.app.AlertDialog$Builder} is left to
 *       the flowgraph's own builder model.</li>
 * </ul>
 */
final class LibraryInflateModel {

  private static final String DBU = "androidx.databinding.DataBindingUtil";
  private static final String VDB = "androidx.databinding.ViewDataBinding";
  private static final String MATERIAL_BUILDER =
      "com.google.android.material.dialog.MaterialAlertDialogBuilder";

  private static int nextLocal = 0;

  private LibraryInflateModel() {
  }

  /** Returns the operation node for a recognised library call, or null when {@code s} is not one. */
  static NOpNode createOpNode(Flowgraph fg, Stmt s) {
    InvokeExpr ie = s.getInvokeExpr();
    SootMethod callee;
    try {
      callee = ie.getMethod();
    } catch (Exception e) {
      return null;
    }
    String cls = callee.getDeclaringClass().getName();
    String name = callee.getName();
    int argc = ie.getArgCount();
    if (DBU.equals(cls) && "setContentView".equals(name) && argc >= 2) {
      return inflate2(fg, s, ie.getArg(1), ie.getArg(0));
    }
    if ((DBU.equals(cls) && "inflate".equals(name) && argc >= 4)
        || (VDB.equals(cls) && "inflateInternal".equals(name) && argc >= 4)) {
      Value parent = ie.getArg(3) instanceof IntConstant
          && ((IntConstant) ie.getArg(3)).value != 0 ? ie.getArg(2) : null;
      return inflate1(fg, s, ie.getArg(1), parent);
    }
    if ("<init>".equals(name) && argc == 1 && ie instanceof SpecialInvokeExpr
        && fg.hier.libActivityClasses.contains(callee.getDeclaringClass())
        && fg.isIntValue(ie.getArg(0))) {
      return inflate2(fg, s, ie.getArg(0), ((SpecialInvokeExpr) ie).getBase());
    }
    if ("setView".equals(name) && argc == 1 && isLibraryAlertBuilder(cls)
        && fg.isIntValue(ie.getArg(0))) {
      return inflate1(fg, s, ie.getArg(0), null);
    }
    return null;
  }

  private static boolean isLibraryAlertBuilder(String cls) {
    return MATERIAL_BUILDER.equals(cls)
        || (cls.endsWith(".AlertDialog$Builder") && !cls.startsWith("android.app."));
  }

  private static Pair<Stmt, SootMethod> callSite(Flowgraph fg, Stmt s) {
    return new Pair<Stmt, SootMethod>(s, fg.jimpleUtil.lookup(s));
  }

  private static NOpNode inflate2(Flowgraph fg, Stmt s, Value layout, Value receiver) {
    if (!(receiver instanceof Local) || fg.ignoreLayoutIdCall(layout)) {
      return null;
    }
    NNode layoutIdNode = fg.simpleNode(layout);
    if (layoutIdNode == null) {
      return null;
    }
    return new NInflate2OpNode(layoutIdNode, fg.varNode((Local) receiver), callSite(fg, s), false);
  }

  private static NOpNode inflate1(Flowgraph fg, Stmt s, Value layout, Value parent) {
    if (fg.ignoreLayoutIdCall(layout)) {
      return null;
    }
    NNode layoutIdNode = fg.simpleNode(layout);
    if (layoutIdNode == null) {
      return null;
    }
    // Own name space: drawing from the flowgraph's FakeName counter would
    // renumber the FakeName_N handlers that already appear in the output.
    Local root = Jimple.v().newLocal("LibInflate_" + (nextLocal++),
        Scene.v().getSootClass("android.view.View").getType());
    NVarNode rootNode = fg.varNode(root);
    NOpNode inflate1 = new NInflate1OpNode(layoutIdNode, rootNode, callSite(fg, s), false);
    if (parent instanceof Local) {
      fg.allNNodes.add(new NAddView2OpNode(
          fg.varNode((Local) parent), rootNode, callSite(fg, s), false));
    }
    return inflate1;
  }
}
