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

final class CharSequence_NotInSetMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<CharSequence_NotInSetMonitor> {

	CharSequence_NotInSetMonitor_Set(){
		this.size = 0;
		this.elements = new CharSequence_NotInSetMonitor[4];
	}
	final void event_set_add() {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			CharSequence_NotInSetMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_set_add();
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_set_addall(Collection c) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			CharSequence_NotInSetMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_set_addall(c);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class CharSequence_UndefinedHashCodeMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<CharSequence_UndefinedHashCodeMonitor> {

	CharSequence_UndefinedHashCodeMonitor_Set(){
		this.size = 0;
		this.elements = new CharSequence_UndefinedHashCodeMonitor[4];
	}
	final void event_equals() {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			CharSequence_UndefinedHashCodeMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_equals();
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_hashCode() {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			CharSequence_UndefinedHashCodeMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_hashCode();
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Closeable_MeaninglessCloseMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Closeable_MeaninglessCloseMonitor> {

	Closeable_MeaninglessCloseMonitor_Set(){
		this.size = 0;
		this.elements = new Closeable_MeaninglessCloseMonitor[4];
	}
	final void event_close() {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Closeable_MeaninglessCloseMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_close();
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Collection_HashCodeMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Collection_HashCodeMonitor> {

	Collection_HashCodeMonitor_Set(){
		this.size = 0;
		this.elements = new Collection_HashCodeMonitor[4];
	}
	final void event_staticinit(org.aspectj.lang.Signature staticsig) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collection_HashCodeMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_staticinit(staticsig);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Collection_UnsynchronizedAddAllMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Collection_UnsynchronizedAddAllMonitor> {

	Collection_UnsynchronizedAddAllMonitor_Set(){
		this.size = 0;
		this.elements = new Collection_UnsynchronizedAddAllMonitor[4];
	}
	final void event_enter(Collection t, Collection s) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collection_UnsynchronizedAddAllMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collection_UnsynchronizedAddAllMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_enter(t, s);
				if(monitorfinalMonitor.Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_modify(Collection s) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collection_UnsynchronizedAddAllMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collection_UnsynchronizedAddAllMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_modify(s);
				if(monitorfinalMonitor.Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_leave(Collection t, Collection s) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collection_UnsynchronizedAddAllMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collection_UnsynchronizedAddAllMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_leave(t, s);
				if(monitorfinalMonitor.Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Collections_SynchronizedCollectionMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Collections_SynchronizedCollectionMonitor> {

	Collections_SynchronizedCollectionMonitor_Set(){
		this.size = 0;
		this.elements = new Collections_SynchronizedCollectionMonitor[4];
	}
	final void event_sync(Collection col) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_SynchronizedCollectionMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collections_SynchronizedCollectionMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_sync(col);
				if(monitorfinalMonitor.Collections_SynchronizedCollectionMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_syncCreateIter(Collection col, Iterator iter) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_SynchronizedCollectionMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collections_SynchronizedCollectionMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_syncCreateIter(col, iter);
				if(monitorfinalMonitor.Collections_SynchronizedCollectionMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_asyncCreateIter(Collection col, Iterator iter) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_SynchronizedCollectionMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collections_SynchronizedCollectionMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_asyncCreateIter(col, iter);
				if(monitorfinalMonitor.Collections_SynchronizedCollectionMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_accessIter(Iterator iter) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_SynchronizedCollectionMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collections_SynchronizedCollectionMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_accessIter(iter);
				if(monitorfinalMonitor.Collections_SynchronizedCollectionMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Collections_SynchronizedMapMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Collections_SynchronizedMapMonitor> {

	Collections_SynchronizedMapMonitor_Set(){
		this.size = 0;
		this.elements = new Collections_SynchronizedMapMonitor[4];
	}
	final void event_sync(Map syncMap) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_SynchronizedMapMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collections_SynchronizedMapMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_sync(syncMap);
				if(monitorfinalMonitor.Collections_SynchronizedMapMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_createSet(Map syncMap, Collection col) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_SynchronizedMapMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collections_SynchronizedMapMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_createSet(syncMap, col);
				if(monitorfinalMonitor.Collections_SynchronizedMapMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_syncCreateIter(Collection col, Iterator iter) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_SynchronizedMapMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collections_SynchronizedMapMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_syncCreateIter(col, iter);
				if(monitorfinalMonitor.Collections_SynchronizedMapMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_asyncCreateIter(Collection col, Iterator iter) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_SynchronizedMapMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collections_SynchronizedMapMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_asyncCreateIter(col, iter);
				if(monitorfinalMonitor.Collections_SynchronizedMapMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_accessIter(Iterator iter) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_SynchronizedMapMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Collections_SynchronizedMapMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_accessIter(iter);
				if(monitorfinalMonitor.Collections_SynchronizedMapMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Collections_UnnecessaryNewSetFromMapMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Collections_UnnecessaryNewSetFromMapMonitor> {

	Collections_UnnecessaryNewSetFromMapMonitor_Set(){
		this.size = 0;
		this.elements = new Collections_UnnecessaryNewSetFromMapMonitor[4];
	}
	final void event_unnecessary() {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Collections_UnnecessaryNewSetFromMapMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_unnecessary();
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Comparable_CompareToNullMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Comparable_CompareToNullMonitor> {

	Comparable_CompareToNullMonitor_Set(){
		this.size = 0;
		this.elements = new Comparable_CompareToNullMonitor[4];
	}
	final void event_nullcompare(Object o) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Comparable_CompareToNullMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_nullcompare(o);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Comparable_CompareToNullExceptionMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Comparable_CompareToNullExceptionMonitor> {

	Comparable_CompareToNullExceptionMonitor_Set(){
		this.size = 0;
		this.elements = new Comparable_CompareToNullExceptionMonitor[4];
	}
	final void event_badexception(Object o, Exception e) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Comparable_CompareToNullExceptionMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_badexception(o, e);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_badcompare(Object o, int i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Comparable_CompareToNullExceptionMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_badcompare(o, i);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class InputStream_ManipulateAfterCloseMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<InputStream_ManipulateAfterCloseMonitor> {

	InputStream_ManipulateAfterCloseMonitor_Set(){
		this.size = 0;
		this.elements = new InputStream_ManipulateAfterCloseMonitor[4];
	}
	final void event_manipulate(InputStream i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			InputStream_ManipulateAfterCloseMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final InputStream_ManipulateAfterCloseMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_manipulate(i);
				if(monitorfinalMonitor.InputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_close(InputStream i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			InputStream_ManipulateAfterCloseMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final InputStream_ManipulateAfterCloseMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_close(i);
				if(monitorfinalMonitor.InputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class ListIterator_SetMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<ListIterator_SetMonitor> {

	ListIterator_SetMonitor_Set(){
		this.size = 0;
		this.elements = new ListIterator_SetMonitor[4];
	}
	final void event_create(ListIterator i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ListIterator_SetMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final ListIterator_SetMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_create(i);
				if(monitorfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_remove(ListIterator i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ListIterator_SetMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final ListIterator_SetMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_remove(i);
				if(monitorfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_add(ListIterator i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ListIterator_SetMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final ListIterator_SetMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_add(i);
				if(monitorfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_next(ListIterator i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ListIterator_SetMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final ListIterator_SetMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_next(i);
				if(monitorfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_previous(ListIterator i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ListIterator_SetMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final ListIterator_SetMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_previous(i);
				if(monitorfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_set(ListIterator i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ListIterator_SetMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final ListIterator_SetMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_set(i);
				if(monitorfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Long_BadParsingArgsMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Long_BadParsingArgsMonitor> {

	Long_BadParsingArgsMonitor_Set(){
		this.size = 0;
		this.elements = new Long_BadParsingArgsMonitor[4];
	}
	final void event_bad_arg(String s, int radix) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Long_BadParsingArgsMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_bad_arg(s, radix);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_bad_arg2(String s) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Long_BadParsingArgsMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_bad_arg2(s);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Map_UnsafeIteratorMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Map_UnsafeIteratorMonitor> {

	Map_UnsafeIteratorMonitor_Set(){
		this.size = 0;
		this.elements = new Map_UnsafeIteratorMonitor[4];
	}
	final void event_getset(Map m, Collection c) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Map_UnsafeIteratorMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Map_UnsafeIteratorMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_getset(m, c);
				if(monitorfinalMonitor.Map_UnsafeIteratorMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_getiter(Collection c, Iterator i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Map_UnsafeIteratorMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Map_UnsafeIteratorMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_getiter(c, i);
				if(monitorfinalMonitor.Map_UnsafeIteratorMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_modifyMap(Map m) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Map_UnsafeIteratorMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Map_UnsafeIteratorMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_modifyMap(m);
				if(monitorfinalMonitor.Map_UnsafeIteratorMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_modifyCol(Collection c) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Map_UnsafeIteratorMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Map_UnsafeIteratorMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_modifyCol(c);
				if(monitorfinalMonitor.Map_UnsafeIteratorMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_useiter(Iterator i) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Map_UnsafeIteratorMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Map_UnsafeIteratorMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_useiter(i);
				if(monitorfinalMonitor.Map_UnsafeIteratorMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Object_MonitorOwnerMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Object_MonitorOwnerMonitor> {

	Object_MonitorOwnerMonitor_Set(){
		this.size = 0;
		this.elements = new Object_MonitorOwnerMonitor[4];
	}
	final void event_bad_notify(Object o) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Object_MonitorOwnerMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_bad_notify(o);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_bad_wait(Object o) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Object_MonitorOwnerMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_bad_wait(o);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class OutputStream_ManipulateAfterCloseMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<OutputStream_ManipulateAfterCloseMonitor> {

	OutputStream_ManipulateAfterCloseMonitor_Set(){
		this.size = 0;
		this.elements = new OutputStream_ManipulateAfterCloseMonitor[4];
	}
	final void event_manipulate(OutputStream o) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			OutputStream_ManipulateAfterCloseMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final OutputStream_ManipulateAfterCloseMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_manipulate(o);
				if(monitorfinalMonitor.OutputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_close(OutputStream o) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			OutputStream_ManipulateAfterCloseMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final OutputStream_ManipulateAfterCloseMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_close(o);
				if(monitorfinalMonitor.OutputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Reader_ManipulateAfterCloseMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Reader_ManipulateAfterCloseMonitor> {

	Reader_ManipulateAfterCloseMonitor_Set(){
		this.size = 0;
		this.elements = new Reader_ManipulateAfterCloseMonitor[4];
	}
	final void event_manipulate(Reader r) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Reader_ManipulateAfterCloseMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Reader_ManipulateAfterCloseMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_manipulate(r);
				if(monitorfinalMonitor.Reader_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_close(Reader r) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Reader_ManipulateAfterCloseMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Reader_ManipulateAfterCloseMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_close(r);
				if(monitorfinalMonitor.Reader_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Serializable_NoArgConstructorMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Serializable_NoArgConstructorMonitor> {

	Serializable_NoArgConstructorMonitor_Set(){
		this.size = 0;
		this.elements = new Serializable_NoArgConstructorMonitor[4];
	}
	final void event_staticinit(org.aspectj.lang.Signature staticsig) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Serializable_NoArgConstructorMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_staticinit(staticsig);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class ServerSocket_BacklogMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<ServerSocket_BacklogMonitor> {

	ServerSocket_BacklogMonitor_Set(){
		this.size = 0;
		this.elements = new ServerSocket_BacklogMonitor[4];
	}
	final void event_construct(int backlog) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ServerSocket_BacklogMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_construct(backlog);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_set(int backlog) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ServerSocket_BacklogMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_set(backlog);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class ServerSocket_SetTimeoutBeforeBlockingMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<ServerSocket_SetTimeoutBeforeBlockingMonitor> {

	ServerSocket_SetTimeoutBeforeBlockingMonitor_Set(){
		this.size = 0;
		this.elements = new ServerSocket_SetTimeoutBeforeBlockingMonitor[4];
	}
	final void event_enter(ServerSocket sock) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ServerSocket_SetTimeoutBeforeBlockingMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final ServerSocket_SetTimeoutBeforeBlockingMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_enter(sock);
				if(monitorfinalMonitor.ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_leave(ServerSocket sock) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ServerSocket_SetTimeoutBeforeBlockingMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final ServerSocket_SetTimeoutBeforeBlockingMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_leave(sock);
				if(monitorfinalMonitor.ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_set(ServerSocket sock, int timeout) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			ServerSocket_SetTimeoutBeforeBlockingMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final ServerSocket_SetTimeoutBeforeBlockingMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_set(sock, timeout);
				if(monitorfinalMonitor.ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail) {
					monitorfinalMonitor.Prop_1_handler_fail();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class SortedSet_ComparableMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<SortedSet_ComparableMonitor> {

	SortedSet_ComparableMonitor_Set(){
		this.size = 0;
		this.elements = new SortedSet_ComparableMonitor[4];
	}
	final void event_add(SortedSet s, Object e) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			SortedSet_ComparableMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_add(s, e);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_addall(SortedSet s, Collection c) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			SortedSet_ComparableMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_addall(s, c);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class TreeMap_ComparableMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<TreeMap_ComparableMonitor> {

	TreeMap_ComparableMonitor_Set(){
		this.size = 0;
		this.elements = new TreeMap_ComparableMonitor[4];
	}
	final void event_create(Map src) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			TreeMap_ComparableMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_create(src);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_put(Object key) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			TreeMap_ComparableMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_put(key);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_putall(Map src) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			TreeMap_ComparableMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_putall(src);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class TreeSet_ComparableMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<TreeSet_ComparableMonitor> {

	TreeSet_ComparableMonitor_Set(){
		this.size = 0;
		this.elements = new TreeSet_ComparableMonitor[4];
	}
	final void event_add(Object e) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			TreeSet_ComparableMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_add(e);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_addall(Collection c) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			TreeSet_ComparableMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_addall(c);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class URLConnection_OverrideGetPermissionMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<URLConnection_OverrideGetPermissionMonitor> {

	URLConnection_OverrideGetPermissionMonitor_Set(){
		this.size = 0;
		this.elements = new URLConnection_OverrideGetPermissionMonitor[4];
	}
	final void event_staticinit(org.aspectj.lang.Signature staticsig) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			URLConnection_OverrideGetPermissionMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_staticinit(staticsig);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class URLDecoder_DecodeUTF8Monitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<URLDecoder_DecodeUTF8Monitor> {

	URLDecoder_DecodeUTF8Monitor_Set(){
		this.size = 0;
		this.elements = new URLDecoder_DecodeUTF8Monitor[4];
	}
	final void event_decode(String enc) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			URLDecoder_DecodeUTF8Monitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_decode(enc);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class URLEncoder_EncodeUTF8Monitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<URLEncoder_EncodeUTF8Monitor> {

	URLEncoder_EncodeUTF8Monitor_Set(){
		this.size = 0;
		this.elements = new URLEncoder_EncodeUTF8Monitor[4];
	}
	final void event_encode(String enc) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			URLEncoder_EncodeUTF8Monitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				monitor.event_encode(enc);
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}
final class Writer_ManipulateAfterCloseMonitor_Set extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractMonitorSet<Writer_ManipulateAfterCloseMonitor> {

	Writer_ManipulateAfterCloseMonitor_Set(){
		this.size = 0;
		this.elements = new Writer_ManipulateAfterCloseMonitor[4];
	}
	final void event_manipulate(Writer w) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Writer_ManipulateAfterCloseMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Writer_ManipulateAfterCloseMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_manipulate(w);
				if(monitorfinalMonitor.Writer_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
	final void event_close(Writer w) {
		int numAlive = 0 ;
		for(int i_1 = 0; i_1 < this.size; i_1++){
			Writer_ManipulateAfterCloseMonitor monitor = this.elements[i_1];
			if(!monitor.isTerminated()){
				elements[numAlive] = monitor;
				numAlive++;

				final Writer_ManipulateAfterCloseMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_close(w);
				if(monitorfinalMonitor.Writer_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}
			}
		}
		for(int i_1 = numAlive; i_1 < this.size; i_1++){
			this.elements[i_1] = null;
		}
		size = numAlive;
	}
}

class CharSequence_NotInSetMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			CharSequence_NotInSetMonitor ret = (CharSequence_NotInSetMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	boolean flag = false;

	CharSequence_NotInSetMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_set_add() {
		RVM_lastevent = 0;
		{
			if ( ! (!flag) ) {
				return false;
			}
			{
				flag = true;
				android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: CharSequence_NotInSet It might not be safe to add a CharSequence instance into a set");
			}
		}
		return true;
	}

	final boolean event_set_addall(Collection c) {
		RVM_lastevent = 1;
		{
			if ( ! (!flag) ) {
				return false;
			}
			{
				for (Object o : c) {
					if (o instanceof CharSequence && !(o instanceof String) && !(o instanceof CharBuffer)) {
						flag = true;
						android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: CharSequence_NotInSet It might not be safe to add a CharSequence instance into a set");
					}
				}
			}
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//set_add
			return;
			case 1:
			//set_addall
			return;
		}
		return;
	}

}
class CharSequence_UndefinedHashCodeMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			CharSequence_UndefinedHashCodeMonitor ret = (CharSequence_UndefinedHashCodeMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	CharSequence_UndefinedHashCodeMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_equals() {
		RVM_lastevent = 0;
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: CharSequence_UndefinedHashCode equals and hashCode methods might not be supported in CharSequence");
		}
		return true;
	}

	final boolean event_hashCode() {
		RVM_lastevent = 1;
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: CharSequence_UndefinedHashCode equals and hashCode methods might not be supported in CharSequence");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//equals
			return;
			case 1:
			//hashCode
			return;
		}
		return;
	}

}
class Closeable_MeaninglessCloseMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Closeable_MeaninglessCloseMonitor ret = (Closeable_MeaninglessCloseMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Closeable_MeaninglessCloseMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_close() {
		RVM_lastevent = 0;
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Closeable_MeaninglessClose close() has no effect.");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//close
			return;
		}
		return;
	}

}
class Collection_HashCodeMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Collection_HashCodeMonitor ret = (Collection_HashCodeMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Collection_HashCodeMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_staticinit(org.aspectj.lang.Signature staticsig) {
		RVM_lastevent = 0;
		{
			Signature initsig = staticsig;
			Class klass = initsig.getDeclaringType();
			if (klass != null) {
				Method equalsmethod = null;
				Method hashcodemethod = null;
				try {
					equalsmethod = klass.getDeclaredMethod("equals", Object.class);
					hashcodemethod = klass.getDeclaredMethod("hashCode", (Class[]) null);
				} catch (NoSuchMethodException e) {
				}
				if (equalsmethod != null && hashcodemethod == null) {
					android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Collection_HashCode " + klass.getName() + " overrides equals() but does not override hashCode().");
				}
			}
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//staticinit
			return;
		}
		return;
	}

}
class Collection_UnsynchronizedAddAllMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Collection_UnsynchronizedAddAllMonitor ret = (Collection_UnsynchronizedAddAllMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	WeakReference Ref_t = null;

	static final int Prop_1_transition_enter[] = {1, 3, 1, 3};;
	static final int Prop_1_transition_modify[] = {3, 3, 2, 3};;
	static final int Prop_1_transition_leave[] = {3, 2, 3, 3};;

	volatile boolean Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail = false;

	private AtomicInteger pairValue;

	Collection_UnsynchronizedAddAllMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
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

	final boolean Prop_1_event_enter(Collection t, Collection s) {
		{
		}
		if(Ref_t == null){
			Ref_t = new WeakReference(t);
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_enter) ;
		this.Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_modify(Collection s) {
		Collection t = null;
		if(Ref_t != null){
			t = (Collection)Ref_t.get();
		}
		{
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_modify) ;
		this.Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail = nextstate == 3;

		return true;
	}

	final boolean Prop_1_event_leave(Collection t, Collection s) {
		{
		}
		if(Ref_t == null){
			Ref_t = new WeakReference(t);
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_leave) ;
		this.Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail = nextstate == 3;

		return true;
	}

	final void Prop_1_handler_fail (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Collection_UnsynchronizedAddAll The source collection of addAll() has been modified.");
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail = false;
	}

	// RVMRef_t was suppressed to reduce memory overhead
	// RVMRef_s was suppressed to reduce memory overhead

	//alive_parameters_0 = [Collection s]
	boolean alive_parameters_0 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		int lastEvent = this.getLastEvent();

		switch(idnum){
			case 0:
			break;
			case 1:
			alive_parameters_0 = false;
			break;
		}
		switch(lastEvent) {
			case -1:
			return;
			case 0:
			//enter
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//modify
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 2:
			//leave
			//alive_s
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

		}
		return;
	}

	public static int getNumberOfEvents() {
		return 3;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}
interface ICollections_SynchronizedCollectionMonitor extends IMonitor, IDisableHolder {
}

class Collections_SynchronizedCollectionDisableHolder extends DisableHolder implements ICollections_SynchronizedCollectionMonitor {
	Collections_SynchronizedCollectionDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class Collections_SynchronizedCollectionMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, ICollections_SynchronizedCollectionMonitor {
	protected Object clone() {
		try {
			Collections_SynchronizedCollectionMonitor ret = (Collections_SynchronizedCollectionMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Collection col;

	WeakReference Ref_col = null;
	WeakReference Ref_iter = null;
	int Prop_1_state;
	static final int Prop_1_transition_sync[] = {1, 4, 4, 4, 4};;
	static final int Prop_1_transition_syncCreateIter[] = {4, 2, 4, 4, 4};;
	static final int Prop_1_transition_asyncCreateIter[] = {4, 3, 4, 4, 4};;
	static final int Prop_1_transition_accessIter[] = {4, 4, 3, 4, 4};;

	boolean Collections_SynchronizedCollectionMonitor_Prop_1_Category_match = false;

	Collections_SynchronizedCollectionMonitor(long tau) {
		this.tau = tau;
		Prop_1_state = 0;

	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_sync(Collection col) {
		Iterator iter = null;
		if(Ref_iter != null){
			iter = (Iterator)Ref_iter.get();
		}
		{
			this.col = col;
		}
		if(Ref_col == null){
			Ref_col = new WeakReference(col);
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_sync[Prop_1_state];
		Collections_SynchronizedCollectionMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_syncCreateIter(Collection col, Iterator iter) {
		{
			if ( ! (Thread.holdsLock(col)) ) {
				return false;
			}
			{
			}
		}
		if(Ref_col == null){
			Ref_col = new WeakReference(col);
		}
		if(Ref_iter == null){
			Ref_iter = new WeakReference(iter);
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_syncCreateIter[Prop_1_state];
		Collections_SynchronizedCollectionMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_asyncCreateIter(Collection col, Iterator iter) {
		{
			if ( ! (!Thread.holdsLock(col)) ) {
				return false;
			}
			{
			}
		}
		if(Ref_col == null){
			Ref_col = new WeakReference(col);
		}
		if(Ref_iter == null){
			Ref_iter = new WeakReference(iter);
		}
		RVM_lastevent = 2;

		Prop_1_state = Prop_1_transition_asyncCreateIter[Prop_1_state];
		Collections_SynchronizedCollectionMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_accessIter(Iterator iter) {
		Collection col = null;
		if(Ref_col != null){
			col = (Collection)Ref_col.get();
		}
		{
			if ( ! (!Thread.holdsLock(this.col)) ) {
				return false;
			}
			{
			}
		}
		if(Ref_iter == null){
			Ref_iter = new WeakReference(iter);
		}
		RVM_lastevent = 3;

		Prop_1_state = Prop_1_transition_accessIter[Prop_1_state];
		Collections_SynchronizedCollectionMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final void Prop_1_handler_match (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Collections_SynchronizedCollection A synchronized collection was accessed in a thread-unsafe manner.");
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		Collections_SynchronizedCollectionMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_col was suppressed to reduce memory overhead
	// RVMRef_iter was suppressed to reduce memory overhead

	//alive_parameters_0 = [Collection col, Iterator iter]
	boolean alive_parameters_0 = true;
	//alive_parameters_1 = [Iterator iter]
	boolean alive_parameters_1 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
			case 1:
			alive_parameters_0 = false;
			alive_parameters_1 = false;
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//sync
			//alive_col && alive_iter
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//syncCreateIter
			//alive_iter
			if(!(alive_parameters_1)){
				RVM_terminated = true;
				return;
			}
			break;

			case 2:
			//asyncCreateIter
			return;
			case 3:
			//accessIter
			return;
		}
		return;
	}

	public static int getNumberOfEvents() {
		return 4;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}
interface ICollections_SynchronizedMapMonitor extends IMonitor, IDisableHolder {
}

class Collections_SynchronizedMapDisableHolder extends DisableHolder implements ICollections_SynchronizedMapMonitor {
	Collections_SynchronizedMapDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class Collections_SynchronizedMapMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, ICollections_SynchronizedMapMonitor {
	protected Object clone() {
		try {
			Collections_SynchronizedMapMonitor ret = (Collections_SynchronizedMapMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Map map;

	WeakReference Ref_col = null;
	WeakReference Ref_syncMap = null;
	WeakReference Ref_iter = null;
	int Prop_1_state;
	static final int Prop_1_transition_sync[] = {2, 5, 5, 5, 5, 5};;
	static final int Prop_1_transition_createSet[] = {5, 5, 1, 5, 5, 5};;
	static final int Prop_1_transition_syncCreateIter[] = {5, 4, 5, 5, 5, 5};;
	static final int Prop_1_transition_asyncCreateIter[] = {5, 3, 5, 5, 5, 5};;
	static final int Prop_1_transition_accessIter[] = {5, 5, 5, 5, 3, 5};;

	boolean Collections_SynchronizedMapMonitor_Prop_1_Category_match = false;

	Collections_SynchronizedMapMonitor(long tau, CachedWeakReference RVMRef_syncMap) {
		this.tau = tau;
		Prop_1_state = 0;

		this.RVMRef_syncMap = RVMRef_syncMap;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_sync(Map syncMap) {
		Collection col = null;
		if(Ref_col != null){
			col = (Collection)Ref_col.get();
		}
		Iterator iter = null;
		if(Ref_iter != null){
			iter = (Iterator)Ref_iter.get();
		}
		{
			this.map = syncMap;
		}
		if(Ref_syncMap == null){
			Ref_syncMap = new WeakReference(syncMap);
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_sync[Prop_1_state];
		Collections_SynchronizedMapMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_createSet(Map syncMap, Collection col) {
		Iterator iter = null;
		if(Ref_iter != null){
			iter = (Iterator)Ref_iter.get();
		}
		{
		}
		if(Ref_col == null){
			Ref_col = new WeakReference(col);
		}
		if(Ref_syncMap == null){
			Ref_syncMap = new WeakReference(syncMap);
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_createSet[Prop_1_state];
		Collections_SynchronizedMapMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_syncCreateIter(Collection col, Iterator iter) {
		Map syncMap = null;
		if(Ref_syncMap != null){
			syncMap = (Map)Ref_syncMap.get();
		}
		{
			if ( ! (Thread.holdsLock(map)) ) {
				return false;
			}
			{
			}
		}
		if(Ref_col == null){
			Ref_col = new WeakReference(col);
		}
		if(Ref_iter == null){
			Ref_iter = new WeakReference(iter);
		}
		RVM_lastevent = 2;

		Prop_1_state = Prop_1_transition_syncCreateIter[Prop_1_state];
		Collections_SynchronizedMapMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_asyncCreateIter(Collection col, Iterator iter) {
		Map syncMap = null;
		if(Ref_syncMap != null){
			syncMap = (Map)Ref_syncMap.get();
		}
		{
			if ( ! (!Thread.holdsLock(map)) ) {
				return false;
			}
			{
			}
		}
		if(Ref_col == null){
			Ref_col = new WeakReference(col);
		}
		if(Ref_iter == null){
			Ref_iter = new WeakReference(iter);
		}
		RVM_lastevent = 3;

		Prop_1_state = Prop_1_transition_asyncCreateIter[Prop_1_state];
		Collections_SynchronizedMapMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_accessIter(Iterator iter) {
		Map syncMap = null;
		if(Ref_syncMap != null){
			syncMap = (Map)Ref_syncMap.get();
		}
		Collection col = null;
		if(Ref_col != null){
			col = (Collection)Ref_col.get();
		}
		{
			if ( ! (!Thread.holdsLock(map)) ) {
				return false;
			}
			{
			}
		}
		if(Ref_iter == null){
			Ref_iter = new WeakReference(iter);
		}
		RVM_lastevent = 4;

		Prop_1_state = Prop_1_transition_accessIter[Prop_1_state];
		Collections_SynchronizedMapMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final void Prop_1_handler_match (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Collections_SynchronizedMap A collection view of a synchronized map was accessed in a thread-unsafe manner.");
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		Collections_SynchronizedMapMonitor_Prop_1_Category_match = false;
	}

	final CachedWeakReference RVMRef_syncMap;
	// RVMRef_col was suppressed to reduce memory overhead
	// RVMRef_iter was suppressed to reduce memory overhead

	//alive_parameters_0 = [Map syncMap, Collection col, Iterator iter]
	boolean alive_parameters_0 = true;
	//alive_parameters_1 = [Collection col, Iterator iter]
	boolean alive_parameters_1 = true;
	//alive_parameters_2 = [Iterator iter]
	boolean alive_parameters_2 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			alive_parameters_0 = false;
			break;
			case 1:
			alive_parameters_0 = false;
			alive_parameters_1 = false;
			break;
			case 2:
			alive_parameters_0 = false;
			alive_parameters_1 = false;
			alive_parameters_2 = false;
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//sync
			//alive_syncMap && alive_col && alive_iter
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//createSet
			//alive_col && alive_iter
			if(!(alive_parameters_1)){
				RVM_terminated = true;
				return;
			}
			break;

			case 2:
			//syncCreateIter
			//alive_iter
			if(!(alive_parameters_2)){
				RVM_terminated = true;
				return;
			}
			break;

			case 3:
			//asyncCreateIter
			return;
			case 4:
			//accessIter
			return;
		}
		return;
	}

	public static int getNumberOfEvents() {
		return 5;
	}

	public static int getNumberOfStates() {
		return 6;
	}

}
class Collections_UnnecessaryNewSetFromMapMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Collections_UnnecessaryNewSetFromMapMonitor ret = (Collections_UnnecessaryNewSetFromMapMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Collections_UnnecessaryNewSetFromMapMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_unnecessary() {
		RVM_lastevent = 0;
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Collections_UnnecessaryNewSetFromMap There is no need to use Collections.newSetFromMap() on HashMap or TreeMap.");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//unnecessary
			return;
		}
		return;
	}

}
class Comparable_CompareToNullMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Comparable_CompareToNullMonitor ret = (Comparable_CompareToNullMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Comparable_CompareToNullMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_nullcompare(Object o) {
		RVM_lastevent = 0;
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Comparable_CompareToNull null cannot be compared to any object");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//nullcompare
			return;
		}
		return;
	}

}
class Comparable_CompareToNullExceptionMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Comparable_CompareToNullExceptionMonitor ret = (Comparable_CompareToNullExceptionMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Comparable_CompareToNullExceptionMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_badexception(Object o, Exception e) {
		RVM_lastevent = 0;
		{
			if ( ! (!(e instanceof NullPointerException)) ) {
				return false;
			}
			{
				android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Comparable_CompareToNullException NullPointerException should be thrown when an object is compared to null");
			}
		}
		return true;
	}

	final boolean event_badcompare(Object o, int i) {
		RVM_lastevent = 1;
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Comparable_CompareToNullException NullPointerException should be thrown when an object is compared to null");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//badexception
			return;
			case 1:
			//badcompare
			return;
		}
		return;
	}

}
class InputStream_ManipulateAfterCloseMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			InputStream_ManipulateAfterCloseMonitor ret = (InputStream_ManipulateAfterCloseMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	static final int Prop_1_transition_manipulate[] = {3, 2, 3, 3};;
	static final int Prop_1_transition_close[] = {1, 1, 3, 3};;

	volatile boolean InputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	InputStream_ManipulateAfterCloseMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
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

	final boolean Prop_1_event_manipulate(InputStream i) {
		{
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_manipulate) ;
		this.InputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match = nextstate == 2;

		return true;
	}

	final boolean Prop_1_event_close(InputStream i) {
		{
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_close) ;
		this.InputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match = nextstate == 2;

		return true;
	}

	final void Prop_1_handler_match (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: InputStream_ManipulateAfterClose read(), available(), reset() or skip() was invoked after close().");
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		InputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_i was suppressed to reduce memory overhead

	//alive_parameters_0 = [InputStream i]
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
			//manipulate
			return;
			case 1:
			//close
			//alive_i
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

		}
		return;
	}

	public static int getNumberOfEvents() {
		return 2;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}
class ListIterator_SetMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			ListIterator_SetMonitor ret = (ListIterator_SetMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	static final int Prop_1_transition_create[] = {1, 4, 4, 4, 4};;
	static final int Prop_1_transition_remove[] = {4, 4, 3, 4, 4};;
	static final int Prop_1_transition_add[] = {4, 1, 1, 4, 4};;
	static final int Prop_1_transition_next[] = {4, 2, 2, 2, 4};;
	static final int Prop_1_transition_previous[] = {4, 2, 2, 2, 4};;
	static final int Prop_1_transition_set[] = {4, 4, 2, 4, 4};;

	volatile boolean ListIterator_SetMonitor_Prop_1_Category_fail = false;

	private AtomicInteger pairValue;

	ListIterator_SetMonitor() {
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

	final boolean Prop_1_event_create(ListIterator i) {
		{
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_create) ;
		this.ListIterator_SetMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_remove(ListIterator i) {
		{
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_remove) ;
		this.ListIterator_SetMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_add(ListIterator i) {
		{
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_add) ;
		this.ListIterator_SetMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_next(ListIterator i) {
		{
		}

		int nextstate = this.handleEvent(3, Prop_1_transition_next) ;
		this.ListIterator_SetMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_previous(ListIterator i) {
		{
		}

		int nextstate = this.handleEvent(4, Prop_1_transition_previous) ;
		this.ListIterator_SetMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_set(ListIterator i) {
		{
		}

		int nextstate = this.handleEvent(5, Prop_1_transition_set) ;
		this.ListIterator_SetMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final void Prop_1_handler_fail (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: ListIterator_Set ListIterator.set() can be made only if neither remove() nor add() have been called after the last call to next() or previous().");
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		ListIterator_SetMonitor_Prop_1_Category_fail = false;
	}

	// RVMRef_i was suppressed to reduce memory overhead

	//alive_parameters_0 = [ListIterator i]
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
			//create
			//alive_i
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//remove
			//alive_i
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 2:
			//add
			//alive_i
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 3:
			//next
			//alive_i
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 4:
			//previous
			//alive_i
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 5:
			//set
			//alive_i
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

		}
		return;
	}

	public static int getNumberOfEvents() {
		return 6;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}
class Long_BadParsingArgsMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Long_BadParsingArgsMonitor ret = (Long_BadParsingArgsMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Long_BadParsingArgsMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_bad_arg(String s, int radix) {
		RVM_lastevent = 0;
		{
			if (s == null || s.length() == 0) {
				android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Long_BadParsingArgs Wrong argument to Long.parseLong(String s, int radix)");
			} else if (radix < java.lang.Character.MIN_RADIX || radix > java.lang.Character.MAX_RADIX) {
				android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Long_BadParsingArgs Wrong argument to Long.parseLong(String s, int radix)");
			} else {
				for (int j = 0; j < s.length(); j++) {
					if (Character.digit(s.charAt(j), radix) == -1) {
						if (j == 0 && s.length() > 1 && s.charAt(0) == '-') {
						} else if (j == s.length() - 1 && (s.charAt(j) == 'l' || s.charAt(j) == 'L')) {
						} else {
							android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Long_BadParsingArgs Wrong argument to Long.parseLong(String s, int radix)");
						}
					}
				}
			}
		}
		return true;
	}

	final boolean event_bad_arg2(String s) {
		RVM_lastevent = 1;
		{
			if (s == null || s.length() == 0) {
				android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Long_BadParsingArgs Wrong argument to Long.parseLong(String s)");
			} else {
				for (int j = 0; j < s.length(); j++) {
					if (Character.digit(s.charAt(j), 10) == -1) {
						if (j == 0 && s.length() > 1 && s.charAt(0) == '-') {
						} else if (j == s.length() - 1 && (s.charAt(j) == 'l' || s.charAt(j) == 'L')) {
						} else {
							android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Long_BadParsingArgs Wrong argument to Long.parseLong(String s)");
						}
					}
				}
			}
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//bad_arg
			return;
			case 1:
			//bad_arg2
			return;
		}
		return;
	}

}
interface IMap_UnsafeIteratorMonitor extends IMonitor, IDisableHolder {
}

class Map_UnsafeIteratorDisableHolder extends DisableHolder implements IMap_UnsafeIteratorMonitor {
	Map_UnsafeIteratorDisableHolder(long tau) {
		super(tau);
	}

	@Override
	public final boolean isTerminated() {
		return false;
	}

	@Override
	public int getLastEvent() {
		return -1;
	}

	@Override
	public int getState() {
		return -1;
	}

}

class Map_UnsafeIteratorMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject, IMap_UnsafeIteratorMonitor {
	protected Object clone() {
		try {
			Map_UnsafeIteratorMonitor ret = (Map_UnsafeIteratorMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	WeakReference Ref_c = null;
	WeakReference Ref_i = null;
	WeakReference Ref_m = null;
	int Prop_1_state;
	static final int Prop_1_transition_getset[] = {2, 5, 5, 5, 5, 5};;
	static final int Prop_1_transition_getiter[] = {5, 5, 1, 5, 5, 5};;
	static final int Prop_1_transition_modifyMap[] = {5, 4, 2, 5, 4, 5};;
	static final int Prop_1_transition_modifyCol[] = {5, 4, 2, 5, 4, 5};;
	static final int Prop_1_transition_useiter[] = {5, 1, 5, 5, 3, 5};;

	boolean Map_UnsafeIteratorMonitor_Prop_1_Category_match = false;

	Map_UnsafeIteratorMonitor(long tau, CachedWeakReference RVMRef_m) {
		this.tau = tau;
		Prop_1_state = 0;

		this.RVMRef_m = RVMRef_m;
	}

	@Override
	public final int getState() {
		return Prop_1_state;
	}

	private final long tau;
	private long disable = -1;

	@Override
	public final long getTau() {
		return this.tau;
	}

	@Override
	public final long getDisable() {
		return this.disable;
	}

	@Override
	public final void setDisable(long value) {
		this.disable = value;
	}

	final boolean Prop_1_event_getset(Map m, Collection c) {
		Iterator i = null;
		if(Ref_i != null){
			i = (Iterator)Ref_i.get();
		}
		{
		}
		if(Ref_c == null){
			Ref_c = new WeakReference(c);
		}
		if(Ref_m == null){
			Ref_m = new WeakReference(m);
		}
		RVM_lastevent = 0;

		Prop_1_state = Prop_1_transition_getset[Prop_1_state];
		Map_UnsafeIteratorMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_getiter(Collection c, Iterator i) {
		Map m = null;
		if(Ref_m != null){
			m = (Map)Ref_m.get();
		}
		{
		}
		if(Ref_c == null){
			Ref_c = new WeakReference(c);
		}
		if(Ref_i == null){
			Ref_i = new WeakReference(i);
		}
		RVM_lastevent = 1;

		Prop_1_state = Prop_1_transition_getiter[Prop_1_state];
		Map_UnsafeIteratorMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_modifyMap(Map m) {
		Collection c = null;
		if(Ref_c != null){
			c = (Collection)Ref_c.get();
		}
		Iterator i = null;
		if(Ref_i != null){
			i = (Iterator)Ref_i.get();
		}
		{
		}
		if(Ref_m == null){
			Ref_m = new WeakReference(m);
		}
		RVM_lastevent = 2;

		Prop_1_state = Prop_1_transition_modifyMap[Prop_1_state];
		Map_UnsafeIteratorMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_modifyCol(Collection c) {
		Map m = null;
		if(Ref_m != null){
			m = (Map)Ref_m.get();
		}
		Iterator i = null;
		if(Ref_i != null){
			i = (Iterator)Ref_i.get();
		}
		{
		}
		if(Ref_c == null){
			Ref_c = new WeakReference(c);
		}
		RVM_lastevent = 3;

		Prop_1_state = Prop_1_transition_modifyCol[Prop_1_state];
		Map_UnsafeIteratorMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final boolean Prop_1_event_useiter(Iterator i) {
		Map m = null;
		if(Ref_m != null){
			m = (Map)Ref_m.get();
		}
		Collection c = null;
		if(Ref_c != null){
			c = (Collection)Ref_c.get();
		}
		{
		}
		if(Ref_i == null){
			Ref_i = new WeakReference(i);
		}
		RVM_lastevent = 4;

		Prop_1_state = Prop_1_transition_useiter[Prop_1_state];
		Map_UnsafeIteratorMonitor_Prop_1_Category_match = Prop_1_state == 3;
		return true;
	}

	final void Prop_1_handler_match (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Map_UnsafeIterator The map was modified while an iteration over the set is in progress.");
		}

	}

	final void reset() {
		RVM_lastevent = -1;
		Prop_1_state = 0;
		Map_UnsafeIteratorMonitor_Prop_1_Category_match = false;
	}

	final CachedWeakReference RVMRef_m;
	// RVMRef_c was suppressed to reduce memory overhead
	// RVMRef_i was suppressed to reduce memory overhead

	//alive_parameters_0 = [Collection c, Iterator i]
	boolean alive_parameters_0 = true;
	//alive_parameters_1 = [Map m, Iterator i]
	boolean alive_parameters_1 = true;
	//alive_parameters_2 = [Iterator i]
	boolean alive_parameters_2 = true;

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			alive_parameters_1 = false;
			break;
			case 1:
			alive_parameters_0 = false;
			break;
			case 2:
			alive_parameters_0 = false;
			alive_parameters_1 = false;
			alive_parameters_2 = false;
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//getset
			//alive_c && alive_i
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//getiter
			//alive_m && alive_i || alive_c && alive_i
			if(!(alive_parameters_1 || alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 2:
			//modifyMap
			//alive_i
			if(!(alive_parameters_2)){
				RVM_terminated = true;
				return;
			}
			break;

			case 3:
			//modifyCol
			//alive_i
			if(!(alive_parameters_2)){
				RVM_terminated = true;
				return;
			}
			break;

			case 4:
			//useiter
			//alive_m && alive_i || alive_c && alive_i
			if(!(alive_parameters_1 || alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

		}
		return;
	}

	public static int getNumberOfEvents() {
		return 5;
	}

	public static int getNumberOfStates() {
		return 6;
	}

}
class Object_MonitorOwnerMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Object_MonitorOwnerMonitor ret = (Object_MonitorOwnerMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	Object_MonitorOwnerMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_bad_notify(Object o) {
		RVM_lastevent = 0;
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Object_MonitorOwner notify() and notifyAll() can be called only by the owner of this object's monitor.");
		}
		return true;
	}

	final boolean event_bad_wait(Object o) {
		RVM_lastevent = 1;
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Object_MonitorOwner wait() can be called only by the owner of this object's monitor.");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//bad_notify
			return;
			case 1:
			//bad_wait
			return;
		}
		return;
	}

}
class OutputStream_ManipulateAfterCloseMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			OutputStream_ManipulateAfterCloseMonitor ret = (OutputStream_ManipulateAfterCloseMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	static final int Prop_1_transition_manipulate[] = {3, 1, 1, 3};;
	static final int Prop_1_transition_close[] = {2, 3, 2, 3};;

	volatile boolean OutputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	OutputStream_ManipulateAfterCloseMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
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

	final boolean Prop_1_event_manipulate(OutputStream o) {
		{
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_manipulate) ;
		this.OutputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_close(OutputStream o) {
		{
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_close) ;
		this.OutputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_match (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: OutputStream_ManipulateAfterClose write() or flush() was invoked after close().");
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		OutputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_o was suppressed to reduce memory overhead

	//alive_parameters_0 = [OutputStream o]
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
			//manipulate
			//alive_o
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//close
			//alive_o
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

		}
		return;
	}

	public static int getNumberOfEvents() {
		return 2;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}
class Reader_ManipulateAfterCloseMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Reader_ManipulateAfterCloseMonitor ret = (Reader_ManipulateAfterCloseMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	static final int Prop_1_transition_manipulate[] = {3, 1, 1, 3};;
	static final int Prop_1_transition_close[] = {2, 3, 2, 3};;

	volatile boolean Reader_ManipulateAfterCloseMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	Reader_ManipulateAfterCloseMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
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

	final boolean Prop_1_event_manipulate(Reader r) {
		{
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_manipulate) ;
		this.Reader_ManipulateAfterCloseMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_close(Reader r) {
		{
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_close) ;
		this.Reader_ManipulateAfterCloseMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_match (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Reader_ManipulateAfterClose read(), ready(), mark(), reset() or skip() was invoked after close().");
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		Reader_ManipulateAfterCloseMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_r was suppressed to reduce memory overhead

	//alive_parameters_0 = [Reader r]
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
			//manipulate
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//close
			//alive_r
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

		}
		return;
	}

	public static int getNumberOfEvents() {
		return 2;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}
class Serializable_NoArgConstructorMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Serializable_NoArgConstructorMonitor ret = (Serializable_NoArgConstructorMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	private String getPackageName(Class cl) {
		String s = cl.getName();
		int i = s.lastIndexOf('[');
		if (i >= 0) s = s.substring(i + 2);
		i = s.lastIndexOf('.');
		return (i >= 0) ? s.substring(0, i) : "";
	}

	Serializable_NoArgConstructorMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_staticinit(org.aspectj.lang.Signature staticsig) {
		RVM_lastevent = 0;
		{
			org.aspectj.lang.Signature initsig = staticsig;
			Class klass = initsig.getDeclaringType();
			if (klass != null) {
				Class nonserialzable = klass;
				while (Serializable.class.isAssignableFrom(nonserialzable)) {
					nonserialzable = nonserialzable.getSuperclass();
					if (nonserialzable == null) break;
				}
				if (nonserialzable != null) {
					boolean samepackage = klass.getClassLoader() == nonserialzable.getClassLoader() && getPackageName(klass).equals(getPackageName(nonserialzable));
					boolean inaccessible = true;
					try {
						Constructor ctor = nonserialzable.getDeclaredConstructor((Class[]) null);
						int mod = ctor.getModifiers();
						inaccessible = (mod & Modifier.PRIVATE) != 0 || ((mod & (Modifier.PUBLIC | Modifier.PROTECTED)) == 0 && !samepackage);
					} catch (NoSuchMethodException e) {
					}
					if (inaccessible) {
						android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Serializable_NoArgConstructor " + "The superclass of " + klass.getName() + " does not have an accessible no-arg constructor.");
					}
				}
			}
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//staticinit
			return;
		}
		return;
	}

}
class ServerSocket_BacklogMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			ServerSocket_BacklogMonitor ret = (ServerSocket_BacklogMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	private void check(int backlog, String msg) {
		if (backlog > 0) return;
		android.util.Log.v("RVSEC", "[helper] ::: ServerSocket_Backlog " + msg);
		android.util.Log.v("RVSEC", "[helper] ::: ServerSocket_Backlog " + "The backlog argument " + backlog + " is invalid; it should be greater than 0.");
	}

	ServerSocket_BacklogMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_construct(int backlog) {
		RVM_lastevent = 0;
		{
			this.check(backlog, "");
		}
		return true;
	}

	final boolean event_set(int backlog) {
		RVM_lastevent = 1;
		{
			this.check(backlog, "");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//construct
			return;
			case 1:
			//set
			return;
		}
		return;
	}

}
class ServerSocket_SetTimeoutBeforeBlockingMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			ServerSocket_SetTimeoutBeforeBlockingMonitor ret = (ServerSocket_SetTimeoutBeforeBlockingMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	static final int Prop_1_transition_enter[] = {1, 4, 4, 1, 4};;
	static final int Prop_1_transition_leave[] = {4, 3, 4, 4, 4};;
	static final int Prop_1_transition_set[] = {0, 4, 2, 2, 4};;

	volatile boolean ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail = false;

	private AtomicInteger pairValue;

	ServerSocket_SetTimeoutBeforeBlockingMonitor() {
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

	final boolean Prop_1_event_enter(ServerSocket sock) {
		{
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_enter) ;
		this.ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_leave(ServerSocket sock) {
		{
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_leave) ;
		this.ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final boolean Prop_1_event_set(ServerSocket sock, int timeout) {
		{
			if ( ! (timeout != 0) ) {
				return false;
			}
			{
			}
		}

		int nextstate = this.handleEvent(2, Prop_1_transition_set) ;
		this.ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail = nextstate == 4;

		return true;
	}

	final void Prop_1_handler_fail (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: ServerSocket_SetTimeoutBeforeBlocking ServerSocket.setSoTimeout() should be set prior to entering the blocking operation.");
			this.reset();
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail = false;
	}

	// RVMRef_sock was suppressed to reduce memory overhead

	//alive_parameters_0 = [ServerSocket sock]
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
			//enter
			//alive_sock
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//leave
			//alive_sock
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 2:
			//set
			//alive_sock
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

		}
		return;
	}

	public static int getNumberOfEvents() {
		return 3;
	}

	public static int getNumberOfStates() {
		return 5;
	}

}
class SortedSet_ComparableMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			SortedSet_ComparableMonitor ret = (SortedSet_ComparableMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	SortedSet_ComparableMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_add(SortedSet s, Object e) {
		RVM_lastevent = 0;
		{
			if (s.comparator() == null && !(e instanceof Comparable)) {
				android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: SortedSet_Comparable A non-comparable object is being inserted into a SortedSet object.");
			}
		}
		return true;
	}

	final boolean event_addall(SortedSet s, Collection c) {
		RVM_lastevent = 1;
		{
			for (Object elem : c) {
				if (s.comparator() == null && !(elem instanceof Comparable)) {
					android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: SortedSet_Comparable A non-comparable object is being inserted into a SortedSet object.");
				}
			}
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	// RVMRef_s was suppressed to reduce memory overhead

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
			case 0:
			break;
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//add
			return;
			case 1:
			//addall
			return;
		}
		return;
	}

}
class TreeMap_ComparableMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			TreeMap_ComparableMonitor ret = (TreeMap_ComparableMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	private void validate(Object elem, String msg) {
		if (!(elem instanceof Comparable)) {
			android.util.Log.v("RVSEC", "[helper] ::: TreeMap_Comparable " + msg);
			android.util.Log.v("RVSEC", "[helper] ::: TreeMap_Comparable A non-comparable object is being inserted into a TreeMap object.");
		}
	}

	private void validateAll(Map src, String msg) {
		for (Map.Entry entry : (Collection<Map.Entry>) src.entrySet()) {
			validate(entry.getKey(), msg);
		}
	}

	TreeMap_ComparableMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_create(Map src) {
		RVM_lastevent = 0;
		{
			validateAll(src, "");
		}
		return true;
	}

	final boolean event_put(Object key) {
		RVM_lastevent = 1;
		{
			validate(key, "");
		}
		return true;
	}

	final boolean event_putall(Map src) {
		RVM_lastevent = 2;
		{
			validateAll(src, "");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//create
			return;
			case 1:
			//put
			return;
			case 2:
			//putall
			return;
		}
		return;
	}

}
class TreeSet_ComparableMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			TreeSet_ComparableMonitor ret = (TreeSet_ComparableMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	TreeSet_ComparableMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_add(Object e) {
		RVM_lastevent = 0;
		{
			if (!(e instanceof Comparable)) {
				android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: TreeSet_Comparable A non-comparable object is being inserted into a TreeSet object.");
			}
		}
		return true;
	}

	final boolean event_addall(Collection c) {
		RVM_lastevent = 1;
		{
			for (Object elem : c) {
				if (!(elem instanceof Comparable)) {
					android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: TreeSet_Comparable A non-comparable object is being inserted into a TreeSet object.");
				}
			}
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//add
			return;
			case 1:
			//addall
			return;
		}
		return;
	}

}
class URLConnection_OverrideGetPermissionMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			URLConnection_OverrideGetPermissionMonitor ret = (URLConnection_OverrideGetPermissionMonitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	URLConnection_OverrideGetPermissionMonitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_staticinit(org.aspectj.lang.Signature staticsig) {
		RVM_lastevent = 0;
		{
			org.aspectj.lang.Signature initsig = staticsig;
			Class klass = initsig.getDeclaringType();
			Method overriden = null;
			while (klass != null && !klass.getName().equals("java.net.URLConnection")) {
				try {
					for (Method m : klass.getDeclaredMethods()) {
						if (!m.getName().equals("getPermission")) continue;
						if (m.getParameterTypes().length != 0) continue;
						overriden = m;
						break;
					}
					if (overriden != null) break;
				} catch (SecurityException e) {
				}
				klass = klass.getSuperclass();
			}
			if (overriden == null) {
				android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: URLConnection_OverrideGetPermission A URLConnection class should override the getPermission() method.");
			}
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//staticinit
			return;
		}
		return;
	}

}
class URLDecoder_DecodeUTF8Monitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			URLDecoder_DecodeUTF8Monitor ret = (URLDecoder_DecodeUTF8Monitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	URLDecoder_DecodeUTF8Monitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_decode(String enc) {
		RVM_lastevent = 0;
		{
			if (enc.equalsIgnoreCase("utf-8") || enc.equalsIgnoreCase("utf8")) return true;
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: URLDecoder_DecodeUTF8 " + "The used encoding '" + enc + "' may introduce incompatibilites.");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//decode
			return;
		}
		return;
	}

}
class URLEncoder_EncodeUTF8Monitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			URLEncoder_EncodeUTF8Monitor ret = (URLEncoder_EncodeUTF8Monitor) super.clone();
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	URLEncoder_EncodeUTF8Monitor(){
	}
	@Override
	public final int getState() {
		return -1;
	}

	final boolean event_encode(String enc) {
		RVM_lastevent = 0;
		{
			if (enc.equalsIgnoreCase("utf-8") || enc.equalsIgnoreCase("utf8")) return true;
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: URLEncoder_EncodeUTF8 " + "The used encoding '" + enc + "' may introduce incompatibilites.");
		}
		return true;
	}

	final void reset() {
		RVM_lastevent = -1;
	}

	@Override
	protected final void terminateInternal(int idnum) {
		switch(idnum){
		}
		switch(RVM_lastevent) {
			case -1:
			return;
			case 0:
			//encode
			return;
		}
		return;
	}

}
class Writer_ManipulateAfterCloseMonitor extends com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractAtomicMonitor implements Cloneable, com.runtimeverification.rvmonitor.java.rt.RVMObject {
	protected Object clone() {
		try {
			Writer_ManipulateAfterCloseMonitor ret = (Writer_ManipulateAfterCloseMonitor) super.clone();
			ret.pairValue = new AtomicInteger(pairValue.get());
			return ret;
		}
		catch (CloneNotSupportedException e) {
			throw new InternalError(e.toString());
		}
	}

	static final int Prop_1_transition_manipulate[] = {3, 1, 1, 3};;
	static final int Prop_1_transition_close[] = {2, 3, 2, 3};;

	volatile boolean Writer_ManipulateAfterCloseMonitor_Prop_1_Category_match = false;

	private AtomicInteger pairValue;

	Writer_ManipulateAfterCloseMonitor() {
		this.pairValue = new AtomicInteger(this.calculatePairValue(-1, 0) ) ;

	}

	@Override public final int getState() {
		return this.getState(this.pairValue.get() ) ;
	}
	@Override public final int getLastEvent() {
		return this.getLastEvent(this.pairValue.get() ) ;
	}
	private final int getState(int pairValue) {
		return (pairValue & 3) ;
	}
	private final int getLastEvent(int pairValue) {
		return (pairValue >> 2) ;
	}
	private final int calculatePairValue(int lastEvent, int state) {
		return (((lastEvent + 1) << 2) | state) ;
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

	final boolean Prop_1_event_manipulate(Writer w) {
		{
		}

		int nextstate = this.handleEvent(0, Prop_1_transition_manipulate) ;
		this.Writer_ManipulateAfterCloseMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final boolean Prop_1_event_close(Writer w) {
		{
		}

		int nextstate = this.handleEvent(1, Prop_1_transition_close) ;
		this.Writer_ManipulateAfterCloseMonitor_Prop_1_Category_match = nextstate == 1;

		return true;
	}

	final void Prop_1_handler_match (){
		{
			android.util.Log.v("RVSEC", com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode() + " ::: Writer_ManipulateAfterClose write() or flush() was invoked after close().");
		}

	}

	final void reset() {
		this.pairValue.set(this.calculatePairValue(-1, 0) ) ;

		Writer_ManipulateAfterCloseMonitor_Prop_1_Category_match = false;
	}

	// RVMRef_w was suppressed to reduce memory overhead

	//alive_parameters_0 = [Writer w]
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
			//manipulate
			//alive_w
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

			case 1:
			//close
			//alive_w
			if(!(alive_parameters_0)){
				RVM_terminated = true;
				return;
			}
			break;

		}
		return;
	}

	public static int getNumberOfEvents() {
		return 2;
	}

	public static int getNumberOfStates() {
		return 4;
	}

}

public final class MultiSpec_1RuntimeMonitor implements com.runtimeverification.rvmonitor.java.rt.RVMObject {
	private static com.runtimeverification.rvmonitor.java.rt.map.RVMMapManager MultiSpec_1MapManager;
	static {
		MultiSpec_1MapManager = new com.runtimeverification.rvmonitor.java.rt.map.RVMMapManager();
		MultiSpec_1MapManager.start();
	}

	// Declarations for the Lock
	static final ReentrantLock MultiSpec_1_RVMLock = new ReentrantLock();
	static final Condition MultiSpec_1_RVMLock_cond = MultiSpec_1_RVMLock.newCondition();

	// Declarations for Timestamps
	private static long Collections_SynchronizedMap_timestamp = 1;
	private static long Map_UnsafeIterator_timestamp = 1;
	private static long Collections_SynchronizedCollection_timestamp = 1;

	private static boolean CharSequence_NotInSet_activated = false;
	private static boolean CharSequence_UndefinedHashCode_activated = false;
	private static boolean Closeable_MeaninglessClose_activated = false;
	private static boolean Collection_HashCode_activated = false;
	private static boolean Collection_UnsynchronizedAddAll_activated = false;
	private static boolean Collections_SynchronizedCollection_activated = false;
	private static boolean Collections_SynchronizedMap_activated = false;
	private static boolean Collections_UnnecessaryNewSetFromMap_activated = false;
	private static boolean Comparable_CompareToNull_activated = false;
	private static boolean Comparable_CompareToNullException_activated = false;
	private static boolean InputStream_ManipulateAfterClose_activated = false;
	private static boolean ListIterator_Set_activated = false;
	private static boolean Long_BadParsingArgs_activated = false;
	private static boolean Map_UnsafeIterator_activated = false;
	private static boolean Object_MonitorOwner_activated = false;
	private static boolean OutputStream_ManipulateAfterClose_activated = false;
	private static boolean Reader_ManipulateAfterClose_activated = false;
	private static boolean Serializable_NoArgConstructor_activated = false;
	private static boolean ServerSocket_Backlog_activated = false;
	private static boolean ServerSocket_SetTimeoutBeforeBlocking_activated = false;
	private static boolean SortedSet_Comparable_activated = false;
	private static boolean TreeMap_Comparable_activated = false;
	private static boolean TreeSet_Comparable_activated = false;
	private static boolean URLConnection_OverrideGetPermission_activated = false;
	private static boolean URLDecoder_DecodeUTF8_activated = false;
	private static boolean URLEncoder_EncodeUTF8_activated = false;
	private static boolean Writer_ManipulateAfterClose_activated = false;

	// Declarations for Indexing Trees
	private static final CharSequence_NotInSetMonitor CharSequence_NotInSet__Map = new CharSequence_NotInSetMonitor() ;

	private static final CharSequence_UndefinedHashCodeMonitor CharSequence_UndefinedHashCode__Map = new CharSequence_UndefinedHashCodeMonitor() ;

	private static final Closeable_MeaninglessCloseMonitor Closeable_MeaninglessClose__Map = new Closeable_MeaninglessCloseMonitor() ;

	private static final Collection_HashCodeMonitor Collection_HashCode__Map = new Collection_HashCodeMonitor() ;

	private static Object Collection_UnsynchronizedAddAll_s_Map_cachekey_s;
	private static Collection_UnsynchronizedAddAllMonitor_Set Collection_UnsynchronizedAddAll_s_Map_cachevalue;
	private static Object Collection_UnsynchronizedAddAll_t_s_Map_cachekey_s;
	private static Object Collection_UnsynchronizedAddAll_t_s_Map_cachekey_t;
	private static Collection_UnsynchronizedAddAllMonitor Collection_UnsynchronizedAddAll_t_s_Map_cachevalue;
	private static final MapOfSet<Collection_UnsynchronizedAddAllMonitor_Set> Collection_UnsynchronizedAddAll_s_Map = new MapOfSet<Collection_UnsynchronizedAddAllMonitor_Set>(1) ;
	private static final MapOfMap<MapOfMonitor<Collection_UnsynchronizedAddAllMonitor>> Collection_UnsynchronizedAddAll_t_s_Map = new MapOfMap<MapOfMonitor<Collection_UnsynchronizedAddAllMonitor>>(0) ;

	private static Object Collections_SynchronizedCollection_col_Map_cachekey_col;
	private static Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> Collections_SynchronizedCollection_col_Map_cachevalue;
	private static Object Collections_SynchronizedCollection_col_iter_Map_cachekey_col;
	private static Object Collections_SynchronizedCollection_col_iter_Map_cachekey_iter;
	private static ICollections_SynchronizedCollectionMonitor Collections_SynchronizedCollection_col_iter_Map_cachevalue;
	private static Object Collections_SynchronizedCollection_iter_Map_cachekey_iter;
	private static Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor> Collections_SynchronizedCollection_iter_Map_cachevalue;
	private static final MapOfSetMonitor<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor> Collections_SynchronizedCollection_iter_Map = new MapOfSetMonitor<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor>(1) ;
	private static final MapOfAll<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> Collections_SynchronizedCollection_col_iter_Map = new MapOfAll<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor>(0) ;

	private static Object Collections_SynchronizedMap_col_iter_Map_cachekey_col;
	private static Object Collections_SynchronizedMap_col_iter_Map_cachekey_iter;
	private static Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> Collections_SynchronizedMap_col_iter_Map_cachevalue;
	private static Object Collections_SynchronizedMap_iter_Map_cachekey_iter;
	private static Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> Collections_SynchronizedMap_iter_Map_cachevalue;
	private static Object Collections_SynchronizedMap_syncMap_Map_cachekey_syncMap;
	private static Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> Collections_SynchronizedMap_syncMap_Map_cachevalue;
	private static Object Collections_SynchronizedMap_syncMap_col_Map_cachekey_col;
	private static Object Collections_SynchronizedMap_syncMap_col_Map_cachekey_syncMap;
	private static Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> Collections_SynchronizedMap_syncMap_col_Map_cachevalue;
	private static Object Collections_SynchronizedMap_syncMap_col_iter_Map_cachekey_col;
	private static Object Collections_SynchronizedMap_syncMap_col_iter_Map_cachekey_iter;
	private static Object Collections_SynchronizedMap_syncMap_col_iter_Map_cachekey_syncMap;
	private static ICollections_SynchronizedMapMonitor Collections_SynchronizedMap_syncMap_col_iter_Map_cachevalue;
	private static final MapOfMap<MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>> Collections_SynchronizedMap_col_iter_Map = new MapOfMap<MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>>(1) ;
	private static final MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> Collections_SynchronizedMap_iter_Map = new MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(2) ;
	private static final MapOfAll<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> Collections_SynchronizedMap_syncMap_col_iter_Map = new MapOfAll<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>(0) ;
	private static Object Collections_SynchronizedMap_col__To__syncMap_col_Map_cachekey_col;
	private static Tuple2<Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> Collections_SynchronizedMap_col__To__syncMap_col_Map_cachevalue;
	private static final MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> Collections_SynchronizedMap_col__To__syncMap_col_Map = new MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>(1) ;

	private static final Collections_UnnecessaryNewSetFromMapMonitor Collections_UnnecessaryNewSetFromMap__Map = new Collections_UnnecessaryNewSetFromMapMonitor() ;

	private static final Comparable_CompareToNullMonitor Comparable_CompareToNull__Map = new Comparable_CompareToNullMonitor() ;

	private static final Comparable_CompareToNullExceptionMonitor Comparable_CompareToNullException__Map = new Comparable_CompareToNullExceptionMonitor() ;

	private static Object InputStream_ManipulateAfterClose_i_Map_cachekey_i;
	private static InputStream_ManipulateAfterCloseMonitor InputStream_ManipulateAfterClose_i_Map_cachevalue;
	private static final MapOfMonitor<InputStream_ManipulateAfterCloseMonitor> InputStream_ManipulateAfterClose_i_Map = new MapOfMonitor<InputStream_ManipulateAfterCloseMonitor>(0) ;

	private static Object ListIterator_Set_i_Map_cachekey_i;
	private static ListIterator_SetMonitor ListIterator_Set_i_Map_cachevalue;
	private static final MapOfMonitor<ListIterator_SetMonitor> ListIterator_Set_i_Map = new MapOfMonitor<ListIterator_SetMonitor>(0) ;

	private static final Long_BadParsingArgsMonitor Long_BadParsingArgs__Map = new Long_BadParsingArgsMonitor() ;

	private static Object Map_UnsafeIterator_c_Map_cachekey_c;
	private static Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> Map_UnsafeIterator_c_Map_cachevalue;
	private static Object Map_UnsafeIterator_c_i_Map_cachekey_c;
	private static Object Map_UnsafeIterator_c_i_Map_cachekey_i;
	private static Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> Map_UnsafeIterator_c_i_Map_cachevalue;
	private static Object Map_UnsafeIterator_i_Map_cachekey_i;
	private static Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> Map_UnsafeIterator_i_Map_cachevalue;
	private static Object Map_UnsafeIterator_m_Map_cachekey_m;
	private static Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> Map_UnsafeIterator_m_Map_cachevalue;
	private static Object Map_UnsafeIterator_m_c_Map_cachekey_c;
	private static Object Map_UnsafeIterator_m_c_Map_cachekey_m;
	private static Tuple3<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> Map_UnsafeIterator_m_c_Map_cachevalue;
	private static Object Map_UnsafeIterator_m_c_i_Map_cachekey_c;
	private static Object Map_UnsafeIterator_m_c_i_Map_cachekey_i;
	private static Object Map_UnsafeIterator_m_c_i_Map_cachekey_m;
	private static IMap_UnsafeIteratorMonitor Map_UnsafeIterator_m_c_i_Map_cachevalue;
	private static final MapOfAll<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> Map_UnsafeIterator_c_i_Map = new MapOfAll<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>(1) ;
	private static final MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> Map_UnsafeIterator_i_Map = new MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>(2) ;
	private static final MapOfAll<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> Map_UnsafeIterator_m_c_i_Map = new MapOfAll<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>(0) ;
	private static Object Map_UnsafeIterator_c__To__m_c_Map_cachekey_c;
	private static Tuple2<Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> Map_UnsafeIterator_c__To__m_c_Map_cachevalue;
	private static final MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> Map_UnsafeIterator_c__To__m_c_Map = new MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>(1) ;

	private static final Object_MonitorOwnerMonitor Object_MonitorOwner__Map = new Object_MonitorOwnerMonitor() ;

	private static Object OutputStream_ManipulateAfterClose_o_Map_cachekey_o;
	private static OutputStream_ManipulateAfterCloseMonitor OutputStream_ManipulateAfterClose_o_Map_cachevalue;
	private static final MapOfMonitor<OutputStream_ManipulateAfterCloseMonitor> OutputStream_ManipulateAfterClose_o_Map = new MapOfMonitor<OutputStream_ManipulateAfterCloseMonitor>(0) ;

	private static Object Reader_ManipulateAfterClose_r_Map_cachekey_r;
	private static Reader_ManipulateAfterCloseMonitor Reader_ManipulateAfterClose_r_Map_cachevalue;
	private static final MapOfMonitor<Reader_ManipulateAfterCloseMonitor> Reader_ManipulateAfterClose_r_Map = new MapOfMonitor<Reader_ManipulateAfterCloseMonitor>(0) ;

	private static final Serializable_NoArgConstructorMonitor Serializable_NoArgConstructor__Map = new Serializable_NoArgConstructorMonitor() ;

	private static final ServerSocket_BacklogMonitor ServerSocket_Backlog__Map = new ServerSocket_BacklogMonitor() ;

	private static Object ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachekey_sock;
	private static ServerSocket_SetTimeoutBeforeBlockingMonitor ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachevalue;
	private static final MapOfMonitor<ServerSocket_SetTimeoutBeforeBlockingMonitor> ServerSocket_SetTimeoutBeforeBlocking_sock_Map = new MapOfMonitor<ServerSocket_SetTimeoutBeforeBlockingMonitor>(0) ;

	private static Object SortedSet_Comparable_s_Map_cachekey_s;
	private static SortedSet_ComparableMonitor SortedSet_Comparable_s_Map_cachevalue;
	private static final MapOfMonitor<SortedSet_ComparableMonitor> SortedSet_Comparable_s_Map = new MapOfMonitor<SortedSet_ComparableMonitor>(0) ;

	private static final TreeMap_ComparableMonitor TreeMap_Comparable__Map = new TreeMap_ComparableMonitor() ;

	private static final TreeSet_ComparableMonitor TreeSet_Comparable__Map = new TreeSet_ComparableMonitor() ;

	private static final URLConnection_OverrideGetPermissionMonitor URLConnection_OverrideGetPermission__Map = new URLConnection_OverrideGetPermissionMonitor() ;

	private static final URLDecoder_DecodeUTF8Monitor URLDecoder_DecodeUTF8__Map = new URLDecoder_DecodeUTF8Monitor() ;

	private static final URLEncoder_EncodeUTF8Monitor URLEncoder_EncodeUTF8__Map = new URLEncoder_EncodeUTF8Monitor() ;

	private static Object Writer_ManipulateAfterClose_w_Map_cachekey_w;
	private static Writer_ManipulateAfterCloseMonitor Writer_ManipulateAfterClose_w_Map_cachevalue;
	private static final MapOfMonitor<Writer_ManipulateAfterCloseMonitor> Writer_ManipulateAfterClose_w_Map = new MapOfMonitor<Writer_ManipulateAfterCloseMonitor>(0) ;

	public static int cleanUp() {
		int collected = 0;
		// indexing trees
		collected += Collection_UnsynchronizedAddAll_s_Map.cleanUpUnnecessaryMappings();
		collected += Collection_UnsynchronizedAddAll_t_s_Map.cleanUpUnnecessaryMappings();
		collected += Collections_SynchronizedCollection_iter_Map.cleanUpUnnecessaryMappings();
		collected += Collections_SynchronizedCollection_col_iter_Map.cleanUpUnnecessaryMappings();
		collected += Collections_SynchronizedMap_col_iter_Map.cleanUpUnnecessaryMappings();
		collected += Collections_SynchronizedMap_iter_Map.cleanUpUnnecessaryMappings();
		collected += Collections_SynchronizedMap_syncMap_col_iter_Map.cleanUpUnnecessaryMappings();
		collected += Collections_SynchronizedMap_col__To__syncMap_col_Map.cleanUpUnnecessaryMappings();
		collected += InputStream_ManipulateAfterClose_i_Map.cleanUpUnnecessaryMappings();
		collected += ListIterator_Set_i_Map.cleanUpUnnecessaryMappings();
		collected += Map_UnsafeIterator_c_i_Map.cleanUpUnnecessaryMappings();
		collected += Map_UnsafeIterator_i_Map.cleanUpUnnecessaryMappings();
		collected += Map_UnsafeIterator_m_c_i_Map.cleanUpUnnecessaryMappings();
		collected += Map_UnsafeIterator_c__To__m_c_Map.cleanUpUnnecessaryMappings();
		collected += OutputStream_ManipulateAfterClose_o_Map.cleanUpUnnecessaryMappings();
		collected += Reader_ManipulateAfterClose_r_Map.cleanUpUnnecessaryMappings();
		collected += ServerSocket_SetTimeoutBeforeBlocking_sock_Map.cleanUpUnnecessaryMappings();
		collected += SortedSet_Comparable_s_Map.cleanUpUnnecessaryMappings();
		collected += Writer_ManipulateAfterClose_w_Map.cleanUpUnnecessaryMappings();
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

	public static final void CharSequence_NotInSet_set_addEvent() {
		CharSequence_NotInSet_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CharSequence_NotInSetMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CharSequence_NotInSet__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CharSequence_NotInSetMonitor created = new CharSequence_NotInSetMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_set_add();

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CharSequence_NotInSet_set_addallEvent(Collection c) {
		CharSequence_NotInSet_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CharSequence_NotInSetMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CharSequence_NotInSet__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CharSequence_NotInSetMonitor created = new CharSequence_NotInSetMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_set_addall(c);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CharSequence_UndefinedHashCode_equalsEvent() {
		CharSequence_UndefinedHashCode_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CharSequence_UndefinedHashCodeMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CharSequence_UndefinedHashCode__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CharSequence_UndefinedHashCodeMonitor created = new CharSequence_UndefinedHashCodeMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_equals();

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void CharSequence_UndefinedHashCode_hashCodeEvent() {
		CharSequence_UndefinedHashCode_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CharSequence_UndefinedHashCodeMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = CharSequence_UndefinedHashCode__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			CharSequence_UndefinedHashCodeMonitor created = new CharSequence_UndefinedHashCodeMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_hashCode();

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Closeable_MeaninglessClose_closeEvent() {
		Closeable_MeaninglessClose_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Closeable_MeaninglessCloseMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Closeable_MeaninglessClose__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Closeable_MeaninglessCloseMonitor created = new Closeable_MeaninglessCloseMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_close();

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collection_HashCode_staticinitEvent(org.aspectj.lang.Signature staticsig) {
		Collection_HashCode_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Collection_HashCodeMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Collection_HashCode__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Collection_HashCodeMonitor created = new Collection_HashCodeMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_staticinit(staticsig);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_SynchronizedCollection_syncEvent(Collection col) {
		Collections_SynchronizedCollection_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_col = null;
		Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> matchedEntry = null;
		boolean cachehit = false;
		if ((col == Collections_SynchronizedCollection_col_Map_cachekey_col) ) {
			matchedEntry = Collections_SynchronizedCollection_col_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_col = new CachedWeakReference(col) ;
			{
				// FindOrCreateEntry
				Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> node_col = Collections_SynchronizedCollection_col_iter_Map.getNodeEquivalent(wr_col) ;
				if ((node_col == null) ) {
					node_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor>() ;
					Collections_SynchronizedCollection_col_iter_Map.putNode(wr_col, node_col) ;
					node_col.setValue1(new MapOfMonitor<ICollections_SynchronizedCollectionMonitor>(1) ) ;
					node_col.setValue2(new Collections_SynchronizedCollectionMonitor_Set() ) ;
				}
				matchedEntry = node_col;
			}
		}
		// D(X) main:1
		Collections_SynchronizedCollectionMonitor matchedLeaf = matchedEntry.getValue3() ;
		if ((matchedLeaf == null) ) {
			if ((wr_col == null) ) {
				wr_col = new CachedWeakReference(col) ;
			}
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				Collections_SynchronizedCollectionMonitor created = new Collections_SynchronizedCollectionMonitor(Collections_SynchronizedCollection_timestamp++) ;
				matchedEntry.setValue3(created) ;
				Collections_SynchronizedCollectionMonitor_Set enclosingSet = matchedEntry.getValue2() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			Collections_SynchronizedCollectionMonitor disableUpdatedLeaf = matchedEntry.getValue3() ;
			disableUpdatedLeaf.setDisable(Collections_SynchronizedCollection_timestamp++) ;
		}
		// D(X) main:8--9
		Collections_SynchronizedCollectionMonitor_Set stateTransitionedSet = matchedEntry.getValue2() ;
		stateTransitionedSet.event_sync(col);

		if ((cachehit == false) ) {
			Collections_SynchronizedCollection_col_Map_cachekey_col = col;
			Collections_SynchronizedCollection_col_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_SynchronizedCollection_syncCreateIterEvent(Collection col, Iterator iter) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Collections_SynchronizedCollection_activated) {
			CachedWeakReference wr_col = null;
			CachedWeakReference wr_iter = null;
			MapOfMonitor<ICollections_SynchronizedCollectionMonitor> matchedLastMap = null;
			ICollections_SynchronizedCollectionMonitor matchedEntry = null;
			boolean cachehit = false;
			if (((col == Collections_SynchronizedCollection_col_iter_Map_cachekey_col) && (iter == Collections_SynchronizedCollection_col_iter_Map_cachekey_iter) ) ) {
				matchedEntry = Collections_SynchronizedCollection_col_iter_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_col = new CachedWeakReference(col) ;
				wr_iter = new CachedWeakReference(iter) ;
				{
					// FindOrCreateEntry
					Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> node_col = Collections_SynchronizedCollection_col_iter_Map.getNodeEquivalent(wr_col) ;
					if ((node_col == null) ) {
						node_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor>() ;
						Collections_SynchronizedCollection_col_iter_Map.putNode(wr_col, node_col) ;
						node_col.setValue1(new MapOfMonitor<ICollections_SynchronizedCollectionMonitor>(1) ) ;
						node_col.setValue2(new Collections_SynchronizedCollectionMonitor_Set() ) ;
					}
					MapOfMonitor<ICollections_SynchronizedCollectionMonitor> itmdMap = node_col.getValue1() ;
					matchedLastMap = itmdMap;
					ICollections_SynchronizedCollectionMonitor node_col_iter = node_col.getValue1() .getNodeEquivalent(wr_iter) ;
					matchedEntry = node_col_iter;
				}
			}
			// D(X) main:1
			if ((matchedEntry == null) ) {
				if ((wr_col == null) ) {
					wr_col = new CachedWeakReference(col) ;
				}
				if ((wr_iter == null) ) {
					wr_iter = new CachedWeakReference(iter) ;
				}
				{
					// D(X) createNewMonitorStates:4 when Dom(theta'') = <col>
					Collections_SynchronizedCollectionMonitor sourceLeaf = null;
					{
						// FindCode
						Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> node_col = Collections_SynchronizedCollection_col_iter_Map.getNodeEquivalent(wr_col) ;
						if ((node_col != null) ) {
							Collections_SynchronizedCollectionMonitor itmdLeaf = node_col.getValue3() ;
							sourceLeaf = itmdLeaf;
						}
					}
					if ((sourceLeaf != null) ) {
						boolean definable = true;
						// D(X) defineTo:1--5 for <col, iter>
						if (definable) {
							// FindCode
							Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> node_col = Collections_SynchronizedCollection_col_iter_Map.getNodeEquivalent(wr_col) ;
							if ((node_col != null) ) {
								ICollections_SynchronizedCollectionMonitor node_col_iter = node_col.getValue1() .getNodeEquivalent(wr_iter) ;
								if ((node_col_iter != null) ) {
									if (((node_col_iter.getDisable() > sourceLeaf.getTau() ) || ((node_col_iter.getTau() > 0) && (node_col_iter.getTau() < sourceLeaf.getTau() ) ) ) ) {
										definable = false;
									}
								}
							}
						}
						// D(X) defineTo:1--5 for <iter>
						if (definable) {
							// FindCode
							Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor> node_iter = Collections_SynchronizedCollection_iter_Map.getNodeEquivalent(wr_iter) ;
							if ((node_iter != null) ) {
								ICollections_SynchronizedCollectionMonitor itmdLeaf = node_iter.getValue2() ;
								if ((itmdLeaf != null) ) {
									if (((itmdLeaf.getDisable() > sourceLeaf.getTau() ) || ((itmdLeaf.getTau() > 0) && (itmdLeaf.getTau() < sourceLeaf.getTau() ) ) ) ) {
										definable = false;
									}
								}
							}
						}
						if (definable) {
							// D(X) defineTo:6
							Collections_SynchronizedCollectionMonitor created = (Collections_SynchronizedCollectionMonitor)sourceLeaf.clone() ;
							matchedEntry = created;
							matchedLastMap.putNode(wr_iter, created) ;
							// D(X) defineTo:7 for <col>
							{
								// InsertMonitor
								Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> node_col = Collections_SynchronizedCollection_col_iter_Map.getNodeEquivalent(wr_col) ;
								if ((node_col == null) ) {
									node_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor>() ;
									Collections_SynchronizedCollection_col_iter_Map.putNode(wr_col, node_col) ;
									node_col.setValue1(new MapOfMonitor<ICollections_SynchronizedCollectionMonitor>(1) ) ;
									node_col.setValue2(new Collections_SynchronizedCollectionMonitor_Set() ) ;
								}
								Collections_SynchronizedCollectionMonitor_Set targetSet = node_col.getValue2() ;
								targetSet.add(created) ;
							}
							// D(X) defineTo:7 for <iter>
							{
								// InsertMonitor
								Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor> node_iter = Collections_SynchronizedCollection_iter_Map.getNodeEquivalent(wr_iter) ;
								if ((node_iter == null) ) {
									node_iter = new Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor>() ;
									Collections_SynchronizedCollection_iter_Map.putNode(wr_iter, node_iter) ;
									node_iter.setValue1(new Collections_SynchronizedCollectionMonitor_Set() ) ;
								}
								Collections_SynchronizedCollectionMonitor_Set targetSet = node_iter.getValue1() ;
								targetSet.add(created) ;
							}
						}
					}
				}
				// D(X) main:6
				if ((matchedEntry == null) ) {
					Collections_SynchronizedCollectionDisableHolder holder = new Collections_SynchronizedCollectionDisableHolder(-1) ;
					matchedLastMap.putNode(wr_iter, holder) ;
					matchedEntry = holder;
				}
				matchedEntry.setDisable(Collections_SynchronizedCollection_timestamp++) ;
			}
			// D(X) main:8--9
			if (matchedEntry instanceof Collections_SynchronizedCollectionMonitor) {
				Collections_SynchronizedCollectionMonitor monitor = (Collections_SynchronizedCollectionMonitor)matchedEntry;
				final Collections_SynchronizedCollectionMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_syncCreateIter(col, iter);
				if(monitorfinalMonitor.Collections_SynchronizedCollectionMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}

				if ((cachehit == false) ) {
					Collections_SynchronizedCollection_col_iter_Map_cachekey_col = col;
					Collections_SynchronizedCollection_col_iter_Map_cachekey_iter = iter;
					Collections_SynchronizedCollection_col_iter_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_SynchronizedCollection_asyncCreateIterEvent(Collection col, Iterator iter) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Collections_SynchronizedCollection_activated) {
			CachedWeakReference wr_col = null;
			CachedWeakReference wr_iter = null;
			MapOfMonitor<ICollections_SynchronizedCollectionMonitor> matchedLastMap = null;
			ICollections_SynchronizedCollectionMonitor matchedEntry = null;
			boolean cachehit = false;
			if (((col == Collections_SynchronizedCollection_col_iter_Map_cachekey_col) && (iter == Collections_SynchronizedCollection_col_iter_Map_cachekey_iter) ) ) {
				matchedEntry = Collections_SynchronizedCollection_col_iter_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_col = new CachedWeakReference(col) ;
				wr_iter = new CachedWeakReference(iter) ;
				{
					// FindOrCreateEntry
					Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> node_col = Collections_SynchronizedCollection_col_iter_Map.getNodeEquivalent(wr_col) ;
					if ((node_col == null) ) {
						node_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor>() ;
						Collections_SynchronizedCollection_col_iter_Map.putNode(wr_col, node_col) ;
						node_col.setValue1(new MapOfMonitor<ICollections_SynchronizedCollectionMonitor>(1) ) ;
						node_col.setValue2(new Collections_SynchronizedCollectionMonitor_Set() ) ;
					}
					MapOfMonitor<ICollections_SynchronizedCollectionMonitor> itmdMap = node_col.getValue1() ;
					matchedLastMap = itmdMap;
					ICollections_SynchronizedCollectionMonitor node_col_iter = node_col.getValue1() .getNodeEquivalent(wr_iter) ;
					matchedEntry = node_col_iter;
				}
			}
			// D(X) main:1
			if ((matchedEntry == null) ) {
				if ((wr_col == null) ) {
					wr_col = new CachedWeakReference(col) ;
				}
				if ((wr_iter == null) ) {
					wr_iter = new CachedWeakReference(iter) ;
				}
				{
					// D(X) createNewMonitorStates:4 when Dom(theta'') = <col>
					Collections_SynchronizedCollectionMonitor sourceLeaf = null;
					{
						// FindCode
						Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> node_col = Collections_SynchronizedCollection_col_iter_Map.getNodeEquivalent(wr_col) ;
						if ((node_col != null) ) {
							Collections_SynchronizedCollectionMonitor itmdLeaf = node_col.getValue3() ;
							sourceLeaf = itmdLeaf;
						}
					}
					if ((sourceLeaf != null) ) {
						boolean definable = true;
						// D(X) defineTo:1--5 for <col, iter>
						if (definable) {
							// FindCode
							Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> node_col = Collections_SynchronizedCollection_col_iter_Map.getNodeEquivalent(wr_col) ;
							if ((node_col != null) ) {
								ICollections_SynchronizedCollectionMonitor node_col_iter = node_col.getValue1() .getNodeEquivalent(wr_iter) ;
								if ((node_col_iter != null) ) {
									if (((node_col_iter.getDisable() > sourceLeaf.getTau() ) || ((node_col_iter.getTau() > 0) && (node_col_iter.getTau() < sourceLeaf.getTau() ) ) ) ) {
										definable = false;
									}
								}
							}
						}
						// D(X) defineTo:1--5 for <iter>
						if (definable) {
							// FindCode
							Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor> node_iter = Collections_SynchronizedCollection_iter_Map.getNodeEquivalent(wr_iter) ;
							if ((node_iter != null) ) {
								ICollections_SynchronizedCollectionMonitor itmdLeaf = node_iter.getValue2() ;
								if ((itmdLeaf != null) ) {
									if (((itmdLeaf.getDisable() > sourceLeaf.getTau() ) || ((itmdLeaf.getTau() > 0) && (itmdLeaf.getTau() < sourceLeaf.getTau() ) ) ) ) {
										definable = false;
									}
								}
							}
						}
						if (definable) {
							// D(X) defineTo:6
							Collections_SynchronizedCollectionMonitor created = (Collections_SynchronizedCollectionMonitor)sourceLeaf.clone() ;
							matchedEntry = created;
							matchedLastMap.putNode(wr_iter, created) ;
							// D(X) defineTo:7 for <col>
							{
								// InsertMonitor
								Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor> node_col = Collections_SynchronizedCollection_col_iter_Map.getNodeEquivalent(wr_col) ;
								if ((node_col == null) ) {
									node_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedCollectionMonitor>, Collections_SynchronizedCollectionMonitor_Set, Collections_SynchronizedCollectionMonitor>() ;
									Collections_SynchronizedCollection_col_iter_Map.putNode(wr_col, node_col) ;
									node_col.setValue1(new MapOfMonitor<ICollections_SynchronizedCollectionMonitor>(1) ) ;
									node_col.setValue2(new Collections_SynchronizedCollectionMonitor_Set() ) ;
								}
								Collections_SynchronizedCollectionMonitor_Set targetSet = node_col.getValue2() ;
								targetSet.add(created) ;
							}
							// D(X) defineTo:7 for <iter>
							{
								// InsertMonitor
								Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor> node_iter = Collections_SynchronizedCollection_iter_Map.getNodeEquivalent(wr_iter) ;
								if ((node_iter == null) ) {
									node_iter = new Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor>() ;
									Collections_SynchronizedCollection_iter_Map.putNode(wr_iter, node_iter) ;
									node_iter.setValue1(new Collections_SynchronizedCollectionMonitor_Set() ) ;
								}
								Collections_SynchronizedCollectionMonitor_Set targetSet = node_iter.getValue1() ;
								targetSet.add(created) ;
							}
						}
					}
				}
				// D(X) main:6
				if ((matchedEntry == null) ) {
					Collections_SynchronizedCollectionDisableHolder holder = new Collections_SynchronizedCollectionDisableHolder(-1) ;
					matchedLastMap.putNode(wr_iter, holder) ;
					matchedEntry = holder;
				}
				matchedEntry.setDisable(Collections_SynchronizedCollection_timestamp++) ;
			}
			// D(X) main:8--9
			if (matchedEntry instanceof Collections_SynchronizedCollectionMonitor) {
				Collections_SynchronizedCollectionMonitor monitor = (Collections_SynchronizedCollectionMonitor)matchedEntry;
				final Collections_SynchronizedCollectionMonitor monitorfinalMonitor = monitor;
				monitor.Prop_1_event_asyncCreateIter(col, iter);
				if(monitorfinalMonitor.Collections_SynchronizedCollectionMonitor_Prop_1_Category_match) {
					monitorfinalMonitor.Prop_1_handler_match();
				}

				if ((cachehit == false) ) {
					Collections_SynchronizedCollection_col_iter_Map_cachekey_col = col;
					Collections_SynchronizedCollection_col_iter_Map_cachekey_iter = iter;
					Collections_SynchronizedCollection_col_iter_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_SynchronizedCollection_accessIterEvent(Iterator iter) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Collections_SynchronizedCollection_activated) {
			CachedWeakReference wr_iter = null;
			Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor> matchedEntry = null;
			boolean cachehit = false;
			if ((iter == Collections_SynchronizedCollection_iter_Map_cachekey_iter) ) {
				matchedEntry = Collections_SynchronizedCollection_iter_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_iter = new CachedWeakReference(iter) ;
				{
					// FindOrCreateEntry
					Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor> node_iter = Collections_SynchronizedCollection_iter_Map.getNodeEquivalent(wr_iter) ;
					if ((node_iter == null) ) {
						node_iter = new Tuple2<Collections_SynchronizedCollectionMonitor_Set, ICollections_SynchronizedCollectionMonitor>() ;
						Collections_SynchronizedCollection_iter_Map.putNode(wr_iter, node_iter) ;
						node_iter.setValue1(new Collections_SynchronizedCollectionMonitor_Set() ) ;
					}
					matchedEntry = node_iter;
				}
			}
			// D(X) main:1
			ICollections_SynchronizedCollectionMonitor matchedLeaf = matchedEntry.getValue2() ;
			if ((matchedLeaf == null) ) {
				if ((wr_iter == null) ) {
					wr_iter = new CachedWeakReference(iter) ;
				}
				// D(X) main:6
				ICollections_SynchronizedCollectionMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
				if ((disableUpdatedLeaf == null) ) {
					Collections_SynchronizedCollectionDisableHolder holder = new Collections_SynchronizedCollectionDisableHolder(-1) ;
					matchedEntry.setValue2(holder) ;
					disableUpdatedLeaf = holder;
				}
				disableUpdatedLeaf.setDisable(Collections_SynchronizedCollection_timestamp++) ;
			}
			// D(X) main:8--9
			Collections_SynchronizedCollectionMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
			stateTransitionedSet.event_accessIter(iter);

			if ((cachehit == false) ) {
				Collections_SynchronizedCollection_iter_Map_cachekey_iter = iter;
				Collections_SynchronizedCollection_iter_Map_cachevalue = matchedEntry;
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_SynchronizedMap_syncEvent(Map syncMap) {
		Collections_SynchronizedMap_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_syncMap = null;
		Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> matchedEntry = null;
		boolean cachehit = false;
		if ((syncMap == Collections_SynchronizedMap_syncMap_Map_cachekey_syncMap) ) {
			matchedEntry = Collections_SynchronizedMap_syncMap_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_syncMap = new CachedWeakReference(syncMap) ;
			{
				// FindOrCreateEntry
				Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
				if ((node_syncMap == null) ) {
					node_syncMap = new Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
					Collections_SynchronizedMap_syncMap_col_iter_Map.putNode(wr_syncMap, node_syncMap) ;
					node_syncMap.setValue1(new MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ) ;
					node_syncMap.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
				}
				matchedEntry = node_syncMap;
			}
		}
		// D(X) main:1
		Collections_SynchronizedMapMonitor matchedLeaf = matchedEntry.getValue3() ;
		if ((matchedLeaf == null) ) {
			if ((wr_syncMap == null) ) {
				wr_syncMap = new CachedWeakReference(syncMap) ;
			}
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				Collections_SynchronizedMapMonitor created = new Collections_SynchronizedMapMonitor(Collections_SynchronizedMap_timestamp++, wr_syncMap) ;
				matchedEntry.setValue3(created) ;
				Collections_SynchronizedMapMonitor_Set enclosingSet = matchedEntry.getValue2() ;
				enclosingSet.add(created) ;
			}
			// D(X) main:6
			Collections_SynchronizedMapMonitor disableUpdatedLeaf = matchedEntry.getValue3() ;
			disableUpdatedLeaf.setDisable(Collections_SynchronizedMap_timestamp++) ;
		}
		// D(X) main:8--9
		Collections_SynchronizedMapMonitor_Set stateTransitionedSet = matchedEntry.getValue2() ;
		stateTransitionedSet.event_sync(syncMap);

		if ((cachehit == false) ) {
			Collections_SynchronizedMap_syncMap_Map_cachekey_syncMap = syncMap;
			Collections_SynchronizedMap_syncMap_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_SynchronizedMap_createSetEvent(Map syncMap, Collection col) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Collections_SynchronizedMap_activated) {
			CachedWeakReference wr_col = null;
			CachedWeakReference wr_syncMap = null;
			Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> matchedEntry = null;
			boolean cachehit = false;
			if (((col == Collections_SynchronizedMap_syncMap_col_Map_cachekey_col) && (syncMap == Collections_SynchronizedMap_syncMap_col_Map_cachekey_syncMap) ) ) {
				matchedEntry = Collections_SynchronizedMap_syncMap_col_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_syncMap = new CachedWeakReference(syncMap) ;
				wr_col = new CachedWeakReference(col) ;
				{
					// FindOrCreateEntry
					Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
					if ((node_syncMap == null) ) {
						node_syncMap = new Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
						Collections_SynchronizedMap_syncMap_col_iter_Map.putNode(wr_syncMap, node_syncMap) ;
						node_syncMap.setValue1(new MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ) ;
						node_syncMap.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
					}
					Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_syncMap_col = node_syncMap.getValue1() .getNodeEquivalent(wr_col) ;
					if ((node_syncMap_col == null) ) {
						node_syncMap_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
						node_syncMap.getValue1() .putNode(wr_col, node_syncMap_col) ;
						node_syncMap_col.setValue1(new MapOfMonitor<ICollections_SynchronizedMapMonitor>(2) ) ;
						node_syncMap_col.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
					}
					matchedEntry = node_syncMap_col;
				}
			}
			// D(X) main:1
			ICollections_SynchronizedMapMonitor matchedLeaf = matchedEntry.getValue3() ;
			if ((matchedLeaf == null) ) {
				if ((wr_syncMap == null) ) {
					wr_syncMap = new CachedWeakReference(syncMap) ;
				}
				if ((wr_col == null) ) {
					wr_col = new CachedWeakReference(col) ;
				}
				{
					// D(X) createNewMonitorStates:4 when Dom(theta'') = <syncMap>
					Collections_SynchronizedMapMonitor sourceLeaf = null;
					{
						// FindCode
						Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
						if ((node_syncMap != null) ) {
							Collections_SynchronizedMapMonitor itmdLeaf = node_syncMap.getValue3() ;
							sourceLeaf = itmdLeaf;
						}
					}
					if ((sourceLeaf != null) ) {
						boolean definable = true;
						// D(X) defineTo:1--5 for <syncMap, col>
						if (definable) {
							// FindCode
							Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
							if ((node_syncMap != null) ) {
								Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_syncMap_col = node_syncMap.getValue1() .getNodeEquivalent(wr_col) ;
								if ((node_syncMap_col != null) ) {
									ICollections_SynchronizedMapMonitor itmdLeaf = node_syncMap_col.getValue3() ;
									if ((itmdLeaf != null) ) {
										if (((itmdLeaf.getDisable() > sourceLeaf.getTau() ) || ((itmdLeaf.getTau() > 0) && (itmdLeaf.getTau() < sourceLeaf.getTau() ) ) ) ) {
											definable = false;
										}
									}
								}
							}
						}
						if (definable) {
							// D(X) defineTo:6
							Collections_SynchronizedMapMonitor created = (Collections_SynchronizedMapMonitor)sourceLeaf.clone() ;
							matchedEntry.setValue3(created) ;
							matchedLeaf = created;
							Collections_SynchronizedMapMonitor_Set enclosingSet = matchedEntry.getValue2() ;
							enclosingSet.add(created) ;
							// D(X) defineTo:7 for <syncMap>
							{
								// InsertMonitor
								Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
								if ((node_syncMap == null) ) {
									node_syncMap = new Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
									Collections_SynchronizedMap_syncMap_col_iter_Map.putNode(wr_syncMap, node_syncMap) ;
									node_syncMap.setValue1(new MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ) ;
									node_syncMap.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
								}
								Collections_SynchronizedMapMonitor_Set targetSet = node_syncMap.getValue2() ;
								targetSet.add(created) ;
							}
							// D(X) defineTo:7 for <col-syncMap, col>
							{
								// InsertMonitor
								Tuple2<Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_col = Collections_SynchronizedMap_col__To__syncMap_col_Map.getNodeEquivalent(wr_col) ;
								if ((node_col == null) ) {
									node_col = new Tuple2<Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
									Collections_SynchronizedMap_col__To__syncMap_col_Map.putNode(wr_col, node_col) ;
									node_col.setValue1(new Collections_SynchronizedMapMonitor_Set() ) ;
								}
								Collections_SynchronizedMapMonitor_Set targetSet = node_col.getValue1() ;
								targetSet.add(created) ;
							}
						}
					}
				}
				// D(X) main:6
				ICollections_SynchronizedMapMonitor disableUpdatedLeaf = matchedEntry.getValue3() ;
				if ((disableUpdatedLeaf == null) ) {
					Collections_SynchronizedMapDisableHolder holder = new Collections_SynchronizedMapDisableHolder(-1) ;
					matchedEntry.setValue3(holder) ;
					disableUpdatedLeaf = holder;
				}
				disableUpdatedLeaf.setDisable(Collections_SynchronizedMap_timestamp++) ;
			}
			// D(X) main:8--9
			Collections_SynchronizedMapMonitor_Set stateTransitionedSet = matchedEntry.getValue2() ;
			stateTransitionedSet.event_createSet(syncMap, col);

			if ((cachehit == false) ) {
				Collections_SynchronizedMap_syncMap_col_Map_cachekey_col = col;
				Collections_SynchronizedMap_syncMap_col_Map_cachekey_syncMap = syncMap;
				Collections_SynchronizedMap_syncMap_col_Map_cachevalue = matchedEntry;
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_SynchronizedMap_syncCreateIterEvent(Collection col, Iterator iter) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Collections_SynchronizedMap_activated) {
			CachedWeakReference wr_col = null;
			CachedWeakReference wr_iter = null;
			Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> matchedEntry = null;
			boolean cachehit = false;
			if (((col == Collections_SynchronizedMap_col_iter_Map_cachekey_col) && (iter == Collections_SynchronizedMap_col_iter_Map_cachekey_iter) ) ) {
				matchedEntry = Collections_SynchronizedMap_col_iter_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_col = new CachedWeakReference(col) ;
				wr_iter = new CachedWeakReference(iter) ;
				{
					// FindOrCreateEntry
					MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col = Collections_SynchronizedMap_col_iter_Map.getNodeEquivalent(wr_col) ;
					if ((node_col == null) ) {
						node_col = new MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ;
						Collections_SynchronizedMap_col_iter_Map.putNode(wr_col, node_col) ;
					}
					Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col_iter = node_col.getNodeEquivalent(wr_iter) ;
					if ((node_col_iter == null) ) {
						node_col_iter = new Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
						node_col.putNode(wr_iter, node_col_iter) ;
						node_col_iter.setValue1(new Collections_SynchronizedMapMonitor_Set() ) ;
					}
					matchedEntry = node_col_iter;
				}
			}
			// D(X) main:1
			ICollections_SynchronizedMapMonitor matchedLeaf = matchedEntry.getValue2() ;
			if ((matchedLeaf == null) ) {
				if ((wr_col == null) ) {
					wr_col = new CachedWeakReference(col) ;
				}
				if ((wr_iter == null) ) {
					wr_iter = new CachedWeakReference(iter) ;
				}
				{
					// D(X) createNewMonitorStates:4 when Dom(theta'') = <col>
					Collections_SynchronizedMapMonitor_Set sourceSet = null;
					{
						// FindCode
						Tuple2<Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_col = Collections_SynchronizedMap_col__To__syncMap_col_Map.getNodeEquivalent(wr_col) ;
						if ((node_col != null) ) {
							Collections_SynchronizedMapMonitor_Set itmdSet = node_col.getValue1() ;
							sourceSet = itmdSet;
						}
					}
					if ((sourceSet != null) ) {
						int numalive = 0;
						int setlen = sourceSet.getSize() ;
						for (int ielem = 0; (ielem < setlen) ;++ielem) {
							Collections_SynchronizedMapMonitor sourceMonitor = sourceSet.get(ielem) ;
							if ((!sourceMonitor.isTerminated() && (sourceMonitor.RVMRef_syncMap.get() != null) ) ) {
								sourceSet.set(numalive++, sourceMonitor) ;
								CachedWeakReference wr_syncMap = sourceMonitor.RVMRef_syncMap;
								MapOfMonitor<ICollections_SynchronizedMapMonitor> destLastMap = null;
								ICollections_SynchronizedMapMonitor destLeaf = null;
								{
									// FindOrCreate
									Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
									if ((node_syncMap == null) ) {
										node_syncMap = new Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
										Collections_SynchronizedMap_syncMap_col_iter_Map.putNode(wr_syncMap, node_syncMap) ;
										node_syncMap.setValue1(new MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ) ;
										node_syncMap.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
									}
									Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_syncMap_col = node_syncMap.getValue1() .getNodeEquivalent(wr_col) ;
									if ((node_syncMap_col == null) ) {
										node_syncMap_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
										node_syncMap.getValue1() .putNode(wr_col, node_syncMap_col) ;
										node_syncMap_col.setValue1(new MapOfMonitor<ICollections_SynchronizedMapMonitor>(2) ) ;
										node_syncMap_col.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
									}
									MapOfMonitor<ICollections_SynchronizedMapMonitor> itmdMap = node_syncMap_col.getValue1() ;
									destLastMap = itmdMap;
									ICollections_SynchronizedMapMonitor node_syncMap_col_iter = node_syncMap_col.getValue1() .getNodeEquivalent(wr_iter) ;
									destLeaf = node_syncMap_col_iter;
								}
								if (((destLeaf == null) || destLeaf instanceof Collections_SynchronizedMapDisableHolder) ) {
									boolean definable = true;
									// D(X) defineTo:1--5 for <col, iter>
									if (definable) {
										// FindCode
										MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col = Collections_SynchronizedMap_col_iter_Map.getNodeEquivalent(wr_col) ;
										if ((node_col != null) ) {
											Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col_iter = node_col.getNodeEquivalent(wr_iter) ;
											if ((node_col_iter != null) ) {
												ICollections_SynchronizedMapMonitor itmdLeaf = node_col_iter.getValue2() ;
												if ((itmdLeaf != null) ) {
													if (((itmdLeaf.getDisable() > sourceMonitor.getTau() ) || ((itmdLeaf.getTau() > 0) && (itmdLeaf.getTau() < sourceMonitor.getTau() ) ) ) ) {
														definable = false;
													}
												}
											}
										}
									}
									// D(X) defineTo:1--5 for <iter>
									if (definable) {
										// FindCode
										Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_iter = Collections_SynchronizedMap_iter_Map.getNodeEquivalent(wr_iter) ;
										if ((node_iter != null) ) {
											ICollections_SynchronizedMapMonitor itmdLeaf = node_iter.getValue2() ;
											if ((itmdLeaf != null) ) {
												if (((itmdLeaf.getDisable() > sourceMonitor.getTau() ) || ((itmdLeaf.getTau() > 0) && (itmdLeaf.getTau() < sourceMonitor.getTau() ) ) ) ) {
													definable = false;
												}
											}
										}
									}
									// D(X) defineTo:1--5 for <syncMap, col, iter>
									if (definable) {
										// FindCode
										Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
										if ((node_syncMap != null) ) {
											Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_syncMap_col = node_syncMap.getValue1() .getNodeEquivalent(wr_col) ;
											if ((node_syncMap_col != null) ) {
												ICollections_SynchronizedMapMonitor node_syncMap_col_iter = node_syncMap_col.getValue1() .getNodeEquivalent(wr_iter) ;
												if ((node_syncMap_col_iter != null) ) {
													if (((node_syncMap_col_iter.getDisable() > sourceMonitor.getTau() ) || ((node_syncMap_col_iter.getTau() > 0) && (node_syncMap_col_iter.getTau() < sourceMonitor.getTau() ) ) ) ) {
														definable = false;
													}
												}
											}
										}
									}
									if (definable) {
										// D(X) defineTo:6
										Collections_SynchronizedMapMonitor created = (Collections_SynchronizedMapMonitor)sourceMonitor.clone() ;
										destLastMap.putNode(wr_iter, created) ;
										// D(X) defineTo:7 for <col, iter>
										{
											// InsertMonitor
											MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col = Collections_SynchronizedMap_col_iter_Map.getNodeEquivalent(wr_col) ;
											if ((node_col == null) ) {
												node_col = new MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ;
												Collections_SynchronizedMap_col_iter_Map.putNode(wr_col, node_col) ;
											}
											Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col_iter = node_col.getNodeEquivalent(wr_iter) ;
											if ((node_col_iter == null) ) {
												node_col_iter = new Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
												node_col.putNode(wr_iter, node_col_iter) ;
												node_col_iter.setValue1(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Collections_SynchronizedMapMonitor_Set targetSet = node_col_iter.getValue1() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <iter>
										{
											// InsertMonitor
											Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_iter = Collections_SynchronizedMap_iter_Map.getNodeEquivalent(wr_iter) ;
											if ((node_iter == null) ) {
												node_iter = new Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
												Collections_SynchronizedMap_iter_Map.putNode(wr_iter, node_iter) ;
												node_iter.setValue1(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Collections_SynchronizedMapMonitor_Set targetSet = node_iter.getValue1() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <syncMap>
										{
											// InsertMonitor
											Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
											if ((node_syncMap == null) ) {
												node_syncMap = new Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
												Collections_SynchronizedMap_syncMap_col_iter_Map.putNode(wr_syncMap, node_syncMap) ;
												node_syncMap.setValue1(new MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ) ;
												node_syncMap.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Collections_SynchronizedMapMonitor_Set targetSet = node_syncMap.getValue2() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <syncMap, col>
										{
											// InsertMonitor
											Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
											if ((node_syncMap == null) ) {
												node_syncMap = new Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
												Collections_SynchronizedMap_syncMap_col_iter_Map.putNode(wr_syncMap, node_syncMap) ;
												node_syncMap.setValue1(new MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ) ;
												node_syncMap.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_syncMap_col = node_syncMap.getValue1() .getNodeEquivalent(wr_col) ;
											if ((node_syncMap_col == null) ) {
												node_syncMap_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
												node_syncMap.getValue1() .putNode(wr_col, node_syncMap_col) ;
												node_syncMap_col.setValue1(new MapOfMonitor<ICollections_SynchronizedMapMonitor>(2) ) ;
												node_syncMap_col.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Collections_SynchronizedMapMonitor_Set targetSet = node_syncMap_col.getValue2() ;
											targetSet.add(created) ;
										}
									}
								}
							}
						}
						sourceSet.eraseRange(numalive) ;
					}
				}
				// D(X) main:6
				ICollections_SynchronizedMapMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
				if ((disableUpdatedLeaf == null) ) {
					Collections_SynchronizedMapDisableHolder holder = new Collections_SynchronizedMapDisableHolder(-1) ;
					matchedEntry.setValue2(holder) ;
					disableUpdatedLeaf = holder;
				}
				disableUpdatedLeaf.setDisable(Collections_SynchronizedMap_timestamp++) ;
			}
			// D(X) main:8--9
			Collections_SynchronizedMapMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
			stateTransitionedSet.event_syncCreateIter(col, iter);

			if ((cachehit == false) ) {
				Collections_SynchronizedMap_col_iter_Map_cachekey_col = col;
				Collections_SynchronizedMap_col_iter_Map_cachekey_iter = iter;
				Collections_SynchronizedMap_col_iter_Map_cachevalue = matchedEntry;
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_SynchronizedMap_asyncCreateIterEvent(Collection col, Iterator iter) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Collections_SynchronizedMap_activated) {
			CachedWeakReference wr_col = null;
			CachedWeakReference wr_iter = null;
			Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> matchedEntry = null;
			boolean cachehit = false;
			if (((col == Collections_SynchronizedMap_col_iter_Map_cachekey_col) && (iter == Collections_SynchronizedMap_col_iter_Map_cachekey_iter) ) ) {
				matchedEntry = Collections_SynchronizedMap_col_iter_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_col = new CachedWeakReference(col) ;
				wr_iter = new CachedWeakReference(iter) ;
				{
					// FindOrCreateEntry
					MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col = Collections_SynchronizedMap_col_iter_Map.getNodeEquivalent(wr_col) ;
					if ((node_col == null) ) {
						node_col = new MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ;
						Collections_SynchronizedMap_col_iter_Map.putNode(wr_col, node_col) ;
					}
					Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col_iter = node_col.getNodeEquivalent(wr_iter) ;
					if ((node_col_iter == null) ) {
						node_col_iter = new Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
						node_col.putNode(wr_iter, node_col_iter) ;
						node_col_iter.setValue1(new Collections_SynchronizedMapMonitor_Set() ) ;
					}
					matchedEntry = node_col_iter;
				}
			}
			// D(X) main:1
			ICollections_SynchronizedMapMonitor matchedLeaf = matchedEntry.getValue2() ;
			if ((matchedLeaf == null) ) {
				if ((wr_col == null) ) {
					wr_col = new CachedWeakReference(col) ;
				}
				if ((wr_iter == null) ) {
					wr_iter = new CachedWeakReference(iter) ;
				}
				{
					// D(X) createNewMonitorStates:4 when Dom(theta'') = <col>
					Collections_SynchronizedMapMonitor_Set sourceSet = null;
					{
						// FindCode
						Tuple2<Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_col = Collections_SynchronizedMap_col__To__syncMap_col_Map.getNodeEquivalent(wr_col) ;
						if ((node_col != null) ) {
							Collections_SynchronizedMapMonitor_Set itmdSet = node_col.getValue1() ;
							sourceSet = itmdSet;
						}
					}
					if ((sourceSet != null) ) {
						int numalive = 0;
						int setlen = sourceSet.getSize() ;
						for (int ielem = 0; (ielem < setlen) ;++ielem) {
							Collections_SynchronizedMapMonitor sourceMonitor = sourceSet.get(ielem) ;
							if ((!sourceMonitor.isTerminated() && (sourceMonitor.RVMRef_syncMap.get() != null) ) ) {
								sourceSet.set(numalive++, sourceMonitor) ;
								CachedWeakReference wr_syncMap = sourceMonitor.RVMRef_syncMap;
								MapOfMonitor<ICollections_SynchronizedMapMonitor> destLastMap = null;
								ICollections_SynchronizedMapMonitor destLeaf = null;
								{
									// FindOrCreate
									Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
									if ((node_syncMap == null) ) {
										node_syncMap = new Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
										Collections_SynchronizedMap_syncMap_col_iter_Map.putNode(wr_syncMap, node_syncMap) ;
										node_syncMap.setValue1(new MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ) ;
										node_syncMap.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
									}
									Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_syncMap_col = node_syncMap.getValue1() .getNodeEquivalent(wr_col) ;
									if ((node_syncMap_col == null) ) {
										node_syncMap_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
										node_syncMap.getValue1() .putNode(wr_col, node_syncMap_col) ;
										node_syncMap_col.setValue1(new MapOfMonitor<ICollections_SynchronizedMapMonitor>(2) ) ;
										node_syncMap_col.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
									}
									MapOfMonitor<ICollections_SynchronizedMapMonitor> itmdMap = node_syncMap_col.getValue1() ;
									destLastMap = itmdMap;
									ICollections_SynchronizedMapMonitor node_syncMap_col_iter = node_syncMap_col.getValue1() .getNodeEquivalent(wr_iter) ;
									destLeaf = node_syncMap_col_iter;
								}
								if (((destLeaf == null) || destLeaf instanceof Collections_SynchronizedMapDisableHolder) ) {
									boolean definable = true;
									// D(X) defineTo:1--5 for <col, iter>
									if (definable) {
										// FindCode
										MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col = Collections_SynchronizedMap_col_iter_Map.getNodeEquivalent(wr_col) ;
										if ((node_col != null) ) {
											Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col_iter = node_col.getNodeEquivalent(wr_iter) ;
											if ((node_col_iter != null) ) {
												ICollections_SynchronizedMapMonitor itmdLeaf = node_col_iter.getValue2() ;
												if ((itmdLeaf != null) ) {
													if (((itmdLeaf.getDisable() > sourceMonitor.getTau() ) || ((itmdLeaf.getTau() > 0) && (itmdLeaf.getTau() < sourceMonitor.getTau() ) ) ) ) {
														definable = false;
													}
												}
											}
										}
									}
									// D(X) defineTo:1--5 for <iter>
									if (definable) {
										// FindCode
										Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_iter = Collections_SynchronizedMap_iter_Map.getNodeEquivalent(wr_iter) ;
										if ((node_iter != null) ) {
											ICollections_SynchronizedMapMonitor itmdLeaf = node_iter.getValue2() ;
											if ((itmdLeaf != null) ) {
												if (((itmdLeaf.getDisable() > sourceMonitor.getTau() ) || ((itmdLeaf.getTau() > 0) && (itmdLeaf.getTau() < sourceMonitor.getTau() ) ) ) ) {
													definable = false;
												}
											}
										}
									}
									// D(X) defineTo:1--5 for <syncMap, col, iter>
									if (definable) {
										// FindCode
										Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
										if ((node_syncMap != null) ) {
											Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_syncMap_col = node_syncMap.getValue1() .getNodeEquivalent(wr_col) ;
											if ((node_syncMap_col != null) ) {
												ICollections_SynchronizedMapMonitor node_syncMap_col_iter = node_syncMap_col.getValue1() .getNodeEquivalent(wr_iter) ;
												if ((node_syncMap_col_iter != null) ) {
													if (((node_syncMap_col_iter.getDisable() > sourceMonitor.getTau() ) || ((node_syncMap_col_iter.getTau() > 0) && (node_syncMap_col_iter.getTau() < sourceMonitor.getTau() ) ) ) ) {
														definable = false;
													}
												}
											}
										}
									}
									if (definable) {
										// D(X) defineTo:6
										Collections_SynchronizedMapMonitor created = (Collections_SynchronizedMapMonitor)sourceMonitor.clone() ;
										destLastMap.putNode(wr_iter, created) ;
										// D(X) defineTo:7 for <col, iter>
										{
											// InsertMonitor
											MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col = Collections_SynchronizedMap_col_iter_Map.getNodeEquivalent(wr_col) ;
											if ((node_col == null) ) {
												node_col = new MapOfSetMonitor<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ;
												Collections_SynchronizedMap_col_iter_Map.putNode(wr_col, node_col) ;
											}
											Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_col_iter = node_col.getNodeEquivalent(wr_iter) ;
											if ((node_col_iter == null) ) {
												node_col_iter = new Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
												node_col.putNode(wr_iter, node_col_iter) ;
												node_col_iter.setValue1(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Collections_SynchronizedMapMonitor_Set targetSet = node_col_iter.getValue1() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <iter>
										{
											// InsertMonitor
											Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_iter = Collections_SynchronizedMap_iter_Map.getNodeEquivalent(wr_iter) ;
											if ((node_iter == null) ) {
												node_iter = new Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
												Collections_SynchronizedMap_iter_Map.putNode(wr_iter, node_iter) ;
												node_iter.setValue1(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Collections_SynchronizedMapMonitor_Set targetSet = node_iter.getValue1() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <syncMap>
										{
											// InsertMonitor
											Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
											if ((node_syncMap == null) ) {
												node_syncMap = new Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
												Collections_SynchronizedMap_syncMap_col_iter_Map.putNode(wr_syncMap, node_syncMap) ;
												node_syncMap.setValue1(new MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ) ;
												node_syncMap.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Collections_SynchronizedMapMonitor_Set targetSet = node_syncMap.getValue2() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <syncMap, col>
										{
											// InsertMonitor
											Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor> node_syncMap = Collections_SynchronizedMap_syncMap_col_iter_Map.getNodeEquivalent(wr_syncMap) ;
											if ((node_syncMap == null) ) {
												node_syncMap = new Tuple3<MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, Collections_SynchronizedMapMonitor>() ;
												Collections_SynchronizedMap_syncMap_col_iter_Map.putNode(wr_syncMap, node_syncMap) ;
												node_syncMap.setValue1(new MapOfAll<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>(1) ) ;
												node_syncMap.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_syncMap_col = node_syncMap.getValue1() .getNodeEquivalent(wr_col) ;
											if ((node_syncMap_col == null) ) {
												node_syncMap_col = new Tuple3<MapOfMonitor<ICollections_SynchronizedMapMonitor>, Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
												node_syncMap.getValue1() .putNode(wr_col, node_syncMap_col) ;
												node_syncMap_col.setValue1(new MapOfMonitor<ICollections_SynchronizedMapMonitor>(2) ) ;
												node_syncMap_col.setValue2(new Collections_SynchronizedMapMonitor_Set() ) ;
											}
											Collections_SynchronizedMapMonitor_Set targetSet = node_syncMap_col.getValue2() ;
											targetSet.add(created) ;
										}
									}
								}
							}
						}
						sourceSet.eraseRange(numalive) ;
					}
				}
				// D(X) main:6
				ICollections_SynchronizedMapMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
				if ((disableUpdatedLeaf == null) ) {
					Collections_SynchronizedMapDisableHolder holder = new Collections_SynchronizedMapDisableHolder(-1) ;
					matchedEntry.setValue2(holder) ;
					disableUpdatedLeaf = holder;
				}
				disableUpdatedLeaf.setDisable(Collections_SynchronizedMap_timestamp++) ;
			}
			// D(X) main:8--9
			Collections_SynchronizedMapMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
			stateTransitionedSet.event_asyncCreateIter(col, iter);

			if ((cachehit == false) ) {
				Collections_SynchronizedMap_col_iter_Map_cachekey_col = col;
				Collections_SynchronizedMap_col_iter_Map_cachekey_iter = iter;
				Collections_SynchronizedMap_col_iter_Map_cachevalue = matchedEntry;
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_SynchronizedMap_accessIterEvent(Iterator iter) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Collections_SynchronizedMap_activated) {
			CachedWeakReference wr_iter = null;
			Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> matchedEntry = null;
			boolean cachehit = false;
			if ((iter == Collections_SynchronizedMap_iter_Map_cachekey_iter) ) {
				matchedEntry = Collections_SynchronizedMap_iter_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_iter = new CachedWeakReference(iter) ;
				{
					// FindOrCreateEntry
					Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor> node_iter = Collections_SynchronizedMap_iter_Map.getNodeEquivalent(wr_iter) ;
					if ((node_iter == null) ) {
						node_iter = new Tuple2<Collections_SynchronizedMapMonitor_Set, ICollections_SynchronizedMapMonitor>() ;
						Collections_SynchronizedMap_iter_Map.putNode(wr_iter, node_iter) ;
						node_iter.setValue1(new Collections_SynchronizedMapMonitor_Set() ) ;
					}
					matchedEntry = node_iter;
				}
			}
			// D(X) main:1
			ICollections_SynchronizedMapMonitor matchedLeaf = matchedEntry.getValue2() ;
			if ((matchedLeaf == null) ) {
				if ((wr_iter == null) ) {
					wr_iter = new CachedWeakReference(iter) ;
				}
				// D(X) main:6
				ICollections_SynchronizedMapMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
				if ((disableUpdatedLeaf == null) ) {
					Collections_SynchronizedMapDisableHolder holder = new Collections_SynchronizedMapDisableHolder(-1) ;
					matchedEntry.setValue2(holder) ;
					disableUpdatedLeaf = holder;
				}
				disableUpdatedLeaf.setDisable(Collections_SynchronizedMap_timestamp++) ;
			}
			// D(X) main:8--9
			Collections_SynchronizedMapMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
			stateTransitionedSet.event_accessIter(iter);

			if ((cachehit == false) ) {
				Collections_SynchronizedMap_iter_Map_cachekey_iter = iter;
				Collections_SynchronizedMap_iter_Map_cachevalue = matchedEntry;
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collections_UnnecessaryNewSetFromMap_unnecessaryEvent() {
		Collections_UnnecessaryNewSetFromMap_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Collections_UnnecessaryNewSetFromMapMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Collections_UnnecessaryNewSetFromMap__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Collections_UnnecessaryNewSetFromMapMonitor created = new Collections_UnnecessaryNewSetFromMapMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_unnecessary();

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collection_UnsynchronizedAddAll_enterEvent(Collection t, Collection s) {
		Collection_UnsynchronizedAddAll_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_s = null;
		CachedWeakReference wr_t = null;
		MapOfMonitor<Collection_UnsynchronizedAddAllMonitor> matchedLastMap = null;
		Collection_UnsynchronizedAddAllMonitor matchedEntry = null;
		boolean cachehit = false;
		if (((s == Collection_UnsynchronizedAddAll_t_s_Map_cachekey_s) && (t == Collection_UnsynchronizedAddAll_t_s_Map_cachekey_t) ) ) {
			matchedEntry = Collection_UnsynchronizedAddAll_t_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_t = new CachedWeakReference(t) ;
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<Collection_UnsynchronizedAddAllMonitor> node_t = Collection_UnsynchronizedAddAll_t_s_Map.getNodeEquivalent(wr_t) ;
				if ((node_t == null) ) {
					node_t = new MapOfMonitor<Collection_UnsynchronizedAddAllMonitor>(1) ;
					Collection_UnsynchronizedAddAll_t_s_Map.putNode(wr_t, node_t) ;
				}
				matchedLastMap = node_t;
				Collection_UnsynchronizedAddAllMonitor node_t_s = node_t.getNodeEquivalent(wr_s) ;
				matchedEntry = node_t_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_t == null) ) {
				wr_t = new CachedWeakReference(t) ;
			}
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			Collection_UnsynchronizedAddAllMonitor created = new Collection_UnsynchronizedAddAllMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
			// D(X) defineNew:5 for <s>
			{
				// InsertMonitor
				Collection_UnsynchronizedAddAllMonitor_Set node_s = Collection_UnsynchronizedAddAll_s_Map.getNodeEquivalent(wr_s) ;
				if ((node_s == null) ) {
					node_s = new Collection_UnsynchronizedAddAllMonitor_Set() ;
					Collection_UnsynchronizedAddAll_s_Map.putNode(wr_s, node_s) ;
				}
				node_s.add(created) ;
			}
		}
		// D(X) main:8--9
		final Collection_UnsynchronizedAddAllMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_enter(t, s);
		if(matchedEntryfinalMonitor.Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		if ((cachehit == false) ) {
			Collection_UnsynchronizedAddAll_t_s_Map_cachekey_s = s;
			Collection_UnsynchronizedAddAll_t_s_Map_cachekey_t = t;
			Collection_UnsynchronizedAddAll_t_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collection_UnsynchronizedAddAll_modifyEvent(Collection s) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Collection_UnsynchronizedAddAll_activated) {
			Collection_UnsynchronizedAddAllMonitor_Set matchedEntry = null;
			boolean cachehit = false;
			if ((s == Collection_UnsynchronizedAddAll_s_Map_cachekey_s) ) {
				matchedEntry = Collection_UnsynchronizedAddAll_s_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				Collection_UnsynchronizedAddAllMonitor_Set node_s = Collection_UnsynchronizedAddAll_s_Map.getNodeWithStrongRef(s) ;
				if ((node_s != null) ) {
					matchedEntry = node_s;
				}
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				matchedEntry.event_modify(s);

				if ((cachehit == false) ) {
					Collection_UnsynchronizedAddAll_s_Map_cachekey_s = s;
					Collection_UnsynchronizedAddAll_s_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Collection_UnsynchronizedAddAll_leaveEvent(Collection t, Collection s) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Collection_UnsynchronizedAddAll_activated) {
			Collection_UnsynchronizedAddAllMonitor matchedEntry = null;
			boolean cachehit = false;
			if (((s == Collection_UnsynchronizedAddAll_t_s_Map_cachekey_s) && (t == Collection_UnsynchronizedAddAll_t_s_Map_cachekey_t) ) ) {
				matchedEntry = Collection_UnsynchronizedAddAll_t_s_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				MapOfMonitor<Collection_UnsynchronizedAddAllMonitor> node_t = Collection_UnsynchronizedAddAll_t_s_Map.getNodeWithStrongRef(t) ;
				if ((node_t != null) ) {
					Collection_UnsynchronizedAddAllMonitor node_t_s = node_t.getNodeWithStrongRef(s) ;
					matchedEntry = node_t_s;
				}
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final Collection_UnsynchronizedAddAllMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_leave(t, s);
				if(matchedEntryfinalMonitor.Collection_UnsynchronizedAddAllMonitor_Prop_1_Category_fail) {
					matchedEntryfinalMonitor.Prop_1_handler_fail();
				}

				if ((cachehit == false) ) {
					Collection_UnsynchronizedAddAll_t_s_Map_cachekey_s = s;
					Collection_UnsynchronizedAddAll_t_s_Map_cachekey_t = t;
					Collection_UnsynchronizedAddAll_t_s_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Comparable_CompareToNullException_badexceptionEvent(Object o, Exception e) {
		Comparable_CompareToNullException_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Comparable_CompareToNullExceptionMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Comparable_CompareToNullException__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Comparable_CompareToNullExceptionMonitor created = new Comparable_CompareToNullExceptionMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_badexception(o, e);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Comparable_CompareToNullException_badcompareEvent(Object o, int i) {
		Comparable_CompareToNullException_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Comparable_CompareToNullExceptionMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Comparable_CompareToNullException__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Comparable_CompareToNullExceptionMonitor created = new Comparable_CompareToNullExceptionMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_badcompare(o, i);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Comparable_CompareToNull_nullcompareEvent(Object o) {
		Comparable_CompareToNull_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Comparable_CompareToNullMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Comparable_CompareToNull__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Comparable_CompareToNullMonitor created = new Comparable_CompareToNullMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_nullcompare(o);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void InputStream_ManipulateAfterClose_manipulateEvent(InputStream i) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (InputStream_ManipulateAfterClose_activated) {
			InputStream_ManipulateAfterCloseMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((i == InputStream_ManipulateAfterClose_i_Map_cachekey_i) ) {
				matchedEntry = InputStream_ManipulateAfterClose_i_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				InputStream_ManipulateAfterCloseMonitor node_i = InputStream_ManipulateAfterClose_i_Map.getNodeWithStrongRef(i) ;
				matchedEntry = node_i;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final InputStream_ManipulateAfterCloseMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_manipulate(i);
				if(matchedEntryfinalMonitor.InputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					matchedEntryfinalMonitor.Prop_1_handler_match();
				}

				if ((cachehit == false) ) {
					InputStream_ManipulateAfterClose_i_Map_cachekey_i = i;
					InputStream_ManipulateAfterClose_i_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void InputStream_ManipulateAfterClose_closeEvent(InputStream i) {
		InputStream_ManipulateAfterClose_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_i = null;
		MapOfMonitor<InputStream_ManipulateAfterCloseMonitor> matchedLastMap = null;
		InputStream_ManipulateAfterCloseMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((i == InputStream_ManipulateAfterClose_i_Map_cachekey_i) ) {
			matchedEntry = InputStream_ManipulateAfterClose_i_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_i = new CachedWeakReference(i) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<InputStream_ManipulateAfterCloseMonitor> itmdMap = InputStream_ManipulateAfterClose_i_Map;
				matchedLastMap = itmdMap;
				InputStream_ManipulateAfterCloseMonitor node_i = InputStream_ManipulateAfterClose_i_Map.getNodeEquivalent(wr_i) ;
				matchedEntry = node_i;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_i == null) ) {
				wr_i = new CachedWeakReference(i) ;
			}
			// D(X) main:4
			InputStream_ManipulateAfterCloseMonitor created = new InputStream_ManipulateAfterCloseMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_i, created) ;
		}
		// D(X) main:8--9
		final InputStream_ManipulateAfterCloseMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_close(i);
		if(matchedEntryfinalMonitor.InputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			InputStream_ManipulateAfterClose_i_Map_cachekey_i = i;
			InputStream_ManipulateAfterClose_i_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ListIterator_Set_createEvent(ListIterator i) {
		ListIterator_Set_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_i = null;
		MapOfMonitor<ListIterator_SetMonitor> matchedLastMap = null;
		ListIterator_SetMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((i == ListIterator_Set_i_Map_cachekey_i) ) {
			matchedEntry = ListIterator_Set_i_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_i = new CachedWeakReference(i) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<ListIterator_SetMonitor> itmdMap = ListIterator_Set_i_Map;
				matchedLastMap = itmdMap;
				ListIterator_SetMonitor node_i = ListIterator_Set_i_Map.getNodeEquivalent(wr_i) ;
				matchedEntry = node_i;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_i == null) ) {
				wr_i = new CachedWeakReference(i) ;
			}
			// D(X) main:4
			ListIterator_SetMonitor created = new ListIterator_SetMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_i, created) ;
		}
		// D(X) main:8--9
		final ListIterator_SetMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_create(i);
		if(matchedEntryfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		if ((cachehit == false) ) {
			ListIterator_Set_i_Map_cachekey_i = i;
			ListIterator_Set_i_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ListIterator_Set_removeEvent(ListIterator i) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (ListIterator_Set_activated) {
			ListIterator_SetMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((i == ListIterator_Set_i_Map_cachekey_i) ) {
				matchedEntry = ListIterator_Set_i_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				ListIterator_SetMonitor node_i = ListIterator_Set_i_Map.getNodeWithStrongRef(i) ;
				matchedEntry = node_i;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final ListIterator_SetMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_remove(i);
				if(matchedEntryfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					matchedEntryfinalMonitor.Prop_1_handler_fail();
				}

				if ((cachehit == false) ) {
					ListIterator_Set_i_Map_cachekey_i = i;
					ListIterator_Set_i_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ListIterator_Set_addEvent(ListIterator i) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (ListIterator_Set_activated) {
			ListIterator_SetMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((i == ListIterator_Set_i_Map_cachekey_i) ) {
				matchedEntry = ListIterator_Set_i_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				ListIterator_SetMonitor node_i = ListIterator_Set_i_Map.getNodeWithStrongRef(i) ;
				matchedEntry = node_i;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final ListIterator_SetMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_add(i);
				if(matchedEntryfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					matchedEntryfinalMonitor.Prop_1_handler_fail();
				}

				if ((cachehit == false) ) {
					ListIterator_Set_i_Map_cachekey_i = i;
					ListIterator_Set_i_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ListIterator_Set_nextEvent(ListIterator i) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (ListIterator_Set_activated) {
			ListIterator_SetMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((i == ListIterator_Set_i_Map_cachekey_i) ) {
				matchedEntry = ListIterator_Set_i_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				ListIterator_SetMonitor node_i = ListIterator_Set_i_Map.getNodeWithStrongRef(i) ;
				matchedEntry = node_i;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final ListIterator_SetMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_next(i);
				if(matchedEntryfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					matchedEntryfinalMonitor.Prop_1_handler_fail();
				}

				if ((cachehit == false) ) {
					ListIterator_Set_i_Map_cachekey_i = i;
					ListIterator_Set_i_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ListIterator_Set_previousEvent(ListIterator i) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (ListIterator_Set_activated) {
			ListIterator_SetMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((i == ListIterator_Set_i_Map_cachekey_i) ) {
				matchedEntry = ListIterator_Set_i_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				ListIterator_SetMonitor node_i = ListIterator_Set_i_Map.getNodeWithStrongRef(i) ;
				matchedEntry = node_i;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final ListIterator_SetMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_previous(i);
				if(matchedEntryfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					matchedEntryfinalMonitor.Prop_1_handler_fail();
				}

				if ((cachehit == false) ) {
					ListIterator_Set_i_Map_cachekey_i = i;
					ListIterator_Set_i_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ListIterator_Set_setEvent(ListIterator i) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (ListIterator_Set_activated) {
			ListIterator_SetMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((i == ListIterator_Set_i_Map_cachekey_i) ) {
				matchedEntry = ListIterator_Set_i_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				ListIterator_SetMonitor node_i = ListIterator_Set_i_Map.getNodeWithStrongRef(i) ;
				matchedEntry = node_i;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final ListIterator_SetMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_set(i);
				if(matchedEntryfinalMonitor.ListIterator_SetMonitor_Prop_1_Category_fail) {
					matchedEntryfinalMonitor.Prop_1_handler_fail();
				}

				if ((cachehit == false) ) {
					ListIterator_Set_i_Map_cachekey_i = i;
					ListIterator_Set_i_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Long_BadParsingArgs_bad_argEvent(String s, int radix) {
		Long_BadParsingArgs_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Long_BadParsingArgsMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Long_BadParsingArgs__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Long_BadParsingArgsMonitor created = new Long_BadParsingArgsMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_bad_arg(s, radix);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Long_BadParsingArgs_bad_arg2Event(String s) {
		Long_BadParsingArgs_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Long_BadParsingArgsMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Long_BadParsingArgs__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Long_BadParsingArgsMonitor created = new Long_BadParsingArgsMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_bad_arg2(s);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Map_UnsafeIterator_getsetEvent(Map m, Collection c) {
		Map_UnsafeIterator_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_c = null;
		CachedWeakReference wr_m = null;
		Tuple3<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> matchedEntry = null;
		boolean cachehit = false;
		if (((c == Map_UnsafeIterator_m_c_Map_cachekey_c) && (m == Map_UnsafeIterator_m_c_Map_cachekey_m) ) ) {
			matchedEntry = Map_UnsafeIterator_m_c_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_m = new CachedWeakReference(m) ;
			wr_c = new CachedWeakReference(c) ;
			{
				// FindOrCreateEntry
				Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_m = Map_UnsafeIterator_m_c_i_Map.getNodeEquivalent(wr_m) ;
				if ((node_m == null) ) {
					node_m = new Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
					Map_UnsafeIterator_m_c_i_Map.putNode(wr_m, node_m) ;
					node_m.setValue1(new MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>(1) ) ;
					node_m.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
				}
				Tuple3<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> node_m_c = node_m.getValue1() .getNodeEquivalent(wr_c) ;
				if ((node_m_c == null) ) {
					node_m_c = new Tuple3<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>() ;
					node_m.getValue1() .putNode(wr_c, node_m_c) ;
					node_m_c.setValue1(new MapOfMonitor<IMap_UnsafeIteratorMonitor>(2) ) ;
					node_m_c.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
				}
				matchedEntry = node_m_c;
			}
		}
		// D(X) main:1
		Map_UnsafeIteratorMonitor matchedLeaf = matchedEntry.getValue3() ;
		if ((matchedLeaf == null) ) {
			if ((wr_m == null) ) {
				wr_m = new CachedWeakReference(m) ;
			}
			if ((wr_c == null) ) {
				wr_c = new CachedWeakReference(c) ;
			}
			if ((matchedLeaf == null) ) {
				// D(X) main:4
				Map_UnsafeIteratorMonitor created = new Map_UnsafeIteratorMonitor(Map_UnsafeIterator_timestamp++, wr_m) ;
				matchedEntry.setValue3(created) ;
				Map_UnsafeIteratorMonitor_Set enclosingSet = matchedEntry.getValue2() ;
				enclosingSet.add(created) ;
				// D(X) defineNew:5 for <c>
				{
					// InsertMonitor
					Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_c = Map_UnsafeIterator_c_i_Map.getNodeEquivalent(wr_c) ;
					if ((node_c == null) ) {
						node_c = new Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
						Map_UnsafeIterator_c_i_Map.putNode(wr_c, node_c) ;
						node_c.setValue1(new MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>(1) ) ;
						node_c.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
					}
					Map_UnsafeIteratorMonitor_Set targetSet = node_c.getValue2() ;
					targetSet.add(created) ;
				}
				// D(X) defineNew:5 for <m>
				{
					// InsertMonitor
					Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_m = Map_UnsafeIterator_m_c_i_Map.getNodeEquivalent(wr_m) ;
					if ((node_m == null) ) {
						node_m = new Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
						Map_UnsafeIterator_m_c_i_Map.putNode(wr_m, node_m) ;
						node_m.setValue1(new MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>(1) ) ;
						node_m.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
					}
					Map_UnsafeIteratorMonitor_Set targetSet = node_m.getValue2() ;
					targetSet.add(created) ;
				}
				// D(X) defineNew:5 for <c-m, c>
				{
					// InsertMonitor
					Tuple2<Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> node_c = Map_UnsafeIterator_c__To__m_c_Map.getNodeEquivalent(wr_c) ;
					if ((node_c == null) ) {
						node_c = new Tuple2<Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>() ;
						Map_UnsafeIterator_c__To__m_c_Map.putNode(wr_c, node_c) ;
						node_c.setValue1(new Map_UnsafeIteratorMonitor_Set() ) ;
					}
					Map_UnsafeIteratorMonitor_Set targetSet = node_c.getValue1() ;
					targetSet.add(created) ;
				}
			}
			// D(X) main:6
			Map_UnsafeIteratorMonitor disableUpdatedLeaf = matchedEntry.getValue3() ;
			disableUpdatedLeaf.setDisable(Map_UnsafeIterator_timestamp++) ;
		}
		// D(X) main:8--9
		Map_UnsafeIteratorMonitor_Set stateTransitionedSet = matchedEntry.getValue2() ;
		stateTransitionedSet.event_getset(m, c);

		if ((cachehit == false) ) {
			Map_UnsafeIterator_m_c_Map_cachekey_c = c;
			Map_UnsafeIterator_m_c_Map_cachekey_m = m;
			Map_UnsafeIterator_m_c_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Map_UnsafeIterator_getiterEvent(Collection c, Iterator i) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Map_UnsafeIterator_activated) {
			CachedWeakReference wr_c = null;
			CachedWeakReference wr_i = null;
			Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> matchedEntry = null;
			boolean cachehit = false;
			if (((c == Map_UnsafeIterator_c_i_Map_cachekey_c) && (i == Map_UnsafeIterator_c_i_Map_cachekey_i) ) ) {
				matchedEntry = Map_UnsafeIterator_c_i_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_c = new CachedWeakReference(c) ;
				wr_i = new CachedWeakReference(i) ;
				{
					// FindOrCreateEntry
					Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_c = Map_UnsafeIterator_c_i_Map.getNodeEquivalent(wr_c) ;
					if ((node_c == null) ) {
						node_c = new Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
						Map_UnsafeIterator_c_i_Map.putNode(wr_c, node_c) ;
						node_c.setValue1(new MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>(1) ) ;
						node_c.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
					}
					Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_c_i = node_c.getValue1() .getNodeEquivalent(wr_i) ;
					if ((node_c_i == null) ) {
						node_c_i = new Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
						node_c.getValue1() .putNode(wr_i, node_c_i) ;
						node_c_i.setValue1(new Map_UnsafeIteratorMonitor_Set() ) ;
					}
					matchedEntry = node_c_i;
				}
			}
			// D(X) main:1
			IMap_UnsafeIteratorMonitor matchedLeaf = matchedEntry.getValue2() ;
			if ((matchedLeaf == null) ) {
				if ((wr_c == null) ) {
					wr_c = new CachedWeakReference(c) ;
				}
				if ((wr_i == null) ) {
					wr_i = new CachedWeakReference(i) ;
				}
				{
					// D(X) createNewMonitorStates:4 when Dom(theta'') = <c>
					Map_UnsafeIteratorMonitor_Set sourceSet = null;
					{
						// FindCode
						Tuple2<Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> node_c = Map_UnsafeIterator_c__To__m_c_Map.getNodeEquivalent(wr_c) ;
						if ((node_c != null) ) {
							Map_UnsafeIteratorMonitor_Set itmdSet = node_c.getValue1() ;
							sourceSet = itmdSet;
						}
					}
					if ((sourceSet != null) ) {
						int numalive = 0;
						int setlen = sourceSet.getSize() ;
						for (int ielem = 0; (ielem < setlen) ;++ielem) {
							Map_UnsafeIteratorMonitor sourceMonitor = sourceSet.get(ielem) ;
							if ((!sourceMonitor.isTerminated() && (sourceMonitor.RVMRef_m.get() != null) ) ) {
								sourceSet.set(numalive++, sourceMonitor) ;
								CachedWeakReference wr_m = sourceMonitor.RVMRef_m;
								MapOfMonitor<IMap_UnsafeIteratorMonitor> destLastMap = null;
								IMap_UnsafeIteratorMonitor destLeaf = null;
								{
									// FindOrCreate
									Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_m = Map_UnsafeIterator_m_c_i_Map.getNodeEquivalent(wr_m) ;
									if ((node_m == null) ) {
										node_m = new Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
										Map_UnsafeIterator_m_c_i_Map.putNode(wr_m, node_m) ;
										node_m.setValue1(new MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>(1) ) ;
										node_m.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
									}
									Tuple3<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> node_m_c = node_m.getValue1() .getNodeEquivalent(wr_c) ;
									if ((node_m_c == null) ) {
										node_m_c = new Tuple3<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>() ;
										node_m.getValue1() .putNode(wr_c, node_m_c) ;
										node_m_c.setValue1(new MapOfMonitor<IMap_UnsafeIteratorMonitor>(2) ) ;
										node_m_c.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
									}
									MapOfMonitor<IMap_UnsafeIteratorMonitor> itmdMap = node_m_c.getValue1() ;
									destLastMap = itmdMap;
									IMap_UnsafeIteratorMonitor node_m_c_i = node_m_c.getValue1() .getNodeEquivalent(wr_i) ;
									destLeaf = node_m_c_i;
								}
								if (((destLeaf == null) || destLeaf instanceof Map_UnsafeIteratorDisableHolder) ) {
									boolean definable = true;
									// D(X) defineTo:1--5 for <c, i>
									if (definable) {
										// FindCode
										Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_c = Map_UnsafeIterator_c_i_Map.getNodeEquivalent(wr_c) ;
										if ((node_c != null) ) {
											Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_c_i = node_c.getValue1() .getNodeEquivalent(wr_i) ;
											if ((node_c_i != null) ) {
												IMap_UnsafeIteratorMonitor itmdLeaf = node_c_i.getValue2() ;
												if ((itmdLeaf != null) ) {
													if (((itmdLeaf.getDisable() > sourceMonitor.getTau() ) || ((itmdLeaf.getTau() > 0) && (itmdLeaf.getTau() < sourceMonitor.getTau() ) ) ) ) {
														definable = false;
													}
												}
											}
										}
									}
									// D(X) defineTo:1--5 for <i>
									if (definable) {
										// FindCode
										Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_i = Map_UnsafeIterator_i_Map.getNodeEquivalent(wr_i) ;
										if ((node_i != null) ) {
											IMap_UnsafeIteratorMonitor itmdLeaf = node_i.getValue2() ;
											if ((itmdLeaf != null) ) {
												if (((itmdLeaf.getDisable() > sourceMonitor.getTau() ) || ((itmdLeaf.getTau() > 0) && (itmdLeaf.getTau() < sourceMonitor.getTau() ) ) ) ) {
													definable = false;
												}
											}
										}
									}
									// D(X) defineTo:1--5 for <m, c, i>
									if (definable) {
										// FindCode
										Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_m = Map_UnsafeIterator_m_c_i_Map.getNodeEquivalent(wr_m) ;
										if ((node_m != null) ) {
											Tuple3<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> node_m_c = node_m.getValue1() .getNodeEquivalent(wr_c) ;
											if ((node_m_c != null) ) {
												IMap_UnsafeIteratorMonitor node_m_c_i = node_m_c.getValue1() .getNodeEquivalent(wr_i) ;
												if ((node_m_c_i != null) ) {
													if (((node_m_c_i.getDisable() > sourceMonitor.getTau() ) || ((node_m_c_i.getTau() > 0) && (node_m_c_i.getTau() < sourceMonitor.getTau() ) ) ) ) {
														definable = false;
													}
												}
											}
										}
									}
									if (definable) {
										// D(X) defineTo:6
										Map_UnsafeIteratorMonitor created = (Map_UnsafeIteratorMonitor)sourceMonitor.clone() ;
										destLastMap.putNode(wr_i, created) ;
										// D(X) defineTo:7 for <c>
										{
											// InsertMonitor
											Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_c = Map_UnsafeIterator_c_i_Map.getNodeEquivalent(wr_c) ;
											if ((node_c == null) ) {
												node_c = new Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
												Map_UnsafeIterator_c_i_Map.putNode(wr_c, node_c) ;
												node_c.setValue1(new MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>(1) ) ;
												node_c.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
											}
											Map_UnsafeIteratorMonitor_Set targetSet = node_c.getValue2() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <c, i>
										{
											// InsertMonitor
											Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_c = Map_UnsafeIterator_c_i_Map.getNodeEquivalent(wr_c) ;
											if ((node_c == null) ) {
												node_c = new Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
												Map_UnsafeIterator_c_i_Map.putNode(wr_c, node_c) ;
												node_c.setValue1(new MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>(1) ) ;
												node_c.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
											}
											Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_c_i = node_c.getValue1() .getNodeEquivalent(wr_i) ;
											if ((node_c_i == null) ) {
												node_c_i = new Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
												node_c.getValue1() .putNode(wr_i, node_c_i) ;
												node_c_i.setValue1(new Map_UnsafeIteratorMonitor_Set() ) ;
											}
											Map_UnsafeIteratorMonitor_Set targetSet = node_c_i.getValue1() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <i>
										{
											// InsertMonitor
											Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_i = Map_UnsafeIterator_i_Map.getNodeEquivalent(wr_i) ;
											if ((node_i == null) ) {
												node_i = new Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
												Map_UnsafeIterator_i_Map.putNode(wr_i, node_i) ;
												node_i.setValue1(new Map_UnsafeIteratorMonitor_Set() ) ;
											}
											Map_UnsafeIteratorMonitor_Set targetSet = node_i.getValue1() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <m>
										{
											// InsertMonitor
											Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_m = Map_UnsafeIterator_m_c_i_Map.getNodeEquivalent(wr_m) ;
											if ((node_m == null) ) {
												node_m = new Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
												Map_UnsafeIterator_m_c_i_Map.putNode(wr_m, node_m) ;
												node_m.setValue1(new MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>(1) ) ;
												node_m.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
											}
											Map_UnsafeIteratorMonitor_Set targetSet = node_m.getValue2() ;
											targetSet.add(created) ;
										}
										// D(X) defineTo:7 for <m, c>
										{
											// InsertMonitor
											Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_m = Map_UnsafeIterator_m_c_i_Map.getNodeEquivalent(wr_m) ;
											if ((node_m == null) ) {
												node_m = new Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
												Map_UnsafeIterator_m_c_i_Map.putNode(wr_m, node_m) ;
												node_m.setValue1(new MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>(1) ) ;
												node_m.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
											}
											Tuple3<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor> node_m_c = node_m.getValue1() .getNodeEquivalent(wr_c) ;
											if ((node_m_c == null) ) {
												node_m_c = new Tuple3<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>() ;
												node_m.getValue1() .putNode(wr_c, node_m_c) ;
												node_m_c.setValue1(new MapOfMonitor<IMap_UnsafeIteratorMonitor>(2) ) ;
												node_m_c.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
											}
											Map_UnsafeIteratorMonitor_Set targetSet = node_m_c.getValue2() ;
											targetSet.add(created) ;
										}
									}
								}
							}
						}
						sourceSet.eraseRange(numalive) ;
					}
				}
				// D(X) main:6
				IMap_UnsafeIteratorMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
				if ((disableUpdatedLeaf == null) ) {
					Map_UnsafeIteratorDisableHolder holder = new Map_UnsafeIteratorDisableHolder(-1) ;
					matchedEntry.setValue2(holder) ;
					disableUpdatedLeaf = holder;
				}
				disableUpdatedLeaf.setDisable(Map_UnsafeIterator_timestamp++) ;
			}
			// D(X) main:8--9
			Map_UnsafeIteratorMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
			stateTransitionedSet.event_getiter(c, i);

			if ((cachehit == false) ) {
				Map_UnsafeIterator_c_i_Map_cachekey_c = c;
				Map_UnsafeIterator_c_i_Map_cachekey_i = i;
				Map_UnsafeIterator_c_i_Map_cachevalue = matchedEntry;
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Map_UnsafeIterator_modifyMapEvent(Map m) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Map_UnsafeIterator_activated) {
			CachedWeakReference wr_m = null;
			Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> matchedEntry = null;
			boolean cachehit = false;
			if ((m == Map_UnsafeIterator_m_Map_cachekey_m) ) {
				matchedEntry = Map_UnsafeIterator_m_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_m = new CachedWeakReference(m) ;
				{
					// FindOrCreateEntry
					Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_m = Map_UnsafeIterator_m_c_i_Map.getNodeEquivalent(wr_m) ;
					if ((node_m == null) ) {
						node_m = new Tuple3<MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
						Map_UnsafeIterator_m_c_i_Map.putNode(wr_m, node_m) ;
						node_m.setValue1(new MapOfAll<MapOfMonitor<IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, Map_UnsafeIteratorMonitor>(1) ) ;
						node_m.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
					}
					matchedEntry = node_m;
				}
			}
			// D(X) main:1
			IMap_UnsafeIteratorMonitor matchedLeaf = matchedEntry.getValue3() ;
			if ((matchedLeaf == null) ) {
				if ((wr_m == null) ) {
					wr_m = new CachedWeakReference(m) ;
				}
				// D(X) main:6
				IMap_UnsafeIteratorMonitor disableUpdatedLeaf = matchedEntry.getValue3() ;
				if ((disableUpdatedLeaf == null) ) {
					Map_UnsafeIteratorDisableHolder holder = new Map_UnsafeIteratorDisableHolder(-1) ;
					matchedEntry.setValue3(holder) ;
					disableUpdatedLeaf = holder;
				}
				disableUpdatedLeaf.setDisable(Map_UnsafeIterator_timestamp++) ;
			}
			// D(X) main:8--9
			Map_UnsafeIteratorMonitor_Set stateTransitionedSet = matchedEntry.getValue2() ;
			stateTransitionedSet.event_modifyMap(m);

			if ((cachehit == false) ) {
				Map_UnsafeIterator_m_Map_cachekey_m = m;
				Map_UnsafeIterator_m_Map_cachevalue = matchedEntry;
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Map_UnsafeIterator_modifyColEvent(Collection c) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Map_UnsafeIterator_activated) {
			CachedWeakReference wr_c = null;
			Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> matchedEntry = null;
			boolean cachehit = false;
			if ((c == Map_UnsafeIterator_c_Map_cachekey_c) ) {
				matchedEntry = Map_UnsafeIterator_c_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_c = new CachedWeakReference(c) ;
				{
					// FindOrCreateEntry
					Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_c = Map_UnsafeIterator_c_i_Map.getNodeEquivalent(wr_c) ;
					if ((node_c == null) ) {
						node_c = new Tuple3<MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>, Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
						Map_UnsafeIterator_c_i_Map.putNode(wr_c, node_c) ;
						node_c.setValue1(new MapOfSetMonitor<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>(1) ) ;
						node_c.setValue2(new Map_UnsafeIteratorMonitor_Set() ) ;
					}
					matchedEntry = node_c;
				}
			}
			// D(X) main:1
			IMap_UnsafeIteratorMonitor matchedLeaf = matchedEntry.getValue3() ;
			if ((matchedLeaf == null) ) {
				if ((wr_c == null) ) {
					wr_c = new CachedWeakReference(c) ;
				}
				// D(X) main:6
				IMap_UnsafeIteratorMonitor disableUpdatedLeaf = matchedEntry.getValue3() ;
				if ((disableUpdatedLeaf == null) ) {
					Map_UnsafeIteratorDisableHolder holder = new Map_UnsafeIteratorDisableHolder(-1) ;
					matchedEntry.setValue3(holder) ;
					disableUpdatedLeaf = holder;
				}
				disableUpdatedLeaf.setDisable(Map_UnsafeIterator_timestamp++) ;
			}
			// D(X) main:8--9
			Map_UnsafeIteratorMonitor_Set stateTransitionedSet = matchedEntry.getValue2() ;
			stateTransitionedSet.event_modifyCol(c);

			if ((cachehit == false) ) {
				Map_UnsafeIterator_c_Map_cachekey_c = c;
				Map_UnsafeIterator_c_Map_cachevalue = matchedEntry;
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Map_UnsafeIterator_useiterEvent(Iterator i) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Map_UnsafeIterator_activated) {
			CachedWeakReference wr_i = null;
			Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> matchedEntry = null;
			boolean cachehit = false;
			if ((i == Map_UnsafeIterator_i_Map_cachekey_i) ) {
				matchedEntry = Map_UnsafeIterator_i_Map_cachevalue;
				cachehit = true;
			}
			else {
				wr_i = new CachedWeakReference(i) ;
				{
					// FindOrCreateEntry
					Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor> node_i = Map_UnsafeIterator_i_Map.getNodeEquivalent(wr_i) ;
					if ((node_i == null) ) {
						node_i = new Tuple2<Map_UnsafeIteratorMonitor_Set, IMap_UnsafeIteratorMonitor>() ;
						Map_UnsafeIterator_i_Map.putNode(wr_i, node_i) ;
						node_i.setValue1(new Map_UnsafeIteratorMonitor_Set() ) ;
					}
					matchedEntry = node_i;
				}
			}
			// D(X) main:1
			IMap_UnsafeIteratorMonitor matchedLeaf = matchedEntry.getValue2() ;
			if ((matchedLeaf == null) ) {
				if ((wr_i == null) ) {
					wr_i = new CachedWeakReference(i) ;
				}
				// D(X) main:6
				IMap_UnsafeIteratorMonitor disableUpdatedLeaf = matchedEntry.getValue2() ;
				if ((disableUpdatedLeaf == null) ) {
					Map_UnsafeIteratorDisableHolder holder = new Map_UnsafeIteratorDisableHolder(-1) ;
					matchedEntry.setValue2(holder) ;
					disableUpdatedLeaf = holder;
				}
				disableUpdatedLeaf.setDisable(Map_UnsafeIterator_timestamp++) ;
			}
			// D(X) main:8--9
			Map_UnsafeIteratorMonitor_Set stateTransitionedSet = matchedEntry.getValue1() ;
			stateTransitionedSet.event_useiter(i);

			if ((cachehit == false) ) {
				Map_UnsafeIterator_i_Map_cachekey_i = i;
				Map_UnsafeIterator_i_Map_cachevalue = matchedEntry;
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Object_MonitorOwner_bad_notifyEvent(Object o) {
		Object_MonitorOwner_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Object_MonitorOwnerMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Object_MonitorOwner__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Object_MonitorOwnerMonitor created = new Object_MonitorOwnerMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_bad_notify(o);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Object_MonitorOwner_bad_waitEvent(Object o) {
		Object_MonitorOwner_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Object_MonitorOwnerMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Object_MonitorOwner__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Object_MonitorOwnerMonitor created = new Object_MonitorOwnerMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_bad_wait(o);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void OutputStream_ManipulateAfterClose_manipulateEvent(OutputStream o) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (OutputStream_ManipulateAfterClose_activated) {
			OutputStream_ManipulateAfterCloseMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((o == OutputStream_ManipulateAfterClose_o_Map_cachekey_o) ) {
				matchedEntry = OutputStream_ManipulateAfterClose_o_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				OutputStream_ManipulateAfterCloseMonitor node_o = OutputStream_ManipulateAfterClose_o_Map.getNodeWithStrongRef(o) ;
				matchedEntry = node_o;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final OutputStream_ManipulateAfterCloseMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_manipulate(o);
				if(matchedEntryfinalMonitor.OutputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					matchedEntryfinalMonitor.Prop_1_handler_match();
				}

				if ((cachehit == false) ) {
					OutputStream_ManipulateAfterClose_o_Map_cachekey_o = o;
					OutputStream_ManipulateAfterClose_o_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void OutputStream_ManipulateAfterClose_closeEvent(OutputStream o) {
		OutputStream_ManipulateAfterClose_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_o = null;
		MapOfMonitor<OutputStream_ManipulateAfterCloseMonitor> matchedLastMap = null;
		OutputStream_ManipulateAfterCloseMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((o == OutputStream_ManipulateAfterClose_o_Map_cachekey_o) ) {
			matchedEntry = OutputStream_ManipulateAfterClose_o_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_o = new CachedWeakReference(o) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<OutputStream_ManipulateAfterCloseMonitor> itmdMap = OutputStream_ManipulateAfterClose_o_Map;
				matchedLastMap = itmdMap;
				OutputStream_ManipulateAfterCloseMonitor node_o = OutputStream_ManipulateAfterClose_o_Map.getNodeEquivalent(wr_o) ;
				matchedEntry = node_o;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_o == null) ) {
				wr_o = new CachedWeakReference(o) ;
			}
			// D(X) main:4
			OutputStream_ManipulateAfterCloseMonitor created = new OutputStream_ManipulateAfterCloseMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_o, created) ;
		}
		// D(X) main:8--9
		final OutputStream_ManipulateAfterCloseMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_close(o);
		if(matchedEntryfinalMonitor.OutputStream_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			OutputStream_ManipulateAfterClose_o_Map_cachekey_o = o;
			OutputStream_ManipulateAfterClose_o_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Reader_ManipulateAfterClose_manipulateEvent(Reader r) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Reader_ManipulateAfterClose_activated) {
			Reader_ManipulateAfterCloseMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((r == Reader_ManipulateAfterClose_r_Map_cachekey_r) ) {
				matchedEntry = Reader_ManipulateAfterClose_r_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				Reader_ManipulateAfterCloseMonitor node_r = Reader_ManipulateAfterClose_r_Map.getNodeWithStrongRef(r) ;
				matchedEntry = node_r;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final Reader_ManipulateAfterCloseMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_manipulate(r);
				if(matchedEntryfinalMonitor.Reader_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					matchedEntryfinalMonitor.Prop_1_handler_match();
				}

				if ((cachehit == false) ) {
					Reader_ManipulateAfterClose_r_Map_cachekey_r = r;
					Reader_ManipulateAfterClose_r_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Reader_ManipulateAfterClose_closeEvent(Reader r) {
		Reader_ManipulateAfterClose_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_r = null;
		MapOfMonitor<Reader_ManipulateAfterCloseMonitor> matchedLastMap = null;
		Reader_ManipulateAfterCloseMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((r == Reader_ManipulateAfterClose_r_Map_cachekey_r) ) {
			matchedEntry = Reader_ManipulateAfterClose_r_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_r = new CachedWeakReference(r) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<Reader_ManipulateAfterCloseMonitor> itmdMap = Reader_ManipulateAfterClose_r_Map;
				matchedLastMap = itmdMap;
				Reader_ManipulateAfterCloseMonitor node_r = Reader_ManipulateAfterClose_r_Map.getNodeEquivalent(wr_r) ;
				matchedEntry = node_r;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_r == null) ) {
				wr_r = new CachedWeakReference(r) ;
			}
			// D(X) main:4
			Reader_ManipulateAfterCloseMonitor created = new Reader_ManipulateAfterCloseMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_r, created) ;
		}
		// D(X) main:8--9
		final Reader_ManipulateAfterCloseMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_close(r);
		if(matchedEntryfinalMonitor.Reader_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			Reader_ManipulateAfterClose_r_Map_cachekey_r = r;
			Reader_ManipulateAfterClose_r_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Serializable_NoArgConstructor_staticinitEvent(org.aspectj.lang.Signature staticsig) {
		Serializable_NoArgConstructor_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		Serializable_NoArgConstructorMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = Serializable_NoArgConstructor__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			Serializable_NoArgConstructorMonitor created = new Serializable_NoArgConstructorMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_staticinit(staticsig);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ServerSocket_Backlog_constructEvent(int backlog) {
		ServerSocket_Backlog_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		ServerSocket_BacklogMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = ServerSocket_Backlog__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			ServerSocket_BacklogMonitor created = new ServerSocket_BacklogMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_construct(backlog);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ServerSocket_Backlog_setEvent(int backlog) {
		ServerSocket_Backlog_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		ServerSocket_BacklogMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = ServerSocket_Backlog__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			ServerSocket_BacklogMonitor created = new ServerSocket_BacklogMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_set(backlog);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ServerSocket_SetTimeoutBeforeBlocking_enterEvent(ServerSocket sock) {
		ServerSocket_SetTimeoutBeforeBlocking_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_sock = null;
		MapOfMonitor<ServerSocket_SetTimeoutBeforeBlockingMonitor> matchedLastMap = null;
		ServerSocket_SetTimeoutBeforeBlockingMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((sock == ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachekey_sock) ) {
			matchedEntry = ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_sock = new CachedWeakReference(sock) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<ServerSocket_SetTimeoutBeforeBlockingMonitor> itmdMap = ServerSocket_SetTimeoutBeforeBlocking_sock_Map;
				matchedLastMap = itmdMap;
				ServerSocket_SetTimeoutBeforeBlockingMonitor node_sock = ServerSocket_SetTimeoutBeforeBlocking_sock_Map.getNodeEquivalent(wr_sock) ;
				matchedEntry = node_sock;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_sock == null) ) {
				wr_sock = new CachedWeakReference(sock) ;
			}
			// D(X) main:4
			ServerSocket_SetTimeoutBeforeBlockingMonitor created = new ServerSocket_SetTimeoutBeforeBlockingMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_sock, created) ;
		}
		// D(X) main:8--9
		final ServerSocket_SetTimeoutBeforeBlockingMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_enter(sock);
		if(matchedEntryfinalMonitor.ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail) {
			matchedEntryfinalMonitor.Prop_1_handler_fail();
		}

		if ((cachehit == false) ) {
			ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachekey_sock = sock;
			ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ServerSocket_SetTimeoutBeforeBlocking_leaveEvent(ServerSocket sock) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (ServerSocket_SetTimeoutBeforeBlocking_activated) {
			ServerSocket_SetTimeoutBeforeBlockingMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((sock == ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachekey_sock) ) {
				matchedEntry = ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				ServerSocket_SetTimeoutBeforeBlockingMonitor node_sock = ServerSocket_SetTimeoutBeforeBlocking_sock_Map.getNodeWithStrongRef(sock) ;
				matchedEntry = node_sock;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final ServerSocket_SetTimeoutBeforeBlockingMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_leave(sock);
				if(matchedEntryfinalMonitor.ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail) {
					matchedEntryfinalMonitor.Prop_1_handler_fail();
				}

				if ((cachehit == false) ) {
					ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachekey_sock = sock;
					ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void ServerSocket_SetTimeoutBeforeBlocking_setEvent(ServerSocket sock, int timeout) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (ServerSocket_SetTimeoutBeforeBlocking_activated) {
			ServerSocket_SetTimeoutBeforeBlockingMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((sock == ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachekey_sock) ) {
				matchedEntry = ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				ServerSocket_SetTimeoutBeforeBlockingMonitor node_sock = ServerSocket_SetTimeoutBeforeBlocking_sock_Map.getNodeWithStrongRef(sock) ;
				matchedEntry = node_sock;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final ServerSocket_SetTimeoutBeforeBlockingMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_set(sock, timeout);
				if(matchedEntryfinalMonitor.ServerSocket_SetTimeoutBeforeBlockingMonitor_Prop_1_Category_fail) {
					matchedEntryfinalMonitor.Prop_1_handler_fail();
				}

				if ((cachehit == false) ) {
					ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachekey_sock = sock;
					ServerSocket_SetTimeoutBeforeBlocking_sock_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SortedSet_Comparable_addEvent(SortedSet s, Object e) {
		SortedSet_Comparable_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_s = null;
		MapOfMonitor<SortedSet_ComparableMonitor> matchedLastMap = null;
		SortedSet_ComparableMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SortedSet_Comparable_s_Map_cachekey_s) ) {
			matchedEntry = SortedSet_Comparable_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SortedSet_ComparableMonitor> itmdMap = SortedSet_Comparable_s_Map;
				matchedLastMap = itmdMap;
				SortedSet_ComparableMonitor node_s = SortedSet_Comparable_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SortedSet_ComparableMonitor created = new SortedSet_ComparableMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		matchedEntry.event_add(s, e);

		if ((cachehit == false) ) {
			SortedSet_Comparable_s_Map_cachekey_s = s;
			SortedSet_Comparable_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void SortedSet_Comparable_addallEvent(SortedSet s, Collection c) {
		SortedSet_Comparable_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_s = null;
		MapOfMonitor<SortedSet_ComparableMonitor> matchedLastMap = null;
		SortedSet_ComparableMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((s == SortedSet_Comparable_s_Map_cachekey_s) ) {
			matchedEntry = SortedSet_Comparable_s_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_s = new CachedWeakReference(s) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<SortedSet_ComparableMonitor> itmdMap = SortedSet_Comparable_s_Map;
				matchedLastMap = itmdMap;
				SortedSet_ComparableMonitor node_s = SortedSet_Comparable_s_Map.getNodeEquivalent(wr_s) ;
				matchedEntry = node_s;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_s == null) ) {
				wr_s = new CachedWeakReference(s) ;
			}
			// D(X) main:4
			SortedSet_ComparableMonitor created = new SortedSet_ComparableMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_s, created) ;
		}
		// D(X) main:8--9
		matchedEntry.event_addall(s, c);

		if ((cachehit == false) ) {
			SortedSet_Comparable_s_Map_cachekey_s = s;
			SortedSet_Comparable_s_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TreeMap_Comparable_createEvent(Map src) {
		TreeMap_Comparable_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TreeMap_ComparableMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = TreeMap_Comparable__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			TreeMap_ComparableMonitor created = new TreeMap_ComparableMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_create(src);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TreeMap_Comparable_putEvent(Object key) {
		TreeMap_Comparable_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TreeMap_ComparableMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = TreeMap_Comparable__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			TreeMap_ComparableMonitor created = new TreeMap_ComparableMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_put(key);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TreeMap_Comparable_putallEvent(Map src) {
		TreeMap_Comparable_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TreeMap_ComparableMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = TreeMap_Comparable__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			TreeMap_ComparableMonitor created = new TreeMap_ComparableMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_putall(src);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TreeSet_Comparable_addEvent(Object e) {
		TreeSet_Comparable_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TreeSet_ComparableMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = TreeSet_Comparable__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			TreeSet_ComparableMonitor created = new TreeSet_ComparableMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_add(e);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void TreeSet_Comparable_addallEvent(Collection c) {
		TreeSet_Comparable_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		TreeSet_ComparableMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = TreeSet_Comparable__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			TreeSet_ComparableMonitor created = new TreeSet_ComparableMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_addall(c);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void URLConnection_OverrideGetPermission_staticinitEvent(org.aspectj.lang.Signature staticsig) {
		URLConnection_OverrideGetPermission_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		URLConnection_OverrideGetPermissionMonitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = URLConnection_OverrideGetPermission__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			URLConnection_OverrideGetPermissionMonitor created = new URLConnection_OverrideGetPermissionMonitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_staticinit(staticsig);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void URLDecoder_DecodeUTF8_decodeEvent(String enc) {
		URLDecoder_DecodeUTF8_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		URLDecoder_DecodeUTF8Monitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = URLDecoder_DecodeUTF8__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			URLDecoder_DecodeUTF8Monitor created = new URLDecoder_DecodeUTF8Monitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_decode(enc);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void URLEncoder_EncodeUTF8_encodeEvent(String enc) {
		URLEncoder_EncodeUTF8_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		URLEncoder_EncodeUTF8Monitor matchedEntry = null;
		{
			// FindOrCreateEntry
			matchedEntry = URLEncoder_EncodeUTF8__Map;
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			// D(X) main:4
			URLEncoder_EncodeUTF8Monitor created = new URLEncoder_EncodeUTF8Monitor() ;
			matchedEntry = created;
		}
		// D(X) main:8--9
		matchedEntry.event_encode(enc);

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Writer_ManipulateAfterClose_manipulateEvent(Writer w) {
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		if (Writer_ManipulateAfterClose_activated) {
			Writer_ManipulateAfterCloseMonitor matchedEntry = null;
			boolean cachehit = false;
			if ((w == Writer_ManipulateAfterClose_w_Map_cachekey_w) ) {
				matchedEntry = Writer_ManipulateAfterClose_w_Map_cachevalue;
				cachehit = true;
			}
			else {
				// FindEntry
				Writer_ManipulateAfterCloseMonitor node_w = Writer_ManipulateAfterClose_w_Map.getNodeWithStrongRef(w) ;
				matchedEntry = node_w;
			}
			// D(X) main:8--9
			if ((matchedEntry != null) ) {
				final Writer_ManipulateAfterCloseMonitor matchedEntryfinalMonitor = matchedEntry;
				matchedEntry.Prop_1_event_manipulate(w);
				if(matchedEntryfinalMonitor.Writer_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
					matchedEntryfinalMonitor.Prop_1_handler_match();
				}

				if ((cachehit == false) ) {
					Writer_ManipulateAfterClose_w_Map_cachekey_w = w;
					Writer_ManipulateAfterClose_w_Map_cachevalue = matchedEntry;
				}
			}

		}

		MultiSpec_1_RVMLock.unlock();
	}

	public static final void Writer_ManipulateAfterClose_closeEvent(Writer w) {
		Writer_ManipulateAfterClose_activated = true;
		while (!MultiSpec_1_RVMLock.tryLock()) {
			Thread.yield();
		}

		CachedWeakReference wr_w = null;
		MapOfMonitor<Writer_ManipulateAfterCloseMonitor> matchedLastMap = null;
		Writer_ManipulateAfterCloseMonitor matchedEntry = null;
		boolean cachehit = false;
		if ((w == Writer_ManipulateAfterClose_w_Map_cachekey_w) ) {
			matchedEntry = Writer_ManipulateAfterClose_w_Map_cachevalue;
			cachehit = true;
		}
		else {
			wr_w = new CachedWeakReference(w) ;
			{
				// FindOrCreateEntry
				MapOfMonitor<Writer_ManipulateAfterCloseMonitor> itmdMap = Writer_ManipulateAfterClose_w_Map;
				matchedLastMap = itmdMap;
				Writer_ManipulateAfterCloseMonitor node_w = Writer_ManipulateAfterClose_w_Map.getNodeEquivalent(wr_w) ;
				matchedEntry = node_w;
			}
		}
		// D(X) main:1
		if ((matchedEntry == null) ) {
			if ((wr_w == null) ) {
				wr_w = new CachedWeakReference(w) ;
			}
			// D(X) main:4
			Writer_ManipulateAfterCloseMonitor created = new Writer_ManipulateAfterCloseMonitor() ;
			matchedEntry = created;
			matchedLastMap.putNode(wr_w, created) ;
		}
		// D(X) main:8--9
		final Writer_ManipulateAfterCloseMonitor matchedEntryfinalMonitor = matchedEntry;
		matchedEntry.Prop_1_event_close(w);
		if(matchedEntryfinalMonitor.Writer_ManipulateAfterCloseMonitor_Prop_1_Category_match) {
			matchedEntryfinalMonitor.Prop_1_handler_match();
		}

		if ((cachehit == false) ) {
			Writer_ManipulateAfterClose_w_Map_cachekey_w = w;
			Writer_ManipulateAfterClose_w_Map_cachevalue = matchedEntry;
		}

		MultiSpec_1_RVMLock.unlock();
	}

}
