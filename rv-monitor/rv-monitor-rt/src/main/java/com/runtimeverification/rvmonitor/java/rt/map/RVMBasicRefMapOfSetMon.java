package com.runtimeverification.rvmonitor.java.rt.map;

import com.runtimeverification.rvmonitor.java.rt.RVMMonitor;
import com.runtimeverification.rvmonitor.java.rt.RVMSet;
import com.runtimeverification.rvmonitor.java.rt.map.hashentry.RVMHashDualEntry;
import com.runtimeverification.rvmonitor.java.rt.ref.RVMTagWeakReference;
import com.runtimeverification.rvmonitor.java.rt.ref.RVMMultiTagWeakReference;
import com.runtimeverification.rvmonitor.java.rt.ref.RVMWeakReference;

public class RVMBasicRefMapOfSetMon extends RVMMapOfSetMon implements RVMRefMap {
	static public RVMWeakReference NULRef = new RVMWeakReference(null);

	protected Object cachedKey = null;
	protected RVMWeakReference cachedValue = NULRef;

	protected Object[] cachedKey2 = new Object[ref_locality_cache_size];
	protected RVMWeakReference[] cachedValue2 = new RVMWeakReference[ref_locality_cache_size];

	public RVMBasicRefMapOfSetMon(int idnum) {
		super(idnum);

		for (int i = 0; i < ref_locality_cache_size; i++) {
			cachedKey2[i] = null;
			cachedValue2[i] = NULRef;
		}
	}

	@Override
	public RVMWeakReference getRef(Object key, int joinPointId) {
		if (key == cachedKey && cachedValue != NULRef) {
			return cachedValue;
		}

		int cacheIndex = joinPointId & (ref_locality_cache_size - 1);

		if (key == cachedKey2[cacheIndex] && cachedValue2[cacheIndex] != NULRef) {
			cachedKey = cachedKey2[cacheIndex];
			cachedValue = cachedValue2[cacheIndex];
			return cachedValue;
		}

		cachedKey = key;
		cachedKey2[cacheIndex] = key;

		RVMHashDualEntry[] data = this.data;

		int hashCode = System.identityHashCode(key);
		int index = hashIndex(hashCode, data.length);
		RVMHashDualEntry entry = data[index];

		while (entry != null) {
			if (key == entry.key.get()) {
				cachedValue = entry.key;
				cachedValue2[cacheIndex] = entry.key;

				return cachedValue;
			}
			entry = entry.next;
		}

		// create new weakreference
		RVMWeakReference keyref = new RVMWeakReference(key, hashCode);
		cachedValue = keyref;

		for (int i = 0; i < ref_locality_cache_size; i++) {
			if (cachedKey2[i] == key)
				cachedValue2[i] = keyref;
		}

		if (multicore && data.length > DEFAULT_THREADED_CLEANUP_THREASHOLD) {
			putIndex = hashIndex(hashCode, data.length);

			while (this.newdata != null) {
				putIndex = -1;
				while (this.newdata != null) {
					Thread.yield();
				}
				data = this.data;
				putIndex = hashIndex(hashCode, data.length);
			}

			while (cleanIndex == putIndex) {
				Thread.yield();
			}

			RVMHashDualEntry newentry = new RVMHashDualEntry(data[putIndex], keyref);
			data[putIndex] = newentry;
			addedMappings++;

			putIndex = -1;

			if (!isCleaning && this.nextInQueue == null && addedMappings - deletedMappings >= data.length / 2 && addedMappings - deletedMappings - lastsize > data.length / 10) {
				this.isCleaning = true;
				if (RVMMapManager.treeQueueTail == this) {
					this.repeat = true;
				} else {
					RVMMapManager.treeQueueTail.nextInQueue = this;
					RVMMapManager.treeQueueTail = this;
				}
			}
		} else {
			RVMHashDualEntry newentry = new RVMHashDualEntry(data[index], keyref);
			data[index] = newentry;
			addedMappings++;

			if (multicore)
				checkCapacityNoOneIter();
			else
				checkCapacity();
		}

		return keyref;
	}

	@Override
	public RVMWeakReference getRefNonCreative(Object key, int joinPointId) {
		if (key == cachedKey) {
			return cachedValue;
		}

		int cacheIndex = joinPointId & (ref_locality_cache_size - 1);

		if (key == cachedKey2[cacheIndex]) {
			cachedKey = cachedKey2[cacheIndex];
			cachedValue = cachedValue2[cacheIndex];
			return cachedValue;
		}

		cachedKey = key;
		cachedKey2[cacheIndex] = key;

		RVMHashDualEntry[] data = this.data;

		int hashCode = System.identityHashCode(key);
		int index = hashIndex(hashCode, data.length);
		RVMHashDualEntry entry = data[index];

		while (entry != null) {
			if (key == entry.key.get()) {
				cachedValue = entry.key;
				cachedValue2[cacheIndex] = entry.key;

				return cachedValue;
			}
			entry = entry.next;
		}
		cachedValue = NULRef;
		cachedValue2[cacheIndex] = NULRef;

		return NULRef;
	}

	@Override
	public RVMTagWeakReference getTagRef(Object key, int joinPointId) {
		return null;
	}

	@Override
	public RVMTagWeakReference getTagRefNonCreative(Object key, int joinPointId) {
		return null;
	}

	@Override
	public RVMMultiTagWeakReference getMultiTagRef(Object key, int joinPointId) {
		return null;
	}

	@Override
	public RVMMultiTagWeakReference getMultiTagRefNonCreative(Object key, int joinPointId) {
		return null;
	}

	@Override
	public RVMWeakReference getRef(Object key) {
		if (key == cachedKey && cachedValue != NULRef) {
			return cachedValue;
		}

		cachedKey = key;

		RVMHashDualEntry[] data = this.data;

		int hashCode = System.identityHashCode(key);
		int index = hashIndex(hashCode, data.length);
		RVMHashDualEntry entry = data[index];

		while (entry != null) {
			if (key == entry.key.get()) {
				cachedValue = entry.key;

				return cachedValue;
			}
			entry = entry.next;
		}

		// create new weakreference
		RVMWeakReference keyref = new RVMWeakReference(key, hashCode);
		cachedValue = keyref;

		if (multicore && data.length > DEFAULT_THREADED_CLEANUP_THREASHOLD) {
			putIndex = hashIndex(hashCode, data.length);

			while (this.newdata != null) {
				putIndex = -1;
				while (this.newdata != null) {
					Thread.yield();
				}
				data = this.data;
				putIndex = hashIndex(hashCode, data.length);
			}

			while (cleanIndex == putIndex) {
				Thread.yield();
			}

			RVMHashDualEntry newentry = new RVMHashDualEntry(data[putIndex], keyref);
			data[putIndex] = newentry;
			addedMappings++;

			putIndex = -1;

			if (!isCleaning && this.nextInQueue == null && addedMappings - deletedMappings >= data.length / 2 && addedMappings - deletedMappings - lastsize > data.length / 10) {
				this.isCleaning = true;
				if (RVMMapManager.treeQueueTail == this) {
					this.repeat = true;
				} else {
					RVMMapManager.treeQueueTail.nextInQueue = this;
					RVMMapManager.treeQueueTail = this;
				}
			}
		} else {
			RVMHashDualEntry newentry = new RVMHashDualEntry(data[index], keyref);
			data[index] = newentry;
			addedMappings++;

			if (multicore)
				checkCapacityNoOneIter();
			else
				checkCapacity();
		}

		return keyref;
	}

	@Override
	public RVMWeakReference getRefNonCreative(Object key) {
		if (key == cachedKey) {
			return cachedValue;
		}

		cachedKey = key;

		RVMHashDualEntry[] data = this.data;

		int hashCode = System.identityHashCode(key);
		int index = hashIndex(hashCode, data.length);
		RVMHashDualEntry entry = data[index];

		while (entry != null) {
			if (key == entry.key.get()) {
				cachedValue = entry.key;

				return cachedValue;
			}
			entry = entry.next;
		}
		cachedValue = NULRef;

		return NULRef;
	}

	@Override
	public RVMTagWeakReference getTagRef(Object key){
		return null;
	}

	@Override
	public RVMTagWeakReference getTagRefNonCreative(Object key){
		return null;
	}
	
	@Override
	public RVMMultiTagWeakReference getMultiTagRef(Object key){
		return null;
	}
	
	@Override
	public RVMMultiTagWeakReference getMultiTagRefNonCreative(Object key){
		return null;
	}

	/* ************************************************************************************ */

	@Override
	protected void endObject(int idnum) {
		this.isDeleted = true;
		for (int i = data.length - 1; i >= 0; i--) {
			RVMHashDualEntry entry = data[i];
			data[i] = null;
			while (entry != null) {
				RVMHashDualEntry next = entry.next;

				RVMSet set = (RVMSet) entry.value1;
				RVMMonitor monitor = (RVMMonitor) entry.value2;
				
				if (set != null)
					set.endObjectAndClean(idnum);
				if (monitor != null && !monitor.RVM_terminated)
					monitor.endObject(idnum);

				entry.next = null;
				entry = next;
			}
		}

		this.deletedMappings = this.addedMappings;
	}

	@Override
	protected void cleanupchunkiter() {
		if (cleancursor < 0)
			cleancursor = data.length - 1;

		for (int i = 0; i < ref_cleanup_piece && cleancursor >= 0; i++) {
			RVMHashDualEntry previous = null;
			RVMHashDualEntry entry = data[cleancursor];

			while (entry != null) {
				RVMHashDualEntry next = entry.next;

				if (entry.key.get() == null) {
					if (previous == null) {
						data[cleancursor] = entry.next;
					} else {
						previous.next = entry.next;
					}

					RVMSet set = (RVMSet) entry.value1;
					RVMMonitor monitor = (RVMMonitor) entry.value2;
					
					if (set != null)
						set.endObjectAndClean(idnum);
					if (monitor != null && !monitor.RVM_terminated)
						monitor.endObject(idnum);

					entry.next = null;
					this.deletedMappings++;
				} else {
					previous = entry;
				}
				entry = next;
			}
			cleancursor--;
		}
	}

	@Override
	protected void cleanupiter() {
		for (int i = data.length - 1; i >= 0; i--) {
			RVMHashDualEntry entry = data[i];
			RVMHashDualEntry previous = null;
			while (entry != null) {
				RVMHashDualEntry next = entry.next;

				if (entry.key.get() == null) {
					if (previous == null) {
						data[i] = entry.next;
					} else {
						previous.next = entry.next;
					}

					RVMSet set = (RVMSet) entry.value1;
					RVMMonitor monitor = (RVMMonitor) entry.value2;

					if (set != null)
						set.endObjectAndClean(idnum);
					if (monitor != null && !monitor.RVM_terminated)
						monitor.endObject(idnum);

					entry.next = null;
					this.deletedMappings++;
				} else {
					previous = entry;
				}
				entry = next;
			}
		}
	}

}
