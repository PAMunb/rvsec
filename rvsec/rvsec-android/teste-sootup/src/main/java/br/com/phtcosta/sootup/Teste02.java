package br.com.phtcosta.sootup;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import sootup.callgraph.CallGraph;
import sootup.callgraph.CallGraphAlgorithm;
import sootup.callgraph.ClassHierarchyAnalysisAlgorithm;
import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.core.model.SourceType;
import sootup.core.signatures.MethodSignature;
import sootup.core.signatures.PackageName;
import sootup.java.bytecode.inputlocation.ApkAnalysisInputLocation;
import sootup.java.core.JavaSootClass;
import sootup.java.core.JavaSootMethod;
import sootup.java.core.types.JavaClassType;
import sootup.java.core.views.JavaView;

public class Teste02 {

	public void execute(String apk) throws ClassNotFoundException {

		AnalysisInputLocation inputLocation = new ApkAnalysisInputLocation(Path.of(apk), SourceType.Application);
		JavaView view = new JavaView(inputLocation);
		System.out.println("view="+view);

		//br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity
//		Optional<JavaSootClass> class1 = view.getClass(new JavaClassType("MainActivity", new PackageName("br.unb.cic.cryptoapp")));
		Optional<JavaSootClass> class1 = view.getClass(new JavaClassType("MessageDigestActivity", new PackageName("br.unb.cic.cryptoapp.messagedigest")));
		if(class1.isPresent()) {
			System.out.println(class1.get());
			JavaSootClass mainActivity = class1.get();

			List<MethodSignature> entryMethodSignature = new ArrayList<>();
			for (JavaSootMethod sootMethod : mainActivity.getMethods()) {
				if(sootMethod.isConcrete()
						&& (sootMethod.isPublic() || sootMethod.isProtected())
						//&& !sootMethod.getName().equals("<init>")) {
						&& sootMethod.getName().equals("generateHash")) {
					System.out.println("entryMethodSignature="+sootMethod.getSignature());
					entryMethodSignature.add(sootMethod.getSignature());
				}
			}

			// Create type hierarchy and CHA
//		    final ViewTypeHierarchy typeHierarchy = new ViewTypeHierarchy(view);
//		    System.out.println(typeHierarchy.subclassesOf(mainActivity.getType()));
		    CallGraphAlgorithm cha = new ClassHierarchyAnalysisAlgorithm(view);
		    System.out.println("cha");

		    // Create CG by initializing CHA with entry method(s)
		    CallGraph cg = cha.initialize(entryMethodSignature);
		    System.out.println("cg ...");

//		    for(MethodSignature sig: entryMethodSignature) {
//		    	System.out.println("****************** sig: "+sig);
//		    	cg.callsFrom(sig).forEach(System.out::println);
//		    }

		    for (MethodSignature sig : cg.getMethodSignatures()) {
		    	if(sig.getDeclClassType().getFullyQualifiedName().contains("br.unb.cic.cryptoapp")) {
		    		System.out.println(sig+ "===="+sig.getDeclClassType()+"======="+sig.getType()+":::::::::::"+sig.getSubSignature());
		    	}
			}
		}


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
		Teste02 teste02 = new Teste02();
		try {
			teste02.execute(apk);
		} catch (ClassNotFoundException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

}
