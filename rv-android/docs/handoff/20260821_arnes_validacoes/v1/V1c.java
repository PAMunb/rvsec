import javamop.parser.SpecExtractor;
import javamop.parser.ast.*;
import javamop.parser.ast.aspectj.*;
import javamop.parser.ast.body.BodyDeclaration;
import javamop.parser.ast.expr.NameExpr;
import javamop.parser.ast.mopspec.*;
import javamop.parser.ast.stmt.BlockStmt;
import javamop.parser.ast.visitor.DumpVisitor;
import javamop.parser.main_parser.JavaMOPParser;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** V1c: cobre tudo que o gerador do V2 precisa - campos, creation, condition, dois handlers. */
public class V1c {

  static JavaMOPParser p(String src) {
    return new JavaMOPParser(new ByteArrayInputStream(src.getBytes(StandardCharsets.UTF_8)));
  }
  static BlockStmt block(String src) throws Exception { return p(src).Block(); }
  static List<BodyDeclaration> bodyDecl(String src) throws Exception { List<BodyDeclaration> l = new ArrayList<>(); l.add(p(src).ClassOrInterfaceBodyDeclaration(false)); return l; }
  static MOPParameter param(String type, String name) {
    return new MOPParameter(0, 0, new BaseTypePattern(0, 0, type), name);
  }

  public static void main(String[] args) throws Exception {
    PackageDeclaration pkg = new PackageDeclaration(0, 0, new ArrayList<>(), new NameExpr(0, 0, "mop"));
    List<ImportDeclaration> imports = new ArrayList<>(List.of(
        new ImportDeclaration(0, 0, new NameExpr(0, 0, "javax.crypto.spec.DHGenParameterSpec"), false, false),
        new ImportDeclaration(0, 0, new NameExpr(0, 0, "br.unb.cic.mop.eh"), false, true),
        new ImportDeclaration(0, 0, new NameExpr(0, 0, "br.unb.cic.mop.ExecutionContext"), false, false),
        new ImportDeclaration(0, 0, new NameExpr(0, 0, "br.unb.cic.mop.Property"), false, false)));

    List<BodyDeclaration> decls = bodyDecl("DHGenParameterSpec spec;");

    List<MOPParameter> evParams = new ArrayList<>(List.of(param("int", "primeSize"), param("int", "exponentSize")));
    List<MOPParameter> retVal = new ArrayList<>(List.of(param("DHGenParameterSpec", "s")));
    String pc = "call(public DHGenParameterSpec.new(int, int)) && args(primeSize, exponentSize) && condition(exponentSize < primeSize)";

    EventDefinition ev = new EventDefinition(
        0, 0, "c1", null, "after", evParams, pc, block("{ spec = s; }"),
        true, retVal, false, new ArrayList<>(), false, /*creation*/ true, false, false);

    Formula ere = new Formula(0, 0, "ere", "c1");
    HashMap<String, BlockStmt> handlers = new LinkedHashMap<>();
    handlers.put("fail", block("{ ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, \"V1bSpec\", \"\" + __LOC, \"v=1 code=X-ORDER-00 ev=\" + __EVENTNAME)); __RESET; }"));
    handlers.put("match", block("{ ExecutionContext.instance().setProperty(Property.PREPARED_DH, spec); ExecutionContext.instance().setObjectAsInAcceptingState(spec); }"));
    List<PropertyAndHandlers> props = new ArrayList<>(List.of(new PropertyAndHandlers(0, 0, ere, handlers)));

    List<MOPParameter> specParams = new ArrayList<>(List.of(param("DHGenParameterSpec", "s")));
    JavaMOPSpec spec = new JavaMOPSpec(pkg, 0, 0, 0, "V1bSpec", specParams, null, decls, List.of(ev), props);
    MOPSpecFile file = new MOPSpecFile(0, 0, pkg, imports, List.of(spec));

    DumpVisitor v = new DumpVisitor(); file.accept(v, null);
    String out = v.getSource();
    System.out.println("=== DUMP ===\n" + out);
    Path tmp = Paths.get(args[0]);
    Files.write(tmp, out.getBytes(StandardCharsets.UTF_8));
    MOPSpecFile again = SpecExtractor.parse(tmp.toFile());
    JavaMOPSpec s2 = again.getSpecs().get(0);
    System.out.println("=== REPARSE OK ===");
    System.out.println("name=" + s2.getName() + " params=" + s2.getParameters().size()
        + " decls=" + (s2.getDeclarations()==null?"null":s2.getDeclarations().size())
        + " events=" + s2.getEvents().size()
        + " creation=" + s2.getEvents().get(0).isCreationEvent()
        + " condition=[" + s2.getEvents().get(0).getCondition() + "]"
        + " handlers=" + s2.getPropertiesAndHandlers().get(0).getHandlers().keySet());
    DumpVisitor v2 = new DumpVisitor(); again.accept(v2, null);
    System.out.println("=== IDEMPOTENTE? " + out.equals(v2.getSource()) + " ===");
  }
}
