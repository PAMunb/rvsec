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

public class V1 {

  static BlockStmt block(String src) throws Exception {
    JavaMOPParser p = new JavaMOPParser(new ByteArrayInputStream(src.getBytes(StandardCharsets.UTF_8)));
    return p.Block();
  }

  static MOPParameter param(String type, String name) {
    return new MOPParameter(0, 0, new BaseTypePattern(0, 0, type), name);
  }

  public static void main(String[] args) throws Exception {
    // --- montar do zero a menor spec possivel ---
    PackageDeclaration pkg = new PackageDeclaration(0, 0, new ArrayList<>(), new NameExpr(0, 0, "mop"));
    List<ImportDeclaration> imports = new ArrayList<>();
    imports.add(new ImportDeclaration(0, 0, new NameExpr(0, 0, "javax.crypto.spec.DHGenParameterSpec"), false, false));
    imports.add(new ImportDeclaration(0, 0, new NameExpr(0, 0, "br.unb.cic.mop.eh"), false, true));

    // event c1 after(int primeSize, int exponentSize) returning(DHGenParameterSpec s) : call(...) && args(...) { spec = s; }
    List<MOPParameter> evParams = new ArrayList<>();
    evParams.add(param("int", "primeSize"));
    evParams.add(param("int", "exponentSize"));
    List<MOPParameter> retVal = new ArrayList<>();
    retVal.add(param("DHGenParameterSpec", "s"));

    String pc = "call(public DHGenParameterSpec.new(int, int)) && args(primeSize, exponentSize)";

    EventDefinition ev = new EventDefinition(
        0, 0, "c1", null, "after", evParams, pc, block("{ spec = s; }"),
        true, retVal, false, new ArrayList<>(), false, false, false, false);

    List<EventDefinition> events = new ArrayList<>();
    events.add(ev);

    Formula ere = new Formula(0, 0, "ere", "c1");
    HashMap<String, BlockStmt> handlers = new LinkedHashMap<>();
    handlers.put("fail", block("{ System.out.println(\"fail\"); __RESET; }"));
    List<PropertyAndHandlers> props = new ArrayList<>();
    props.add(new PropertyAndHandlers(0, 0, ere, handlers));

    // declaracao de campo dentro da spec: "DHGenParameterSpec spec;"
    List<BodyDeclaration> decls = new ArrayList<>();

    List<MOPParameter> specParams = new ArrayList<>();
    specParams.add(param("DHGenParameterSpec", "s"));

    JavaMOPSpec spec = new JavaMOPSpec(pkg, 0, 0, 0, "V1MinimalSpec", specParams, null, decls, events, props);

    List<JavaMOPSpec> specs = new ArrayList<>();
    specs.add(spec);
    MOPSpecFile file = new MOPSpecFile(0, 0, pkg, imports, specs);

    DumpVisitor v = new DumpVisitor();
    file.accept(v, null);
    String out = v.getSource();
    System.out.println("=== DUMP ===");
    System.out.println(out);

    Path tmp = Paths.get(args[0]);
    Files.write(tmp, out.getBytes(StandardCharsets.UTF_8));
    System.out.println("=== REPARSE ===");
    MOPSpecFile again = SpecExtractor.parse(tmp.toFile());
    System.out.println("reparse OK, specs=" + again.getSpecs().size()
        + " events=" + again.getSpecs().get(0).getEvents().size()
        + " props=" + again.getSpecs().get(0).getPropertiesAndHandlers().size());
    DumpVisitor v2 = new DumpVisitor();
    again.accept(v2, null);
    String out2 = v2.getSource();
    System.out.println("=== IDEMPOTENTE? " + out.equals(out2) + " ===");
    if (!out.equals(out2)) System.out.println(out2);
  }
}
