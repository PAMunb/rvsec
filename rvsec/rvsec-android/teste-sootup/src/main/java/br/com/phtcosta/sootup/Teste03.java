package br.com.phtcosta.sootup;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import com.googlecode.dex2jar.tools.Dex2jarCmd;

import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.java.bytecode.inputlocation.JavaClassPathAnalysisInputLocation;
import sootup.java.core.JavaSootClass;
import sootup.java.core.JavaSootMethod;
import sootup.java.core.views.JavaView;

public class Teste03 {
	private String dex2jar(Path path) {
	    String apkPath = path.toAbsolutePath().toString();
	    String outDir = "./tmp/";
	    int start = apkPath.lastIndexOf(File.separator);
	    int end = apkPath.lastIndexOf(".apk");
	    String outputFile = outDir + apkPath.substring(start + 1, end) + ".jar";
	    Dex2jarCmd.main("-f", apkPath, "-o", outputFile);
	    return outputFile;
	  }
	public void execute(String apk) throws ClassNotFoundException {

//		AnalysisInputLocation inputLocation = new ApkAnalysisInputLocation(Path.of(apk), SourceType.Application);
//		JavaView view = new JavaView(inputLocation);
//		System.out.println("view="+view);

		String jarPath = dex2jar(Path.of(apk));
	    Path new_path = Paths.get(jarPath);

		List<AnalysisInputLocation> inputLocations = new ArrayList<>();
//	    inputLocations.add(new JavaModulePathAnalysisInputLocation(new_path));
		inputLocations.add(new JavaClassPathAnalysisInputLocation(new_path.toString()));
		inputLocations.add(new JavaClassPathAnalysisInputLocation("/home/pedro/desenvolvimento/aplicativos/android/platforms-sable/android-29/android.jar"));
//		inputLocations.add(new JavaModulePathAnalysisInputLocation(Path.of("/home/pedro/desenvolvimento/aplicativos/android/platforms-sable/android-29/android.jar")));
//	    inputLocations.add(new JavaClassPathAnalysisInputLocation("/home/pedro/desenvolvimento/aplicativos/android/platforms/android-29/android.jar"));
	    inputLocations.add(new JavaClassPathAnalysisInputLocation("/home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar")); // add rt.jar

	    JavaView view = new JavaView(inputLocations);

	    for (JavaSootClass clazz : view.getClasses()) {
			System.out.println("Clazz: "+clazz.getName());
			for (JavaSootMethod method : clazz.getMethods()) {
				System.out.println("\t method="+method.getName());
				for (Stmt stmt : method.getBody().getStmts()) {
					System.out.println("\t\t stmt="+stmt);
				}
			}
		}


////		Optional<JavaSootClass> class1 = view.getClass(new JavaClassType("MainActivity", new PackageName("br.unb.cic.cryptoapp")));
//		Optional<JavaSootClass> class1 = view.getClass(new JavaClassType("MessageDigestActivity", new PackageName("br.unb.cic.cryptoapp.messagedigest")));
//		if(class1.isPresent()) {
//			System.out.println(class1.get());
//			JavaSootClass mainActivity = class1.get();
//
//			List<MethodSignature> entryMethodSignature = new ArrayList<>();
//			for (JavaSootMethod sootMethod : mainActivity.getMethods()) {
//				if(sootMethod.isConcrete()
//						&& (sootMethod.isPublic() || sootMethod.isProtected())
//						//&& !sootMethod.getName().equals("<init>")) {
//						&& sootMethod.getName().equals("generateHash")) {
//					System.out.println("entryMethodSignature="+sootMethod.getSignature());
//					entryMethodSignature.add(sootMethod.getSignature());
//				}
//			}
//
////			Object entryMethod;
////			JimpleBasedInterproceduralCFG icfg = new JimpleBasedInterproceduralCFG(view, entryMethodSignature.get(0), false, false);
////			DefaultJimpleIDETabulationProblem problem = new DefaultJimpleIDETabulationProblem(icfg);
////			JimpleIFDSSolver<?, InterproceduralCFG<Stmt, SootMethod>> solver = new JimpleIFDSSolver(problem);
////			solver.solve();
//
//
//			// Create type hierarchy and CHA
////		    final ViewTypeHierarchy typeHierarchy = new ViewTypeHierarchy(view);
////		    System.out.println(typeHierarchy.subclassesOf(mainActivity.getType()));
////		    CallGraphAlgorithm cha = new ClassHierarchyAnalysisAlgorithm(view);
//			CallGraphAlgorithm cha = new RapidTypeAnalysisAlgorithm(view);
//
//		    System.out.println("cha");
//
//		    // Create CG by initializing CHA with entry method(s)
//		    CallGraph cg = cha.initialize(entryMethodSignature);
//		    System.out.println("cg ...");
//
////		    for(MethodSignature sig: entryMethodSignature) {
////		    	System.out.println("****************** sig: "+sig);
////		    	cg.callsFrom(sig).forEach(System.out::println);
////		    }
//
//		    for (MethodSignature sig : cg.getMethodSignatures()) {
//		    	//if(sig.getDeclClassType().getFullyQualifiedName().contains("br.unb.cic.cryptoapp")) {
//		    	if(sig.getDeclClassType().getFullyQualifiedName().contains("br.unb.cic.cryptoapp")) {
//		    		System.out.println(sig+ "===="+sig.getDeclClassType()+"======="+sig.getType()+":::::::::::"+sig.getSubSignature());
//		    		cg.callsFrom(sig).forEach(c -> System.out.println(" ***** "+c));
//		    	}
//			}
//		}


//		for (JavaSootClass clazz : view.getClasses()) {
//			System.out.println("Clazz: "+clazz.getName());
//			if(clazz.hasSuperclass()) {
//				Optional<JavaClassType> superclassOpt = clazz.getSuperclass();
//				if(superclassOpt.isPresent()) {
//					JavaClassType javaClassType = superclassOpt.get();
////					Class<?> forName = Class.forName(javaClassType.getFullyQualifiedName());
//					String name = javaClassType.getFullyQualifiedName();
//					if("androidx.appcompat.app.AppCompatActivity".equals(name) || "android.app.Activity".equals(name)) {
//						System.out.println("activity ................. ");
//					}
////					if(forName.isAssignableFrom(Activity.class)) {
////						System.out.println("activity ................. ");
////					}
//				}
//			}
//		}
	}

	public static void main(String[] args) {
		String apk = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/cryptoapp.apk";
		String apk_decoded = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/teste-sootup/cryptoapp";
		Teste03 teste02 = new Teste03();
		try {
			teste02.execute(apk);
		} catch (ClassNotFoundException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

}
