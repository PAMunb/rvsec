import android.util.Log;

public aspect LogAdapter {
	
	pointcut rvmLogging() : execution(void com.runtimeverification.rvmonitor.java.rt.RVMLogging.println(..)) || execution(void com.runtimeverification.rvmonitor.java.rt.RVMLogging.print(..));
	
	boolean around() : rvmLogging() {
		return true;
	}
	
}