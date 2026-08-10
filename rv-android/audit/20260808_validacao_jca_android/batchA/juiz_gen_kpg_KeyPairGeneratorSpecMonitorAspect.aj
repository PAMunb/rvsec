package mop;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.SecureRandom;
import java.security.spec.AlgorithmParameterSpec;
import br.unb.cic.mop.eh.*;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;
import java.util.concurrent.*;
import java.util.concurrent.locks.*;
import java.util.*;

import java.lang.ref.*;
import org.aspectj.lang.*;

aspect BaseAspect {
	pointcut notwithin() :
	!within(sun..*) &&
	!within(java..*) &&
	!within(javax..*) &&
	!within(com.sun..*) &&
	!within(org.dacapo.harness..*) &&
	!within(org.apache.commons..*) &&
	!within(org.apache.geronimo..*) &&
	!within(net.sf.cglib..*) &&
	!within(mop..*) &&
	!within(javamoprt..*) &&
	!within(rvmonitorrt..*) &&
	!within(com.runtimeverification..*);
}

public aspect KeyPairGeneratorSpecMonitorAspect implements com.runtimeverification.rvmonitor.java.rt.RVMObject {
	public KeyPairGeneratorSpecMonitorAspect(){
	}

	// Declarations for the Lock
	static ReentrantLock KeyPairGeneratorSpec_MOPLock = new ReentrantLock();
	static Condition KeyPairGeneratorSpec_MOPLock_cond = KeyPairGeneratorSpec_MOPLock.newCondition();

	pointcut MOP_CommonPointCut() : !within(com.runtimeverification.rvmonitor.java.rt.RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
	pointcut KeyPairGeneratorSpec_g1(String alg) : (call(public static KeyPairGenerator KeyPairGenerator.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (KeyPairGenerator k) : KeyPairGeneratorSpec_g1(alg) {
		//KeyPairGeneratorSpec_g1
		KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g1Event(alg, k);
		//KeyPairGeneratorSpec_g3
		KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g3Event(alg, k);
	}

	pointcut KeyPairGeneratorSpec_g2(String alg, String provider) : (call(public static KeyPairGenerator KeyPairGenerator.getInstance(String, String)) && args(alg, provider)) && MOP_CommonPointCut();
	after (String alg, String provider) returning (KeyPairGenerator k) : KeyPairGeneratorSpec_g2(alg, provider) {
		KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_g2Event(alg, provider, k);
	}

	pointcut KeyPairGeneratorSpec_init1(int keySize, KeyPairGenerator k) : (call(public void KeyPairGenerator.initialize(int)) && args(keySize) && target(k)) && MOP_CommonPointCut();
	after (int keySize, KeyPairGenerator k) : KeyPairGeneratorSpec_init1(keySize, k) {
		//KeyPairGeneratorSpec_init1
		KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init1Event(keySize, k);
		//KeyPairGeneratorSpec_initError
		KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(keySize, k);
	}

	pointcut KeyPairGeneratorSpec_init2(int keySize, SecureRandom random, KeyPairGenerator k) : (call(public void KeyPairGenerator.initialize(int, SecureRandom)) && args(keySize, random) && target(k)) && MOP_CommonPointCut();
	after (int keySize, SecureRandom random, KeyPairGenerator k) : KeyPairGeneratorSpec_init2(keySize, random, k) {
		KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init2Event(keySize, random, k);
	}

	pointcut KeyPairGeneratorSpec_init3(AlgorithmParameterSpec params, KeyPairGenerator k) : (call(public void KeyPairGenerator.initialize(AlgorithmParameterSpec)) && args(params) && target(k)) && MOP_CommonPointCut();
	after (AlgorithmParameterSpec params, KeyPairGenerator k) : KeyPairGeneratorSpec_init3(params, k) {
		KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init3Event(params, k);
	}

	pointcut KeyPairGeneratorSpec_init4(AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) : (call(public void KeyPairGenerator.initialize(AlgorithmParameterSpec, SecureRandom)) && args(params, random) && target(k)) && MOP_CommonPointCut();
	after (AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) : KeyPairGeneratorSpec_init4(params, random, k) {
		KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_init4Event(params, random, k);
	}

	pointcut KeyPairGeneratorSpec_gen(KeyPairGenerator k) : ((call(public KeyPair KeyPairGenerator.generateKeyPair()) || call(public KeyPair KeyPairGenerator.genKeyPair())) && target(k)) && MOP_CommonPointCut();
	after (KeyPairGenerator k) returning (KeyPair keyPair) : KeyPairGeneratorSpec_gen(k) {
		KeyPairGeneratorSpecRuntimeMonitor.KeyPairGeneratorSpec_genEvent(k, keyPair);
	}

}
