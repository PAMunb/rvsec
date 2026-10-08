package br.unb.cic.rv.mutator;

import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.FiveRegisterInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.OffsetInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.RegisterRangeInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction21t;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction3rc;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

/**
 * The handler-stamp weave: which call sites are routed to {@code mop.RvsecStamp},
 * which are left alone, and the call inserted after Compose's node population.
 */
class StampWeaverTest {

    private static final String CLICK_SIG = "Landroid/view/View$OnClickListener;";
    private static final String LONG_SIG = "Landroid/view/View$OnLongClickListener;";
    private static final String DELEGATE_SIG = "Landroid/view/View$AccessibilityDelegate;";
    private static final String COMPOSE =
            "Landroidx/compose/ui/platform/AndroidComposeViewAccessibilityDelegateCompat;";

    private static Path androidJar;

    @BeforeAll
    static void resolveAndroidJar() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null || home.isEmpty()) return;
        Path platforms = Path.of(home, "platforms", "android-30", "android.jar");
        if (Files.isRegularFile(platforms)) {
            androidJar = platforms;
            return;
        }
        try (Stream<Path> levels = Files.list(Path.of(home, "platforms"))) {
            androidJar = levels.map(p -> p.resolve("android.jar"))
                    .filter(Files::isRegularFile).findFirst().orElse(null);
        } catch (IOException ex) {
            androidJar = null;
        }
    }

    static boolean hasAndroidJar() {
        return androidJar != null;
    }

    private static MethodReference ref(String owner, String name, String param) {
        return new ImmutableMethodReference(owner, name, List.of(param), "V");
    }

    private static ImmutableInstruction invoke(Opcode op, String owner, String name, String param) {
        return new ImmutableInstruction35c(op, 2, 1, 2, 0, 0, 0, ref(owner, name, param));
    }

    private static Method method(String owner, String name, int registers, List<ImmutableInstruction> body) {
        List<ImmutableInstruction> code = new ArrayList<>(body);
        code.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        return new ImmutableMethod(owner, name, List.of(), "V", AccessFlags.PUBLIC.getValue(),
                null, null, new ImmutableMethodImplementation(registers, code, null, null));
    }

    private static ClassDef cls(String type, String superType, Method... methods) {
        return new ImmutableClassDef(type, AccessFlags.PUBLIC.getValue(), superType, null, null,
                null, null, List.of(methods));
    }

    private static List<Instruction> body(DexFile dex, String owner, String name) {
        for (ClassDef c : dex.getClasses()) {
            if (!c.getType().equals(owner)) continue;
            for (Method m : c.getMethods()) {
                if (!m.getName().equals(name)) continue;
                List<Instruction> out = new ArrayList<>();
                m.getImplementation().getInstructions().forEach(out::add);
                return out;
            }
        }
        throw new AssertionError("no " + owner + "->" + name);
    }

    private static MethodReference target(Instruction ins) {
        return (MethodReference) ((ReferenceInstruction) ins).getReference();
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void viewSettersAreRoutedAndOtherSitesLeftAlone() {
        String app = "Lcom/example/Screen;";
        String myView = "Lcom/example/MyView;";
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                cls(app, "Ljava/lang/Object;", method(app, "bind", 3, List.of(
                        invoke(Opcode.INVOKE_VIRTUAL, "Landroid/widget/Button;", "setOnClickListener", CLICK_SIG),
                        new ImmutableInstruction3rc(Opcode.INVOKE_VIRTUAL_RANGE, 1, 2,
                                ref(myView, "setOnLongClickListener", LONG_SIG)),
                        invoke(Opcode.INVOKE_VIRTUAL, "Landroid/view/View;", "setAccessibilityDelegate", DELEGATE_SIG),
                        invoke(Opcode.INVOKE_VIRTUAL, "Lcom/example/NotAView;", "setOnClickListener", CLICK_SIG),
                        invoke(Opcode.INVOKE_VIRTUAL, "Landroid/view/View;", "setOnFocusChangeListener",
                                "Landroid/view/View$OnFocusChangeListener;")))),
                cls(myView, "Landroid/view/View;", method(myView, "setOnClickListener", 3, List.of(
                        invoke(Opcode.INVOKE_SUPER, "Landroid/view/View;", "setOnClickListener", CLICK_SIG)))),
                cls("Lcom/example/NotAView;", "Ljava/lang/Object;")));

        DexFileMutator mutator = new DexFileMutator(dex);
        StampWeaver.StampReport report = new StampWeaver(
                new InheritanceResolver(new AndroidClassIndex(androidJar), dex))
                .weave(dex, mutator::forMethod);

        assertEquals(new StampWeaver.StampReport(1, 1, 1, 0, 1, 1), report);
        DexFile woven = mutator.toDexFile();
        List<Instruction> bind = body(woven, app, "bind");
        assertEquals(6, bind.size(), "the rewrite is size-stable");

        assertEquals(Opcode.INVOKE_STATIC, bind.get(0).getOpcode());
        assertEquals(new ImmutableMethodReference(StampWeaver.STAMP_CLASS_DESC, "setOnClickListener",
                List.of("Landroid/view/View;", CLICK_SIG), "V"), target(bind.get(0)));
        FiveRegisterInstruction first = (FiveRegisterInstruction) bind.get(0);
        assertEquals(List.of(2, 1, 2), List.of(first.getRegisterCount(),
                first.getRegisterC(), first.getRegisterD()), "registers are kept");

        assertEquals(Opcode.INVOKE_STATIC_RANGE, bind.get(1).getOpcode());
        assertEquals("setOnLongClickListener", target(bind.get(1)).getName());
        assertEquals(1, ((RegisterRangeInstruction) bind.get(1)).getStartRegister());

        assertEquals("setAccessibilityDelegate", target(bind.get(2)).getName());
        assertEquals(StampWeaver.STAMP_CLASS_DESC, target(bind.get(2)).getDefiningClass());

        assertEquals(Opcode.INVOKE_VIRTUAL, bind.get(3).getOpcode(), "owner is not a View");
        assertEquals(Opcode.INVOKE_VIRTUAL, bind.get(4).getOpcode(), "not a stamped setter");

        List<Instruction> override = body(woven, myView, "setOnClickListener");
        assertEquals(Opcode.INVOKE_SUPER, override.get(0).getOpcode(), "invoke-super is left alone");
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void composeNodePopulationIsFollowedByTheStampCall() {
        MethodReference populate = new ImmutableMethodReference(COMPOSE,
                "populateAccessibilityNodeInfoProperties",
                List.of("I", "Landroidx/core/view/accessibility/AccessibilityNodeInfoCompat;",
                        "Landroidx/compose/ui/semantics/SemanticsNode;"), "V");
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                cls(COMPOSE, "Ljava/lang/Object;",
                        method(COMPOSE, "createNodeInfo", 10, List.of(
                                new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 4, 8, 9, 0, 3, 0,
                                        populate))),
                        method(COMPOSE, "createNodeInfoRange", 40, List.of(
                                new ImmutableInstruction3rc(Opcode.INVOKE_DIRECT_RANGE, 20, 4,
                                        populate))))));

        DexFileMutator mutator = new DexFileMutator(dex);
        StampWeaver.StampReport report = new StampWeaver(
                new InheritanceResolver(new AndroidClassIndex(androidJar), dex))
                .weave(dex, mutator::forMethod);

        assertEquals(2, report.composeSites());
        DexFile woven = mutator.toDexFile();
        MethodReference helper = new ImmutableMethodReference(StampWeaver.STAMP_CLASS_DESC,
                "composeNode", List.of("Ljava/lang/Object;", "Ljava/lang/Object;"), "V");

        List<Instruction> small = body(woven, COMPOSE, "createNodeInfo");
        assertEquals(3, small.size());
        assertEquals(Opcode.INVOKE_DIRECT, small.get(0).getOpcode(), "the population call stays");
        assertEquals(Opcode.INVOKE_STATIC, small.get(1).getOpcode());
        assertEquals(helper, target(small.get(1)));
        FiveRegisterInstruction stamp = (FiveRegisterInstruction) small.get(1);
        assertEquals(List.of(2, 0, 3), List.of(stamp.getRegisterCount(),
                stamp.getRegisterC(), stamp.getRegisterD()), "the info and node registers");

        List<Instruction> range = body(woven, COMPOSE, "createNodeInfoRange");
        assertEquals(Opcode.INVOKE_STATIC_RANGE, range.get(1).getOpcode());
        RegisterRangeInstruction r = (RegisterRangeInstruction) range.get(1);
        assertEquals(List.of(22, 2), List.of(r.getStartRegister(), r.getRegisterCount()));
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void invokeSuperAndNonViewOwnersAreCountedOnceAndLeftUnchanged() {
        String myView = "Lcom/example/MyView;";
        List<ImmutableInstruction> original = List.of(
                invoke(Opcode.INVOKE_SUPER, "Landroid/view/View;", "setOnClickListener", CLICK_SIG),
                new ImmutableInstruction3rc(Opcode.INVOKE_SUPER_RANGE, 1, 2,
                        ref("Landroid/view/View;", "setOnLongClickListener", LONG_SIG)),
                invoke(Opcode.INVOKE_VIRTUAL, "Landroid/app/Dialog;", "setOnClickListener", CLICK_SIG),
                invoke(Opcode.INVOKE_VIRTUAL, "Lcom/example/Unresolved;", "setAccessibilityDelegate",
                        DELEGATE_SIG));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                cls(myView, "Landroid/view/View;", method(myView, "bind", 3, original))));

        DexFileMutator mutator = new DexFileMutator(dex);
        StampWeaver.StampReport report = new StampWeaver(
                new InheritanceResolver(new AndroidClassIndex(androidJar), dex))
                .weave(dex, mutator::forMethod);

        assertEquals(new StampWeaver.StampReport(0, 0, 0, 0, 2, 2), report,
                "two invoke-super sites, one framework non-View owner, one unresolvable owner");
        List<Instruction> bind = body(mutator.toDexFile(), myView, "bind");
        assertEquals(original.size() + 1, bind.size());
        for (int i = 0; i < original.size(); i++) {
            assertEquals(original.get(i).getOpcode(), bind.get(i).getOpcode(), "opcode of #" + i);
            assertEquals(target(original.get(i)), target(bind.get(i)), "reference of #" + i);
        }
    }

    /**
     * INV-INS-176: a setter's name and descriptor reached through any opcode other than
     * {@code invoke-virtual} / {@code invoke-super} names an interface, private or static
     * method, so the site is left unchanged and counted nowhere, even with a {@code View} owner.
     */
    @Test
    @EnabledIf("hasAndroidJar")
    void otherInvokeOpcodesAreLeftUnchangedAndCountedNowhere() {
        String myView = "Lcom/example/MyView;";
        String view = "Landroid/view/View;";
        List<ImmutableInstruction> original = List.of(
                invoke(Opcode.INVOKE_INTERFACE, view, "setOnClickListener", CLICK_SIG),
                invoke(Opcode.INVOKE_DIRECT, view, "setOnLongClickListener", LONG_SIG),
                new ImmutableInstruction35c(Opcode.INVOKE_STATIC, 1, 2, 0, 0, 0, 0,
                        ref(view, "setAccessibilityDelegate", DELEGATE_SIG)),
                new ImmutableInstruction3rc(Opcode.INVOKE_STATIC_RANGE, 2, 1,
                        ref(view, "setOnClickListener", CLICK_SIG)));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                cls(myView, view, method(myView, "bind", 3, original))));

        DexFileMutator mutator = new DexFileMutator(dex);
        StampWeaver.StampReport report = new StampWeaver(
                new InheritanceResolver(new AndroidClassIndex(androidJar), dex))
                .weave(dex, mutator::forMethod);

        assertEquals(new StampWeaver.StampReport(0, 0, 0, 0, 0, 0), report,
                "invoke-interface, invoke-direct, invoke-static and invoke-static/range are not counted");
        List<Instruction> bind = body(mutator.toDexFile(), myView, "bind");
        assertEquals(original.size() + 1, bind.size());
        for (int i = 0; i < original.size(); i++) {
            assertEquals(original.get(i).getOpcode(), bind.get(i).getOpcode(), "opcode of #" + i);
            assertEquals(target(original.get(i)), target(bind.get(i)), "reference of #" + i);
        }
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void rangeSetterBecomesStaticRangeWithTheSameRegisters() {
        String app = "Lcom/example/Screen;";
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                cls(app, "Ljava/lang/Object;", method(app, "bind", 8, List.of(
                        new ImmutableInstruction3rc(Opcode.INVOKE_VIRTUAL_RANGE, 5, 2,
                                ref("Landroid/widget/TextView;", "setOnLongClickListener", LONG_SIG)))))));

        DexFileMutator mutator = new DexFileMutator(dex);
        StampWeaver.StampReport report = new StampWeaver(
                new InheritanceResolver(new AndroidClassIndex(androidJar), dex))
                .weave(dex, mutator::forMethod);

        assertEquals(new StampWeaver.StampReport(0, 1, 0, 0, 0, 0), report);
        Instruction rewritten = body(mutator.toDexFile(), app, "bind").get(0);
        assertEquals(Opcode.INVOKE_STATIC_RANGE, rewritten.getOpcode());
        assertEquals(new ImmutableMethodReference(StampWeaver.STAMP_CLASS_DESC, "setOnLongClickListener",
                List.of("Landroid/view/View;", LONG_SIG), "V"), target(rewritten));
        RegisterRangeInstruction r = (RegisterRangeInstruction) rewritten;
        assertEquals(List.of(5, 2), List.of(r.getStartRegister(), r.getRegisterCount()));
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void composeRangePopulationIsFollowedByTheStampCallOverInfoAndNode() {
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                cls(COMPOSE, "Ljava/lang/Object;",
                        method(COMPOSE, "createNodeInfo", 12, List.of(
                                new ImmutableInstruction3rc(Opcode.INVOKE_VIRTUAL_RANGE, 7, 4,
                                        populateRef(COMPOSE)))))));

        DexFileMutator mutator = new DexFileMutator(dex);
        StampWeaver.StampReport report = new StampWeaver(
                new InheritanceResolver(new AndroidClassIndex(androidJar), dex))
                .weave(dex, mutator::forMethod);

        assertEquals(new StampWeaver.StampReport(0, 0, 0, 1, 0, 0), report);
        List<Instruction> woven = body(mutator.toDexFile(), COMPOSE, "createNodeInfo");
        assertEquals(3, woven.size());
        assertEquals(Opcode.INVOKE_VIRTUAL_RANGE, woven.get(0).getOpcode(), "the population call stays");
        assertEquals(Opcode.INVOKE_STATIC_RANGE, woven.get(1).getOpcode());
        assertEquals("composeNode", target(woven.get(1)).getName());
        RegisterRangeInstruction r = (RegisterRangeInstruction) woven.get(1);
        assertEquals(List.of(9, 2), List.of(r.getStartRegister(), r.getRegisterCount()),
                "start + 2 .. start + 3: the info and node registers");
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void composeOwnerDifferingByOneCharacterIsNotMatched() {
        String renamed =
                "Landroidx/compose/ui/platform/AndroidComposeViewAccessibilityDelegateCompaT;";
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                cls(renamed, "Ljava/lang/Object;",
                        method(renamed, "createNodeInfo", 10, List.of(
                                new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 4, 8, 9, 0, 3, 0,
                                        populateRef(renamed)))))));

        DexFileMutator mutator = new DexFileMutator(dex);
        StampWeaver.StampReport report = new StampWeaver(
                new InheritanceResolver(new AndroidClassIndex(androidJar), dex))
                .weave(dex, mutator::forMethod);

        assertEquals(new StampWeaver.StampReport(0, 0, 0, 0, 0, 0), report);
        assertFalse(mutator.hasAnyMutations(), "no method body is materialised or changed");
        List<Instruction> body = body(mutator.toDexFile(), renamed, "createNodeInfo");
        assertEquals(2, body.size());
        assertEquals(Opcode.INVOKE_DIRECT, body.get(0).getOpcode());
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void rewriteKeepsTheCodeUnitSizeAndBranchOffsets() {
        String app = "Lcom/example/Screen;";
        List<ImmutableInstruction> original = List.of(
                // Branches over the three setter calls to the trailing return-void:
                // 2 (if-eqz) + 3 + 3 + 3 code units.
                new ImmutableInstruction21t(Opcode.IF_EQZ, 1, 11),
                invoke(Opcode.INVOKE_VIRTUAL, "Landroid/widget/Button;", "setOnClickListener", CLICK_SIG),
                new ImmutableInstruction3rc(Opcode.INVOKE_VIRTUAL_RANGE, 1, 2,
                        ref("Landroid/widget/ImageView;", "setOnLongClickListener", LONG_SIG)),
                invoke(Opcode.INVOKE_VIRTUAL, "Landroid/view/View;", "setAccessibilityDelegate",
                        DELEGATE_SIG));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                cls(app, "Ljava/lang/Object;", method(app, "bind", 3, original))));
        int before = codeUnits(body(dex, app, "bind"));

        DexFileMutator mutator = new DexFileMutator(dex);
        StampWeaver.StampReport report = new StampWeaver(
                new InheritanceResolver(new AndroidClassIndex(androidJar), dex))
                .weave(dex, mutator::forMethod);

        assertEquals(new StampWeaver.StampReport(1, 1, 1, 0, 0, 0), report);
        List<Instruction> bind = body(mutator.toDexFile(), app, "bind");
        assertEquals(before, codeUnits(bind), "the rewritten method keeps its code-unit size");
        assertEquals(Opcode.IF_EQZ, bind.get(0).getOpcode());
        assertEquals(11, ((OffsetInstruction) bind.get(0)).getCodeOffset(),
                "the branch still lands on the return-void");
    }

    private static MethodReference populateRef(String owner) {
        return new ImmutableMethodReference(owner, "populateAccessibilityNodeInfoProperties",
                List.of("I", "Landroidx/core/view/accessibility/AccessibilityNodeInfoCompat;",
                        "Landroidx/compose/ui/semantics/SemanticsNode;"), "V");
    }

    private static int codeUnits(List<Instruction> instructions) {
        int units = 0;
        for (Instruction ins : instructions) units += ins.getCodeUnits();
        return units;
    }
}
