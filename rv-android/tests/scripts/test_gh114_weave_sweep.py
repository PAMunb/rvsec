"""The weave sweep counts what it says it counts, on inputs built here.

`scripts/gh114_weave_sweep.py` is the before/after measure of four weaver repairs
(INV-INS-159 to INV-INS-162). Its numbers are only as good as three readings: of the aspect
descriptor (which events are `before`, what arity each `args(...)` clause demands, which
owners carry `+`), of `dexdump -d` text (instructions, branch and switch targets, invoke
references), and of binary structures `dexdump` does not print (switch payloads, the
`class_defs` of a DEX, the ancestry in `android.jar`).

The unit half feeds each reading a synthetic input. The end-to-end half compiles a tiny
application and a tiny monitor with `javac` and `d8`, packs them as an APK, and runs the
real `dexdump` through `scan_apk`; it skips when the Android build tools are absent. No
file of any corpus is read.
"""

from __future__ import annotations

import collections
import json
import os
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import gh114_weave_sweep as sweep

MONITOR = "Lmop/MultiSpec_1RuntimeMonitor;"


def _descriptor_json(tmp_path: Path) -> Path:
    """An aspect descriptor with one `before` event, an arity pair and a `Key+` owner."""
    call = "MultiSpec_1RuntimeMonitor.{}".format
    document = {
        "package": "package mop;",
        "baseAspectExclusions": ["java..*", "javax..*", "mop..*"],
        "advices": [
            {
                "name": "CipherSpec_i2",
                "position": "before",
                "expression": "call(public void Cipher.init(int, Key, ..)) && args(mode, key, ..) && target(c)",
                "monitorCalls": [{"method": call("CipherSpec_i2Event")}],
            },
            {
                "name": "CipherSpec_g",
                "position": "after",
                "expression": "call(public static Cipher Cipher.getInstance(String)) && args(alg)",
                "monitorCalls": [{"method": call("CipherSpec_gEvent")}],
            },
            {
                "name": "CipherSpec_g2",
                "position": "after",
                "expression": "call(public static Cipher Cipher.getInstance(String, ..)) && args(alg, *)",
                "monitorCalls": [{"method": call("CipherSpec_g2Event")}],
            },
            {
                "name": "KeySpec_ge",
                "position": "after",
                "expression": "call(public byte[] Key+.getEncoded()) && target(k)",
                "monitorCalls": [{"method": call("KeySpec_geEvent")}],
            },
        ],
    }
    path = tmp_path / "MultiSpec_1MonitorAspect.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _class_file(name: str, superclass: str | None, interfaces: list[str]) -> bytes:
    """A minimal class file: constant pool of Utf8/Class pairs, header, no members."""
    pool = bytearray()
    index = {}

    def class_ref(internal: str) -> int:
        if internal not in index:
            count = 1 + 2 * len(index)
            encoded = internal.encode()
            pool.extend(struct.pack(">BH", 1, len(encoded)) + encoded)
            pool.extend(struct.pack(">BH", 7, count))
            index[internal] = count + 1
        return index[internal]

    this_idx = class_ref(name)
    super_idx = class_ref(superclass) if superclass else 0
    interface_idx = [class_ref(i) for i in interfaces]
    # A long constant takes two slots; the parser must skip both.
    pool.extend(struct.pack(">BQ", 5, 7))
    slots = 1 + 2 * len(index) + 2
    header = struct.pack(">IHHH", 0xCAFEBABE, 0, 52, slots)
    body = struct.pack(">HHHH", 0x0601, this_idx, super_idx, len(interface_idx))
    body += b"".join(struct.pack(">H", i) for i in interface_idx)
    return header + bytes(pool) + body + struct.pack(">HHH", 0, 0, 0)


def _android_jar(tmp_path: Path) -> Path:
    path = tmp_path / "android.jar"
    with zipfile.ZipFile(path, "w") as jar:
        jar.writestr(
            "java/security/Key.class",
            _class_file(
                "java/security/Key", "java/lang/Object", ["java/io/Serializable"]
            ),
        )
        jar.writestr(
            "javax/crypto/SecretKey.class",
            _class_file(
                "javax/crypto/SecretKey", "java/lang/Object", ["java/security/Key"]
            ),
        )
    return path


class TestDescriptor:
    """What the sweep reads from the aspect descriptor."""

    @pytest.mark.parametrize(
        ("expression", "clauses"),
        [
            ("call(* A.f(String)) && args(alg)", ((1, False),)),
            ("call(* A.f(String, ..)) && args(alg, *)", ((2, False),)),
            ("call(* A.f(int, Key, ..)) && args(mode, key, ..)", ((2, True),)),
            ("call(* A.f(..)) && args(..)", ((0, True),)),
            ("call(* A.f()) && target(a)", ()),
        ],
    )
    def test_args_clauses(self, expression, clauses):
        assert sweep.args_clauses(expression) == clauses

    def test_arity_rule_of_every_form(self):
        """`k` positions need exactly `k`; a trailing `..` needs at least `k`; no clause, anything."""
        assert sweep.arity_compatible(((2, False),), 2)
        assert not sweep.arity_compatible(((2, False),), 1)
        assert not sweep.arity_compatible(((2, False),), 3)
        assert sweep.arity_compatible(((1, True),), 1)
        assert sweep.arity_compatible(((1, True),), 4)
        assert not sweep.arity_compatible(((1, True),), 0)
        assert sweep.arity_compatible((), 7)

    def test_load_descriptor(self, tmp_path):
        descriptor = sweep.load_descriptor(_descriptor_json(tmp_path))

        assert descriptor.monitor_class == MONITOR
        assert descriptor.before_events == {"CipherSpec_i2Event"}
        assert descriptor.events["CipherSpec_g2Event"].args_clauses == ((2, False),)
        assert descriptor.events["KeySpec_geEvent"].owners == (("Key", True),)
        assert descriptor.excluded_prefixes == ("Ljava/", "Ljavax/", "Lmop/")


class TestBinaryReadings:
    """Structures `dexdump` does not print."""

    def test_parameter_count_and_invoke_ref(self):
        assert (
            sweep.parameter_count("(I[BLjava/lang/String;[[Ljava/lang/Object;J)V") == 5
        )
        operands = " {v1, v0, v2}, Ljavax/crypto/Cipher;.init:(ILjava/security/Key;)V // method@0008"
        assert sweep.invoke_ref(operands) == (
            "Ljavax/crypto/Cipher;",
            "init",
            "(ILjava/security/Key;)V",
        )
        assert (
            sweep.invoke_ref(" {v0}, [B.clone:()Ljava/lang/Object; // method@0001")[0]
            == "[B"
        )

    def test_packed_and_sparse_switch_payloads(self):
        # A switch at address 0x10, file offset 0x100, payload at address 0x20.
        dex = bytearray(0x200)
        struct.pack_into("<HHi2i", dex, 0x120, 0x0100, 2, 0, 5, 9)
        assert sweep.switch_targets(bytes(dex), 0x100, 0x10, 0x20) == [0x15, 0x19]
        struct.pack_into("<HH2i2i", dex, 0x120, 0x0200, 2, 0, 1000, 5, 9)
        assert sweep.switch_targets(bytes(dex), 0x100, 0x10, 0x20) == [0x15, 0x19]

    def test_dex_class_descriptors(self):
        """`class_defs` -> `type_ids` -> `string_ids` -> MUTF-8 data."""
        dex = bytearray(0x200)
        struct.pack_into("<II", dex, 0x38, 2, 0x100)  # string_ids
        struct.pack_into("<II", dex, 0x40, 2, 0x110)  # type_ids
        struct.pack_into("<II", dex, 0x60, 1, 0x120)  # class_defs
        struct.pack_into("<II", dex, 0x100, 0x180, 0x190)
        dex[0x180:0x187] = b"\x05La/B;\x00"
        dex[0x190:0x195] = b"\x03Lc;\x00"
        struct.pack_into("<II", dex, 0x110, 1, 0)
        struct.pack_into("<I", dex, 0x120, 1)  # class_idx 1 -> string 0
        assert sweep.dex_class_descriptors(bytes(dex)) == ["La/B;"]

    def test_framework_ancestry(self, tmp_path):
        index = sweep.FrameworkIndex(_android_jar(tmp_path))

        assert index.ancestors("Ljavax/crypto/SecretKey;") == {
            "Ljava/lang/Object;",
            "Ljava/security/Key;",
            "Ljava/io/Serializable;",
        }
        assert index.ancestors("Ljava/security/PublicKey;") is None


DEXDUMP_FIXTURE = """\
000100:                                        |[000100] app.Main.m:(Ljavax/crypto/Cipher;Ljava/security/Key;Z)V
000110: 1210                                   |0000: const/4 v0, #int 1 // #1
000112: 3803 0800                              |0001: if-eqz v3, 0009 // +0008
000116: 1223                                   |0003: const/4 v3, #int 2 // #2
000118: 6703 0000                              |0004: sput v3, Lapp/Main;.x:I // field@0000
00011c: 7130 0c00 2001                         |0006: invoke-static {v0, v2, v1}, Lmop/MultiSpec_1RuntimeMonitor;.CipherSpec_i2Event:(ILjava/security/Key;Ljavax/crypto/Cipher;)V // method@000c
000122: 6e30 0800 0102                         |0009: invoke-virtual {v1, v0, v2}, Ljavax/crypto/Cipher;.init:(ILjava/security/Key;)V // method@0008
000128: 3803 0500                              |000c: if-eqz v3, 0014 // +0005
00012c: 7130 0c00 2001                         |000e: invoke-static {v0, v2, v1}, Lmop/MultiSpec_1RuntimeMonitor;.CipherSpec_i2Event:(ILjava/security/Key;Ljavax/crypto/Cipher;)V // method@000c
000132: 6e30 0800 0102                         |0011: invoke-virtual {v1, v0, v2}, Ljavax/crypto/Cipher;.init:(ILjava/security/Key;)V // method@0008
000138: 2a00 0000 0000                         |0014: goto/32 #fffffffb
00013e: 7130 0c00 2001                         |0017: invoke-static {v0, v2, v1}, Lmop/MultiSpec_1RuntimeMonitor;.CipherSpec_i2Event:(ILjava/security/Key;Ljavax/crypto/Cipher;)V // method@000c
000144: 6e30 0800 0102                         |001a: invoke-virtual {v1, v0, v2}, Ljavax/crypto/Cipher;.init:(I)V // method@0008
00014a: 0e00                                   |001d: return-void
"""


class TestMethodScan:
    """Measures (a)-inline and (c) over one method of `dexdump` text."""

    def _scan(self, tmp_path):
        descriptor = sweep.load_descriptor(_descriptor_json(tmp_path))
        counts = sweep.ApkCounts("fixture.apk")
        invokes = sweep._Invokes()
        (method,) = list(sweep.parse_dexdump(DEXDUMP_FIXTURE.splitlines()))
        sweep.scan_method(method, b"", "classes.dex", descriptor, counts, invokes)
        return counts

    def test_a_branch_to_the_hooked_call_is_counted(self, tmp_path):
        """`0001: if-eqz -> 0009` lands on the call behind the hook at `0006`."""
        counts = self._scan(tmp_path)

        assert counts.before_hooks == 3
        branch_sites = [site for site in counts.sites if site[1] == "branch"]
        assert [site[6].split()[0] for site in branch_sites] == ["off=0009"]
        assert counts.branch_target_hooks == 1

    def test_a_guard_immediately_before_the_hook_is_not_counted(self, tmp_path):
        """`000c: if-eqz -> 0014` skips the hook run it precedes: the guard shape.

        And `goto/32 #fffffffb` from `0014` lands on `000f`, not on a call, so it adds nothing.
        """
        counts = self._scan(tmp_path)

        assert all("off=0011" not in site[6] for site in counts.sites)

    def test_an_inline_hook_on_a_call_of_the_wrong_arity(self, tmp_path):
        """`args(mode, key, ..)` needs at least two parameters; `init(I)` has one."""
        counts = self._scan(tmp_path)

        assert counts.arity_inline_hooks == 1
        assert counts.branch_detail == {"CipherSpec_i2Event": 1}


class TestResolution:
    """Measures (a), (b) and (d) once the wrappers are known."""

    def test_wrappers_subtypes_and_keystore(self, tmp_path):
        descriptor = sweep.load_descriptor(_descriptor_json(tmp_path))
        framework = sweep.FrameworkIndex(_android_jar(tmp_path))
        wrappers = [
            sweep.Wrapper(
                "javax_crypto_Cipher_getInstance",
                (
                    "Ljavax/crypto/Cipher;",
                    "getInstance",
                    "(Ljava/lang/String;)Ljavax/crypto/Cipher;",
                ),
                ["CipherSpec_gEvent", "CipherSpec_g2Event"],
            ),
            sweep.Wrapper(
                "java_security_Key_getEncoded",
                ("Ljava/security/Key;", "getEncoded", "()[B"),
                ["KeySpec_geEvent"],
            ),
        ]
        invokes = sweep._Invokes()
        invokes.wrapper_calls["javax_crypto_Cipher_getInstance"] = 3
        invokes.dispatched[("Ljavax/crypto/SecretKey;", "getEncoded", "()[B")] = [
            2,
            "a.B.m:()V",
            "classes.dex",
        ]
        invokes.dispatched[("La/AppKey;", "getEncoded", "()[B")] = [
            5,
            "a.B.m:()V",
            "classes.dex",
        ]
        counts = sweep.ApkCounts("fixture.apk")

        sweep.resolve_invokes(
            counts, wrappers, invokes, {"La/AppKey;"}, descriptor, framework
        )

        assert (counts.arity_pairs, counts.arity_wrappers, counts.arity_call_sites) == (
            1,
            1,
            3,
        )
        assert counts.arity_detail == {
            "javax_crypto_Cipher_getInstance>CipherSpec_g2Event": 3
        }
        # The APK-defined owner is not a framework subtype and is left out.
        assert (counts.subtype_unwoven, counts.subtype_targets) == (2, 1)
        assert counts.wrappers == 2

    def test_totals_trailer(self):
        first = sweep.ApkCounts(
            "a.apk",
            wrappers=4,
            arity_pairs=2,
            branch_detail=collections.Counter({"e": 1}),
        )
        second = sweep.ApkCounts(
            "b.apk",
            wrappers=4,
            arity_pairs=1,
            error="boom",
            branch_detail=collections.Counter({"e": 2}),
        )

        total = sweep.totals([first, second])

        assert (total.arity_pairs, total.wrappers) == (3, 4)
        assert total.branch_detail == {"e": 3}
        assert total.error == "1 APK(s) failed"


# ---------------------------------------------------------------------------
# End to end through javac, d8 and dexdump
# ---------------------------------------------------------------------------

MONITOR_SOURCE = """
package mop;
public final class MultiSpec_1RuntimeMonitor {
  public static void CipherSpec_i2Event(int mode, java.security.Key key, javax.crypto.Cipher c) {}
  public static void CipherSpec_gEvent(String alg, javax.crypto.Cipher c) {}
  public static void CipherSpec_g2Event(String alg, javax.crypto.Cipher c) {}
  public static void KeySpec_geEvent(java.security.Key k, byte[] out) {}
}
"""

WRAPPERS_SOURCE = """
package mop;
public final class MonitorWrappers {
  public static javax.crypto.Cipher javax_crypto_Cipher_getInstance(String alg) throws Exception {
    javax.crypto.Cipher c = javax.crypto.Cipher.getInstance(alg);
    MultiSpec_1RuntimeMonitor.CipherSpec_gEvent(alg, c);
    MultiSpec_1RuntimeMonitor.CipherSpec_g2Event(alg, c);
    return c;
  }
  public static byte[] java_security_Key_getEncoded(java.security.Key k) {
    byte[] out = k.getEncoded();
    MultiSpec_1RuntimeMonitor.KeySpec_geEvent(k, out);
    return out;
  }
}
"""

# Woven shapes written by hand: a hook placed before a call, reached by an `if`, by a
# packed switch case and by a sparse switch case; a hook without a branch; a guard.
APP_SOURCE = """
package app;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import java.security.Key;
import java.security.KeyStore;
import mop.MultiSpec_1RuntimeMonitor;
import mop.MonitorWrappers;
public class Main {
  static int x;
  static void branch(Cipher c, Key k, boolean flag) throws Exception {
    if (flag) { x = 2; MultiSpec_1RuntimeMonitor.CipherSpec_i2Event(1, k, c); }
    c.init(1, k);
  }
  static void packed(Cipher c, Key k, int sel) throws Exception {
    switch (sel) {
      case 0: x = 1; MultiSpec_1RuntimeMonitor.CipherSpec_i2Event(1, k, c);
      case 1: c.init(1, k); break;
      case 2: x = 3; break;
    }
  }
  static void sparse(Cipher c, Key k, int sel) throws Exception {
    switch (sel) {
      case 0: x = 1; MultiSpec_1RuntimeMonitor.CipherSpec_i2Event(1, k, c);
      case 1000: c.init(1, k); break;
      case 70000: x = 3; break;
    }
  }
  static void plain(Cipher c, Key k) throws Exception {
    MultiSpec_1RuntimeMonitor.CipherSpec_i2Event(1, k, c);
    c.init(1, k);
  }
  static void guarded(Cipher c, Key k, boolean flag) throws Exception {
    if (flag) MultiSpec_1RuntimeMonitor.CipherSpec_i2Event(1, k, c);
    c.init(1, k);
  }
  static byte[] use(SecretKey sk, KeyStore ks) throws Exception {
    Cipher c = MonitorWrappers.javax_crypto_Cipher_getInstance("AES");
    ks.getEntry("a", null);
    byte[] a = MonitorWrappers.java_security_Key_getEncoded(sk);
    return sk.getEncoded();
  }
}
"""


def _tools():
    home = Path(os.environ.get("ANDROID_HOME", "/nonexistent"))
    dexdump = sweep.newest_under(home / "build-tools", "dexdump")
    d8 = sweep.newest_under(home / "build-tools", "d8")
    platform_jar = sweep.newest_under(home / "platforms", "android.jar")
    java_home = os.environ.get("JAVA_HOME")
    javac = Path(java_home, "bin", "javac") if java_home else shutil.which("javac")
    if not (dexdump and d8 and platform_jar and javac and Path(javac).exists()):
        pytest.skip(
            "ANDROID_HOME build tools, a platform android.jar or javac are absent"
        )
    return dexdump, d8, platform_jar, Path(javac)


def test_scan_apk_end_to_end(tmp_path):
    """The real `dexdump` output of a real DEX gives the counts the woven shapes imply."""
    dexdump, d8, platform_jar, javac = _tools()
    sources = {
        "mop/MultiSpec_1RuntimeMonitor.java": MONITOR_SOURCE,
        "mop/MonitorWrappers.java": WRAPPERS_SOURCE,
        "app/Main.java": APP_SOURCE,
    }
    for name, text in sources.items():
        (tmp_path / "src" / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / name).write_text(text, encoding="utf-8")
    classes = tmp_path / "classes"
    subprocess.run(
        [str(javac), "--release", "11", "-d", str(classes)]
        + [str(tmp_path / "src" / n) for n in sources],
        check=True,
        capture_output=True,
    )
    for part, inputs in (
        ("app", ["app/Main.class"]),
        ("mon", ["mop/MultiSpec_1RuntimeMonitor.class", "mop/MonitorWrappers.class"]),
    ):
        (tmp_path / part).mkdir()
        subprocess.run(
            [
                str(d8),
                "--debug",
                "--min-api",
                "26",
                "--lib",
                str(platform_jar),
                "--classpath",
                str(classes),
                "--output",
                str(tmp_path / part),
            ]
            + [str(classes / i) for i in inputs],
            check=True,
            capture_output=True,
        )
    apk = tmp_path / "fixture.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        archive.write(tmp_path / "app" / "classes.dex", "classes.dex")
        archive.write(tmp_path / "mon" / "classes.dex", "classes2.dex")

    descriptor = sweep.load_descriptor(_descriptor_json(tmp_path))
    counts = sweep.scan_apk(apk, descriptor, dexdump, _android_jar(tmp_path))

    assert counts.error == ""
    assert counts.dex_files == 2 and counts.wrappers == 2
    assert (counts.arity_pairs, counts.arity_call_sites) == (1, 1)
    assert (counts.subtype_unwoven, counts.subtype_detail) == (
        1,
        {"Ljavax/crypto/SecretKey;.getEncoded:()[B": 1},
    )
    assert counts.before_hooks == 5
    branch_callers = sorted(
        site[3].split(":")[0] for site in counts.sites if site[1] == "branch"
    )
    assert branch_callers == ["app.Main.branch", "app.Main.packed", "app.Main.sparse"]
    assert (counts.keystore_entry_calls, counts.keystore_entry_woven) == (1, 0)

    out = tmp_path / "out.csv"
    sweep.write_outputs([counts], out, None)
    rows = out.read_text(encoding="utf-8").splitlines()
    assert rows[0].split(",")[:4] == ["apk", "dex_files", "wrappers", "arity_pairs"]
    assert rows[-1].startswith("TOTAL,2,2,1,")
