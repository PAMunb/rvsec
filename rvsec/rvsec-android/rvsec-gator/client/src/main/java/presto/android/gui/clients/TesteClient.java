package presto.android.gui.clients;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Collection;

import com.google.gson.Gson;

import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.reader.AppReader;
import presto.android.Configs;
import presto.android.gui.GUIAnalysisClient;
import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.clients.energy.VarUtil;
import presto.android.gui.clients.out.Evento;
import presto.android.gui.clients.out.Janela;
import presto.android.gui.clients.out.Resultado;
import presto.android.gui.clients.out.Transicao;
import presto.android.gui.clients.wtg.Window;
import presto.android.gui.graph.NActivityNode;
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
//		extracted(output);
		
//		Graph graph = new Graph();
		Resultado result = new Resultado();
		
		VarUtil.v().guiOutput = output;
		WTGBuilder wtgBuilder = new WTGBuilder();
		wtgBuilder.build(output);
		WTGAnalysisOutput wtgAO = new WTGAnalysisOutput(output, wtgBuilder);
		WTG wtg = wtgAO.getWTG();
		
		for (WTGNode n : wtg.getNodes()) {
			NObjectNode node = n.getWindow();
			
//			Window vertex = new Window(node);
//			graph.addWindow(vertex);
			
			Janela source = new Janela(node.id, node.getClassType().getName());
			result.addWindow(source);
			
			Collection<WTGEdge> outEdges = n.getOutEdges();
			for (WTGEdge e : outEdges) {
				Window target = new Window(e.getTargetNode().getWindow());

//				Event event = new Event(e);
//				graph.addTransition(vertex, target, event);
				
				Transicao transition = new Transicao(source.getId(), target.getId(), new Evento(e));
				result.addTransition(transition);
			}
		}
		
//		for (Window w : graph.getWindows()) {
//			System.out.println(w);
//			Map<Window,Set<Event>> successors = graph.getSuccessors(w);
//			for (Map.Entry<Window, Set<Event>> entry : successors.entrySet()) {
//				Window target = entry.getKey();
//				Set<Event> events = entry.getValue();
//				
//				System.out.println(" --> "+target);
//				events.forEach(e -> System.out.println("     - "+e));
//			}
//		}

		System.out.println("&&&&&&&&&&& Configs.pathoutfilename="+Configs.pathoutfilename);
		Gson gson = new Gson();
//		String json = gson.toJson(graph);
//		String json = gson.toJson(ResultadoFactory.newResult(graph));
		String json = gson.toJson(result);
		try (FileWriter writer = new FileWriter(Configs.pathoutfilename)) {
			writer.write(json);
			System.out.println("File saved in: "+Configs.pathoutfilename);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		
		System.out.println("FIM DE FESTA!!!");

	}

	private void extracted(GUIAnalysisOutput output) {
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

			if(window instanceof NActivityNode) {
				NActivityNode actNode = (NActivityNode) window;
				System.out.println("********************* ACTIVITY: "+actNode);
				actNode.getChildren().forEach(System.out::println);
			}
			
			Collection<WTGEdge> inEdges = n.getInEdges();
			System.out.println("Number of in edges: " + Integer.toString(inEdges.size()));
//			for (WTGEdge inEdge : inEdges) {
//
//			}

			Collection<WTGEdge> outEdges = n.getOutEdges();
			System.out.println("Number of out edges: " + Integer.toString(n.getOutEdges().size()) + "\n");
			System.out.println(">>>>> ");
			for (WTGEdge e : outEdges) {
				NObjectNode guiWidget = e.getGUIWidget();
				System.out.println("   - "+e.getTargetNode().getWindow()+", event="+e.getEventType()+" .... clazz="+e.getClass()+" :::: widget="+e.getGUIWidget()+" :::: widget_clazz="+e.getGUIWidget().getClass()+" :::: widget_clazzType="+e.getGUIWidget().getClassType());
				System.out.println("     - Event handlers: "+e.getEventHandlers().size());
				for (SootMethod method : e.getEventHandlers()) {
					System.out.println("     --- "+method.getSignature());
				}
				System.out.println("     - Callbacks: "+e.getCallbacks().size());
				for (EventHandler handler : e.getCallbacks()) {
					NObjectNode widget = handler.getWidget();
					System.out.println("     --- "+handler.toString()+" ::: widget="+handler.getWidget()+" ::: widget.class="+handler.getWidget().getClass()+" ::: "+handler.getEventHandler()+" ::: "+handler.getEvent()+" :::: "+handler.getSig());
				}
				System.out.println("     - Stack Operations: "+e.getStackOps().size());
				for (StackOperation stackOperation : e.getStackOps()) {
					System.out.println("     --- "+(stackOperation.isPushOp()?"PUSH":"POP")+" ::: widget="+stackOperation.getWindow());
				}
			}
		}
	}
	
	public static void main(String[] args) throws Exception {
		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/";
		String apk = baseDir + "cryptoapp.apk";
		String sootAndroidDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gator/sootandroid";
		
		AppInfo appInfo = AppReader.readApk(apk);
		File decompileAppDir = AppReader.decompileApp(appInfo);
		
		Configs.guiAnalysis = true;
		Configs.clients.add("TesteClient");
		Configs.project = apk;
		Configs.benchmarkName = "cryptoapp.apk";
		Configs.apiLevel = "android-29";
		Configs.sootAndroidDir = sootAndroidDir;
		Configs.sdkDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk";
		Configs.android = Configs.sdkDir+"/platforms/"+Configs.apiLevel+"/android.jar";
		Configs.listenerSpecFile = sootAndroidDir+"/listeners.xml";
		Configs.wtgSpecFile = sootAndroidDir+"/wtg.xml";
		Configs.libraryPackageFile = sootAndroidDir+"/libPackages.txt";
		Configs.resourceLocation = decompileAppDir.getAbsolutePath()+"/res";
		Configs.manifestLocation = decompileAppDir.getAbsolutePath()+"/AndroidManifest.xml";
		
		Configs.pathoutfilename = "/home/pedro/tmp/rvsec-gator.json";
		
		
		presto.android.Main.main(new String[0]);
//		presto.android.Main.parseArgs(args);
	}

}
