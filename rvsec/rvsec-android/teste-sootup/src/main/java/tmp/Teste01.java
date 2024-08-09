package tmp;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import com.googlecode.dex2jar.tools.Dex2jarCmd;

import sootup.callgraph.CallGraph;
import sootup.callgraph.CallGraphAlgorithm;
import sootup.callgraph.ClassHierarchyAnalysisAlgorithm;
import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.model.SourceType;
import sootup.core.signatures.MethodSignature;
import sootup.java.bytecode.inputlocation.JavaClassPathAnalysisInputLocation;
import sootup.java.core.JavaSootClass;
import sootup.java.core.JavaSootMethod;
import sootup.java.core.views.JavaView;

public class Teste01 {

	public void execute(String apkPath, String mopSpecsDir, String androidPlatformsDir, String rtJarPath, String sourcesAndSinksFile) {
		String jarPath = dex2jar(Path.of(apkPath)); 
		Path new_path = Paths.get(jarPath);

		List<AnalysisInputLocation> inputLocations = new ArrayList<>();
//	    inputLocations.add(new JavaModulePathAnalysisInputLocation(new_path));
		inputLocations.add(new JavaClassPathAnalysisInputLocation(new_path.toString(), SourceType.Application));
		inputLocations.add(new JavaClassPathAnalysisInputLocation("/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms/android-29/android.jar", SourceType.Library));
//		inputLocations.add(new JavaClassPathAnalysisInputLocation("/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms-sable/android-29/android.jar", SourceType.Library));
//		inputLocations.add(new ArchiveBasedAnalysisInputLocation(Path.of("/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms-sable"), SourceType.Library));
//		inputLocations.add(new JavaClassPathAnalysisInputLocation("/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms-sable"));
//		inputLocations.add(new JavaModulePathAnalysisInputLocation(Path.of("/home/pedro/desenvolvimento/aplicativos/android/platforms-sable/android-29/android.jar")));
//	    inputLocations.add(new JavaClassPathAnalysisInputLocation("/home/pedro/desenvolvimento/aplicativos/android/platforms/android-29/android.jar"));
		inputLocations.add(new JavaClassPathAnalysisInputLocation("/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar", SourceType.Library)); // add rt.jar
//		inputLocations.add(new DefaultRTJarAnalysisInputLocation(SourceType.Library)); precisa de JAVA_HOME

		JavaView view = new JavaView(inputLocations);

		List<MethodSignature> entryPoints = new ArrayList<>();
		List<MethodSignature> mopTmp = new ArrayList<>();
		for (JavaSootClass clazz : view.getClasses()) {
			if (clazz.getName().contains("cryptoapp")
//					&& clazz.getName().contains("Activity") 
					&& !clazz.getName().startsWith("br.unb.cic.cryptoapp.R")) {
				System.out.println("Clazz: " + clazz.getName());
				for (JavaSootMethod method : clazz.getMethods()) {
					System.out.println("\t method=" + method.getName());

					if (method.isConcrete() && (method.isPublic() || method.isProtected())) {
						System.out.println("\t %%% entrypoint:" + method.getName());
						entryPoints.add(method.getSignature());
					}

					if (method.getName().equals("hash")) {
						mopTmp.add(method.getSignature());
						System.out.println("\t*** MessageDigest:::" + method);
						if (method.hasBody()) {
							for (Stmt stmt : method.getBody().getStmts()) {
								System.out.println("\t\t stmt=" + stmt);
							}
						} else {
							System.out.println("nao tem corpo");
						}
					}

//					if (method.hasBody()) {
//						for (Stmt stmt : method.getBody().getStmts()) {
//							System.out.println("\t\t stmt=" + stmt);
//						}
//					}
				}
			}
		}

		System.out.println("construindo call graph .....................");

		CallGraphAlgorithm cha = new ClassHierarchyAnalysisAlgorithm(view);
		CallGraph cg = cha.initialize(entryPoints);

//		CallGraphAlgorithm rta = new RapidTypeAnalysisAlgorithm(view);
//		CallGraph cg = rta.initialize(entryPoints);

//		Spark spark = new Spark.Builder(view, cg).vta(true).build();
//		spark.analyze();
//		CallGraph vtaCAllGraph = spark.getCallGraph();
		
		
		cg.getMethodSignatures().stream().filter(m -> m.toString().contains("MessageDigest")).forEach(System.out::println);
		
		System.out.println("------------- teste 01 ------------");
		for (MethodSignature mop : mopTmp) {
			System.out.println("MOP: "+mop);
			System.out.println("TO: "+cg.callsTo(mop));
			System.out.println("FROM: "+cg.callsFrom(mop));
		}
		
	}

	private String dex2jar(Path path) {
		String apkPath = path.toAbsolutePath().toString();
		String outDir = "./tmp/";
		int start = apkPath.lastIndexOf(File.separator);
		int end = apkPath.lastIndexOf(".apk");
		String outputFile = outDir + apkPath.substring(start + 1, end) + ".jar";
		Dex2jarCmd.main("-f", apkPath, "-o", outputFile);
		return outputFile;
	}

	public static void main(String[] args) {
		String mopSpecsDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources";

		String androidPlatformsDir = "/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms";
		String rtJarPath = "/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar";

		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/";
		String apk = baseDir + "cryptoapp.apk";

		String sourcesAndSinksFile = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-taint/SourcesAndSinks.txt";
//		String sinksFile = "";
		String callbacksFile = "";

		Teste01 t = new Teste01();
		try {
			t.execute(apk, mopSpecsDir, androidPlatformsDir, rtJarPath, sourcesAndSinksFile);
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
