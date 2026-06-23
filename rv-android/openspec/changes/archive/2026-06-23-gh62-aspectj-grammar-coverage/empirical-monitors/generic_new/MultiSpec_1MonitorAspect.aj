package mop;
import java.io.*;
import java.lang.*;
import java.nio.*;
import java.util.*;
import java.lang.reflect.*;
import org.aspectj.lang.Signature;
import java.net.*;
import java.util.concurrent.*;
import java.util.concurrent.locks.*;

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

	// Declarations for the Lock
	static ReentrantLock MultiSpec_1_MOPLock = new ReentrantLock();
	static Condition MultiSpec_1_MOPLock_cond = MultiSpec_1_MOPLock.newCondition();

	pointcut MOP_CommonPointCut() : !within(com.runtimeverification.rvmonitor.java.rt.RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
	pointcut Writer_ManipulateAfterClose_close(Writer w) : (call(* Writer+.close(..)) && target(w) && !target(CharArrayWriter) && !target(StringWriter)) && MOP_CommonPointCut();
	before (Writer w) : Writer_ManipulateAfterClose_close(w) {
		MultiSpec_1RuntimeMonitor.Writer_ManipulateAfterClose_closeEvent(w);
	}

	pointcut Writer_ManipulateAfterClose_manipulate(Writer w) : ((call(* Writer+.write*(..)) || call(* Writer+.flush(..))) && target(w) && !target(CharArrayWriter) && !target(StringWriter)) && MOP_CommonPointCut();
	before (Writer w) : Writer_ManipulateAfterClose_manipulate(w) {
		MultiSpec_1RuntimeMonitor.Writer_ManipulateAfterClose_manipulateEvent(w);
	}

	pointcut URLEncoder_EncodeUTF8_encode(String enc) : (call(* URLEncoder.encode(String, String)) && args(*, enc)) && MOP_CommonPointCut();
	before (String enc) : URLEncoder_EncodeUTF8_encode(enc) {
		MultiSpec_1RuntimeMonitor.URLEncoder_EncodeUTF8_encodeEvent(enc);
	}

	pointcut URLDecoder_DecodeUTF8_decode(String enc) : (call(* URLDecoder.decode(String, String)) && args(*, enc)) && MOP_CommonPointCut();
	before (String enc) : URLDecoder_DecodeUTF8_decode(enc) {
		MultiSpec_1RuntimeMonitor.URLDecoder_DecodeUTF8_decodeEvent(enc);
	}

	pointcut TreeSet_Comparable_addall(Collection c) : (call(* Collection+.addAll(Collection)) && target(TreeSet) && args(c)) && MOP_CommonPointCut();
	before (Collection c) : TreeSet_Comparable_addall(c) {
		MultiSpec_1RuntimeMonitor.TreeSet_Comparable_addallEvent(c);
	}

	pointcut TreeSet_Comparable_add(Object e) : (call(* Collection+.add*(..)) && target(TreeSet) && args(e)) && MOP_CommonPointCut();
	before (Object e) : TreeSet_Comparable_add(e) {
		MultiSpec_1RuntimeMonitor.TreeSet_Comparable_addEvent(e);
	}

	pointcut TreeMap_Comparable_putall(Map src) : (call(* Map+.putAll(Map)) && args(src) && target(TreeMap)) && MOP_CommonPointCut();
	before (Map src) : TreeMap_Comparable_putall(src) {
		MultiSpec_1RuntimeMonitor.TreeMap_Comparable_putallEvent(src);
	}

	pointcut TreeMap_Comparable_put(Object key) : (call(* Map+.put(Object, Object)) && args(key, ..) && target(TreeMap)) && MOP_CommonPointCut();
	before (Object key) : TreeMap_Comparable_put(key) {
		MultiSpec_1RuntimeMonitor.TreeMap_Comparable_putEvent(key);
	}

	pointcut TreeMap_Comparable_create(Map src) : (call(TreeMap.new(Map)) && args(src)) && MOP_CommonPointCut();
	before (Map src) : TreeMap_Comparable_create(src) {
		MultiSpec_1RuntimeMonitor.TreeMap_Comparable_createEvent(src);
	}

	pointcut SortedSet_Comparable_addall(SortedSet s, Collection c) : (call(* Collection+.addAll(Collection)) && target(s) && args(c)) && MOP_CommonPointCut();
	before (SortedSet s, Collection c) : SortedSet_Comparable_addall(s, c) {
		MultiSpec_1RuntimeMonitor.SortedSet_Comparable_addallEvent(s, c);
	}

	pointcut SortedSet_Comparable_add(SortedSet s, Object e) : ((call(* Collection+.add*(..)) || call(* Queue+.offer*(..))) && target(s) && args(e)) && MOP_CommonPointCut();
	before (SortedSet s, Object e) : SortedSet_Comparable_add(s, e) {
		MultiSpec_1RuntimeMonitor.SortedSet_Comparable_addEvent(s, e);
	}

	pointcut ServerSocket_SetTimeoutBeforeBlocking_set(ServerSocket sock, int timeout) : (call(* ServerSocket+.setSoTimeout(int)) && target(sock) && args(timeout)) && MOP_CommonPointCut();
	before (ServerSocket sock, int timeout) : ServerSocket_SetTimeoutBeforeBlocking_set(sock, timeout) {
		MultiSpec_1RuntimeMonitor.ServerSocket_SetTimeoutBeforeBlocking_setEvent(sock, timeout);
	}

	pointcut ServerSocket_SetTimeoutBeforeBlocking_enter(ServerSocket sock) : (call(* ServerSocket+.accept(..)) && target(sock)) && MOP_CommonPointCut();
	before (ServerSocket sock) : ServerSocket_SetTimeoutBeforeBlocking_enter(sock) {
		MultiSpec_1RuntimeMonitor.ServerSocket_SetTimeoutBeforeBlocking_enterEvent(sock);
	}

	pointcut ServerSocket_Backlog_set(int backlog) : (call(* ServerSocket+.bind(SocketAddress, int)) && args(*, backlog)) && MOP_CommonPointCut();
	before (int backlog) : ServerSocket_Backlog_set(backlog) {
		MultiSpec_1RuntimeMonitor.ServerSocket_Backlog_setEvent(backlog);
	}

	pointcut ServerSocket_Backlog_construct(int backlog) : ((call(ServerSocket.new(int, int)) || call(ServerSocket.new(int, int, InetAddress))) && args(*, backlog, ..)) && MOP_CommonPointCut();
	before (int backlog) : ServerSocket_Backlog_construct(backlog) {
		MultiSpec_1RuntimeMonitor.ServerSocket_Backlog_constructEvent(backlog);
	}

	pointcut Reader_ManipulateAfterClose_close(Reader r) : (call(* Reader+.close(..)) && target(r)) && MOP_CommonPointCut();
	before (Reader r) : Reader_ManipulateAfterClose_close(r) {
		MultiSpec_1RuntimeMonitor.Reader_ManipulateAfterClose_closeEvent(r);
	}

	pointcut Reader_ManipulateAfterClose_manipulate(Reader r) : ((call(* Reader+.read(..)) || call(* Reader+.ready(..)) || call(* Reader+.mark(..)) || call(* Reader+.reset(..)) || call(* Reader+.skip(..))) && target(r)) && MOP_CommonPointCut();
	before (Reader r) : Reader_ManipulateAfterClose_manipulate(r) {
		MultiSpec_1RuntimeMonitor.Reader_ManipulateAfterClose_manipulateEvent(r);
	}

	pointcut OutputStream_ManipulateAfterClose_close(OutputStream o) : (call(* OutputStream+.close(..)) && target(o) && !target(ByteArrayOutputStream)) && MOP_CommonPointCut();
	before (OutputStream o) : OutputStream_ManipulateAfterClose_close(o) {
		MultiSpec_1RuntimeMonitor.OutputStream_ManipulateAfterClose_closeEvent(o);
	}

	pointcut OutputStream_ManipulateAfterClose_manipulate(OutputStream o) : ((call(* OutputStream+.write*(..)) || call(* OutputStream+.flush(..))) && target(o) && !target(ByteArrayOutputStream)) && MOP_CommonPointCut();
	before (OutputStream o) : OutputStream_ManipulateAfterClose_manipulate(o) {
		MultiSpec_1RuntimeMonitor.OutputStream_ManipulateAfterClose_manipulateEvent(o);
	}

	pointcut Object_MonitorOwner_bad_wait(Object o) : (call(* Object+.wait(..)) && target(o) && if(!Thread.holdsLock(o))) && MOP_CommonPointCut();
	before (Object o) : Object_MonitorOwner_bad_wait(o) {
		MultiSpec_1RuntimeMonitor.Object_MonitorOwner_bad_waitEvent(o);
	}

	pointcut Object_MonitorOwner_bad_notify(Object o) : ((call(* Object+.notify(..)) || call(* Object+.notifyAll(..))) && target(o) && if(!Thread.holdsLock(o))) && MOP_CommonPointCut();
	before (Object o) : Object_MonitorOwner_bad_notify(o) {
		MultiSpec_1RuntimeMonitor.Object_MonitorOwner_bad_notifyEvent(o);
	}

	pointcut Map_UnsafeIterator_useiter(Iterator i) : ((call(* Iterator.hasNext(..)) || call(* Iterator.next(..))) && target(i)) && MOP_CommonPointCut();
	before (Iterator i) : Map_UnsafeIterator_useiter(i) {
		MultiSpec_1RuntimeMonitor.Map_UnsafeIterator_useiterEvent(i);
	}

	pointcut Map_UnsafeIterator_modifyCol(Collection c) : ((call(* Collection+.clear(..)) || call(* Collection+.offer*(..)) || call(* Collection+.pop(..)) || call(* Collection+.push(..)) || call(* Collection+.remove*(..)) || call(* Collection+.retain*(..))) && target(c)) && MOP_CommonPointCut();
	before (Collection c) : Map_UnsafeIterator_modifyCol(c) {
		MultiSpec_1RuntimeMonitor.Map_UnsafeIterator_modifyColEvent(c);
	}

	pointcut Map_UnsafeIterator_modifyMap(Map m) : ((call(* Map+.clear*(..)) || call(* Map+.put*(..)) || call(* Map+.remove(..))) && target(m)) && MOP_CommonPointCut();
	before (Map m) : Map_UnsafeIterator_modifyMap(m) {
		MultiSpec_1RuntimeMonitor.Map_UnsafeIterator_modifyMapEvent(m);
	}

	pointcut Long_BadParsingArgs_bad_arg2(String s) : (call(* Long.parseLong(String)) && args(s)) && MOP_CommonPointCut();
	before (String s) : Long_BadParsingArgs_bad_arg2(s) {
		MultiSpec_1RuntimeMonitor.Long_BadParsingArgs_bad_arg2Event(s);
	}

	pointcut Long_BadParsingArgs_bad_arg(String s, int radix) : (call(* Long.parseLong(String, int)) && args(s, radix)) && MOP_CommonPointCut();
	before (String s, int radix) : Long_BadParsingArgs_bad_arg(s, radix) {
		MultiSpec_1RuntimeMonitor.Long_BadParsingArgs_bad_argEvent(s, radix);
	}

	pointcut ListIterator_Set_set(ListIterator i) : (call(* ListIterator+.set(..)) && target(i)) && MOP_CommonPointCut();
	before (ListIterator i) : ListIterator_Set_set(i) {
		MultiSpec_1RuntimeMonitor.ListIterator_Set_setEvent(i);
	}

	pointcut ListIterator_Set_previous(ListIterator i) : (call(* ListIterator+.previous()) && target(i)) && MOP_CommonPointCut();
	before (ListIterator i) : ListIterator_Set_previous(i) {
		MultiSpec_1RuntimeMonitor.ListIterator_Set_previousEvent(i);
	}

	pointcut ListIterator_Set_next(ListIterator i) : (call(* Iterator+.next()) && target(i)) && MOP_CommonPointCut();
	before (ListIterator i) : ListIterator_Set_next(i) {
		MultiSpec_1RuntimeMonitor.ListIterator_Set_nextEvent(i);
	}

	pointcut ListIterator_Set_add(ListIterator i) : (call(void ListIterator+.add(..)) && target(i)) && MOP_CommonPointCut();
	before (ListIterator i) : ListIterator_Set_add(i) {
		MultiSpec_1RuntimeMonitor.ListIterator_Set_addEvent(i);
	}

	pointcut ListIterator_Set_remove(ListIterator i) : (call(void Iterator+.remove()) && target(i)) && MOP_CommonPointCut();
	before (ListIterator i) : ListIterator_Set_remove(i) {
		MultiSpec_1RuntimeMonitor.ListIterator_Set_removeEvent(i);
	}

	pointcut InputStream_ManipulateAfterClose_close(InputStream i) : (call(* InputStream+.close(..)) && target(i) && !target(ByteArrayInputStream) && !target(StringBufferInputStream)) && MOP_CommonPointCut();
	before (InputStream i) : InputStream_ManipulateAfterClose_close(i) {
		MultiSpec_1RuntimeMonitor.InputStream_ManipulateAfterClose_closeEvent(i);
	}

	pointcut InputStream_ManipulateAfterClose_manipulate(InputStream i) : ((call(* InputStream+.read(..)) || call(* InputStream+.available(..)) || call(* InputStream+.reset(..)) || call(* InputStream+.skip(..))) && target(i) && !target(ByteArrayInputStream) && !target(StringBufferInputStream)) && MOP_CommonPointCut();
	before (InputStream i) : InputStream_ManipulateAfterClose_manipulate(i) {
		MultiSpec_1RuntimeMonitor.InputStream_ManipulateAfterClose_manipulateEvent(i);
	}

	pointcut Comparable_CompareToNullException_badexception(Object o) : (call(* Comparable+.compareTo(..)) && args(o) && if(o == null)) && MOP_CommonPointCut();
	before (Object o) : Comparable_CompareToNullException_badexception(o) {
		MultiSpec_1RuntimeMonitor.Comparable_CompareToNull_nullcompareEvent(o);
	}

	pointcut Collection_UnsynchronizedAddAll_modify(Collection s) : ((call(* Collection+.add*(..)) || call(* Collection+.remove*(..)) || call(* Collection+.clear(..)) || call(* Collection+.retain*(..))) && target(s)) && MOP_CommonPointCut();
	before (Collection s) : Collection_UnsynchronizedAddAll_modify(s) {
		MultiSpec_1RuntimeMonitor.Collection_UnsynchronizedAddAll_modifyEvent(s);
	}

	pointcut Collection_UnsynchronizedAddAll_enter(Collection t, Collection s) : (call(boolean Collection+.addAll(..)) && target(t) && args(s)) && MOP_CommonPointCut();
	before (Collection t, Collection s) : Collection_UnsynchronizedAddAll_enter(t, s) {
		MultiSpec_1RuntimeMonitor.Collection_UnsynchronizedAddAll_enterEvent(t, s);
	}

	pointcut Collections_UnnecessaryNewSetFromMap_unnecessary() : (call(* Collections.newSetFromMap(Map)) && (args(HashMap) || args(TreeMap))) && MOP_CommonPointCut();
	before () : Collections_UnnecessaryNewSetFromMap_unnecessary() {
		MultiSpec_1RuntimeMonitor.Collections_UnnecessaryNewSetFromMap_unnecessaryEvent();
	}

	pointcut Collections_SynchronizedCollection_accessIter(Iterator iter) : (call(* Iterator.*(..)) && target(iter)) && MOP_CommonPointCut();
	before (Iterator iter) : Collections_SynchronizedCollection_accessIter(iter) {
		//Collections_SynchronizedMap_accessIter
		MultiSpec_1RuntimeMonitor.Collections_SynchronizedMap_accessIterEvent(iter);
		//Collections_SynchronizedCollection_accessIter
		MultiSpec_1RuntimeMonitor.Collections_SynchronizedCollection_accessIterEvent(iter);
	}

	pointcut Closeable_MeaninglessClose_close() : (call(* Closeable+.close()) && (target(ByteArrayInputStream) || target(ByteArrayOutputStream) || target(CharArrayWriter) || target(StringWriter))) && MOP_CommonPointCut();
	before () : Closeable_MeaninglessClose_close() {
		MultiSpec_1RuntimeMonitor.Closeable_MeaninglessClose_closeEvent();
	}

	pointcut CharSequence_UndefinedHashCode_hashCode() : (call(* CharSequence+.hashCode(..)) && !target(String) && !target(CharBuffer)) && MOP_CommonPointCut();
	before () : CharSequence_UndefinedHashCode_hashCode() {
		MultiSpec_1RuntimeMonitor.CharSequence_UndefinedHashCode_hashCodeEvent();
	}

	pointcut CharSequence_UndefinedHashCode_equals() : (call(* CharSequence+.equals(..)) && !target(String) && !target(CharBuffer)) && MOP_CommonPointCut();
	before () : CharSequence_UndefinedHashCode_equals() {
		MultiSpec_1RuntimeMonitor.CharSequence_UndefinedHashCode_equalsEvent();
	}

	pointcut CharSequence_NotInSet_set_addall(Collection c) : (call(* Set+.addAll(Collection)) && args(c)) && MOP_CommonPointCut();
	before (Collection c) : CharSequence_NotInSet_set_addall(c) {
		MultiSpec_1RuntimeMonitor.CharSequence_NotInSet_set_addallEvent(c);
	}

	pointcut CharSequence_NotInSet_set_add() : (call(* Set+.add(..)) && args(CharSequence) && !args(String) && !args(CharBuffer)) && MOP_CommonPointCut();
	before () : CharSequence_NotInSet_set_add() {
		MultiSpec_1RuntimeMonitor.CharSequence_NotInSet_set_addEvent();
	}

	pointcut Collection_HashCode_staticinit() : (staticinitialization(Collection+)) && MOP_CommonPointCut();
	after () : Collection_HashCode_staticinit() {
		MultiSpec_1RuntimeMonitor.Collection_HashCode_staticinitEvent(thisJoinPoint.getStaticPart().getSignature());
	}

	pointcut Collections_SynchronizedCollection_sync() : (call(* Collections.synchronizedCollection(Collection)) || call(* Collections.synchronizedSet(Set)) || call(* Collections.synchronizedSortedSet(SortedSet)) || call(* Collections.synchronizedList(List))) && MOP_CommonPointCut();
	after () returning (Collection col) : Collections_SynchronizedCollection_sync() {
		MultiSpec_1RuntimeMonitor.Collections_SynchronizedCollection_syncEvent(col);
	}

	pointcut Collections_SynchronizedCollection_syncCreateIter(Collection col) : (call(* Collection+.iterator()) && target(col)) && MOP_CommonPointCut();
	after (Collection col) returning (Iterator iter) : Collections_SynchronizedCollection_syncCreateIter(col) {
		//Collections_SynchronizedCollection_syncCreateIter
		MultiSpec_1RuntimeMonitor.Collections_SynchronizedCollection_syncCreateIterEvent(col, iter);
		//Collections_SynchronizedCollection_asyncCreateIter
		MultiSpec_1RuntimeMonitor.Collections_SynchronizedCollection_asyncCreateIterEvent(col, iter);
		//Collections_SynchronizedMap_syncCreateIter
		MultiSpec_1RuntimeMonitor.Collections_SynchronizedMap_syncCreateIterEvent(col, iter);
		//Collections_SynchronizedMap_asyncCreateIter
		MultiSpec_1RuntimeMonitor.Collections_SynchronizedMap_asyncCreateIterEvent(col, iter);
	}

	pointcut Collections_SynchronizedMap_sync() : (call(* Collections.synchronizedMap(Map)) || call(* Collections.synchronizedSortedMap(SortedMap))) && MOP_CommonPointCut();
	after () returning (Map syncMap) : Collections_SynchronizedMap_sync() {
		MultiSpec_1RuntimeMonitor.Collections_SynchronizedMap_syncEvent(syncMap);
	}

	pointcut Collections_SynchronizedMap_createSet(Map syncMap) : ((call(Set Map+.keySet()) || call(Set Map+.entrySet()) || call(Collection Map+.values())) && target(syncMap)) && MOP_CommonPointCut();
	after (Map syncMap) returning (Collection col) : Collections_SynchronizedMap_createSet(syncMap) {
		MultiSpec_1RuntimeMonitor.Collections_SynchronizedMap_createSetEvent(syncMap, col);
	}

	after (Collection t, Collection s) : Collection_UnsynchronizedAddAll_enter(t, s) {
		MultiSpec_1RuntimeMonitor.Collection_UnsynchronizedAddAll_leaveEvent(t, s);
	}

	after (Object o) throwing (Exception e) : Comparable_CompareToNullException_badexception(o) {
		MultiSpec_1RuntimeMonitor.Comparable_CompareToNullException_badexceptionEvent(o, e);
	}

	after (Object o) returning (int i) : Comparable_CompareToNullException_badexception(o) {
		MultiSpec_1RuntimeMonitor.Comparable_CompareToNullException_badcompareEvent(o, i);
	}

	pointcut ListIterator_Set_create() : (call(ListIterator Iterable+.listIterator())) && MOP_CommonPointCut();
	after () returning (ListIterator i) : ListIterator_Set_create() {
		MultiSpec_1RuntimeMonitor.ListIterator_Set_createEvent(i);
	}

	pointcut Map_UnsafeIterator_getset(Map m) : ((call(Set Map+.keySet()) || call(Set Map+.entrySet()) || call(Collection Map+.values())) && target(m)) && MOP_CommonPointCut();
	after (Map m) returning (Collection c) : Map_UnsafeIterator_getset(m) {
		MultiSpec_1RuntimeMonitor.Map_UnsafeIterator_getsetEvent(m, c);
	}

	pointcut Map_UnsafeIterator_getiter(Collection c) : (call(Iterator Iterable+.iterator()) && target(c)) && MOP_CommonPointCut();
	after (Collection c) returning (Iterator i) : Map_UnsafeIterator_getiter(c) {
		MultiSpec_1RuntimeMonitor.Map_UnsafeIterator_getiterEvent(c, i);
	}

	pointcut Serializable_NoArgConstructor_staticinit() : (staticinitialization(Serializable+)) && MOP_CommonPointCut();
	after () : Serializable_NoArgConstructor_staticinit() {
		MultiSpec_1RuntimeMonitor.Serializable_NoArgConstructor_staticinitEvent(thisJoinPoint.getStaticPart().getSignature());
	}

	after (ServerSocket sock) : ServerSocket_SetTimeoutBeforeBlocking_enter(sock) {
		MultiSpec_1RuntimeMonitor.ServerSocket_SetTimeoutBeforeBlocking_leaveEvent(sock);
	}

	pointcut URLConnection_OverrideGetPermission_staticinit() : (staticinitialization(URLConnection+)) && MOP_CommonPointCut();
	after () : URLConnection_OverrideGetPermission_staticinit() {
		MultiSpec_1RuntimeMonitor.URLConnection_OverrideGetPermission_staticinitEvent(thisJoinPoint.getStaticPart().getSignature());
	}

}
