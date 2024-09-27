package br.unb.cic.rvsec.reach.mop;

import java.util.HashSet;
import java.util.Iterator;
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
	private static Logger log = LoggerFactory.getLogger(MopFacade.class);
	
	public Set<SootMethod> getMopMethods(String mopSpecsDir, AppInfo apkInfo) throws MOPException {
		log.info("Retrieving methods used  in MOP specs ...");
		Set<SootMethod> sootMopMethods = new HashSet<>();

		JavamopFacade javamopFacade = new JavamopFacade();
		Set<MopMethod> mopMethods = javamopFacade.listUsedMethods(mopSpecsDir, false);

		for (SootClass c : Scene.v().getApplicationClasses()) {
			if (AndroidUtil.isClassInApplicationPackage(c, apkInfo)) {
//				System.out.println("CLASSE: " + c.getName());
				for (SootMethod m : c.getMethods()) {
					UnitPatchingChain units = m.retrieveActiveBody().getUnits();
                    for (Unit unit : units) {
                        Stmt stmt = (Stmt) unit;
                        if (stmt.containsInvokeExpr()) {
                            InvokeExpr invokeExpr = stmt.getInvokeExpr();
                            if (isMop(invokeExpr, mopMethods)) {
//								System.out.println("MOP ********************* " + invokeExpr.getMethod().getDeclaringClass().getName() + " :: " + invokeExpr.getMethod().getSubSignature());
                                sootMopMethods.add(invokeExpr.getMethod());
                            }
                        }
                    }
				}
			}
		}

		return sootMopMethods;
	}
	
	private boolean isMop(InvokeExpr invokeExpr, Set<MopMethod> mopMethods) {
		for (MopMethod mopMethod : mopMethods) {
			if (mopMethod.getClassName().equals(invokeExpr.getMethod().getDeclaringClass().getName()) 
					&& mopMethod.getName().equals(invokeExpr.getMethod().getName())) {
				return true;
			}
		}
		return false;
	}
}
