
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
import com.runtimeverification.rvmonitor.java.rt.*;
import com.runtimeverification.rvmonitor.java.rt.ref.*;
import com.runtimeverification.rvmonitor.java.rt.table.*;
import com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractIndexingTree;
import com.runtimeverification.rvmonitor.java.rt.tablebase.SetEventDelegator;
import com.runtimeverification.rvmonitor.java.rt.tablebase.TableAdopter.Tuple2;
import com.runtimeverification.rvmonitor.java.rt.tablebase.TableAdopter.Tuple3;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IDisableHolder;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IMonitor;
import com.runtimeverification.rvmonitor.java.rt.tablebase.DisableHolder;
import com.runtimeverification.rvmonitor.java.rt.tablebase.TerminatedMonitorCleaner;
import java.util.concurrent.atomic.AtomicInteger;

final class MessageDigestSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<MessageDigestSpecMonitor> {

	MessageDigestSpecMonitor_Set(){
		this.size = 0;
		this.elements = new MessageDigestSpecMonitor[4];
	}
	final void event_g1(String alg, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, String provider, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, provider, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String alg, Provider provider, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(alg, provider, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g4(String alg, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g4(alg, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_update(MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_update(digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_reset(MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_reset(digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_d1(MessageDigest digest, byte[] out) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_d1(digest, out);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_d2(MessageDigest digest, byte[] out) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_d2(digest, out);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_d3(byte[] out, int offset, int len, MessageDigest digest) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			MessageDigestSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final MessageDigestSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_d3(out, offset, len, digest);
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
}

class MessageDigestSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		MessageDigestSpec_Monitor_num++;
		try {
			MessageDigestSpecMonitor ret = (MessageDigestSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> algorithms = Arrays.asList("SHA-256", "SHA-384", "SHA-512");

	MessageDigest md = null;

	String currentAlgorithmInstance = "";

	protected static long MessageDigestSpec_Monitor_num = 0;
	protected static long MessageDigestSpec_CollectedMonitor_num = 0;
	protected static long MessageDigestSpec_TerminatedMonitor_num = 0;
	protected static long MessageDigestSpec_update_num = 0;
	protected static long MessageDigestSpec_reset_num = 0;
	protected static long MessageDigestSpec_g1_num = 0;
	protected static long MessageDigestSpec_g2_num = 0;
	protected static long MessageDigestSpec_g3_num = 0;
	protected static long MessageDigestSpec_g4_num = 0;
	protected static long MessageDigestSpec_d1_num = 0;
	protected static long MessageDigestSpec_d2_num = 0;
	protected static long MessageDigestSpec_d3_num = 0;
	protected static long MessageDigestSpec_1_fail_num = 0;
	protected static long MessageDigestSpec_1_match_num = 0;

	static final int Prop_1_transition_g1[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g2[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g3[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g4[] = {0, 4, 4, 4, 4};;
	static final int Prop_1_transition_update[] = {4, 1, 1, 1, 4};;
	static final int Prop_1_transition_reset[] = {4, 4, 4, 4, 4};;
	static final int Prop_1_transition_d1[] = {4, 3, 4, 4, 4};;
	static final int Prop_1_transition_d2[] = {4, 3, 3, 3, 4};;
	static final int Prop_1_transition_d3[] = {4, 3, 4, 4, 4};;

	volatile boolean MessageDigestSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean MessageDigestSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	MessageDigestSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

		MessageDigestSpec_Monitor_num++;
	}

	public static long getTotalMonitorCount() {
		return MessageDigestSpec_Monitor_num;
	}
	public static long getCollectedMonitorCount() {
		return MessageDigestSpec_CollectedMonitor_num;
	}
	public static long getTerminatedMonitorCount() {
		return MessageDigestSpec_TerminatedMonitor_num;
	}
	public static Map<String, Long> getEventCounters() {
		HashMap<String, Long> eventCounters = new HashMap<String, Long>();
		eventCounters.put("update", MessageDigestSpec_update_num);
		eventCounters.put("reset", MessageDigestSpec_reset_num);
		eventCounters.put("g1", MessageDigestSpec_g1_num);
		eventCounters.put("g2", MessageDigestSpec_g2_num);
		eventCounters.put("g3", MessageDigestSpec_g3_num);
		eventCounters.put("g4", MessageDigestSpec_g4_num);
		eventCounters.put("d1", MessageDigestSpec_d1_num);
		eventCounters.put("d2", MessageDigestSpec_d2_num);
		eventCounters.put("d3", MessageDigestSpec_d3_num);
		return eventCounters;
	}
	public static Map<String, Long> getCategoryCounters() {
		HashMap<String, Long> categoryCounters = new HashMap<String, Long>();
		categoryCounters.put("fail", MessageDigestSpec_1_fail_num);
		categoryCounters.put("match", MessageDigestSpec_1_match_num);
		return categoryCounters;
	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 7) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 3) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 3) | state) ;
	}

	private final int handleEvent(int eventId, int[] table) {
		int nextstate;
		while (true) {
			int oldpairvalue = this.pairValue.get() ;
			int oldstate = this.getState(oldpairvalue) ;
			nextstate = table [ oldstate ];
			int nextpairvalue = this.calculatePairValue(eventId, nextstate) ;
			if (this.pairValue.compareAndSet(oldpairvalue, nextpairvalue) ) {
				break;
			}
		}
		return nextstate;
	}

	final boolean Prop_1_event_g1(String alg, MessageDigest digest) {
		{
			if ( ! (algorithms.contains(alg.toUpperCase())) ) {
				return false;
			}
			{
				md = digest;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_g1) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g2(String alg, String provider, MessageDigest digest) {
		{
			if ( ! (algorithms.contains(alg.toUpperCase())) ) {
				return false;
			}
			{
				md = digest;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_g2) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g3(String alg, Provider provider, MessageDigest digest) {
		{
			if ( ! (algorithms.contains(alg.toUpperCase())) ) {
				return false;
			}
			{
				md = digest;
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_g3) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_g4(String alg, MessageDigest digest) {
		{
			if ( ! (!algorithms.contains(currentAlgorithmInstance.toUpperCase())) ) {
				return false;
			}
			{
				currentAlgorithmInstance = alg;
			}
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_g4) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_update(MessageDigest digest) {
		{
			if (!algorithms.contains(currentAlgorithmInstance.toUpperCase())) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of {SHA-256, SHA-384, SHA-512} but found " + currentAlgorithmInstance + "."));
			}
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_update) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_reset(MessageDigest digest) {
		{
		}

		int nextstate = this.handleEvent(5, Prop_1_transition_reset) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_d1(MessageDigest digest, byte[] out) {
		{
			ExecutionContext.instance().setProperty(Property.DIGESTED, out);
		}

		int nextstate = this.handleEvent(6, Prop_1_transition_d1) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_d2(MessageDigest digest, byte[] out) {
		{
			if (!algorithms.contains(currentAlgorithmInstance.toUpperCase())) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "expecting one of {SHA-256, SHA-384, SHA-512} but found " + currentAlgorithmInstance + "."));
			}
			ExecutionContext.instance().setProperty(Property.DIGESTED, out);
		}

		int nextstate = this.handleEvent(7, Prop_1_transition_d2) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_d3(byte[] out, int offset, int len, MessageDigest digest) {
		{
			ExecutionContext.instance().setProperty(Property.DIGESTED, out);
		}

		int nextstate = this.handleEvent(8, Prop_1_transition_d3) ;
		this.MessageDigestSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.MessageDigestSpecMonitor_Prop_1_Category_match = nextstate == 3;

		return true;
	}

	final void Prop_1_handler_fail (){
		if(MessageDigestSpecMonitor_Prop_1_Category_fail) {
			MessageDigestSpec_1_fail_num++;
		}
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "MessageDigestSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().unsetObjectAsInAcceptingState(md);
			this.reset();
		}

	}

	final void Prop_1_handler_match (){
		if(MessageDigestSpecMonitor_Prop_1_Category_match) {
			MessageDigestSpec_1_match_num++;
		}
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(md);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		MessageDigestSpecMonitor_Prop_1_Category_fail = false;
		MessageDigestSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_digest was suppressed to reduce memory overhead

	//alive_parameters_0 = [MessageDigest digest]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//g1
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 1:
			//g2
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 2:
			//g3
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 3:
			//g4
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 4:
			//update
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 5:
			//reset
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 6:
			//d1
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 7:
			//d2
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

			case 8:
			//d3
			//alive_digest
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				MessageDigestSpec_TerminatedMonitor_num++;
				return;
			}
			break;

		}
		return;
	}

	protected void finalize() throws Throwable {
		try {
			MessageDigestSpec_CollectedMonitor_num++;
		} finally {
			super.finalize();
		}
	}
	public static int getNumberOfEvents() {
		return 9;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}

public final class MessageDigestSpecRuntimeMonitor implements com.runtimeverification.rvmonitor.java.rt.RVMObject {
	private static com.runtimeverification.rvmonitor.java.rt.map.RVMMapManager MessageDigestSpecMapManager;
	static {
		MessageDigestSpecMapManager = new com.runtimeverification.rvmonitor.java.rt.map.RVMMapManager();
		MessageDigestSpecMapManager.start();
	}

	// Declarations for the Lock
	static final ReentrantLock MessageDigestSpec_RVMLock = new ReentrantLock();
	static final Condition MessageDigestSpec_RVMLock_cond = MessageDigestSpec_RVMLock.newCondition();

	private static boolean MessageDigestSpec_activated = false;

	// Declarations for Indexing Trees
	private static Object MessageDigestSpec_digest_Map_cachekey_digest;
	private static MessageDigestSpecMonitor MessageDigestSpec_digest_Map_cachevalue;
	private static final MapOfMonitor<MessageDigestSpecMonitor> MessageDigestSpec_digest_Map = new MapOfMonitor<MessageDigestSpecMonitor>(0) ;

	public static int cleanUp() {
		int collected = 0;
		// indexing trees
		collected += MessageDigestSpec_digest_Map.cleanUpUnnecessaryMappings();
		return collected;
	}

	// Removing terminated monitors from partitioned sets
	static {
		TerminatedMonitorCleaner.start() ;
	}
	// Setting the behavior of the runtime library according to the compile-time option
	static {
		RuntimeOption.enableFineGrainedLock(false) ;
	}

	public static final void MessageDigestSpec_g1Event(String alg, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MessageDigestSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_g1_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MessageDigestSpec_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_g2Event(String alg, String provider, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MessageDigestSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_g2_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, provider, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MessageDigestSpec_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_g3Event(String alg, Provider provider, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MessageDigestSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_g3_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(alg, provider, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MessageDigestSpec_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_g4Event(String alg, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MessageDigestSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_g4_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g4(alg, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MessageDigestSpec_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_updateEvent(MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MessageDigestSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_update_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_update(digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MessageDigestSpec_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_resetEvent(MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MessageDigestSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_reset_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_reset(digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MessageDigestSpec_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_d1Event(MessageDigest digest, byte[] out) {
		MessageDigestSpec_activated = true;
		while (!MessageDigestSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_d1_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_d1(digest, out);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MessageDigestSpec_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_d2Event(MessageDigest digest, byte[] out) {
		MessageDigestSpec_activated = true;
		while (!MessageDigestSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_d2_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_d2(digest, out);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MessageDigestSpec_RVMLock.unlock();
	}

	public static final void MessageDigestSpec_d3Event(byte[] out, int offset, int len, MessageDigest digest) {
		MessageDigestSpec_activated = true;
		while (!MessageDigestSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		MessageDigestSpecMonitor.MessageDigestSpec_d3_num++;

		CachedWeakReference wr_digest = null;
		MapOfMonitor<MessageDigestSpecMonitor> matchedLastMap = null;
		MessageDigestSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((digest == MessageDigestSpec_digest_Map_cachekey_digest) ) {
			matchedEntry = MessageDigestSpec_digest_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_digest = new CachedWeakReference(digest) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<MessageDigestSpecMonitor> itmdMap = MessageDigestSpec_digest_Map;
				matchedLastMap = itmdMap;
				MessageDigestSpecMonitor node_digest = MessageDigestSpec_digest_Map.getNodeEquivalent(wr_digest) ;
				matchedEntry = node_digest;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_digest == null) ) {
				wr_digest = new CachedWeakReference(digest) ;
			}
			// D(X) main:4
			MessageDigestSpecMonitor created = new MessageDigestSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_digest, created) ;
		}
		// D(X) main:8--9
		final MessageDigestSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_d3(out, offset, len, digest);
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.MessageDigestSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			MessageDigestSpec_digest_Map_cachekey_digest = digest;
			MessageDigestSpec_digest_Map_cachevalue = matchedEntry;
		}

		MessageDigestSpec_RVMLock.unlock();
	}

}
