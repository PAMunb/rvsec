package presto.android.gui.clients;

import java.util.Collection;

import presto.android.Configs;
import presto.android.gui.GUIAnalysisClient;
import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.clients.energy.VarUtil;
import presto.android.gui.graph.NObjectNode;
import presto.android.gui.wtg.EventHandler;
import presto.android.gui.wtg.StackOperation;
import presto.android.gui.wtg.WTGAnalysisOutput;
import presto.android.gui.wtg.WTGBuilder;
import presto.android.gui.wtg.ds.WTG;
import presto.android.gui.wtg.ds.WTGEdge;
import presto.android.gui.wtg.ds.WTGNode;
import soot.SootMethod;

public class TesteClient implements GUIAnalysisClient {

	@Override
	public void run(GUIAnalysisOutput output) {
		VarUtil.v().guiOutput = output;
		WTGBuilder wtgBuilder = new WTGBuilder();
		wtgBuilder.build(output);
		WTGAnalysisOutput wtgAO = new WTGAnalysisOutput(output, wtgBuilder);
		WTG wtg = wtgAO.getWTG();

		Collection<WTGEdge> edges = wtg.getEdges();
		Collection<WTGNode> nodes = wtg.getNodes();

		System.out.println("********************************************");
		System.out.println("Application: " + Configs.benchmarkName);
		System.out.println("Launcher Node: " + wtg.getLauncherNode());

		for (WTGNode n : nodes) {
			NObjectNode window = n.getWindow();
			System.out.println("Current Node: " + window + " ::: " + window.getClassType() + " ::: " + window.getClass() + " ::: id=" + window.id+ " ::: idNode=" + window.idNode);

			Collection<WTGEdge> inEdges = n.getInEdges();
			System.out.println("Number of in edges: " + Integer.toString(inEdges.size()));
			for (WTGEdge inEdge : inEdges) {

			}

			Collection<WTGEdge> outEdges = n.getOutEdges();
			System.out.println("Number of out edges: " + Integer.toString(n.getOutEdges().size()) + "\n");
			System.out.println(">>>>> ");
			for (WTGEdge e : outEdges) {
				System.out.println("   - "+e.getTargetNode().getWindow()+", event="+e.getEventType());
				System.out.println("     - Event handlers: "+e.getEventHandlers().size());
				for (SootMethod method : e.getEventHandlers()) {
					System.out.println("     --- "+method.getSignature());
				}
				System.out.println("     - Callbacks: "+e.getCallbacks().size());
				for (EventHandler handler : e.getCallbacks()) {
					System.out.println("     --- "+handler.toString()+" ::: widget="+handler.getWidget()+" ::: widget.class="+handler.getWidget().getClass());
				}
				System.out.println("     - Stack Operations: "+e.getStackOps().size());
				for (StackOperation stackOperation : e.getStackOps()) {
					System.out.println("     --- "+(stackOperation.isPushOp()?"PUSH":"POP")+" ::: widget="+stackOperation.getWindow());
				}
			}
		}

		System.out.println("FIM DE FESTA!!!");

	}

}
