package com.fdu.se.sootanalyze.utils;

public class NumberIncrementer {

	private long num;
	
	public NumberIncrementer() {
		this(0);
	}
	
	public NumberIncrementer(long initialValue) {
		num = initialValue;
	}
	
	public long inc() {
		return increment();
	}
	
	public long increment() {
		return ++num;
	}
	
	public long get() {
		return num;
	}
	
	public long next() {
		return increment();
	}
	
}
