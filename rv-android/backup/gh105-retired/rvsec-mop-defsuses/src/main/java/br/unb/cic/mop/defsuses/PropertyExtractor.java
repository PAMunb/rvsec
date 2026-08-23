package br.unb.cic.mop.defsuses;

import java.util.ArrayList;
import java.util.List;

import com.github.javaparser.JavaParser;
import com.github.javaparser.ParseResult;
import com.github.javaparser.ast.expr.BinaryExpr;
import com.github.javaparser.ast.expr.Expression;
import com.github.javaparser.ast.expr.MethodCallExpr;

public class PropertyExtractor {

	private List<String> properties;
	private String methodPrefix;
	private String methodName;

	public PropertyExtractor(String methodPrefix, String methodName) {
		this.methodPrefix = methodPrefix;
		this.methodName = methodName;
	}

	public List<String> parse(String exp) {
		properties = new ArrayList<>();
		JavaParser parser = new JavaParser();

		ParseResult<Expression> expression = parser.parseExpression(exp);
//		System.out.println(">> " + expression);
//		System.out.println(expression.isSuccessful());
//		System.out.println(expression.getResult().isPresent());

		explore(expression.getResult().get());

		return properties;
	}

	private void explore(Expression expression) {
		if (expression instanceof BinaryExpr) {
			BinaryExpr exp = (BinaryExpr) expression;
//			System.out.println("BIN: " + exp);
			explore(exp);
		}
		if (expression instanceof MethodCallExpr) {
			MethodCallExpr exp = (MethodCallExpr) expression;
//			System.out.println("METHOD: " + exp);
			explore(exp);
		}
	}

	private void explore(BinaryExpr exp) {
		explore(exp.getLeft());
		explore(exp.getRight());
	}

	private void explore(MethodCallExpr exp) {
//		System.out.println("01: " + exp.getArguments());
//		System.out.println("02: " + exp.getChildNodes());
//		System.out.println("03: " + exp.getName());
//		System.out.println("04: " + exp.getScope().isPresent());
//		System.out.println("05: " + exp.getChildNodes().get(0));
//		System.out.println("06: "+exp.);

		if (methodPrefix.equals(exp.getChildNodes().get(0).toString()) && methodName.equals(exp.getNameAsString())) {
//			System.out.println("001: " + exp.getArguments().get(0).getChildNodes().get(1));
properties.add(exp.getArguments().get(0).getChildNodes().get(1).toString());
		}
	}

}
