package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.WrapperEmitter;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;

/**
 * INV-INS-31 phase 2: when an instance wrapper is registered for a parent
 * class (e.g. {@code Base.doFinal([B)[B}) and the APK declares a subclass
 * {@code Sub extends Base}, calling
 * {@link DexWeaver#expandWrapperReplacementsForApk(InheritanceResolver)} must
 * register an additional lookup key under the subclass descriptor that
 * resolves to the SAME wrapper {@link MethodReference} as the parent key.
 *
 * <p>The test builds a synthetic 2-class {@link DexFile} (no method bodies
 * needed — only the type / superclass relationship matters for the resolver),
 * runs the resolver+expand cycle, and asserts both keys are present and
 * resolve to the same ref. Static wrappers are also exercised to confirm
 * they are NOT expanded (out of scope per the contract).
 */
class DexWeaverWrapperSubtypeTest {

    private static final String BASE_DESC = "LBase;";
    private static final String SUB_DESC  = "LSub;";
    private static final String BASE_FQN  = "Base";

    @Test
    void expandRegistersSubtypeKeyForInstanceWrapper() throws Exception {
        // 1. Synthetic DEX: Base, Sub extends Base. No methods required —
        //    InheritanceResolver only walks the type → superclass chain.
        ClassDef base = new ImmutableClassDef(
                BASE_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(), null,
                null, null, null);
        ClassDef sub = new ImmutableClassDef(
                SUB_DESC, AccessFlags.PUBLIC.getValue(),
                BASE_DESC,
                Collections.emptyList(), null,
                null, null, null);
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(base, sub));

        // 2. InheritanceResolver over the synthetic DEX (no real android.jar
        //    needed — the relationship lives entirely in APK classes).
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        // 3. Wrapper for Base.doFinal([B)[B (instance, isStatic=false). The
        //    isStatic flag is the gate: subtype expansion only fires for
        //    instance wrappers.
        WrapperEmitter.WrapperEntry entry = new WrapperEmitter.WrapperEntry(
                "Base_doFinal",
                BASE_FQN,
                "doFinal",
                List.of("byte[]"),
                "byte[]",
                false /* instance */);
        DexWeaver weaver = new DexWeaver(
                new EmitterDispatch(), new RegisterAllocator(), List.of(entry));

        // 4. Sanity: parent key present pre-expansion, subtype key absent.
        Map<String, MethodReference> table = readReplacements(weaver);
        String parentKey = BASE_DESC + "#doFinal([B)[B";
        String subKey    = SUB_DESC  + "#doFinal([B)[B";
        assertNotNull(table.get(parentKey),
                "parent FQN key must be registered at construction time");
        assertNull(table.get(subKey),
                "subtype key must NOT be present before expansion");

        // 5. Expand and verify subtype key now resolves to the SAME wrapper
        //    MethodReference (same instance — we reuse the parent's ref).
        weaver.expandWrapperReplacementsForApk(inheritance);
        table = readReplacements(weaver);
        MethodReference parentRef = table.get(parentKey);
        MethodReference subRef    = table.get(subKey);
        assertNotNull(parentRef, "parent key still present after expansion");
        assertNotNull(subRef,    "subtype key registered after expansion");
        assertSame(parentRef, subRef,
                "subtype key must point at the SAME wrapper MethodReference as the parent");

        // 6. Idempotency: a second expand call must not duplicate keys.
        int sizeBefore = table.size();
        weaver.expandWrapperReplacementsForApk(inheritance);
        table = readReplacements(weaver);
        assertEquals(sizeBefore, table.size(),
                "expandWrapperReplacementsForApk must be idempotent");
    }

    @Test
    void staticWrappersAreNotExpandedToSubtypes() throws Exception {
        // Same fixture, but the wrapper is a static — subtype expansion must
        // skip it (an invoke-static MyCipher.create(...) resolves to MyCipher's
        // own static, not Cipher's, so a subtype redirect would over-match).
        ClassDef base = new ImmutableClassDef(
                BASE_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(), null, null, null, null);
        ClassDef sub = new ImmutableClassDef(
                SUB_DESC, AccessFlags.PUBLIC.getValue(),
                BASE_DESC,
                Collections.emptyList(), null, null, null, null);
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(base, sub));
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        WrapperEmitter.WrapperEntry staticEntry = new WrapperEmitter.WrapperEntry(
                "Base_create",
                BASE_FQN,
                "create",
                List.of(),
                "Base",
                true /* static */);
        DexWeaver weaver = new DexWeaver(
                new EmitterDispatch(), new RegisterAllocator(), List.of(staticEntry));

        weaver.expandWrapperReplacementsForApk(inheritance);

        Map<String, MethodReference> table = readReplacements(weaver);
        assertNotNull(table.get(BASE_DESC + "#create()LBase;"),
                "static wrapper's parent key must remain registered");
        assertNull(table.get(SUB_DESC + "#create()LBase;"),
                "static wrapper must NOT be aliased to a subtype key");
    }

    /** Reflectively read the wrapperReplacements map (package-private would also work). */
    @SuppressWarnings("unchecked")
    private static Map<String, MethodReference> readReplacements(DexWeaver w) throws Exception {
        Field f = DexWeaver.class.getDeclaredField("wrapperReplacements");
        f.setAccessible(true);
        return (Map<String, MethodReference>) f.get(w);
    }
}
