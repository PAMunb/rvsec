import android.util.Log;

public aspect Coverage {
	
	pointcut notwithin() :
		!within(sun..*) &&
		!within(java..*) &&
		!within(javax..*) &&
		!within(jakarta..*) &&
		!within(com.sun..*) &&
		!within(android..*) &&
		!within(androidx..*) &&
		!within(kotlin..*) &&
		!within(net.sf.cglib..*) &&
		!within(org.aspectj..*) &&
		!within(com.google.android..*) &&
		!within(com.android..*) &&
		!within(com.google..*) &&
		!within(com.facebook..*) &&
		!within(org.apache..*) &&
		!within(libcore..*) &&
		!within(mop..*) &&
		!within(javamop..*) &&
		!within(javamoprt..*) &&
		!within(rvmonitorrt..*) &&
		!within(com.runtimeverification..*) && 
		!within(br.unb.cic.mop..*) &&
		!within(*..Log) &&
		!within(*..Coverage);		
	
	pointcut traced() : execution(* *.*(..)) && notwithin();
	
	before() : traced() {
		String sig = thisJoinPointStaticPart.getSignature().toLongString().strip();
		String methodSignature = String.format("%s:::%s:::%s", thisJoinPointStaticPart.getSignature().getDeclaringTypeName(), thisJoinPointStaticPart.getSignature().getName(), sig.substring(sig.indexOf('(')));
		Log.v("RVSEC-COV", methodSignature);
	}
	
}