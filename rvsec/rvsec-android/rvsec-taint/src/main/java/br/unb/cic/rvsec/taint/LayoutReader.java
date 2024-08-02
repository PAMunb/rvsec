package br.unb.cic.rvsec.taint;

import soot.Scene;
import soot.SootClass;

public class LayoutReader {
	private SootClass rLayout;

	public SootClass getRLayout() {
		if(rLayout == null) {
			for (SootClass appClass : Scene.v().getApplicationClasses()) {
				if (appClass.getName().endsWith("R$layout")) {
					rLayout = appClass;
					break;
				}
			}
		}
		return rLayout;
//		for (SootClass appClass : Scene.v().getApplicationClasses()) {
//			if (appClass.getName().endsWith("R$layout")) {
//				SootClass layoutClass = appClass;
//				for (SootField layoutField : layoutClass.getFields()) {
//					if (layoutField.isFinal() && layoutField.isStatic()) {
//						String fieldName = layoutField.getName();
//						Tag fieldTag = layoutField.getTag("IntegerConstantValueTag");
//						if (fieldTag != null) {
//							String tagString = fieldTag.toString();
//							String fieldValue = tagString.split(" ")[1];
//							if (layoutValue.equals(fieldValue)) {
//								return fieldName;
//							}
//						}
//					}
//				}
//			}
//		}
	}

}
