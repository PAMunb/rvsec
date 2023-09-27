package br.unb.cic.mop.extractor.visitor;

import javamop.parser.ast.CompilationUnit;
import javamop.parser.ast.ImportDeclaration;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.Node;
import javamop.parser.ast.PackageDeclaration;
import javamop.parser.ast.TypeParameter;
import javamop.parser.ast.aspectj.ArgsPointCut;
import javamop.parser.ast.aspectj.BaseTypePattern;
import javamop.parser.ast.aspectj.CFlowPointCut;
import javamop.parser.ast.aspectj.CombinedPointCut;
import javamop.parser.ast.aspectj.CombinedTypePattern;
import javamop.parser.ast.aspectj.ConditionPointCut;
import javamop.parser.ast.aspectj.CountCondPointCut;
import javamop.parser.ast.aspectj.EndObjectPointCut;
import javamop.parser.ast.aspectj.EndProgramPointCut;
import javamop.parser.ast.aspectj.EndThreadPointCut;
import javamop.parser.ast.aspectj.FieldPattern;
import javamop.parser.ast.aspectj.FieldPointCut;
import javamop.parser.ast.aspectj.IDPointCut;
import javamop.parser.ast.aspectj.IFPointCut;
import javamop.parser.ast.aspectj.MethodPattern;
import javamop.parser.ast.aspectj.MethodPointCut;
import javamop.parser.ast.aspectj.NotPointCut;
import javamop.parser.ast.aspectj.NotTypePattern;
import javamop.parser.ast.aspectj.StartThreadPointCut;
import javamop.parser.ast.aspectj.TargetPointCut;
import javamop.parser.ast.aspectj.ThisPointCut;
import javamop.parser.ast.aspectj.ThreadBlockedPointCut;
import javamop.parser.ast.aspectj.ThreadNamePointCut;
import javamop.parser.ast.aspectj.ThreadPointCut;
import javamop.parser.ast.aspectj.WildcardParameter;
import javamop.parser.ast.aspectj.WithinPointCut;
import javamop.parser.ast.body.AnnotationDeclaration;
import javamop.parser.ast.body.AnnotationMemberDeclaration;
import javamop.parser.ast.body.ClassOrInterfaceDeclaration;
import javamop.parser.ast.body.ConstructorDeclaration;
import javamop.parser.ast.body.EmptyMemberDeclaration;
import javamop.parser.ast.body.EmptyTypeDeclaration;
import javamop.parser.ast.body.EnumConstantDeclaration;
import javamop.parser.ast.body.EnumDeclaration;
import javamop.parser.ast.body.FieldDeclaration;
import javamop.parser.ast.body.InitializerDeclaration;
import javamop.parser.ast.body.MethodDeclaration;
import javamop.parser.ast.body.Parameter;
import javamop.parser.ast.body.VariableDeclarator;
import javamop.parser.ast.body.VariableDeclaratorId;
import javamop.parser.ast.expr.ArrayAccessExpr;
import javamop.parser.ast.expr.ArrayCreationExpr;
import javamop.parser.ast.expr.ArrayInitializerExpr;
import javamop.parser.ast.expr.AssignExpr;
import javamop.parser.ast.expr.BinaryExpr;
import javamop.parser.ast.expr.BooleanLiteralExpr;
import javamop.parser.ast.expr.CastExpr;
import javamop.parser.ast.expr.CharLiteralExpr;
import javamop.parser.ast.expr.ClassExpr;
import javamop.parser.ast.expr.ConditionalExpr;
import javamop.parser.ast.expr.DoubleLiteralExpr;
import javamop.parser.ast.expr.EnclosedExpr;
import javamop.parser.ast.expr.FieldAccessExpr;
import javamop.parser.ast.expr.InstanceOfExpr;
import javamop.parser.ast.expr.IntegerLiteralExpr;
import javamop.parser.ast.expr.IntegerLiteralMinValueExpr;
import javamop.parser.ast.expr.LongLiteralExpr;
import javamop.parser.ast.expr.LongLiteralMinValueExpr;
import javamop.parser.ast.expr.MarkerAnnotationExpr;
import javamop.parser.ast.expr.MemberValuePair;
import javamop.parser.ast.expr.MethodCallExpr;
import javamop.parser.ast.expr.NameExpr;
import javamop.parser.ast.expr.NormalAnnotationExpr;
import javamop.parser.ast.expr.NullLiteralExpr;
import javamop.parser.ast.expr.ObjectCreationExpr;
import javamop.parser.ast.expr.QualifiedNameExpr;
import javamop.parser.ast.expr.SingleMemberAnnotationExpr;
import javamop.parser.ast.expr.StringLiteralExpr;
import javamop.parser.ast.expr.SuperExpr;
import javamop.parser.ast.expr.SuperMemberAccessExpr;
import javamop.parser.ast.expr.ThisExpr;
import javamop.parser.ast.expr.UnaryExpr;
import javamop.parser.ast.expr.VariableDeclarationExpr;
import javamop.parser.ast.mopspec.EventDefinition;
import javamop.parser.ast.mopspec.Formula;
import javamop.parser.ast.mopspec.JavaMOPSpec;
import javamop.parser.ast.mopspec.MOPParameter;
import javamop.parser.ast.mopspec.PropertyAndHandlers;
import javamop.parser.ast.stmt.AssertStmt;
import javamop.parser.ast.stmt.BlockStmt;
import javamop.parser.ast.stmt.BreakStmt;
import javamop.parser.ast.stmt.CatchClause;
import javamop.parser.ast.stmt.ContinueStmt;
import javamop.parser.ast.stmt.DoStmt;
import javamop.parser.ast.stmt.EmptyStmt;
import javamop.parser.ast.stmt.ExplicitConstructorInvocationStmt;
import javamop.parser.ast.stmt.ExpressionStmt;
import javamop.parser.ast.stmt.ForStmt;
import javamop.parser.ast.stmt.ForeachStmt;
import javamop.parser.ast.stmt.IfStmt;
import javamop.parser.ast.stmt.LabeledStmt;
import javamop.parser.ast.stmt.ReturnStmt;
import javamop.parser.ast.stmt.SwitchEntryStmt;
import javamop.parser.ast.stmt.SwitchStmt;
import javamop.parser.ast.stmt.SynchronizedStmt;
import javamop.parser.ast.stmt.ThrowStmt;
import javamop.parser.ast.stmt.TryStmt;
import javamop.parser.ast.stmt.TypeDeclarationStmt;
import javamop.parser.ast.stmt.WhileStmt;
import javamop.parser.ast.type.ClassOrInterfaceType;
import javamop.parser.ast.type.PrimitiveType;
import javamop.parser.ast.type.ReferenceType;
import javamop.parser.ast.type.VoidType;
import javamop.parser.ast.type.WildcardType;
import javamop.parser.ast.visitor.VoidVisitor;

public class VoidVisitorAdapter<T> implements VoidVisitor<T> {

	@Override
	public void visit(Node arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(MOPSpecFile arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(JavaMOPSpec arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(MOPParameter arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EventDefinition arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(PropertyAndHandlers arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(Formula arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(WildcardParameter arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ArgsPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(CombinedPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(NotPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ConditionPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(CountCondPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(FieldPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(MethodPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(TargetPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ThisPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(CFlowPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(IFPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(IDPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(WithinPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ThreadPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ThreadNamePointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ThreadBlockedPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EndProgramPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EndThreadPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EndObjectPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(StartThreadPointCut arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(FieldPattern arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(MethodPattern arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(CombinedTypePattern arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(NotTypePattern arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(BaseTypePattern arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(CompilationUnit arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(PackageDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ImportDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(TypeParameter arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ClassOrInterfaceDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EnumDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EmptyTypeDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EnumConstantDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(AnnotationDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(AnnotationMemberDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(FieldDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(VariableDeclarator arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(VariableDeclaratorId arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ConstructorDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(MethodDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(Parameter arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EmptyMemberDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(InitializerDeclaration arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ClassOrInterfaceType arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(PrimitiveType arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ReferenceType arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(VoidType arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(WildcardType arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ArrayAccessExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ArrayCreationExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ArrayInitializerExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(AssignExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(BinaryExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(CastExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ClassExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ConditionalExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EnclosedExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(FieldAccessExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(InstanceOfExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(StringLiteralExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(IntegerLiteralExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(LongLiteralExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(IntegerLiteralMinValueExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(LongLiteralMinValueExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(CharLiteralExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(DoubleLiteralExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(BooleanLiteralExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(NullLiteralExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(MethodCallExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(NameExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ObjectCreationExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(QualifiedNameExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(SuperMemberAccessExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ThisExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(SuperExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(UnaryExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(VariableDeclarationExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(MarkerAnnotationExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(SingleMemberAnnotationExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(NormalAnnotationExpr arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(MemberValuePair arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ExplicitConstructorInvocationStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(TypeDeclarationStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(AssertStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(BlockStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(LabeledStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(EmptyStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ExpressionStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(SwitchStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(SwitchEntryStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(BreakStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ReturnStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(IfStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(WhileStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ContinueStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(DoStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ForeachStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ForStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(ThrowStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(SynchronizedStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(TryStmt arg0, T arg1) {
		// TODO Auto-generated method stub

	}

	@Override
	public void visit(CatchClause arg0, T arg1) {
		// TODO Auto-generated method stub

	}

}
