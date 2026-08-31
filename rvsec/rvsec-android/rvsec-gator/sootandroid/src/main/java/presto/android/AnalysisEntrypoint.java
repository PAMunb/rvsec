/*
 * AnalysisEntrypoint.java - part of the GATOR project
 *
 * Copyright (c) 2019 The Ohio State University
 *
 * This file is distributed under the terms described in LICENSE in the
 * root directory.
 */
package presto.android;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import presto.android.gui.GUIAnalysis;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.util.Date;
import java.util.HashSet;
import java.util.Set;

public class AnalysisEntrypoint {
  private static AnalysisEntrypoint theInstance;

  final String TAG = AnalysisEntrypoint.class.getSimpleName();

  /**
   * The client parameter that carries the scope key. {@code Configs.getClientParamCode}
   * returns the <em>whole</em> parameter string, prefix included, so every reader has to
   * strip it — see {@code RvsecAnalysisClient.getCodePackage()}, which carries the same strip.
   */
  static final String CODE_PACKAGE_PARAM = "codePackage=";

  private AnalysisEntrypoint() {
  }

  public static synchronized AnalysisEntrypoint v() {
    if (theInstance == null) {
      theInstance = new AnalysisEntrypoint();
    }
    return theInstance;
  }

  public void run() {
//    Logger.stat("#Classes: " + Scene.v().getClasses().size() +
//            ", #AppClasses: " + Scene.v().getApplicationClasses().size());
//    Logger.trace("TIMECOST", "Start at " + System.currentTimeMillis());
    // Sanity check
    if (!"1".equals(System.getenv("PRODUCTION"))) {
      validate();
    }


//    final int[] numStmt = {0};
//    Scene.v().getClasses().parallelStream().forEach(new Consumer<SootClass>() {
//      @Override
//      public void accept(SootClass sootClass) {
//        if (!sootClass.isConcrete())
//          return;
//        sootClass.getMethods().parallelStream().forEach(new Consumer<SootMethod>() {
//          @Override
//          public void accept(SootMethod sootMethod) {
//            if (!sootMethod.isConcrete())
//              return;
//            Body b = sootMethod.retrieveActiveBody();
//            Stream<Unit> stmtStream = b.getUnits().parallelStream();
//            stmtStream.forEach(new Consumer<Unit>() {
//              @Override
//              public void accept(Unit unit) {
//                Stmt currentStmt = (Stmt) unit;
//                numStmt[0] += 1;
//              }
//            });
//          }
//        });
//      }
//    });
//
//    Logger.stat("#Stmt: " + numStmt[0] + " (not correct)");

    if (Configs.libraryPackages == null || Configs.libraryPackages.isEmpty()) {
      //If library packages are not defined
      Logger.trace("VERB", "lib pkg list is empty. Use default");
      Configs.addLibraryPackage("android.support.*");
      Configs.addLibraryPackage("com.google.android.gms.*");
    }

    //get package name and activity names
    String appPkg;
    Set<String> activityNames = new HashSet<String>();
    String fn = Configs.manifestLocation;
    DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
    dbFactory.setNamespaceAware(true);
    try {
      DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
      Document doc = dBuilder.parse(fn);
      Node root = doc.getElementsByTagName("manifest").item(0);
      appPkg = root.getAttributes().getNamedItem("package").getTextContent().trim();
      Node application = ((Element) root).getElementsByTagName("application").item(0);
      NodeList activityNodes = ((Element) application).getElementsByTagName("activity");
      for (int i = 0; i < activityNodes.getLength(); i++) {
        String name = ((Element) activityNodes.item(i)).getAttribute("android:name");
        if (name.equals("")) {
          Logger.warn(TAG, "Name is missing in the activity tag.");
          continue;
        }
        if (name.startsWith("."))
          name = appPkg + name;
        activityNames.add(name);
      }
    } catch (Exception e) {
      throw new RuntimeException(e);
    }

    // INV-ANA-65 — the guard below and the client's own filter must answer to the SAME key.
    // The client filters by codePackage (falling back to the manifest); this loop used to
    // protect only what started with the manifest package, so whenever the two differed the
    // demotion below stripped exactly the classes the client was about to count, and the
    // denominator collapsed to whatever libPackages.txt happened not to match.
    String scopeKey = resolveScopeKey(Configs.getClientParamCode(CODE_PACKAGE_PARAM), appPkg);
    Logger.stat("scope key for app/library classification: " + scopeKey);

    for (SootClass c : Scene.v().getClasses()) {
      if (activityNames.contains(c.getName())) {
        // The <activity> rescue. It is no longer load-bearing FOR THE DENOMINATOR — with the
        // guard reading the effective key, every class under that key already leaves the loop
        // below. It stays load-bearing for the reachability predicates: it promotes declared
        // activities into Hierarchy.appClasses, which is what reachable / reachesTarget /
        // directlyReachesTarget are computed over.
        if (!c.isApplicationClass()) {
          Logger.warn(TAG, "soot reckons " + c.getName() + " as lib class which is not.");
          c.setApplicationClass();
        }
        continue;
      }
      if (c.getName().startsWith(scopeKey))
        continue;
      if (Configs.isLibraryClass(c.getName())) {
        if ((!c.isPhantomClass()) && c.isApplicationClass()) {
          c.setLibraryClass();
        }
      }
    }

//    Logger.verb("DEBUG", "After loading library packages");
    Logger.stat("#Classes: " + Scene.v().getClasses().size() +
            ", #AppClasses: " + Scene.v().getApplicationClasses().size());

    // Analysis
    // TODO: use reflection to allow nice little extensions.
    if (Configs.guiAnalysis) {
      GUIAnalysis guiAnalysis = GUIAnalysis.v();
      guiAnalysis.run();
      Date endTime = new Date();
      Logger.verb(this.getClass().getSimpleName(),
              "Soot stopped on " + endTime);
      System.exit(0);
    }
  }

  void validate() {
    try {
      validateMethodNames();
    } catch (RuntimeException e) {
      Logger.warn(this.TAG, e.getMessage());
    }
  }

  // Validate to catch typos in MethodNames.
  void validateMethodNames() {
    SootClass activity = Scene.v().getSootClass("android.app.Activity");
    //assertTrue(!activity.isPhantom(), "Activity class is phantom.");
    activity.getMethod(MethodNames.activityOpenContextMenuSubsig);
    activity.getMethod(MethodNames.activityOpenOptionsMenuSubsig);
    activity.getMethod(MethodNames.onCreateContextMenuSubSig);
    activity.getMethod(MethodNames.onPrepareOptionsMenuSubsig);
    activity.getMethod(MethodNames.activityShowDialogSubSig);
    if (Configs.numericApiLevel >= 8) {
      activity.getMethod(MethodNames.activityShowDialogBundleSubSig);
    }
    activity.getMethod(MethodNames.activityDismissDialogSubSig);
    activity.getMethod(MethodNames.activityRemoveDialogSubSig);

    SootClass listActivity = Scene.v().getSootClass("android.app.ListActivity");
//    assertTrue(!listActivity.isPhantom(), "ListActivity is phantom.");
    if (!listActivity.isPhantom()) {
      listActivity.getMethod(MethodNames.onListItemClickSubSig);
    } else {
      Scene.v().removeClass(listActivity);
    }

    SootClass tabHost = Scene.v().getSootClass("android.widget.TabHost");
    if (!tabHost.isPhantom()) {
      tabHost.getMethod(MethodNames.tabHostAddTabSugSig);
      tabHost.getMethod(MethodNames.tabHostNewTabSpecSubSig);
    } else {
      Scene.v().removeClass(tabHost);
    }

    SootClass tabSpec = Scene.v().getSootClass("android.widget.TabHost$TabSpec");
    if (!tabSpec.isPhantom()) {
      tabSpec.getMethod(MethodNames.tabSpecSetIndicatorCharSeqSubSig);
      tabSpec.getMethod(MethodNames.tabSpecSetIndicatorCharSeqDrawableSubSig);
      if (Configs.numericApiLevel >= 4) {
        tabSpec.getMethod(MethodNames.tabSpecSetIndicatorViewSubSig);
      }
      tabSpec.getMethod(MethodNames.tabSpecSetContentIntSubSig);
      tabSpec.getMethod(MethodNames.tabSpecSetContentFactorySubSig);
      tabSpec.getMethod(MethodNames.tabSpecSetContentIntentSubSig);
    } else {
      Scene.v().removeClass(tabSpec);
    }

    SootClass tabContentFactory =
            Scene.v().getSootClass("android.widget.TabHost$TabContentFactory");
    if (!tabContentFactory.isPhantom()) {
      tabContentFactory.getMethod(MethodNames.tabContentFactoryCreateSubSig);
    } else {
      Scene.v().removeClass(tabContentFactory);
    }

    SootClass layoutInflater =
            Scene.v().getSootClass("android.view.LayoutInflater");
    assertTrue(!layoutInflater.isPhantom(), "LayoutInflater class is phantom.");

    SootClass view = Scene.v().getSootClass("android.view.View");
    assertTrue(!view.isPhantom(), "View class is phantom.");

    view.getMethod(MethodNames.viewShowContextMenuSubsig);
    view.getMethod(MethodNames.viewOnCreateContextMenuSubSig);

    SootMethod setContentView1 = activity.getMethod(MethodNames.setContentViewSubSig);
    assertTrue(MethodNames.setContentViewSubSig.equals(setContentView1.getSubSignature()),
            "MethodNames.setContentViewSubSig is incorrect.");
    SootMethod setContentView2 = activity.getMethod(MethodNames.setContentViewViewSubSig);
    assertTrue(MethodNames.setContentViewViewSubSig.equals(setContentView2.getSubSignature()),
            "MethodNames.setContentViewViewSubSig is incorrect.");
    activity.getMethod(MethodNames.setContentViewViewParaSubSig);

    SootClass dialog = Scene.v().getSootClass("android.app.Dialog");
    dialog.getMethod(MethodNames.setContentViewSubSig);
    dialog.getMethod(MethodNames.setContentViewViewSubSig);
    dialog.getMethod(MethodNames.setContentViewViewParaSubSig);

    SootMethod inflate1 = layoutInflater.getMethod(
            "android.view.View inflate(int,android.view.ViewGroup)");
    assertTrue(MethodNames.layoutInflaterInflate.equals(inflate1.getSignature()),
            "MethodNames.layoutInflaterInflate is incorrect.");
    SootMethod inflate2 = layoutInflater.getMethod(
            "android.view.View inflate(int,android.view.ViewGroup,boolean)");
    assertTrue(MethodNames.layoutInflaterInflateBool.equals(inflate2.getSignature()),
            "MethodNames.layoutInflaterInflateBool is incorrect.");

    SootMethod inflate3 = view.getMethod(
            "android.view.View inflate(android.content.Context,int,android.view.ViewGroup)");
    assertTrue(MethodNames.viewCtxInflate.equals(inflate3.getSignature()),
            "MethodNames.viewCtxInflate is incorrect.");

    SootMethod findView1 = view.getMethod(
            "android.view.View findViewById(int)");
    assertTrue(MethodNames.viewFindViewById.equals(findView1.getSignature()),
            "MethodNames.viewFindViewById is incorrect.");
    SootMethod findView2 = activity.getMethod(
            "android.view.View findViewById(int)");
    assertTrue(MethodNames.actFindViewById.equals(findView2.getSignature()),
            "MethodNames.actFindViewById is incorrect.");

    SootMethod findView3 = activity.getMethod(MethodNames.findViewByIdSubSig);
    assertTrue(MethodNames.findViewByIdSubSig.equals(findView3.getSubSignature()),
            "MethodNames.findViewByIdSubSig is incorrect.");

    SootMethod setId = view.getMethod(MethodNames.setIdSubSig);
    assertTrue(MethodNames.setIdSubSig.equals(setId.getSubSignature()),
            "MethodNames.setIdSubSig is incorrect.");

    // MethodNames.addViewName is fine

    SootMethod findFocus1 = view.getMethod(MethodNames.findFocusSubSig);
    assertTrue(MethodNames.findFocusSubSig.equals(findFocus1.getSubSignature()),
            "MethodNames.findFocusSubSig is incorrect.");

    // Dialogs
    SootClass dialogInterfaceOnCancel =
            Scene.v().getSootClass("android.content.DialogInterface$OnCancelListener");
    assertTrue(
            !dialogInterfaceOnCancel.isPhantom(),
            "DialogInterface.OnCancelListener is phantom!");

    SootMethod dialogInterfaceOnCancelMethod =
            dialogInterfaceOnCancel.getMethod(MethodNames.dialogOnCancelSubSig);
    assertTrue(
            MethodNames.dialogOnCancelSubSig.equals(
                    dialogInterfaceOnCancelMethod.getSubSignature()),
            "MethodNames.dialogOnCancelSubSig is incorrect.");

    SootClass dialogInterfaceOnKey =
            Scene.v().getSootClass("android.content.DialogInterface$OnKeyListener");
    assertTrue(!dialogInterfaceOnKey.isPhantom(), "DialogInterface.OnCancelListener is phantom!");

    dialogInterfaceOnKey.getMethod(MethodNames.dialogOnKeySubSig);

    SootClass dialogInterfaceOnShow =
            Scene.v().getSootClass("android.content.DialogInterface$OnShowListener");
    assertTrue(
            !dialogInterfaceOnShow.isPhantom(),
            "DialogInterface.OnShowListener is phantom!");
    dialogInterfaceOnShow.getMethod(MethodNames.dialogOnShowSubSig);

    SootClass alertDialog = Scene.v().getSootClass("android.app.AlertDialog");
    assertTrue(!alertDialog.isPhantom(), "AlertDialog is phantom!");

    alertDialog.getMethod(MethodNames.alertDialogSetButtonCharSeqListenerSubSig);
    alertDialog.getMethod(MethodNames.alertDialogSetButtonCharSeqMsgSubSig);
    alertDialog.getMethod(MethodNames.alertDialogSetButtonIntCharSeqListenerSubSig);
    alertDialog.getMethod(MethodNames.alertDialogSetButtonIntCharSeqMsgSubSig);
  }

  void assertTrue(boolean assertion, String message) {
    if (!assertion) {
      throw new RuntimeException(message);
    }
  }

  /**
   * Resolve the scope key that decides which classes this run treats as app-owned.
   *
   * <p>Four cases, and the third is the one that matters: an empty key would make
   * {@code startsWith("")} true for every class in the Scene and promote the whole
   * universe — including every library — into the denominator. It falls back to the
   * manifest package instead.
   *
   * @param clientParam the raw {@code codePackage=<key>} parameter as
   *                    {@code Configs.getClientParamCode} returns it (prefix included),
   *                    or {@code null} when the run did not pass one
   * @param manifestPackage the package declared in AndroidManifest.xml
   * @return the effective scope key; never {@code null} unless the manifest package is
   */
  static String resolveScopeKey(String clientParam, String manifestPackage) {
    if (clientParam == null || !clientParam.startsWith(CODE_PACKAGE_PARAM)) {
      return manifestPackage;
    }
    String key = clientParam.substring(CODE_PACKAGE_PARAM.length()).trim();
    if (key.isEmpty()) {
      return manifestPackage;
    }
    return key;
  }

}
