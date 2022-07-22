package com.runtimeverification.rvmonitor.java.rt.table;

import com.runtimeverification.rvmonitor.java.rt.ref.CachedTagWeakReference;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IMonitor;
import com.runtimeverification.rvmonitor.java.rt.tablebase.IWeakRefTableOperation;

public class TagRefMapOfMonitor<TLeaf extends IMonitor> extends AbstractMapOfMonitor<CachedTagWeakReference, TLeaf> implements IWeakRefTableOperation<CachedTagWeakReference> {
	public TagRefMapOfMonitor(int treeid) {
		super(treeid);
	}

	@Override
	protected CachedTagWeakReference createWeakRef(Object key, int hashval) {
		return new CachedTagWeakReference(key, hashval);
	}
	
	@Override
	public CachedTagWeakReference findWeakRef(Object key) {
		return this.findOrCreateWeakRefInternal(key, false);
	}

	@Override
	public CachedTagWeakReference findOrCreateWeakRef(Object key) {
		return this.findOrCreateWeakRefInternal(key, true);
	}
}