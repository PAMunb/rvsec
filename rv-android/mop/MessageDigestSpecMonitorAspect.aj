
import java.security.Provider;
import java.security.MessageDigest;
import java.util.List;
import br.unb.cic.mop.eh.*;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.ExecutionContext.Property;
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

public aspect MessageDigestSpecMonitorAspect implements com.runtimeverification.rvmonitor.java.rt.RVMObject {
	public MessageDigestSpecMonitorAspect(){
	}

	// advices for Statistics
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
	// Declarations for the Lock
	static ReentrantLock MessageDigestSpec_MOPLock = new ReentrantLock();
	static Condition MessageDigestSpec_MOPLock_cond = MessageDigestSpec_MOPLock.newCondition();

	pointcut MOP_CommonPointCut() : !within(com.runtimeverification.rvmonitor.java.rt.RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
	pointcut MessageDigestSpec_reset(MessageDigest digest) : (call(void MessageDigest.reset()) && target(digest)) && MOP_CommonPointCut();
	before (MessageDigest digest) : MessageDigestSpec_reset(digest) {
		MessageDigestSpecRuntimeMonitor.MessageDigestSpec_resetEvent(digest);
	}

	pointcut MessageDigestSpec_g1(String alg) : (call(public static MessageDigest MessageDigest.getInstance(String)) && args(alg)) && MOP_CommonPointCut();
	after (String alg) returning (MessageDigest digest) : MessageDigestSpec_g1(alg) {
		//MessageDigestSpec_g1
		MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g1Event(alg, digest);
		//MessageDigestSpec_g4
		MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g4Event(alg, digest);
	}

	pointcut MessageDigestSpec_g2(String alg, String provider) : (call(public static MessageDigest MessageDigest.getInstance(String, String)) && args(alg, provider)) && MOP_CommonPointCut();
	after (String alg, String provider) returning (MessageDigest digest) : MessageDigestSpec_g2(alg, provider) {
		MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g2Event(alg, provider, digest);
	}

	pointcut MessageDigestSpec_g3(String alg, Provider provider) : (call(public static MessageDigest MessageDigest.getInstance(String, Provider)) && args(alg, provider)) && MOP_CommonPointCut();
	after (String alg, Provider provider) returning (MessageDigest digest) : MessageDigestSpec_g3(alg, provider) {
		MessageDigestSpecRuntimeMonitor.MessageDigestSpec_g3Event(alg, provider, digest);
	}

	pointcut MessageDigestSpec_update(MessageDigest digest) : (call(void MessageDigest.update(..)) && target(digest)) && MOP_CommonPointCut();
	after (MessageDigest digest) : MessageDigestSpec_update(digest) {
		MessageDigestSpecRuntimeMonitor.MessageDigestSpec_updateEvent(digest);
	}

	pointcut MessageDigestSpec_d1(MessageDigest digest) : (call(public byte[] MessageDigest.digest()) && target(digest)) && MOP_CommonPointCut();
	after (MessageDigest digest) returning (byte[] out) : MessageDigestSpec_d1(digest) {
		MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d1Event(digest, out);
	}

	pointcut MessageDigestSpec_d2(MessageDigest digest) : (call(public byte[] MessageDigest.digest(byte[])) && target(digest)) && MOP_CommonPointCut();
	after (MessageDigest digest) returning (byte[] out) : MessageDigestSpec_d2(digest) {
		MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d2Event(digest, out);
	}

	pointcut MessageDigestSpec_d3(byte[] out, int offset, int len, MessageDigest digest) : (call(public int MessageDigest.digest(byte[], int, int)) && args(out, offset, len) && target(digest)) && MOP_CommonPointCut();
	after (byte[] out, int offset, int len, MessageDigest digest) : MessageDigestSpec_d3(out, offset, len, digest) {
		MessageDigestSpecRuntimeMonitor.MessageDigestSpec_d3Event(out, offset, len, digest);
	}

}
