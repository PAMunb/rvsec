package br.unb.cic.rvsec.taint.model;

import soot.SootField;
import soot.SootMethod;

public class ViewInfo {
	private String id;
	private String name;
	private String callback;
	private String textId;

	private String tipo;

	private SootField field;// sootfield
	private SootMethod callbackMethod;

	public String getId() {
		return id;
	}

	public void setId(String id) {
		this.id = id;
	}

	public String getTextId() {
		return textId;
	}

	public void setTextId(String textId) {
		this.textId = textId;
	}

	public String getTipo() {
		return tipo;
	}

	public void setTipo(String tipo) {
		this.tipo = tipo;
	}

	public SootField getField() {
		return field;
	}

	public void setField(SootField field) {
		this.field = field;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getCallback() {
		return callback;
	}

	public void setCallback(String callback) {
		this.callback = callback;
	}

	public SootMethod getCallbackMethod() {
		return callbackMethod;
	}

	public void setCallbackMethod(SootMethod callbackMethod) {
		this.callbackMethod = callbackMethod;
	}

	@Override
	public String toString() {
		return String.format("ViewInfo [id=%s, name=%s, callback=%s, textId=%s, tipo=%s, field=%s, callbackMethod=%s]", id, name, callback, textId, tipo, field, callbackMethod);
	}

}
