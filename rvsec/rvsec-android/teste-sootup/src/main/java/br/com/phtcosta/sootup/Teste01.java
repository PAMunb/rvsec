package br.com.phtcosta.sootup;

import java.nio.file.Path;

//import brut.androlib.ApkDecoder;
//import brut.androlib.exceptions.AndrolibException;
//import brut.directory.DirectoryException;
import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.model.SourceType;
import sootup.java.bytecode.inputlocation.ApkAnalysisInputLocation;
import sootup.java.core.JavaSootClass;
import sootup.java.core.JavaSootField;
import sootup.java.core.JavaSootMethod;
import sootup.java.core.views.JavaView;

public class Teste01 {

	public void execute(String apk) {
		AnalysisInputLocation inputLocation = new ApkAnalysisInputLocation(Path.of(apk), SourceType.Application);
		JavaView view = new JavaView(inputLocation);
		System.out.println("view=" + view);

		for (JavaSootClass clazz : view.getClasses()) {
			if (clazz.getName().contains("br.unb.cic.cryptoapp")) {
				System.out.println("Clazz: " + clazz.getName());

				for (JavaSootMethod method : clazz.getMethods()) {
					System.out.println("\t method=" + method.getName());
					for (Stmt stmt : method.getBody().getStmts()) {
						System.out.println("\t\t stmt=" + stmt);
//					if(stmt.containsInvokeExpr()) {
//						System.out.println("\t\t stmt="+stmt);
//					}
					}
				}

				for (JavaSootField field : clazz.getFields()) {
					System.out.println("FIELD="+field);
				}
			}
		}
	}


	private void teste01(String apk_decoded_dir) {
		Path of = Path.of(apk_decoded_dir, "res", "layout");
		for (String string : of.toFile().list()) {
			System.out.println(string);
		}
	}

	public static void main(String[] args) {
		String apk = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk";
		String apk_decoded = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/teste-sootup/cryptoapp";
		Teste01 teste01 = new Teste01();
		teste01.execute(apk);
//		teste01.teste01(apk_decoded);
	}

}
