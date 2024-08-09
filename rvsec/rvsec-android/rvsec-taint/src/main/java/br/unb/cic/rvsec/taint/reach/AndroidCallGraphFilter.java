package br.unb.cic.rvsec.taint.reach;

import java.util.HashSet;
import java.util.Set;

import br.unb.cic.rvsec.taint.model.ApkInfo;
import br.unb.cic.rvsec.taint.util.AndroidUtil;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;

//TODO implementar direto soot.jimple.toolkits.callgraph.Filter?
public class AndroidCallGraphFilter implements CallGraphFilter {
		
	private Set<SootClass> validClasses = new HashSet<>();
	private Set<SootMethod> mopMethods;

//	public AndroidCallGraphFilter(String appPackageName) {
//		for (SootClass sootClass : Scene.v().getApplicationClasses()) {
//			if (!sootClass.getName().contains(appPackageName) 
//					|| sootClass.getName().contains(appPackageName + ".R") 
//					|| sootClass.getName().contains(appPackageName + ".BuildConfig"))
//				continue;
//			validClasses.add(sootClass);
//		}
//	}
	
	public AndroidCallGraphFilter(ApkInfo apkInfo, Set<SootMethod> mopMethods) {
		this.mopMethods = mopMethods;
		for (SootClass clazz : Scene.v().getApplicationClasses()) {
			if (!AndroidUtil.isAppClass(clazz, apkInfo)) {
				continue;
			}
			validClasses.add(clazz);
		}
		for (SootMethod method : mopMethods) {
			validClasses.add(method.getDeclaringClass());
		}
	}
	
	@Override
	public boolean isValidEdge(soot.jimple.toolkits.callgraph.Edge sEdge) {
		if (!sEdge.src().getDeclaringClass().isApplicationClass() 
				|| !isValidMethod(sEdge.src()) 
				|| !isValidMethod(sEdge.tgt()))
			return false;
		boolean flag = validClasses.contains(sEdge.src().getDeclaringClass());
		flag |= validClasses.contains(sEdge.tgt().getDeclaringClass());
		return flag;
	}

	public boolean isValidMethod(SootMethod sootMethod) {
		if(mopMethods.contains(sootMethod)) {
			return true;
		}
		if (AndroidUtil.isAndroidMethod(sootMethod) 
				|| sootMethod.getDeclaringClass().getPackageName().startsWith("java")
				|| sootMethod.getDeclaringClass().getPackageName().startsWith("sun.")
				|| sootMethod.getDeclaringClass().getPackageName().startsWith("com.sun")
				|| sootMethod.toString().contains("<init>") 
				|| sootMethod.toString().contains("<clinit>") 
				|| sootMethod.getName().equals("dummyMainMethod"))
			return false;
		return true;
	}

	public Set<SootClass> getValidClasses() {
		return validClasses;
	}
	
}
