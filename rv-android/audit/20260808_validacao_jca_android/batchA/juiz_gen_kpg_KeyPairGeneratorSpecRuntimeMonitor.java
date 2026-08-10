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

final class KeyPairGeneratorSpecMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<KeyPairGeneratorSpecMonitor> {

	KeyPairGeneratorSpecMonitor_Set(){
		this.size = 0;
		this.elements = new KeyPairGeneratorSpecMonitor[4];
	}
	final void event_g1(String alg, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g1(alg, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g2(String alg, String provider, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g2(alg, provider, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_g3(String alg, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_g3(alg, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init1(int keySize, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init1(keySize, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init2(int keySize, SecureRandom random, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init2(keySize, random, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init3(AlgorithmParameterSpec params, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init3(params, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_init4(AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_init4(params, random, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_initError(int keySize, KeyPairGenerator k) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_initError(keySize, k);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i = numAlive; i < this.size; i++){
			this.elements[i] = null;
		}
		size = numAlive;
	}
	final void event_gen(KeyPairGenerator k, KeyPair keyPair) {
		int numAlive = 0 ;
		for(int i = 0; i < this.size; i++){
			KeyPairGeneratorSpecMonitor monitor = this.elements[i];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final KeyPairGeneratorSpecMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_gen(k, keyPair);
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
				if(monitorfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
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

class KeyPairGeneratorSpecMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			KeyPairGeneratorSpecMonitor ret = (KeyPairGeneratorSpecMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	List<String> safeAlgorithms = Arrays.asList("DH", "DSA", "RSA");

	KeyPairGenerator kpg = null;

	KeyPair kp;

	String algorithm;

	private boolean validate(int keySize) {
		switch(algorithm) {
			case "RSA":
			return Arrays.asList(4096, 2048).contains(keySize);
			case "DSA":
			return keySize == 2048;
			case "DH":
			return keySize == 2048;
			case "EC":
			return keySize == 256;
		}
		return false;
	}

	static final int Prop_1_transition_g1[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g2[] = {2, 4, 4, 4, 4};;
	static final int Prop_1_transition_g3[] = {0, 4, 4, 4, 4};;
	static final int Prop_1_transition_init1[] = {4, 4, 3, 4, 4};;
	static final int Prop_1_transition_init2[] = {4, 4, 3, 4, 4};;
	static final int Prop_1_transition_init3[] = {4, 4, 3, 4, 4};;
	static final int Prop_1_transition_init4[] = {4, 4, 3, 4, 4};;
	static final int Prop_1_transition_initError[] = {4, 4, 2, 3, 4};;
	static final int Prop_1_transition_gen[] = {4, 4, 4, 1, 4};;

	volatile boolean KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = false;
	volatile boolean KeyPairGeneratorSpecMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	KeyPairGeneratorSpecMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

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

	final boolean Prop_1_event_g1(String alg, KeyPairGenerator k) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				kpg = k;
				algorithm = alg;
			}
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_g1) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_g2(String alg, String provider, KeyPairGenerator k) {
		{
			if ( ! (safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				kpg = k;
				algorithm = alg;
			}
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_g2) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_g3(String alg, KeyPairGenerator k) {
		{
			if ( ! (!safeAlgorithms.contains(alg)) ) {
				return false;
			}
			{
				algorithm = alg;
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_g3) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_init1(int keySize, KeyPairGenerator k) {
		{
			if ( ! (validate(keySize)) ) {
				return false;
			}
			{
				if (!safeAlgorithms.contains(algorithm)) {
					ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "KeyPairGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), " expecting one of " + String.join(",", safeAlgorithms) + " but found " + algorithm + "."));
				}
			}
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_init1) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_init2(int keySize, SecureRandom random, KeyPairGenerator k) {
		{
			if ( ! (validate(keySize)) ) {
				return false;
			}
			{
			}
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_init2) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_init3(AlgorithmParameterSpec params, KeyPairGenerator k) {
		{
			if ("DH".equals(algorithm) && params != null && !ExecutionContext.instance().validate(Property.PREPARED_DH, params)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "KeyPairGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "initialize() for DH requires an AlgorithmParameterSpec established by a monitored DHGenParameterSpec sequence."));
			}
		}

		int nextstate = this.handleEvent(5, Prop_1_transition_init3) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_init4(AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) {
		{
			if ("DH".equals(algorithm) && params != null && !ExecutionContext.instance().validate(Property.PREPARED_DH, params)) {
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint, "KeyPairGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "initialize() for DH requires an AlgorithmParameterSpec established by a monitored DHGenParameterSpec sequence."));
			}
		}

		int nextstate = this.handleEvent(6, Prop_1_transition_init4) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_initError(int keySize, KeyPairGenerator k) {
		{
			if ( ! (!validate(keySize)) ) {
				return false;
			}
			{
				ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidKeySize, "KeyPairGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode(), "invalid key size for algorithm " + algorithm + "."));
			}
		}

		int nextstate = this.handleEvent(7, Prop_1_transition_initError) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_gen(KeyPairGenerator k, KeyPair keyPair) {
		{
			kp = keyPair;
			ExecutionContext.instance().setProperty(Property.GENERATED_KEY_PAIR, kp);
		}

		int nextstate = this.handleEvent(8, Prop_1_transition_gen) ;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = nextstate == 4;
		this.KeyPairGeneratorSpecMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_fail (){
		{
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "KeyPairGeneratorSpec", "" + com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()));
			ExecutionContext.instance().remove(Property.GENERATED_KEY_PAIR, kp);
		}

	}

	final void Prop_1_handler_match (){
		{
			ExecutionContext.instance().setObjectAsInAcceptingState(kpg);
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		KeyPairGeneratorSpecMonitor_Prop_1_Category_fail = false;
		KeyPairGeneratorSpecMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_k was suppressed to reduce memory overhead

	//alive_parameters_0 = [KeyPairGenerator k]
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
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//g2
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 2:
			//g3
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 3:
			//init1
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 4:
			//init2
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 5:
			//init3
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 6:
			//init4
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 7:
			//initError
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 8:
			//gen
			//alive_k
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

		}
		return;
	}

	public static int getNumberOfEvents() {
		return 9;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}

public final class KeyPairGeneratorSpecRuntimeMonitor implements com.runtimeverification.rvmonitor.java.rt.RVMObject {
	private static com.runtimeverification.rvmonitor.java.rt.map.RVMMapManager KeyPairGeneratorSpecMapManager;
	static {
		KeyPairGeneratorSpecMapManager = new com.runtimeverification.rvmonitor.java.rt.map.RVMMapManager();
		KeyPairGeneratorSpecMapManager.start();
	}

	// Declarations for the Lock
	static final ReentrantLock KeyPairGeneratorSpec_RVMLock = new ReentrantLock();
	static final Condition KeyPairGeneratorSpec_RVMLock_cond = KeyPairGeneratorSpec_RVMLock.newCondition();

	private static boolean KeyPairGeneratorSpec_activated = false;

	// Declarations for Indexing Trees
	private static Object KeyPairGeneratorSpec_k_Map_cachekey_k;
	private static KeyPairGeneratorSpecMonitor KeyPairGeneratorSpec_k_Map_cachevalue;
	private static final MapOfMonitor<KeyPairGeneratorSpecMonitor> KeyPairGeneratorSpec_k_Map = new MapOfMonitor<KeyPairGeneratorSpecMonitor>(0) ;

	public static int cleanUp() {
		int collected = 0;
		// indexing trees
		collected += KeyPairGeneratorSpec_k_Map.cleanUpUnnecessaryMappings();
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

	public static final void KeyPairGeneratorSpec_g1Event(String alg, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!KeyPairGeneratorSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g1(alg, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		KeyPairGeneratorSpec_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_g2Event(String alg, String provider, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!KeyPairGeneratorSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g2(alg, provider, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		KeyPairGeneratorSpec_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_g3Event(String alg, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!KeyPairGeneratorSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_g3(alg, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		KeyPairGeneratorSpec_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_init1Event(int keySize, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!KeyPairGeneratorSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init1(keySize, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		KeyPairGeneratorSpec_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_init2Event(int keySize, SecureRandom random, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!KeyPairGeneratorSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init2(keySize, random, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		KeyPairGeneratorSpec_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_init3Event(AlgorithmParameterSpec params, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!KeyPairGeneratorSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init3(params, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		KeyPairGeneratorSpec_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_init4Event(AlgorithmParameterSpec params, SecureRandom random, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!KeyPairGeneratorSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_init4(params, random, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		KeyPairGeneratorSpec_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_initErrorEvent(int keySize, KeyPairGenerator k) {
		KeyPairGeneratorSpec_activated = true;
		while (!KeyPairGeneratorSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_initError(keySize, k);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		KeyPairGeneratorSpec_RVMLock.unlock();
	}

	public static final void KeyPairGeneratorSpec_genEvent(KeyPairGenerator k, KeyPair keyPair) {
		KeyPairGeneratorSpec_activated = true;
		while (!KeyPairGeneratorSpec_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_k = null;
		MapOfMonitor<KeyPairGeneratorSpecMonitor> matchedLastMap = null;
		KeyPairGeneratorSpecMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((k == KeyPairGeneratorSpec_k_Map_cachekey_k) ) {
			matchedEntry = KeyPairGeneratorSpec_k_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_k = new CachedWeakReference(k) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<KeyPairGeneratorSpecMonitor> itmdMap = KeyPairGeneratorSpec_k_Map;
				matchedLastMap = itmdMap;
				KeyPairGeneratorSpecMonitor node_k = KeyPairGeneratorSpec_k_Map.getNodeEquivalent(wr_k) ;
				matchedEntry = node_k;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_k == null) ) {
				wr_k = new CachedWeakReference(k) ;
			}
			// D(X) main:4
			KeyPairGeneratorSpecMonitor created = new KeyPairGeneratorSpecMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_k, created) ;
		}
		// D(X) main:8--9
		final KeyPairGeneratorSpecMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_gen(k, keyPair);
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}
		if(matchedEntryfinalMonitor.KeyPairGeneratorSpecMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			KeyPairGeneratorSpec_k_Map_cachekey_k = k;
			KeyPairGeneratorSpec_k_Map_cachevalue = matchedEntry;
		}

		KeyPairGeneratorSpec_RVMLock.unlock();
	}

}
