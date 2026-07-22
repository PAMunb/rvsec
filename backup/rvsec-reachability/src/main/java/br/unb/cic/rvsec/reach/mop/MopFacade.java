package br.unb.cic.rvsec.reach.mop;

import java.util.HashSet;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;
import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.util.AndroidUtil;
import javamop.util.MOPException;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.UnitPatchingChain;
import soot.jimple.InvokeExpr;
import soot.jimple.Stmt;

public class MopFacade {
	private static final Logger log = LoggerFactory.getLogger(MopFacade.class);

	private JavamopFacade javamopFacade = new JavamopFacade();

	public Set<SootMethod> getMopMethodsUsed(String mopSpecsDir, AppInfo apkInfo) throws MOPException {
		return getMopMethodsUsed(mopSpecsDir, apkInfo, true);
	}

	public Set<SootMethod> getMopMethodsUsed(String mopSpecsDir, AppInfo apkInfo, boolean checkOnlyInAppPackage) throws MOPException {
	    log.info("Retrieving MOP methods used ...");
	    log.debug("Check only in application package? "+checkOnlyInAppPackage);

	    Set<SootMethod> sootMopMethods = new HashSet<>();

	    Set<MopMethod> targetMethods = javamopFacade.listUsedMethods(mopSpecsDir, false);

	    for (SootClass c : Scene.v().getApplicationClasses()) {
	        if (checkOnlyInAppPackage && !AndroidUtil.isClassInApplicationPackage(c, apkInfo)) {
	            continue;
	        }
	        for (SootMethod m : c.getMethods()) {
	            sootMopMethods.addAll(findMopMethodsInMethod(m, targetMethods));
	        }
	    }

	    return sootMopMethods;
	}

	private Set<SootMethod> findMopMethodsInMethod(SootMethod m, Set<MopMethod> targetMethods) {
	    Set<SootMethod> targetMethodsInMethod = new HashSet<>();
	    if (!m.isConcrete()) {
            return targetMethodsInMethod;
        }
		UnitPatchingChain units = m.retrieveActiveBody().getUnits();
	    for (Unit unit : units) {
	        Stmt stmt = (Stmt) unit;
	        if (stmt.containsInvokeExpr()) {
	            InvokeExpr invokeExpr = stmt.getInvokeExpr();
	            if (isMop(invokeExpr, targetMethods)) {
	                targetMethodsInMethod.add(invokeExpr.getMethod());
	            }
	        }
	    }
	    return targetMethodsInMethod;
	}

	private boolean isMop(InvokeExpr invokeExpr, Set<MopMethod> targetMethods) {
		SootMethod invokeMethod = invokeExpr.getMethod();
		for (MopMethod mopMethod : targetMethods) {
			//TODO testar/comparar assinatura completa
			if (mopMethod.getClassName().equals(invokeMethod.getDeclaringClass().getName())
					&& mopMethod.getName().equals(invokeMethod.getName())) {
				return true;
			}
		}
		return false;
	}

}
