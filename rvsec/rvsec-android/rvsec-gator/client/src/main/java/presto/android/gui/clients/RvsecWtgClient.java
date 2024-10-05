package presto.android.gui.clients;

import java.io.IOException;
import java.util.Collection;

import presto.android.Configs;
import presto.android.gui.GUIAnalysisClient;
import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.clients.energy.VarUtil;
import presto.android.gui.clients.wtg.model.Event;
import presto.android.gui.clients.wtg.model.Result;
import presto.android.gui.clients.wtg.model.Transition;
import presto.android.gui.clients.wtg.model.Window;
import presto.android.gui.clients.wtg.writer.Writer;
import presto.android.gui.graph.NObjectNode;
import presto.android.gui.wtg.WTGAnalysisOutput;
import presto.android.gui.wtg.WTGBuilder;
import presto.android.gui.wtg.ds.WTG;
import presto.android.gui.wtg.ds.WTGEdge;
import presto.android.gui.wtg.ds.WTGNode;

public class RvsecWtgClient implements GUIAnalysisClient {

	@Override
	public void run(GUIAnalysisOutput output) {
		VarUtil.v().guiOutput = output;
		WTGBuilder wtgBuilder = new WTGBuilder();
		wtgBuilder.build(output);
		WTGAnalysisOutput wtgAO = new WTGAnalysisOutput(output, wtgBuilder);
		WTG wtg = wtgAO.getWTG();

		Result result = new Result();
		for (WTGNode node : wtg.getNodes()) {
			NObjectNode sourceNode = node.getWindow();
			
			Window source = new Window(sourceNode.id, sourceNode.getClassType().getName());
			result.addWindow(source);
			
			Collection<WTGEdge> outEdges = node.getOutEdges();
			for (WTGEdge e : outEdges) {
				NObjectNode targetNode = e.getTargetNode().getWindow();
				
				Window target = new Window(targetNode.id, targetNode.getClassType().getName());
				result.addWindow(target);
				
				Transition transition = new Transition(source.getId(), target.getId(), new Event(e));
				result.addTransition(transition);
			}
		}

		saveResult(result);
	}

	private void saveResult(Result result) {
		try {
			Writer.write(result);
			System.out.println("File saved in: "+Configs.pathoutfilename);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
	
//	public static void main(String[] args) throws Exception {
//		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/";
//		String apk = baseDir + "cryptoapp.apk";
//		String sootAndroidDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gator/sootandroid";
//		
//		AppInfo appInfo = AppReader.readApk(apk);
//		File decompileAppDir = AppReader.decompileApp(appInfo);
//		
//		Configs.guiAnalysis = true;
//		Configs.clients.add("RvsecWtgClient");
//		Configs.project = apk;
//		Configs.benchmarkName = "cryptoapp.apk";
//		Configs.apiLevel = "android-29";
//		Configs.sootAndroidDir = sootAndroidDir;
//		Configs.sdkDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk";
//		Configs.android = Configs.sdkDir+"/platforms/"+Configs.apiLevel+"/android.jar";
//		Configs.listenerSpecFile = sootAndroidDir+"/listeners.xml";
//		Configs.wtgSpecFile = sootAndroidDir+"/wtg.xml";
//		Configs.libraryPackageFile = sootAndroidDir+"/libPackages.txt";
//		Configs.resourceLocation = decompileAppDir.getAbsolutePath()+"/res";
//		Configs.manifestLocation = decompileAppDir.getAbsolutePath()+"/AndroidManifest.xml";
//		
//		Configs.pathoutfilename = "/home/pedro/tmp/rvsec-gator.json";
//		
//		
//		presto.android.Main.main(new String[0]);
////		presto.android.Main.parseArgs(args);
//	}

}
