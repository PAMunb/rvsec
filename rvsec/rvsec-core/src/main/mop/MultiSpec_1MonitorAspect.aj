package mop;
import javax.crypto.CipherInputStream;
import java.io.InputStream;
import javax.crypto.Cipher;
import br.unb.cic.mop.eh.*;
import br.unb.cic.mop.ExecutionContext;
import javax.crypto.CipherOutputStream;
import java.io.OutputStream;
import java.security.Provider;
import java.security.Key;
import java.security.SecureRandom;
import java.security.spec.AlgorithmParameterSpec;
import java.nio.ByteBuffer;
import static br.unb.cic.mop.jca.util.CipherTransformationUtil.*;
import javax.crypto.spec.DHGenParameterSpec;
import javax.crypto.spec.GCMParameterSpec;
import javax.xml.crypto.dsig.spec.HMACParameterSpec;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.ManagerFactoryParameters;
import javax.net.ssl.KeyManager;
import java.security.KeyStore;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.KeyStore.ProtectionParameter;
import java.security.KeyStore.Entry;
import javax.crypto.Mac;
import java.security.MessageDigest;
import java.util.List;
import br.unb.cic.mop.ExecutionContext.Property;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.PBEParameterSpec;
import java.util.stream.IntStream;
import javax.crypto.spec.SecretKeySpec;
import java.security.Signature;
import java.security.cert.Certificate;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLEngine;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
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

public aspect MultiSpec_1MonitorAspect implements com.runtimeverification.rvmonitor.java.rt.RVMObject {
	public MultiSpec_1MonitorAspect(){
	}

	// advices for Statistics
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start HMACParameterSpecSpec ==");
		System.err.println("#monitors: " + HMACParameterSpecSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + HMACParameterSpecSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + HMACParameterSpecSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - c: " + HMACParameterSpecSpecMonitor.getEventCounters().get("c"));
		System.err.println("#category - prop 1 - fail: " + HMACParameterSpecSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + HMACParameterSpecSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end HMACParameterSpecSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start CipherInputStreamSpec ==");
		System.err.println("#monitors: " + CipherInputStreamSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + CipherInputStreamSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + CipherInputStreamSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - r2: " + CipherInputStreamSpecMonitor.getEventCounters().get("r2"));
		System.err.println("#event - cl1: " + CipherInputStreamSpecMonitor.getEventCounters().get("cl1"));
		System.err.println("#event - c1: " + CipherInputStreamSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#event - r1: " + CipherInputStreamSpecMonitor.getEventCounters().get("r1"));
		System.err.println("#category - prop 1 - fail: " + CipherInputStreamSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("==end CipherInputStreamSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start KeyGeneratorSpec ==");
		System.err.println("#monitors: " + KeyGeneratorSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + KeyGeneratorSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + KeyGeneratorSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - init: " + KeyGeneratorSpecMonitor.getEventCounters().get("init"));
		System.err.println("#event - g1: " + KeyGeneratorSpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - g2: " + KeyGeneratorSpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - g3: " + KeyGeneratorSpecMonitor.getEventCounters().get("g3"));
		System.err.println("#event - gk1: " + KeyGeneratorSpecMonitor.getEventCounters().get("gk1"));
		System.err.println("#category - prop 1 - fail: " + KeyGeneratorSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + KeyGeneratorSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end KeyGeneratorSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start SecureRandomSpec ==");
		System.err.println("#monitors: " + SecureRandomSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + SecureRandomSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + SecureRandomSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - next2: " + SecureRandomSpecMonitor.getEventCounters().get("next2"));
		System.err.println("#event - next1: " + SecureRandomSpecMonitor.getEventCounters().get("next1"));
		System.err.println("#event - g1: " + SecureRandomSpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - g2: " + SecureRandomSpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - g3: " + SecureRandomSpecMonitor.getEventCounters().get("g3"));
		System.err.println("#event - g4: " + SecureRandomSpecMonitor.getEventCounters().get("g4"));
		System.err.println("#event - c1: " + SecureRandomSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#event - c2: " + SecureRandomSpecMonitor.getEventCounters().get("c2"));
		System.err.println("#event - setSeed3: " + SecureRandomSpecMonitor.getEventCounters().get("setSeed3"));
		System.err.println("#event - c3: " + SecureRandomSpecMonitor.getEventCounters().get("c3"));
		System.err.println("#event - setSeed2: " + SecureRandomSpecMonitor.getEventCounters().get("setSeed2"));
		System.err.println("#event - setSeed1: " + SecureRandomSpecMonitor.getEventCounters().get("setSeed1"));
		System.err.println("#event - genSeed: " + SecureRandomSpecMonitor.getEventCounters().get("genSeed"));
		System.err.println("#event - ints: " + SecureRandomSpecMonitor.getEventCounters().get("ints"));
		System.err.println("#event - next3: " + SecureRandomSpecMonitor.getEventCounters().get("next3"));
		System.err.println("#category - prop 1 - fail: " + SecureRandomSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match1: " + SecureRandomSpecMonitor.getCategoryCounters().get("match1"));
		System.err.println("==end SecureRandomSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start MessageDigestSpec ==");
		System.err.println("#monitors: " + MessageDigestSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + MessageDigestSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + MessageDigestSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - update: " + MessageDigestSpecMonitor.getEventCounters().get("update"));
		System.err.println("#event - reset: " + MessageDigestSpecMonitor.getEventCounters().get("reset"));
		System.err.println("#event - g1: " + MessageDigestSpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - g2: " + MessageDigestSpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - g3: " + MessageDigestSpecMonitor.getEventCounters().get("g3"));
		System.err.println("#event - g4: " + MessageDigestSpecMonitor.getEventCounters().get("g4"));
		System.err.println("#event - d1: " + MessageDigestSpecMonitor.getEventCounters().get("d1"));
		System.err.println("#event - d2: " + MessageDigestSpecMonitor.getEventCounters().get("d2"));
		System.err.println("#event - d3: " + MessageDigestSpecMonitor.getEventCounters().get("d3"));
		System.err.println("#category - prop 1 - fail: " + MessageDigestSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + MessageDigestSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end MessageDigestSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start KeyStoreSpec ==");
		System.err.println("#monitors: " + KeyStoreSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + KeyStoreSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + KeyStoreSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - ge1: " + KeyStoreSpecMonitor.getEventCounters().get("ge1"));
		System.err.println("#event - load: " + KeyStoreSpecMonitor.getEventCounters().get("load"));
		System.err.println("#event - g1: " + KeyStoreSpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - g2: " + KeyStoreSpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - store: " + KeyStoreSpecMonitor.getEventCounters().get("store"));
		System.err.println("#event - gk1: " + KeyStoreSpecMonitor.getEventCounters().get("gk1"));
		System.err.println("#event - se1: " + KeyStoreSpecMonitor.getEventCounters().get("se1"));
		System.err.println("#category - prop 1 - fail: " + KeyStoreSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + KeyStoreSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end KeyStoreSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start IvParameterSpecSpec ==");
		System.err.println("#monitors: " + IvParameterSpecSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + IvParameterSpecSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + IvParameterSpecSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - c3: " + IvParameterSpecSpecMonitor.getEventCounters().get("c3"));
		System.err.println("#event - c1: " + IvParameterSpecSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#event - c2: " + IvParameterSpecSpecMonitor.getEventCounters().get("c2"));
		System.err.println("#category - prop 1 - fail: " + IvParameterSpecSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + IvParameterSpecSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end IvParameterSpecSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start KeyPairGeneratorSpec ==");
		System.err.println("#monitors: " + KeyPairGeneratorSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + KeyPairGeneratorSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + KeyPairGeneratorSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - gen: " + KeyPairGeneratorSpecMonitor.getEventCounters().get("gen"));
		System.err.println("#event - init3: " + KeyPairGeneratorSpecMonitor.getEventCounters().get("init3"));
		System.err.println("#event - init2: " + KeyPairGeneratorSpecMonitor.getEventCounters().get("init2"));
		System.err.println("#event - g1: " + KeyPairGeneratorSpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - init1: " + KeyPairGeneratorSpecMonitor.getEventCounters().get("init1"));
		System.err.println("#event - g2: " + KeyPairGeneratorSpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - g3: " + KeyPairGeneratorSpecMonitor.getEventCounters().get("g3"));
		System.err.println("#event - initError: " + KeyPairGeneratorSpecMonitor.getEventCounters().get("initError"));
		System.err.println("#event - init4: " + KeyPairGeneratorSpecMonitor.getEventCounters().get("init4"));
		System.err.println("#category - prop 1 - fail: " + KeyPairGeneratorSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + KeyPairGeneratorSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end KeyPairGeneratorSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start PBEKeySpecSpec ==");
		System.err.println("#monitors: " + PBEKeySpecSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + PBEKeySpecSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + PBEKeySpecSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - err3: " + PBEKeySpecSpecMonitor.getEventCounters().get("err3"));
		System.err.println("#event - err2: " + PBEKeySpecSpecMonitor.getEventCounters().get("err2"));
		System.err.println("#event - err1: " + PBEKeySpecSpecMonitor.getEventCounters().get("err1"));
		System.err.println("#event - f1: " + PBEKeySpecSpecMonitor.getEventCounters().get("f1"));
		System.err.println("#event - f2: " + PBEKeySpecSpecMonitor.getEventCounters().get("f2"));
		System.err.println("#event - c1: " + PBEKeySpecSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#event - c2: " + PBEKeySpecSpecMonitor.getEventCounters().get("c2"));
		System.err.println("#category - prop 1 - fail: " + PBEKeySpecSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + PBEKeySpecSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end PBEKeySpecSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start SecretKeySpecSpec ==");
		System.err.println("#monitors: " + SecretKeySpecSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + SecretKeySpecSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + SecretKeySpecSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - c3: " + SecretKeySpecSpecMonitor.getEventCounters().get("c3"));
		System.err.println("#event - c4: " + SecretKeySpecSpecMonitor.getEventCounters().get("c4"));
		System.err.println("#event - c1: " + SecretKeySpecSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#event - c2: " + SecretKeySpecSpecMonitor.getEventCounters().get("c2"));
		System.err.println("#category - prop 1 - fail: " + SecretKeySpecSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + SecretKeySpecSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end SecretKeySpecSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start SignatureSpec ==");
		System.err.println("#monitors: " + SignatureSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + SignatureSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + SignatureSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - i1: " + SignatureSpecMonitor.getEventCounters().get("i1"));
		System.err.println("#event - i2: " + SignatureSpecMonitor.getEventCounters().get("i2"));
		System.err.println("#event - update: " + SignatureSpecMonitor.getEventCounters().get("update"));
		System.err.println("#event - g1: " + SignatureSpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - i3: " + SignatureSpecMonitor.getEventCounters().get("i3"));
		System.err.println("#event - g2: " + SignatureSpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - i4: " + SignatureSpecMonitor.getEventCounters().get("i4"));
		System.err.println("#event - v1: " + SignatureSpecMonitor.getEventCounters().get("v1"));
		System.err.println("#event - g3: " + SignatureSpecMonitor.getEventCounters().get("g3"));
		System.err.println("#event - v2: " + SignatureSpecMonitor.getEventCounters().get("v2"));
		System.err.println("#event - s1: " + SignatureSpecMonitor.getEventCounters().get("s1"));
		System.err.println("#event - s2: " + SignatureSpecMonitor.getEventCounters().get("s2"));
		System.err.println("#category - prop 1 - fail: " + SignatureSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + SignatureSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end SignatureSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start DHGenParameterSpecSpec ==");
		System.err.println("#monitors: " + DHGenParameterSpecSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + DHGenParameterSpecSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + DHGenParameterSpecSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - c1: " + DHGenParameterSpecSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#category - prop 1 - fail: " + DHGenParameterSpecSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + DHGenParameterSpecSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end DHGenParameterSpecSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start KeyPairSpec ==");
		System.err.println("#monitors: " + KeyPairSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + KeyPairSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + KeyPairSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - gpr: " + KeyPairSpecMonitor.getEventCounters().get("gpr"));
		System.err.println("#event - gpu: " + KeyPairSpecMonitor.getEventCounters().get("gpu"));
		System.err.println("#event - c1: " + KeyPairSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#category - prop 1 - fail: " + KeyPairSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + KeyPairSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end KeyPairSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start RandomStringPasswordSpec ==");
		System.err.println("#monitors: " + RandomStringPasswordSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + RandomStringPasswordSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + RandomStringPasswordSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - vo: " + RandomStringPasswordSpecMonitor.getEventCounters().get("vo"));
		System.err.println("#event - gb: " + RandomStringPasswordSpecMonitor.getEventCounters().get("gb"));
		System.err.println("#category - prop 1 - match: " + RandomStringPasswordSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end RandomStringPasswordSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start GCMParameterSpecSpec ==");
		System.err.println("#monitors: " + GCMParameterSpecSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + GCMParameterSpecSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + GCMParameterSpecSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - c1: " + GCMParameterSpecSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#category - prop 1 - fail: " + GCMParameterSpecSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + GCMParameterSpecSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end GCMParameterSpecSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start SecretKeySpec ==");
		System.err.println("#monitors: " + SecretKeySpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + SecretKeySpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + SecretKeySpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - e1: " + SecretKeySpecMonitor.getEventCounters().get("e1"));
		System.err.println("#category - prop 1 - match: " + SecretKeySpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end SecretKeySpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start PBEParameterSpecSpec ==");
		System.err.println("#monitors: " + PBEParameterSpecSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + PBEParameterSpecSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + PBEParameterSpecSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - c3: " + PBEParameterSpecSpecMonitor.getEventCounters().get("c3"));
		System.err.println("#event - c1: " + PBEParameterSpecSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#event - c2: " + PBEParameterSpecSpecMonitor.getEventCounters().get("c2"));
		System.err.println("#category - prop 1 - fail: " + PBEParameterSpecSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + PBEParameterSpecSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end PBEParameterSpecSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start KeyManagerFactorySpec ==");
		System.err.println("#monitors: " + KeyManagerFactorySpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + KeyManagerFactorySpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + KeyManagerFactorySpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - init: " + KeyManagerFactorySpecMonitor.getEventCounters().get("init"));
		System.err.println("#event - gkm1: " + KeyManagerFactorySpecMonitor.getEventCounters().get("gkm1"));
		System.err.println("#event - g1: " + KeyManagerFactorySpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - g2: " + KeyManagerFactorySpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - g3: " + KeyManagerFactorySpecMonitor.getEventCounters().get("g3"));
		System.err.println("#category - prop 1 - fail: " + KeyManagerFactorySpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match1: " + KeyManagerFactorySpecMonitor.getCategoryCounters().get("match1"));
		System.err.println("==end KeyManagerFactorySpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start SSLContextSpec ==");
		System.err.println("#monitors: " + SSLContextSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + SSLContextSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + SSLContextSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - init: " + SSLContextSpecMonitor.getEventCounters().get("init"));
		System.err.println("#event - engine: " + SSLContextSpecMonitor.getEventCounters().get("engine"));
		System.err.println("#event - unsafe_protocol: " + SSLContextSpecMonitor.getEventCounters().get("unsafe_protocol"));
		System.err.println("#event - g1: " + SSLContextSpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - g2: " + SSLContextSpecMonitor.getEventCounters().get("g2"));
		System.err.println("#category - prop 1 - fail: " + SSLContextSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match1: " + SSLContextSpecMonitor.getCategoryCounters().get("match1"));
		System.err.println("==end SSLContextSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start CipherOutputStreamSpec ==");
		System.err.println("#monitors: " + CipherOutputStreamSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + CipherOutputStreamSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + CipherOutputStreamSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - fl: " + CipherOutputStreamSpecMonitor.getEventCounters().get("fl"));
		System.err.println("#event - cl: " + CipherOutputStreamSpecMonitor.getEventCounters().get("cl"));
		System.err.println("#event - w1: " + CipherOutputStreamSpecMonitor.getEventCounters().get("w1"));
		System.err.println("#event - w2: " + CipherOutputStreamSpecMonitor.getEventCounters().get("w2"));
		System.err.println("#event - c1: " + CipherOutputStreamSpecMonitor.getEventCounters().get("c1"));
		System.err.println("#category - prop 1 - fail: " + CipherOutputStreamSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("==end CipherOutputStreamSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start MacSpec ==");
		System.err.println("#monitors: " + MacSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + MacSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + MacSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - i1: " + MacSpecMonitor.getEventCounters().get("i1"));
		System.err.println("#event - i2: " + MacSpecMonitor.getEventCounters().get("i2"));
		System.err.println("#event - update: " + MacSpecMonitor.getEventCounters().get("update"));
		System.err.println("#event - g1: " + MacSpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - g2: " + MacSpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - f1: " + MacSpecMonitor.getEventCounters().get("f1"));
		System.err.println("#event - g3: " + MacSpecMonitor.getEventCounters().get("g3"));
		System.err.println("#event - f2: " + MacSpecMonitor.getEventCounters().get("f2"));
		System.err.println("#category - prop 1 - fail: " + MacSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match: " + MacSpecMonitor.getCategoryCounters().get("match"));
		System.err.println("==end MacSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start CipherSpec ==");
		System.err.println("#monitors: " + CipherSpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + CipherSpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + CipherSpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - u5: " + CipherSpecMonitor.getEventCounters().get("u5"));
		System.err.println("#event - i1: " + CipherSpecMonitor.getEventCounters().get("i1"));
		System.err.println("#event - i2: " + CipherSpecMonitor.getEventCounters().get("i2"));
		System.err.println("#event - g1: " + CipherSpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - g2: " + CipherSpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - f1: " + CipherSpecMonitor.getEventCounters().get("f1"));
		System.err.println("#event - g3: " + CipherSpecMonitor.getEventCounters().get("g3"));
		System.err.println("#event - f2: " + CipherSpecMonitor.getEventCounters().get("f2"));
		System.err.println("#event - f3: " + CipherSpecMonitor.getEventCounters().get("f3"));
		System.err.println("#event - f5: " + CipherSpecMonitor.getEventCounters().get("f5"));
		System.err.println("#event - f6: " + CipherSpecMonitor.getEventCounters().get("f6"));
		System.err.println("#event - f7: " + CipherSpecMonitor.getEventCounters().get("f7"));
		System.err.println("#event - wkb1: " + CipherSpecMonitor.getEventCounters().get("wkb1"));
		System.err.println("#event - u1: " + CipherSpecMonitor.getEventCounters().get("u1"));
		System.err.println("#event - u2: " + CipherSpecMonitor.getEventCounters().get("u2"));
		System.err.println("#event - u3: " + CipherSpecMonitor.getEventCounters().get("u3"));
		System.err.println("#event - u4: " + CipherSpecMonitor.getEventCounters().get("u4"));
		System.err.println("#category - prop 1 - fail: " + CipherSpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match1: " + CipherSpecMonitor.getCategoryCounters().get("match1"));
		System.err.println("==end CipherSpec ==");
	}
	after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
		System.err.println("==start TrustManagerFactorySpec ==");
		System.err.println("#monitors: " + TrustManagerFactorySpecMonitor.getTotalMonitorCount());
		System.err.println("#collected monitors: " + TrustManagerFactorySpecMonitor.getCollectedMonitorCount());
		System.err.println("#terminated monitors: " + TrustManagerFactorySpecMonitor.getTerminatedMonitorCount());
		System.err.println("#event - init: " + TrustManagerFactorySpecMonitor.getEventCounters().get("init"));
		System.err.println("#event - gtm1: " + TrustManagerFactorySpecMonitor.getEventCounters().get("gtm1"));
		System.err.println("#event - g1: " + TrustManagerFactorySpecMonitor.getEventCounters().get("g1"));
		System.err.println("#event - g2: " + TrustManagerFactorySpecMonitor.getEventCounters().get("g2"));
		System.err.println("#event - g3: " + TrustManagerFactorySpecMonitor.getEventCounters().get("g3"));
		System.err.println("#category - prop 1 - fail: " + TrustManagerFactorySpecMonitor.getCategoryCounters().get("fail"));
		System.err.println("#category - prop 1 - match1: " + TrustManagerFactorySpecMonitor.getCategoryCounters().get("match1"));
		System.err.println("==end TrustManagerFactorySpec ==");
	}
	// Declarations for the Lock
	static ReentrantLock MultiSpec_1_MOPLock = new ReentrantLock();
	static Condition MultiSpec_1_MOPLock_cond = MultiSpec_1_MOPLock.newCondition();

	pointcut MOP_CommonPointCut() : !within(com.runtimeverification.rvmonitor.java.rt.RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
	pointcut TrustManagerFactorySpec_init(TrustManagerFactory mf) : ((call(public void TrustManagerFactory.init(KeyStore)) || call(public void TrustManagerFactory.init(ManagerFactoryParameters))) && target(mf)) && MOP_CommonPointCut();
	before (TrustManagerFactory mf) : TrustManagerFactorySpec_init(mf) {
		MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_initEvent(mf);
	}

	pointcut SignatureSpec_update(Signature s) : (call(public void Signature.update(..)) && target(s)) && MOP_CommonPointCut();
	before (Signature s) : SignatureSpec_update(s) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_updateEvent(s);
	}

	pointcut SignatureSpec_i4(PublicKey key, Signature s) : (call(public void Signature.initVerify(PublicKey)) && args(key) && target(s)) && MOP_CommonPointCut();
	before (PublicKey key, Signature s) : SignatureSpec_i4(key, s) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_i4Event(key, s);
	}

	pointcut SignatureSpec_i3(Certificate cert, Signature s) : (call(public void Signature.initVerify(Certificate)) && args(cert) && target(s)) && MOP_CommonPointCut();
	before (Certificate cert, Signature s) : SignatureSpec_i3(cert, s) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_i3Event(cert, s);
	}

	pointcut SignatureSpec_i2(PrivateKey privateKey, SecureRandom random, Signature s) : (call(public void Signature.initSign(PrivateKey, SecureRandom)) && args(privateKey, random) && target(s)) && MOP_CommonPointCut();
	before (PrivateKey privateKey, SecureRandom random, Signature s) : SignatureSpec_i2(privateKey, random, s) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_i2Event(privateKey, random, s);
	}

	pointcut SignatureSpec_i1(PrivateKey privateKey, Signature s) : (call(public void Signature.initSign(PrivateKey)) && args(privateKey) && target(s)) && MOP_CommonPointCut();
	before (PrivateKey privateKey, Signature s) : SignatureSpec_i1(privateKey, s) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_i1Event(privateKey, s);
	}

	pointcut SecureRandomSpec_next2(SecureRandom r, byte[] bytes) : (call(public void SecureRandom.nextBytes(byte[])) && args(bytes) && target(r)) && MOP_CommonPointCut();
	before (SecureRandom r, byte[] bytes) : SecureRandomSpec_next2(r, bytes) {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_next2Event(r, bytes);
	}

	pointcut SecureRandomSpec_next1(SecureRandom r, int randIntInRange) : (call(public int SecureRandom.nextInt(int)) && args(randIntInRange) && target(r)) && MOP_CommonPointCut();
	before (SecureRandom r, int randIntInRange) : SecureRandomSpec_next1(r, randIntInRange) {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_next1Event(r, randIntInRange);
	}

	pointcut MessageDigestSpec_reset(MessageDigest digest) : (call(void MessageDigest.reset()) && target(digest)) && MOP_CommonPointCut();
	before (MessageDigest digest) : MessageDigestSpec_reset(digest) {
		MultiSpec_1RuntimeMonitor.MessageDigestSpec_resetEvent(digest);
	}

	pointcut MacSpec_i1(java.security.Key key, Mac m) : (call(public void Mac.init(java.security.Key)) && args(key) && target(m)) && MOP_CommonPointCut();
	before (java.security.Key key, Mac m) : MacSpec_i1(key, m) {
		MultiSpec_1RuntimeMonitor.MacSpec_i1Event(key, m);
	}

	pointcut KeyStoreSpec_se1(KeyStore k) : (call(public void KeyStore.setEntry(String, Entry, ProtectionParameter)) && target(k)) && MOP_CommonPointCut();
	before (KeyStore k) : KeyStoreSpec_se1(k) {
		MultiSpec_1RuntimeMonitor.KeyStoreSpec_se1Event(k);
	}

	pointcut KeyStoreSpec_ge1(KeyStore k) : (call(public Entry KeyStore.getEntry(String, ProtectionParameter)) && target(k)) && MOP_CommonPointCut();
	before (KeyStore k) : KeyStoreSpec_ge1(k) {
		MultiSpec_1RuntimeMonitor.KeyStoreSpec_ge1Event(k);
	}

	pointcut KeyStoreSpec_store(KeyStore k) : (call(public void KeyStore.store(..)) && target(k)) && MOP_CommonPointCut();
	before (KeyStore k) : KeyStoreSpec_store(k) {
		MultiSpec_1RuntimeMonitor.KeyStoreSpec_storeEvent(k);
	}

	pointcut KeyStoreSpec_load(KeyStore k) : (call(public void KeyStore.load(..)) && target(k)) && MOP_CommonPointCut();
	before (KeyStore k) : KeyStoreSpec_load(k) {
		MultiSpec_1RuntimeMonitor.KeyStoreSpec_loadEvent(k);
	}

	pointcut KeyManagerFactorySpec_init(KeyManagerFactory k) : ((call(public void KeyManagerFactory.init(KeyStore, char[])) || call(public void KeyManagerFactory.init(ManagerFactoryParameters))) && target(k)) && MOP_CommonPointCut();
	before (KeyManagerFactory k) : KeyManagerFactorySpec_init(k) {
		MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_initEvent(k);
	}

	pointcut KeyGeneratorSpec_init(KeyGenerator k) : ((call(public void KeyGenerator.init(int)) || call(public void KeyGenerator.init(int, SecureRandom)) || call(public void KeyGenerator.init(AlgorithmParameterSpec)) || call(public void KeyGenerator.init(AlgorithmParameterSpec, SecureRandom)) || call(public void KeyGenerator.init(SecureRandom))) && target(k)) && MOP_CommonPointCut();
	before (KeyGenerator k) : KeyGeneratorSpec_init(k) {
		MultiSpec_1RuntimeMonitor.KeyGeneratorSpec_initEvent(k);
	}

	pointcut CipherSpec_i2(int mode, Key key, Cipher c) : (call(public void Cipher.init(int, Key, ..)) && args(mode, key, ..) && target(c)) && MOP_CommonPointCut();
	before (int mode, Key key, Cipher c) : CipherSpec_i2(mode, key, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_i2Event(mode, key, c);
	}

	pointcut CipherSpec_i1(int mode, Certificate cert, Cipher c) : (call(public void Cipher.init(int, Certificate, ..)) && args(mode, cert, ..) && target(c)) && MOP_CommonPointCut();
	before (int mode, Certificate cert, Cipher c) : CipherSpec_i1(mode, cert, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_i1Event(mode, cert, c);
	}

	pointcut CipherInputStreamSpec_c1() : (call(public CipherInputStream.new(InputStream, Cipher))) && MOP_CommonPointCut();
	after () : CipherInputStreamSpec_c1() {
		MultiSpec_1RuntimeMonitor.CipherInputStreamSpec_c1Event();
	}

	pointcut CipherInputStreamSpec_r1() : (call(public int CipherInputStream.read()) || call(public int CipherInputStream.read(byte[]))) && MOP_CommonPointCut();
	after () : CipherInputStreamSpec_r1() {
		MultiSpec_1RuntimeMonitor.CipherInputStreamSpec_r1Event();
	}

	pointcut CipherInputStreamSpec_r2(byte[] arr, int offset, int len) : (call(public int CipherInputStream.read(byte[], int, int)) && args(arr, offset, len)) && MOP_CommonPointCut();
	after (byte[] arr, int offset, int len) : CipherInputStreamSpec_r2(arr, offset, len) {
		MultiSpec_1RuntimeMonitor.CipherInputStreamSpec_r2Event(arr, offset, len);
	}

	pointcut CipherInputStreamSpec_cl1() : (call(public void CipherInputStream.close())) && MOP_CommonPointCut();
	after () : CipherInputStreamSpec_cl1() {
		MultiSpec_1RuntimeMonitor.CipherInputStreamSpec_cl1Event();
	}

	pointcut CipherOutputStreamSpec_c1() : (call(public CipherOutputStream.new(OutputStream, Cipher))) && MOP_CommonPointCut();
	after () : CipherOutputStreamSpec_c1() {
		MultiSpec_1RuntimeMonitor.CipherOutputStreamSpec_c1Event();
	}

	pointcut CipherOutputStreamSpec_w1() : (call(public void CipherOutputStream.write(int)) || call(public void CipherOutputStream.write(byte[]))) && MOP_CommonPointCut();
	after () : CipherOutputStreamSpec_w1() {
		MultiSpec_1RuntimeMonitor.CipherOutputStreamSpec_w1Event();
	}

	pointcut CipherOutputStreamSpec_w2(byte[] b, int off, int len) : (call(public void CipherOutputStream.write(byte[], int, int)) && args(b, off, len)) && MOP_CommonPointCut();
	after (byte[] b, int off, int len) : CipherOutputStreamSpec_w2(b, off, len) {
		MultiSpec_1RuntimeMonitor.CipherOutputStreamSpec_w2Event(b, off, len);
	}

	pointcut CipherOutputStreamSpec_fl() : (call(public void CipherOutputStream.flush())) && MOP_CommonPointCut();
	after () : CipherOutputStreamSpec_fl() {
		MultiSpec_1RuntimeMonitor.CipherOutputStreamSpec_flEvent();
	}

	pointcut CipherOutputStreamSpec_cl() : (call(public void CipherOutputStream.close())) && MOP_CommonPointCut();
	after () : CipherOutputStreamSpec_cl() {
		MultiSpec_1RuntimeMonitor.CipherOutputStreamSpec_clEvent();
	}

	pointcut CipherSpec_g1(String transformation) : (call(public static Cipher Cipher.getInstance(String)) && args(transformation)) && MOP_CommonPointCut();
	after (String transformation) returning (Cipher c) : CipherSpec_g1(transformation) {
		//CipherSpec_g1
		MultiSpec_1RuntimeMonitor.CipherSpec_g1Event(transformation, c);
		//CipherSpec_g3
		MultiSpec_1RuntimeMonitor.CipherSpec_g3Event(transformation, c);
	}

	pointcut CipherSpec_g2(String transformation, Object provider) : (call(public static Cipher Cipher.getInstance(String, Object+)) && args(transformation, provider)) && MOP_CommonPointCut();
	after (String transformation, Object provider) returning (Cipher c) : CipherSpec_g2(transformation, provider) {
		MultiSpec_1RuntimeMonitor.CipherSpec_g2Event(transformation, provider, c);
	}

	pointcut CipherSpec_u1(byte[] plainText, Cipher c) : (call(public byte[] Cipher.update(byte[])) && args(plainText) && target(c)) && MOP_CommonPointCut();
	after (byte[] plainText, Cipher c) returning (byte[] cipherText) : CipherSpec_u1(plainText, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_u1Event(plainText, c, cipherText);
	}

	pointcut CipherSpec_u2(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, Cipher c) : (call(public byte[] Cipher.update(byte[], int, int)) && args(plainText, prePlainTextOffset, prePlainTextLen) && target(c)) && MOP_CommonPointCut();
	after (byte[] plainText, int prePlainTextOffset, int prePlainTextLen, Cipher c) returning (byte[] cipherText) : CipherSpec_u2(plainText, prePlainTextOffset, prePlainTextLen, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_u2Event(plainText, prePlainTextOffset, prePlainTextLen, c, cipherText);
	}

	pointcut CipherSpec_u3(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, Cipher c) : (call(public int Cipher.update(byte[], int, int, byte[])) && args(plainText, prePlainTextOffset, prePlainTextLen, cipherText) && target(c)) && MOP_CommonPointCut();
	after (byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, Cipher c) : CipherSpec_u3(plainText, prePlainTextOffset, prePlainTextLen, cipherText, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_u3Event(plainText, prePlainTextOffset, prePlainTextLen, cipherText, c);
	}

	pointcut CipherSpec_u4(byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, int outputOffset, Cipher c) : (call(public int Cipher.update(byte[], int, int, byte[], int)) && args(plainText, prePlainTextOffset, prePlainTextLen, cipherText, outputOffset) && target(c)) && MOP_CommonPointCut();
	after (byte[] plainText, int prePlainTextOffset, int prePlainTextLen, byte[] cipherText, int outputOffset, Cipher c) : CipherSpec_u4(plainText, prePlainTextOffset, prePlainTextLen, cipherText, outputOffset, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_u4Event(plainText, prePlainTextOffset, prePlainTextLen, cipherText, outputOffset, c);
	}

	pointcut CipherSpec_u5(ByteBuffer plainBuffer, ByteBuffer cipherBuffer, Cipher c) : (call(public int Cipher.update(ByteBuffer, ByteBuffer)) && args(plainBuffer, cipherBuffer) && target(c)) && MOP_CommonPointCut();
	after (ByteBuffer plainBuffer, ByteBuffer cipherBuffer, Cipher c) : CipherSpec_u5(plainBuffer, cipherBuffer, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_u5Event(plainBuffer, cipherBuffer, c);
	}

	pointcut CipherSpec_wkb1(Cipher c) : (call(byte[] Cipher.wrap(Key)) && target(c)) && MOP_CommonPointCut();
	after (Cipher c) returning (byte[] wrappedKeyBytes) : CipherSpec_wkb1(c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_wkb1Event(c, wrappedKeyBytes);
	}

	pointcut CipherSpec_f1(Cipher c) : (call(public byte[] Cipher.doFinal()) && target(c)) && MOP_CommonPointCut();
	after (Cipher c) returning (byte[] cipherText) : CipherSpec_f1(c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_f1Event(c, cipherText);
	}

	pointcut CipherSpec_f2(Cipher c) : (call(public byte[] Cipher.doFinal(..)) && target(c)) && MOP_CommonPointCut();
	after (Cipher c) returning (byte[] cipherText) : CipherSpec_f2(c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_f2Event(c, cipherText);
	}

	pointcut CipherSpec_f3(byte[] cipherText, int offset, Cipher c) : (call(public int Cipher.doFinal(byte[], int)) && args(cipherText, offset) && target(c)) && MOP_CommonPointCut();
	after (byte[] cipherText, int offset, Cipher c) : CipherSpec_f3(cipherText, offset, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_f3Event(cipherText, offset, c);
	}

	pointcut CipherSpec_f5(byte[] plainText, int offset, int len, byte[] cipherText, Cipher c) : (call(public int Cipher.doFinal(byte[], int, int, byte[])) && args(plainText, offset, len, cipherText) && target(c)) && MOP_CommonPointCut();
	after (byte[] plainText, int offset, int len, byte[] cipherText, Cipher c) : CipherSpec_f5(plainText, offset, len, cipherText, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_f5Event(plainText, offset, len, cipherText, c);
	}

	pointcut CipherSpec_f6(byte[] plainText, int offset, int len, byte[] cipherText, int cipherOffset, Cipher c) : (call(public int Cipher.doFinal(byte[], int, int, byte[], int)) && args(plainText, offset, len, cipherText, cipherOffset) && target(c)) && MOP_CommonPointCut();
	after (byte[] plainText, int offset, int len, byte[] cipherText, int cipherOffset, Cipher c) : CipherSpec_f6(plainText, offset, len, cipherText, cipherOffset, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_f6Event(plainText, offset, len, cipherText, cipherOffset, c);
	}

	pointcut CipherSpec_f7(ByteBuffer plainTextBuffer, ByteBuffer cipherTextBuffer, Cipher c) : (call(public int Cipher.doFinal(ByteBuffer, ByteBuffer)) && args(plainTextBuffer, cipherTextBuffer) && target(c)) && MOP_CommonPointCut();
	after (ByteBuffer plainTextBuffer, ByteBuffer cipherTextBuffer, Cipher c) : CipherSpec_f7(plainTextBuffer, cipherTextBuffer, c) {
		MultiSpec_1RuntimeMonitor.CipherSpec_f7Event(plainTextBuffer, cipherTextBuffer, c);
	}

	pointcut DHGenParameterSpecSpec_c1(int primeSize, int exponentSize) : (call(public DHGenParameterSpec.new(int, int)) && args(primeSize, exponentSize)) && MOP_CommonPointCut();
	after (int primeSize, int exponentSize) returning (DHGenParameterSpec s) : DHGenParameterSpecSpec_c1(primeSize, exponentSize) {
		MultiSpec_1RuntimeMonitor.DHGenParameterSpecSpec_c1Event(primeSize, exponentSize, s);
	}

	pointcut GCMParameterSpecSpec_c1_3(int tagLen, byte[] src) : (call(public GCMParameterSpec.new(int, byte[])) && args(tagLen, src)) && MOP_CommonPointCut();
	after (int tagLen, byte[] src) returning (GCMParameterSpec s) : GCMParameterSpecSpec_c1_3(tagLen, src) {
		MultiSpec_1RuntimeMonitor.GCMParameterSpecSpec_c1Event(tagLen, src, s);
	}

	pointcut GCMParameterSpecSpec_c1_4(int tagLen, byte[] src, int offset, int len) : (call(public GCMParameterSpec.new(int, byte[], int, int)) && args(tagLen, src, offset, len)) && MOP_CommonPointCut();
	after (int tagLen, byte[] src, int offset, int len) returning (GCMParameterSpec s) : GCMParameterSpecSpec_c1_4(tagLen, src, offset, len) {
		MultiSpec_1RuntimeMonitor.GCMParameterSpecSpec_c1Event(tagLen, src, offset, len, s);
	}

	pointcut HMACParameterSpecSpec_c() : (call(public HMACParameterSpec.new(int))) && MOP_CommonPointCut();
	after () returning (HMACParameterSpec s) : HMACParameterSpecSpec_c() {
		MultiSpec_1RuntimeMonitor.HMACParameterSpecSpec_cEvent(s);
	}

	pointcut IvParameterSpecSpec_c1(byte[] iv) : (call(public IvParameterSpec.new(byte[])) && args(iv)) && MOP_CommonPointCut();
	after (byte[] iv) returning (IvParameterSpec s) : IvParameterSpecSpec_c1(iv) {
		//IvParameterSpecSpec_c1
		MultiSpec_1RuntimeMonitor.IvParameterSpecSpec_c1Event(iv, s);
		//IvParameterSpecSpec_c3
		MultiSpec_1RuntimeMonitor.IvParameterSpecSpec_c3Event(iv, s);
	}

	pointcut IvParameterSpecSpec_c2(byte[] iv, int offset, int len) : (call(public IvParameterSpec.new(byte[], int, int)) && args(iv, offset, len)) && MOP_CommonPointCut();
	after (byte[] iv, int offset, int len) returning (IvParameterSpec s) : IvParameterSpecSpec_c2(iv, offset, len) {
		MultiSpec_1RuntimeMonitor.IvParameterSpecSpec_c2Event(iv, offset, len, s);
	}

	pointcut KeyGeneratorSpec_g1(String alg) : (call(public static KeyGenerator KeyGenerator.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (KeyGenerator k) : KeyGeneratorSpec_g1(alg) {
		//KeyGeneratorSpec_g1
		MultiSpec_1RuntimeMonitor.KeyGeneratorSpec_g1Event(alg, k);
		//KeyGeneratorSpec_g3
		MultiSpec_1RuntimeMonitor.KeyGeneratorSpec_g3Event(alg, k);
	}

	pointcut KeyGeneratorSpec_g2(String alg, Object provider) : (call(public static KeyGenerator KeyGenerator.getInstance(String, Object+)) && args(alg, provider)) && MOP_CommonPointCut();
	after (String alg, Object provider) returning (KeyGenerator k) : KeyGeneratorSpec_g2(alg, provider) {
		MultiSpec_1RuntimeMonitor.KeyGeneratorSpec_g2Event(alg, provider, k);
	}

	pointcut KeyGeneratorSpec_gk1(KeyGenerator k) : (call(public SecretKey KeyGenerator.generateKey()) && target(k)) && MOP_CommonPointCut();
	after (KeyGenerator k) returning (SecretKey key) : KeyGeneratorSpec_gk1(k) {
		MultiSpec_1RuntimeMonitor.KeyGeneratorSpec_gk1Event(k, key);
	}

	pointcut KeyManagerFactorySpec_g1(String alg) : (call(public static KeyManagerFactory KeyManagerFactory.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (KeyManagerFactory k) : KeyManagerFactorySpec_g1(alg) {
		//KeyManagerFactorySpec_g1
		MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_g1Event(alg, k);
		//KeyManagerFactorySpec_g3
		MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_g3Event(alg, k);
	}

	pointcut KeyManagerFactorySpec_g2(String alg) : (call(public static KeyManagerFactory KeyManagerFactory.getInstance(String, ..)) && args(alg, *)) && MOP_CommonPointCut();
	after (String alg) returning (KeyManagerFactory k) : KeyManagerFactorySpec_g2(alg) {
		MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_g2Event(alg, k);
	}

	pointcut KeyManagerFactorySpec_gkm1(KeyManagerFactory k) : (call(public KeyManager[] KeyManagerFactory.getKeyManagers()) && target(k)) && MOP_CommonPointCut();
	after (KeyManagerFactory k) returning (KeyManager[] keyManager) : KeyManagerFactorySpec_gkm1(k) {
		MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_gkm1Event(k, keyManager);
	}

	pointcut KeyPairGeneratorSpec_g1(String alg) : (call(public static KeyPairGenerator KeyPairGenerator.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (KeyPairGenerator k) : KeyPairGeneratorSpec_g1(alg) {
		//KeyPairGeneratorSpec_g1
		MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_g1Event(alg, k);
		//KeyPairGeneratorSpec_g3
		MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_g3Event(alg, k);
	}

	pointcut KeyPairGeneratorSpec_g2(String alg, String provider) : (call(public static KeyPairGenerator KeyPairGenerator.getInstance(String, String)) && args(alg, provider)) && MOP_CommonPointCut();
	after (String alg, String provider) returning (KeyPairGenerator k) : KeyPairGeneratorSpec_g2(alg, provider) {
		MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_g2Event(alg, provider, k);
	}

	pointcut KeyPairGeneratorSpec_init1(int keySize, KeyPairGenerator k) : (call(public void KeyPairGenerator.initialize(int)) && args(keySize) && target(k)) && MOP_CommonPointCut();
	after (int keySize, KeyPairGenerator k) : KeyPairGeneratorSpec_init1(keySize, k) {
		//KeyPairGeneratorSpec_init1
		MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_init1Event(keySize, k);
		//KeyPairGeneratorSpec_initError
		MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_initErrorEvent(keySize, k);
	}

	pointcut KeyPairGeneratorSpec_init2(int keySize, SecureRandom random, KeyPairGenerator k) : (call(public void KeyPairGenerator.initialize(int, SecureRandom)) && args(keySize, random) && target(k)) && MOP_CommonPointCut();
	after (int keySize, SecureRandom random, KeyPairGenerator k) : KeyPairGeneratorSpec_init2(keySize, random, k) {
		MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_init2Event(keySize, random, k);
	}

	pointcut KeyPairGeneratorSpec_init3(AlgorithmParameterSpec params, KeyPairGenerator k) : (call(public void KeyPairGenerator.initialize(AlgorithmParameterSpec)) && args(params) && target(k)) && MOP_CommonPointCut();
	after (AlgorithmParameterSpec params, KeyPairGenerator k) : KeyPairGeneratorSpec_init3(params, k) {
		MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_init3Event(params, k);
	}

	pointcut KeyPairGeneratorSpec_init4(AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) : (call(public void KeyPairGenerator.initialize(AlgorithmParameterSpec, SecureRandom)) && args(params, random) && target(k)) && MOP_CommonPointCut();
	after (AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) : KeyPairGeneratorSpec_init4(params, random, k) {
		MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_init4Event(params, random, k);
	}

	pointcut KeyPairGeneratorSpec_gen(KeyPairGenerator k) : ((call(public KeyPair KeyPairGenerator.generateKeyPair()) || call(public KeyPair KeyPairGenerator.genKeyPair())) && target(k)) && MOP_CommonPointCut();
	after (KeyPairGenerator k) returning (KeyPair keyPair) : KeyPairGeneratorSpec_gen(k) {
		MultiSpec_1RuntimeMonitor.KeyPairGeneratorSpec_genEvent(k, keyPair);
	}

	pointcut KeyPairSpec_c1(PublicKey publicKey, PrivateKey privateKey) : (call(public KeyPair.new(PublicKey, PrivateKey)) && args(publicKey, privateKey)) && MOP_CommonPointCut();
	after (PublicKey publicKey, PrivateKey privateKey) returning (KeyPair kp) : KeyPairSpec_c1(publicKey, privateKey) {
		MultiSpec_1RuntimeMonitor.KeyPairSpec_c1Event(publicKey, privateKey, kp);
	}

	pointcut KeyPairSpec_gpu(KeyPair keyPair) : (call(public PublicKey KeyPair.getPublic()) && target(keyPair)) && MOP_CommonPointCut();
	after (KeyPair keyPair) returning (PublicKey publicKey) : KeyPairSpec_gpu(keyPair) {
		MultiSpec_1RuntimeMonitor.KeyPairSpec_gpuEvent(keyPair, publicKey);
	}

	pointcut KeyPairSpec_gpr(KeyPair keyPair) : (call(public PrivateKey KeyPair.getPrivate()) && target(keyPair)) && MOP_CommonPointCut();
	after (KeyPair keyPair) returning (PrivateKey privateKey) : KeyPairSpec_gpr(keyPair) {
		MultiSpec_1RuntimeMonitor.KeyPairSpec_gprEvent(keyPair, privateKey);
	}

	pointcut KeyStoreSpec_g1(String ksType) : (call(public static KeyStore KeyStore.getInstance(String)) && args(ksType)) && MOP_CommonPointCut();
	after (String ksType) returning (KeyStore k) : KeyStoreSpec_g1(ksType) {
		//KeyStoreSpec_g1
		MultiSpec_1RuntimeMonitor.KeyStoreSpec_g1Event(ksType, k);
		//KeyStoreSpec_g2
		MultiSpec_1RuntimeMonitor.KeyStoreSpec_g2Event(ksType, k);
	}

	pointcut KeyStoreSpec_gk1(KeyStore k) : (call(public Key KeyStore.getKey(String, char[])) && target(k)) && MOP_CommonPointCut();
	after (KeyStore k) returning (Key key) : KeyStoreSpec_gk1(k) {
		MultiSpec_1RuntimeMonitor.KeyStoreSpec_gk1Event(k, key);
	}

	pointcut MacSpec_g1(String alg) : (call(public static Mac Mac.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (Mac m) : MacSpec_g1(alg) {
		//MacSpec_g1
		MultiSpec_1RuntimeMonitor.MacSpec_g1Event(alg, m);
		//MacSpec_g3
		MultiSpec_1RuntimeMonitor.MacSpec_g3Event(alg, m);
	}

	pointcut MacSpec_g2(String alg, String provider) : (call(public static Mac Mac.getInstance(String, String)) && args(alg, provider)) && MOP_CommonPointCut();
	after (String alg, String provider) returning (Mac m) : MacSpec_g2(alg, provider) {
		MultiSpec_1RuntimeMonitor.MacSpec_g2Event(alg, provider, m);
	}

	pointcut MacSpec_i2(java.security.Key key, java.security.spec.AlgorithmParameterSpec params, Mac m) : (call(public void Mac.init(java.security.Key, java.security.spec.AlgorithmParameterSpec)) && args(key, params) && target(m)) && MOP_CommonPointCut();
	after (java.security.Key key, java.security.spec.AlgorithmParameterSpec params, Mac m) : MacSpec_i2(key, params, m) {
		MultiSpec_1RuntimeMonitor.MacSpec_i2Event(key, params, m);
	}

	pointcut MacSpec_update(Mac m) : (call(public void Mac.update(..)) && target(m)) && MOP_CommonPointCut();
	after (Mac m) : MacSpec_update(m) {
		MultiSpec_1RuntimeMonitor.MacSpec_updateEvent(m);
	}

	pointcut MacSpec_f1(Mac m) : ((call(byte[] Mac.doFinal(byte[])) || call(byte[] Mac.doFinal())) && target(m)) && MOP_CommonPointCut();
	after (Mac m) returning (byte[] output) : MacSpec_f1(m) {
		MultiSpec_1RuntimeMonitor.MacSpec_f1Event(m, output);
	}

	pointcut MacSpec_f2(byte[] output, int outOffset) : (call(void Mac.doFinal(byte[], int)) && args(output, outOffset) && target(m)) && MOP_CommonPointCut();
	after (byte[] output, int outOffset) : MacSpec_f2(output, outOffset) {
		MultiSpec_1RuntimeMonitor.MacSpec_f2Event(output, outOffset);
	}

	pointcut MessageDigestSpec_g1(String alg) : (call(public static MessageDigest MessageDigest.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (MessageDigest digest) : MessageDigestSpec_g1(alg) {
		//MessageDigestSpec_g1
		MultiSpec_1RuntimeMonitor.MessageDigestSpec_g1Event(alg, digest);
		//MessageDigestSpec_g4
		MultiSpec_1RuntimeMonitor.MessageDigestSpec_g4Event(alg, digest);
	}

	pointcut MessageDigestSpec_g2(String alg, String provider) : (call(public static MessageDigest MessageDigest.getInstance(String, String)) && args(alg, provider)) && MOP_CommonPointCut();
	after (String alg, String provider) returning (MessageDigest digest) : MessageDigestSpec_g2(alg, provider) {
		MultiSpec_1RuntimeMonitor.MessageDigestSpec_g2Event(alg, provider, digest);
	}

	pointcut MessageDigestSpec_g3(String alg, Provider provider) : (call(public static MessageDigest MessageDigest.getInstance(String, Provider)) && args(alg, provider)) && MOP_CommonPointCut();
	after (String alg, Provider provider) returning (MessageDigest digest) : MessageDigestSpec_g3(alg, provider) {
		MultiSpec_1RuntimeMonitor.MessageDigestSpec_g3Event(alg, provider, digest);
	}

	pointcut MessageDigestSpec_update(MessageDigest digest) : (call(void MessageDigest.update(..)) && target(digest)) && MOP_CommonPointCut();
	after (MessageDigest digest) : MessageDigestSpec_update(digest) {
		MultiSpec_1RuntimeMonitor.MessageDigestSpec_updateEvent(digest);
	}

	pointcut MessageDigestSpec_d1(MessageDigest digest) : (call(public byte[] MessageDigest.digest()) && target(digest)) && MOP_CommonPointCut();
	after (MessageDigest digest) returning (byte[] out) : MessageDigestSpec_d1(digest) {
		MultiSpec_1RuntimeMonitor.MessageDigestSpec_d1Event(digest, out);
	}

	pointcut MessageDigestSpec_d2(MessageDigest digest) : (call(public byte[] MessageDigest.digest(byte[])) && target(digest)) && MOP_CommonPointCut();
	after (MessageDigest digest) returning (byte[] out) : MessageDigestSpec_d2(digest) {
		MultiSpec_1RuntimeMonitor.MessageDigestSpec_d2Event(digest, out);
	}

	pointcut MessageDigestSpec_d3(byte[] out, int offset, int len, MessageDigest digest) : (call(public int MessageDigest.digest(byte[], int, int)) && args(out, offset, len) && target(digest)) && MOP_CommonPointCut();
	after (byte[] out, int offset, int len, MessageDigest digest) : MessageDigestSpec_d3(out, offset, len, digest) {
		MultiSpec_1RuntimeMonitor.MessageDigestSpec_d3Event(out, offset, len, digest);
	}

	pointcut PBEKeySpecSpec_f1(char[] password) : (call(public PBEKeySpec.new(char[])) && args(password)) && MOP_CommonPointCut();
	after (char[] password) : PBEKeySpecSpec_f1(password) {
		MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_f1Event(password);
	}

	pointcut PBEKeySpecSpec_f2(char[] password, byte[] salt, int keyLength) : (call(public PBEKeySpec.new(char[], byte[], int)) && args(password, salt, keyLength)) && MOP_CommonPointCut();
	after (char[] password, byte[] salt, int keyLength) : PBEKeySpecSpec_f2(password, salt, keyLength) {
		MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_f2Event(password, salt, keyLength);
	}

	pointcut PBEKeySpecSpec_c1(char[] password, byte[] salt, int iterationCount, int keyLength) : (call(public PBEKeySpec.new(char[], byte[], int, int)) && args(password, salt, iterationCount, keyLength)) && MOP_CommonPointCut();
	after (char[] password, byte[] salt, int iterationCount, int keyLength) returning (PBEKeySpec s) : PBEKeySpecSpec_c1(password, salt, iterationCount, keyLength) {
		//PBEKeySpecSpec_c1
		MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_c1Event(password, salt, iterationCount, keyLength, s);
		//PBEKeySpecSpec_err1
		MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_err1Event(password, salt, iterationCount, keyLength, s);
		//PBEKeySpecSpec_err2
		MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_err2Event(password, salt, iterationCount, keyLength, s);
		//PBEKeySpecSpec_err3
		MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_err3Event(password, salt, iterationCount, keyLength, s);
	}

	pointcut PBEKeySpecSpec_c2(PBEKeySpec s) : (call(public void PBEKeySpec.clearPassword()) && target(s)) && MOP_CommonPointCut();
	after (PBEKeySpec s) : PBEKeySpecSpec_c2(s) {
		MultiSpec_1RuntimeMonitor.PBEKeySpecSpec_c2Event(s);
	}

	pointcut PBEParameterSpecSpec_c1(byte[] salt, int iterationCount) : (call(public PBEParameterSpec.new(byte[], int)) && args(salt, iterationCount)) && MOP_CommonPointCut();
	after (byte[] salt, int iterationCount) returning (PBEParameterSpec s) : PBEParameterSpecSpec_c1(salt, iterationCount) {
		//PBEParameterSpecSpec_c1
		MultiSpec_1RuntimeMonitor.PBEParameterSpecSpec_c1Event(salt, iterationCount, s);
		//PBEParameterSpecSpec_c3
		MultiSpec_1RuntimeMonitor.PBEParameterSpecSpec_c3Event(salt, iterationCount, s);
	}

	pointcut PBEParameterSpecSpec_c2(byte[] salt, int iterationCount, AlgorithmParameterSpec paramSpec) : (call(public PBEParameterSpec.new(byte[], int, AlgorithmParameterSpec)) && args(salt, iterationCount, paramSpec)) && MOP_CommonPointCut();
	after (byte[] salt, int iterationCount, AlgorithmParameterSpec paramSpec) returning (PBEParameterSpec s) : PBEParameterSpecSpec_c2(salt, iterationCount, paramSpec) {
		MultiSpec_1RuntimeMonitor.PBEParameterSpecSpec_c2Event(salt, iterationCount, paramSpec, s);
	}

	pointcut RandomStringPasswordSpec_vo(Object obj) : (call(public static String String.valueOf(Object)) && args(obj)) && MOP_CommonPointCut();
	after (Object obj) returning (String s) : RandomStringPasswordSpec_vo(obj) {
		MultiSpec_1RuntimeMonitor.RandomStringPasswordSpec_voEvent(obj, s);
	}

	pointcut RandomStringPasswordSpec_gb(String s) : (call(public char[] String.toCharArray()) && target(s)) && MOP_CommonPointCut();
	after (String s) returning (char[] chars) : RandomStringPasswordSpec_gb(s) {
		MultiSpec_1RuntimeMonitor.RandomStringPasswordSpec_gbEvent(s, chars);
	}

	pointcut SecretKeySpec_e1(SecretKey secretKey) : (call(public byte[] SecretKey.getEncoded()) && target(secretKey)) && MOP_CommonPointCut();
	after (SecretKey secretKey) returning (byte[] key) : SecretKeySpec_e1(secretKey) {
		MultiSpec_1RuntimeMonitor.SecretKeySpec_e1Event(secretKey, key);
	}

	pointcut SecretKeySpecSpec_c1(byte[] keyMaterial, String keyAlgorithm) : (call(public SecretKeySpec.new(byte[], String)) && args(keyMaterial, keyAlgorithm)) && MOP_CommonPointCut();
	after (byte[] keyMaterial, String keyAlgorithm) returning (SecretKeySpec secretKeySpec) : SecretKeySpecSpec_c1(keyMaterial, keyAlgorithm) {
		//SecretKeySpecSpec_c1
		MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c1Event(keyMaterial, keyAlgorithm, secretKeySpec);
		//SecretKeySpecSpec_c3
		MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c3Event(keyMaterial, keyAlgorithm, secretKeySpec);
	}

	pointcut SecretKeySpecSpec_c2(byte[] keyMaterial, int offset, int len, String keyAlgorithm) : (call(public SecretKeySpec.new(byte[], int, int, String)) && args(keyMaterial, offset, len, keyAlgorithm)) && MOP_CommonPointCut();
	after (byte[] keyMaterial, int offset, int len, String keyAlgorithm) returning (SecretKeySpec secretKeySpec) : SecretKeySpecSpec_c2(keyMaterial, offset, len, keyAlgorithm) {
		//SecretKeySpecSpec_c2
		MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c2Event(keyMaterial, offset, len, keyAlgorithm, secretKeySpec);
		//SecretKeySpecSpec_c4
		MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c4Event(keyMaterial, offset, len, keyAlgorithm, secretKeySpec);
	}

	pointcut SecureRandomSpec_c1() : (call(public SecureRandom.new())) && MOP_CommonPointCut();
	after () returning (SecureRandom r) : SecureRandomSpec_c1() {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_c1Event(r);
	}

	pointcut SecureRandomSpec_c2(byte[] seed) : (call(public SecureRandom.new(byte[])) && args(seed)) && MOP_CommonPointCut();
	after (byte[] seed) returning (SecureRandom r) : SecureRandomSpec_c2(seed) {
		//SecureRandomSpec_c2
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_c2Event(seed, r);
		//SecureRandomSpec_c3
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_c3Event(seed, r);
	}

	pointcut SecureRandomSpec_g1(String alg) : (call(public static SecureRandom SecureRandom.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (SecureRandom r) : SecureRandomSpec_g1(alg) {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_g1Event(alg, r);
	}

	pointcut SecureRandomSpec_g2(String alg) : (call(public static SecureRandom SecureRandom.getInstance(String, ..)) && args(alg, *)) && MOP_CommonPointCut();
	after (String alg) returning (SecureRandom r) : SecureRandomSpec_g2(alg) {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_g2Event(alg, r);
	}

	pointcut SecureRandomSpec_g3() : (call(public static SecureRandom SecureRandom.getInstanceStrong())) && MOP_CommonPointCut();
	after () returning (SecureRandom r) : SecureRandomSpec_g3() {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_g3Event(r);
	}

	pointcut SecureRandomSpec_g4(String alg) : (call(public static SecureRandom SecureRandom.getInstance(String, ..)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (SecureRandom r) : SecureRandomSpec_g4(alg) {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_g4Event(alg, r);
	}

	pointcut SecureRandomSpec_setSeed1(SecureRandom r) : (call(public void SecureRandom.setSeed(long)) && target(r)) && MOP_CommonPointCut();
	after (SecureRandom r) : SecureRandomSpec_setSeed1(r) {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_setSeed1Event(r);
	}

	pointcut SecureRandomSpec_setSeed2(byte[] seed, SecureRandom r) : (call(public void SecureRandom.setSeed(byte[])) && args(seed) && target(r)) && MOP_CommonPointCut();
	after (byte[] seed, SecureRandom r) : SecureRandomSpec_setSeed2(seed, r) {
		//SecureRandomSpec_setSeed2
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_setSeed2Event(seed, r);
		//SecureRandomSpec_setSeed3
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_setSeed3Event(seed, r);
	}

	pointcut SecureRandomSpec_genSeed(SecureRandom r) : (call(public byte[] SecureRandom.generateSeed(int)) && target(r)) && MOP_CommonPointCut();
	after (SecureRandom r) returning (byte[] seed) : SecureRandomSpec_genSeed(r) {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_genSeedEvent(r, seed);
	}

	pointcut SecureRandomSpec_next3(SecureRandom r) : (call(public int SecureRandom.nextInt()) && target(r)) && MOP_CommonPointCut();
	after (SecureRandom r) returning (int randInt) : SecureRandomSpec_next3(r) {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_next3Event(r, randInt);
	}

	pointcut SecureRandomSpec_ints(SecureRandom r) : (call(public IntStream SecureRandom.ints(..)) && target(r)) && MOP_CommonPointCut();
	after (SecureRandom r) returning (IntStream stream) : SecureRandomSpec_ints(r) {
		MultiSpec_1RuntimeMonitor.SecureRandomSpec_intsEvent(r, stream);
	}

	pointcut SignatureSpec_g1(String alg) : (call(public static Signature Signature.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (Signature s) : SignatureSpec_g1(alg) {
		//SignatureSpec_g1
		MultiSpec_1RuntimeMonitor.SignatureSpec_g1Event(alg, s);
		//SignatureSpec_g3
		MultiSpec_1RuntimeMonitor.SignatureSpec_g3Event(alg, s);
	}

	pointcut SignatureSpec_g2(String alg, String provider) : (call(public static Signature Signature.getInstance(String, String)) && args(alg, provider)) && MOP_CommonPointCut();
	after (String alg, String provider) returning (Signature s) : SignatureSpec_g2(alg, provider) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_g2Event(alg, provider, s);
	}

	pointcut SignatureSpec_s1(Signature s) : (call(public byte Signature.sign()) && target(s)) && MOP_CommonPointCut();
	after (Signature s) returning (byte[] output) : SignatureSpec_s1(s) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_s1Event(s, output);
	}

	pointcut SignatureSpec_s2(byte[] output, int offset, int len, Signature s) : (call(public byte Signature.sign(byte[], int, int)) && args(output, offset, len) && target(s)) && MOP_CommonPointCut();
	after (byte[] output, int offset, int len, Signature s) : SignatureSpec_s2(output, offset, len, s) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_s2Event(output, offset, len, s);
	}

	pointcut SignatureSpec_v1(byte[] sign, Signature s) : (call(public boolean Signature.verify(byte[])) && args(sign) && target(s)) && MOP_CommonPointCut();
	after (byte[] sign, Signature s) returning (boolean signed) : SignatureSpec_v1(sign, s) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_v1Event(sign, s, signed);
	}

	pointcut SignatureSpec_v2(byte[] sign, int offset, int len, Signature s) : (call(public boolean Signature.verify(byte[], int, int)) && args(sign, offset, len) && target(s)) && MOP_CommonPointCut();
	after (byte[] sign, int offset, int len, Signature s) returning (boolean signed) : SignatureSpec_v2(sign, offset, len, s) {
		MultiSpec_1RuntimeMonitor.SignatureSpec_v2Event(sign, offset, len, s, signed);
	}

	pointcut SSLContextSpec_g1(String protocol) : (call(public static SSLContext SSLContext.getInstance(String)) && args(protocol)) && MOP_CommonPointCut();
	after (String protocol) returning (SSLContext ctx) : SSLContextSpec_g1(protocol) {
		MultiSpec_1RuntimeMonitor.SSLContextSpec_g1Event(protocol, ctx);
	}

	pointcut SSLContextSpec_g2(String protocol, String provider) : (call(public static SSLContext SSLContext.getInstance(String, String)) && args(protocol, provider)) && MOP_CommonPointCut();
	after (String protocol, String provider) returning (SSLContext ctx) : SSLContextSpec_g2(protocol, provider) {
		MultiSpec_1RuntimeMonitor.SSLContextSpec_g2Event(protocol, provider, ctx);
	}

	after (String protocol) : SSLContextSpec_g1(protocol) {
		MultiSpec_1RuntimeMonitor.SSLContextSpec_unsafe_protocolEvent(protocol);
	}

	pointcut SSLContextSpec_init(SSLContext ctx) : (call(public void SSLContext.init(KeyManager[], TrustManager[], SecureRandom)) && target(ctx)) && MOP_CommonPointCut();
	after (SSLContext ctx) : SSLContextSpec_init(ctx) {
		MultiSpec_1RuntimeMonitor.SSLContextSpec_initEvent(ctx);
	}

	pointcut SSLContextSpec_engine(SSLContext ctx) : (call(public void SSLContext.createSSLEngine(..)) && target(ctx)) && MOP_CommonPointCut();
	after (SSLContext ctx) returning (SSLEngine eng) : SSLContextSpec_engine(ctx) {
		MultiSpec_1RuntimeMonitor.SSLContextSpec_engineEvent(ctx, eng);
	}

	pointcut TrustManagerFactorySpec_g1(String alg) : (call(public static TrustManagerFactory TrustManagerFactory.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (TrustManagerFactory mf) : TrustManagerFactorySpec_g1(alg) {
		MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g1Event(alg, mf);
	}

	pointcut TrustManagerFactorySpec_g2(String alg) : (call(public static TrustManagerFactory TrustManagerFactory.getInstance(String, ..)) && args(alg, *)) && MOP_CommonPointCut();
	after (String alg) returning (TrustManagerFactory mf) : TrustManagerFactorySpec_g2(alg) {
		MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g2Event(alg, mf);
	}

	after (String alg) returning (TrustManagerFactory k) : TrustManagerFactorySpec_g1(alg) {
		MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g3Event(alg, k);
	}

	pointcut TrustManagerFactorySpec_gtm1(TrustManagerFactory k) : (call(public KeyManager[] TrustManagerFactory.getTrustManagers()) && target(k)) && MOP_CommonPointCut();
	after (TrustManagerFactory k) returning (TrustManager[][] trustManager) : TrustManagerFactorySpec_gtm1(k) {
		MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_gtm1Event(k, trustManager);
	}

}
