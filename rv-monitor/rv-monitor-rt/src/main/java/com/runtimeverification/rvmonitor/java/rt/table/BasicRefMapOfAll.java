package com.runtimeverification.rvmonitor.java.rt.table;

import com.runtimeverification.rvmonitor.java.rt.ref.CachedWeakReference;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IIndexingTree;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IMonitor;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IMonitorSet;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IWeakRefTableOperation;

public class BasicRefMapOfAll<TMap extends IIndexingTree, TSet extends IMonitorSet, TLeaf extends IMonitor> extends AbstractMapOfAll<CachedWeakReference, TMap, TSet, TLeaf> implements IWeakRefTableOperation<CachedWeakReference> {
	public BasicRefMapOfAll(int treeid) {
		super(treeid);
	}
	
	@Override
	protected CachedWeakReference createWeakRef(Object key, int hashval) {
		return new CachedWeakReference(key, hashval);
	}
	
	@Override
	public CachedWeakReference findWeakRef(Object key) {
		return this.findOrCreateWeakRefInternal(key, false);
	}

	@Override
	public CachedWeakReference findOrCreateWeakRef(Object key) {
		return this.findOrCreateWeakRefInternal(key, true);
	}
}