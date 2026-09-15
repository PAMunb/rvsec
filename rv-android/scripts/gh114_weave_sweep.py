#!/usr/bin/env python3
"""Static counts of four weaving defects over a directory of instrumented APKs.

The DEX-native weaver is accepted against counts taken on its own output, not against a
campaign: a campaign mixes what the weaver did with what the tool happened to reach and
what the monitor decided, and none of the three can be read back from the reports. The
woven DEX can be read directly. This script disassembles every `classes*.dex` of every APK
with `dexdump -d` and counts, per APK, the four shapes the weaver repairs are about:

  (a) arity         a wrapper of a concrete overload invokes a monitor event whose advice
                    declares an `args(...)` clause that overload's parameter count cannot
                    satisfy (INV-INS-159): `k` positions need exactly `k` parameters, a
                    trailing `..` after `k` positions needs at least `k`. The wrappers live
                    in the monitor DEX (`mop/MonitorWrappers`), so the pair count is a
                    property of the monitor; `arity_call_sites` is how many invokes of the
                    application reach such a wrapper, which is what fires on a device.
                    Inline `before` hooks get the same check against the call they
                    precede (`arity_inline_hooks`).

  (b) subtype       an invoke whose owner is a framework type, strict subtype of the owner
                    of a wrapper for the same method name and descriptor, whose advice
                    names that owner with `+` -- and which is still a plain invoke, because
                    a woven one is replaced by the wrapper (INV-INS-160). Owners the APK
                    defines are not counted: aliasing to application subtypes is a separate
                    mechanism. Framework ancestry is read from `android.jar`.

  (c) branch        an inline `before` hook whose matched call is the target of an
                    `if-*`, `goto*`, `packed-switch` or `sparse-switch` of the same method,
                    so control arriving by that branch skips the hook (INV-INS-161).

  (d) keystore      invokes of `KeyStore.getEntry` / `KeyStore.setEntry`, and how many of
                    them are woven -- preceded by an inline hook or replaced by a wrapper
                    whose target is one of them (INV-INS-162: the nested parameter types of
                    these two methods decide whether their pointcuts resolve at all).

What is a hook is decided by the aspect descriptor (`MultiSpec_1MonitorAspect.json`) that
the monitor generator wrote for the specification set the APKs were woven with: its
advices give the monitor event methods, their position and their pointcut expression. A
run of consecutive `invoke-static` calls to `before` events of the runtime monitor
immediately followed by an invoke is one inline hook of that invoke. Code the descriptor's
`baseAspectExclusions` exclude from weaving (`java..*`, `mop..*`, ...) is not scanned, and
of the monitor DEX -- the DEX that defines `mop/MonitorWrappers` -- only the wrappers are.

An `if-*` placed immediately before a hook run that targets the matched call is the skip
branch of an `if(...)` guard, which targets the call by design, and is not counted: before
weaving the same branch would target the instruction right after itself, which no compiler
emits.

Usage:
    gh114_weave_sweep.py <apk_dir> <descriptor.json> <out.csv>
        [--sites <sites.csv>] [--jobs N] [--dexdump <path>] [--android-jar <path>]

`<apk_dir>` is read non-recursively and only `*.apk` files are processed. `dexdump`
defaults to the newest `$ANDROID_HOME/build-tools/*/dexdump`, `android.jar` to the newest
`$ANDROID_HOME/platforms/*/android.jar`. `--jobs` bounds the parallel APKs, each running
one `dexdump` at a time (default 4).

Output: one row per APK in name order, then a `TOTAL` trailer row whose numeric columns
are sums and whose `*_detail` columns merge the per-APK details. Columns:

    apk, dex_files, wrappers,
    arity_pairs, arity_wrappers, arity_call_sites, arity_inline_hooks, arity_detail,
    subtype_unwoven, subtype_targets, subtype_detail,
    before_hooks, branch_target_hooks, branch_detail,
    keystore_entry_calls, keystore_entry_woven,
    error

`*_detail` cells are `key:count` pairs joined by `|`, most frequent first: the wrapper and
event of each arity pair with its call sites, the unwoven subtype invoke targets, the
events of branch-target hooks. `--sites` writes one row per counted item instead
(`apk,measure,dex,caller,target,event,detail`), which is what makes a count traceable to a
method; a `subtype` row aggregates every invoke of one target and names its first caller,
and an `arity` row names the wrapper and counts its call sites in `detail`. An APK that cannot be read keeps its row, with zero counts and the cause in
`error`, so a short total cannot pass for a clean one.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

#: The class `WrapperEmitter` generates the wrappers into, as a DEX type descriptor.
WRAPPER_CLASS = "Lmop/MonitorWrappers;"

#: The two methods of measure (d).
KEYSTORE_OWNER = "Ljava/security/KeyStore;"
KEYSTORE_ENTRY_METHODS = frozenset({"getEntry", "setEntry"})

#: Invoke opcodes whose static owner can be a supertype of the runtime receiver. A super
#: call and a static call are not dispatched through a subtype, so measure (b) ignores them.
DISPATCHED_INVOKES = frozenset(
    {
        "invoke-virtual",
        "invoke-virtual/range",
        "invoke-interface",
        "invoke-interface/range",
    }
)

DEFAULT_JOBS = 4

CSV_FIELDS = [
    "apk",
    "dex_files",
    "wrappers",
    "arity_pairs",
    "arity_wrappers",
    "arity_call_sites",
    "arity_inline_hooks",
    "arity_detail",
    "subtype_unwoven",
    "subtype_targets",
    "subtype_detail",
    "before_hooks",
    "branch_target_hooks",
    "branch_detail",
    "keystore_entry_calls",
    "keystore_entry_woven",
    "error",
]
SITE_FIELDS = ["apk", "measure", "dex", "caller", "target", "event", "detail"]

#: `<file offset>: <hex bytes> |<address>: <opcode> <operands>` -- one instruction line.
INSN_RE = re.compile(r"^([0-9a-f]{6,}): [0-9a-f ]+\|([0-9a-f]{4,}): (\S+)(.*)$")
#: `<file offset>: |[<file offset>] <dotted class>.<method>:<descriptor>` -- a method header.
METHOD_RE = re.compile(r"\|\[[0-9a-f]+\] ([^\s:]+):(\S+)")
#: The method reference of an invoke: `, <owner>.<name>:<descriptor>`.
INVOKE_REF_RE = re.compile(r", (\[*L[^;]+;|\[+[A-Z])\.([^:\s]+):(\([^)]*\)\S+)")
BRANCH_RE = re.compile(r"^(if-\w+|goto(?:/16|/32)?)$")
SWITCH_RE = re.compile(r"^(packed-switch|sparse-switch)$")
#: One field type of a JVM descriptor.
FIELD_TYPE_RE = re.compile(r"\[*(?:[ZBCSIJFD]|L[^;]+;)")
#: The owner and name of every `call(...)` signature of a pointcut expression.
CALL_OWNER_RE = re.compile(r"([\w.$]+)(\+?)\.([\w$]+)\(")

PACKED_SWITCH_PAYLOAD = 0x0100
SPARSE_SWITCH_PAYLOAD = 0x0200


# ---------------------------------------------------------------------------
# Descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    """One monitor event method and the advice that calls it."""

    advice: str
    position: str
    #: `(positions, open)` for each `args(...)` clause of the advice's expression.
    args_clauses: tuple[tuple[int, bool], ...]
    #: `(owner as written, has +)` for each `call(...)` signature of the expression.
    owners: tuple[tuple[str, bool], ...]


@dataclass(frozen=True)
class Descriptor:
    """What the sweep reads from `MultiSpec_1MonitorAspect.json`."""

    #: DEX type descriptor of the runtime monitor class, e.g. `Lmop/MultiSpec_1RuntimeMonitor;`.
    monitor_class: str
    #: Event method name (`CipherSpec_i2Event`) to its advice.
    events: dict[str, Event]
    #: DEX descriptor prefixes of code the weaver does not weave, e.g. `Ljava/`.
    excluded_prefixes: tuple[str, ...]

    @property
    def before_events(self) -> frozenset[str]:
        return frozenset(
            name for name, event in self.events.items() if event.position == "before"
        )


def args_clauses(expression: str) -> tuple[tuple[int, bool], ...]:
    """The `args(...)` clauses of a pointcut expression as `(positions, open)` pairs.

    `args(alg, *)` is `(2, False)`; `args(mode, key, ..)` is `(2, True)`, because a trailing
    `..` admits any further parameters. A `..` elsewhere counts as no position and opens the
    clause, which over-admits rather than invents a mismatch.
    """
    clauses = []
    for body in re.findall(r"\bargs\(([^()]*)\)", expression):
        tokens = [token.strip() for token in body.split(",") if token.strip()]
        positions = sum(1 for token in tokens if token != "..")
        clauses.append((positions, ".." in tokens))
    return tuple(clauses)


def arity_compatible(clauses: tuple[tuple[int, bool], ...], parameters: int) -> bool:
    """Whether a call with `parameters` parameters can satisfy an advice's `args` clauses.

    An advice with no clause is not constrained. With several clauses (one per `||`
    branch), satisfying any one of them is enough.
    """
    if not clauses:
        return True
    return any(
        parameters >= positions if is_open else parameters == positions
        for positions, is_open in clauses
    )


def load_descriptor(path: Path) -> Descriptor:
    """Read the aspect descriptor the monitor generator wrote.

    Raises:
        ValueError: when the monitor calls do not name exactly one runtime monitor class,
            since every count below keys on that class.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    # The generator writes the aspect's package declaration verbatim: `package mop;`.
    package = re.sub(r"^package\s+|\s*;$", "", document["package"].strip())
    events: dict[str, Event] = {}
    classes = set()
    for advice in document.get("advices") or []:
        expression = advice.get("expression") or ""
        event = Event(
            advice=advice["name"],
            position=advice["position"],
            args_clauses=args_clauses(expression),
            owners=tuple(
                (owner, plus == "+")
                for owner, plus, _ in CALL_OWNER_RE.findall(expression)
            ),
        )
        for call in advice.get("monitorCalls") or []:
            monitor, method = call["method"].split(".", 1)
            classes.add(monitor)
            events[method] = event
    if len(classes) != 1:
        raise ValueError(
            f"{path}: expected one runtime monitor class, found {sorted(classes)}"
        )
    prefixes = tuple(
        "L" + pattern[: -len("..*")].replace(".", "/") + "/"
        for pattern in document.get("baseAspectExclusions") or []
        if pattern.endswith("..*")
    )
    monitor_class = f"L{package.replace('.', '/')}/{classes.pop()};"
    return Descriptor(monitor_class, events, prefixes)


# ---------------------------------------------------------------------------
# DEX and dexdump
# ---------------------------------------------------------------------------


def parameter_count(descriptor: str) -> int:
    """Number of parameters of a method descriptor `(...)R`, receiver excluded."""
    return len(FIELD_TYPE_RE.findall(descriptor[1 : descriptor.index(")")]))


def invoke_ref(operands: str) -> tuple[str, str, str] | None:
    """`(owner, name, descriptor)` of an invoke line's operands, or `None` when absent."""
    match = INVOKE_REF_RE.search(operands)
    return match.groups() if match else None


def _uleb128(data: bytes, offset: int) -> int:
    """Offset just past the unsigned LEB128 value at `offset`."""
    while data[offset] & 0x80:
        offset += 1
    return offset + 1


def dex_class_descriptors(dex: bytes) -> list[str]:
    """Type descriptors of the classes a DEX defines, read from its `class_defs` table."""
    string_ids_off = struct.unpack_from("<I", dex, 0x3C)[0]
    type_ids_off = struct.unpack_from("<I", dex, 0x44)[0]
    class_defs_size, class_defs_off = struct.unpack_from("<II", dex, 0x60)
    names = []
    for index in range(class_defs_size):
        class_idx = struct.unpack_from("<I", dex, class_defs_off + 32 * index)[0]
        string_idx = struct.unpack_from("<I", dex, type_ids_off + 4 * class_idx)[0]
        data_off = struct.unpack_from("<I", dex, string_ids_off + 4 * string_idx)[0]
        start = _uleb128(dex, data_off)
        names.append(dex[start : dex.index(b"\0", start)].decode("utf-8", "replace"))
    return names


def switch_targets(
    dex: bytes, file_off: int, switch_addr: int, payload_addr: int
) -> list[int]:
    """Case target addresses of a `packed-switch` or `sparse-switch`.

    `dexdump` prints the payload address but not the cases, so they are read from the DEX:
    the payload sits `2 * (payload_addr - switch_addr)` bytes after the switch instruction,
    and every case is relative to the switch.
    """
    offset = file_off + 2 * (payload_addr - switch_addr)
    ident, size = struct.unpack_from("<HH", dex, offset)
    if ident == PACKED_SWITCH_PAYLOAD:
        relative = struct.unpack_from(f"<{size}i", dex, offset + 8)
    elif ident == SPARSE_SWITCH_PAYLOAD:
        relative = struct.unpack_from(f"<{size}i", dex, offset + 4 + 4 * size)
    else:
        raise ValueError(f"bad switch payload ident {ident:#x} at {offset:#x}")
    return [switch_addr + rel for rel in relative]


@dataclass
class Method:
    """One disassembled method: dotted `class.method`, descriptor, and its instructions."""

    name: str
    descriptor: str
    #: `(file offset, address, opcode, operands)` per instruction.
    insns: list[tuple[int, int, str, str]] = field(default_factory=list)

    @property
    def class_descriptor(self) -> str:
        return "L" + self.name.rsplit(".", 1)[0].replace(".", "/") + ";"


def parse_dexdump(lines: Iterable[str]) -> Iterator[Method]:
    """Yield the methods of a `dexdump -d` listing, in listing order."""
    current: Method | None = None
    for line in lines:
        header = METHOD_RE.search(line)
        if header:
            if current is not None:
                yield current
            current = Method(header.group(1), header.group(2))
            continue
        insn = INSN_RE.match(line)
        if insn and current is not None:
            current.insns.append(
                (
                    int(insn.group(1), 16),
                    int(insn.group(2), 16),
                    insn.group(3),
                    insn.group(4),
                )
            )
    if current is not None:
        yield current


def branch_targets(
    insns: list[tuple[int, int, str, str]], dex: bytes
) -> dict[int, list[tuple[int, int]]]:
    """Map each branch or switch target address to its `(instruction index, address)` sources."""
    targets: dict[int, list[tuple[int, int]]] = collections.defaultdict(list)
    for index, (file_off, addr, op, operands) in enumerate(insns):
        if BRANCH_RE.match(op):
            arg = operands.split(",")[-1].split("//")[0].strip()
            if arg.startswith("#"):  # goto/32 is printed as a signed relative offset
                rel = int(arg[1:], 16)
                target = addr + (rel - (1 << 32) if rel >= 1 << 31 else rel)
            else:
                target = int(arg, 16)
            targets[target].append((index, addr))
        elif SWITCH_RE.match(op):
            payload = int(operands.split(",")[-1].split("//")[0].strip(), 16)
            for target in switch_targets(dex, file_off, addr, payload):
                targets[target].append((index, addr))
    return targets


class FrameworkIndex:
    """Ancestry of framework classes, read from the class files of `android.jar`."""

    def __init__(self, jar: Path):
        self._zip = zipfile.ZipFile(jar)
        self._names = set(self._zip.namelist())
        self._ancestors: dict[str, frozenset[str] | None] = {}

    @staticmethod
    def class_header(data: bytes) -> tuple[str | None, list[str]]:
        """`(superclass, interfaces)` of a class file, as internal names."""
        count = struct.unpack_from(">H", data, 8)[0]
        utf8: dict[int, str] = {}
        class_name: dict[int, int] = {}
        offset, index = 10, 1
        sizes = {
            3: 4,
            4: 4,
            9: 4,
            10: 4,
            11: 4,
            12: 4,
            15: 3,
            16: 2,
            17: 4,
            18: 4,
            19: 2,
            20: 2,
            8: 2,
        }
        while index < count:
            tag = data[offset]
            if tag == 1:
                length = struct.unpack_from(">H", data, offset + 1)[0]
                utf8[index] = data[offset + 3 : offset + 3 + length].decode(
                    "utf-8", "replace"
                )
                offset += 3 + length
            elif tag == 7:
                class_name[index] = struct.unpack_from(">H", data, offset + 1)[0]
                offset += 3
            elif tag in (5, 6):  # long and double take two slots
                offset += 9
                index += 1
            else:
                offset += 1 + sizes[tag]
            index += 1
        _, _, super_idx, interface_count = struct.unpack_from(">HHHH", data, offset)
        interfaces = struct.unpack_from(f">{interface_count}H", data, offset + 8)
        superclass = utf8[class_name[super_idx]] if super_idx else None
        return superclass, [utf8[class_name[i]] for i in interfaces]

    def ancestors(self, descriptor: str) -> frozenset[str] | None:
        """Every proper supertype of a framework class, or `None` when the jar lacks it."""
        if descriptor not in self._ancestors:
            entry = descriptor[1:-1] + ".class"
            if not descriptor.startswith("L") or entry not in self._names:
                self._ancestors[descriptor] = None
            else:
                superclass, interfaces = self.class_header(self._zip.read(entry))
                found: set[str] = set()
                for parent in ([superclass] if superclass else []) + interfaces:
                    parent_desc = f"L{parent};"
                    found.add(parent_desc)
                    found |= self.ancestors(parent_desc) or frozenset()
                self._ancestors[descriptor] = frozenset(found)
        return self._ancestors[descriptor]


# ---------------------------------------------------------------------------
# Per-APK scan
# ---------------------------------------------------------------------------


@dataclass
class Wrapper:
    """One method of the wrapper class: the call it wraps and the events it fires."""

    name: str
    target: tuple[str, str, str]
    events: list[str]


@dataclass
class ApkCounts:
    """Everything measured on one APK; the row and the sites derive from it."""

    apk: str
    dex_files: int = 0
    wrappers: int = 0
    arity_pairs: int = 0
    arity_wrappers: int = 0
    arity_call_sites: int = 0
    arity_inline_hooks: int = 0
    arity_detail: collections.Counter = field(default_factory=collections.Counter)
    subtype_unwoven: int = 0
    subtype_targets: int = 0
    subtype_detail: collections.Counter = field(default_factory=collections.Counter)
    before_hooks: int = 0
    branch_target_hooks: int = 0
    branch_detail: collections.Counter = field(default_factory=collections.Counter)
    keystore_entry_calls: int = 0
    keystore_entry_woven: int = 0
    error: str = ""
    sites: list[list[str]] = field(default_factory=list)


@dataclass
class _Invokes:
    """Invokes of application code whose meaning is only known once the wrappers are read."""

    #: Name of a wrapper method to the number of invokes of it.
    wrapper_calls: collections.Counter = field(default_factory=collections.Counter)
    #: Dispatched `(owner, name, descriptor)` to `[count, first caller, dex]`.
    dispatched: dict = field(default_factory=dict)


def _hook_run(insns, index: int, descriptor: Descriptor) -> tuple[list[str], int]:
    """The `before` events invoked immediately ahead of instruction `index`, in order.

    Returns the events and the index of the instruction just before the run.
    """
    run = []
    j = index - 1
    prefix = descriptor.monitor_class + "."
    while j >= 0 and insns[j][2].startswith("invoke-static") and prefix in insns[j][3]:
        event = insns[j][3].split(prefix, 1)[1].split(":", 1)[0]
        if event not in descriptor.before_events:
            break
        run.append(event)
        j -= 1
    return list(reversed(run)), j


def scan_wrapper(method: Method, descriptor: Descriptor) -> Wrapper | None:
    """Read one wrapper method: its first non-monitor invoke and the events it fires.

    Returns `None` for the class's constructors and for a method that wraps no call.
    """
    if method.name.rsplit(".", 1)[1].startswith("<"):
        return None
    target = None
    events = []
    for _, _, op, operands in method.insns:
        if not op.startswith("invoke"):
            continue
        ref = invoke_ref(operands)
        if ref is None:
            continue
        if ref[0] == descriptor.monitor_class:
            events.append(ref[1])
        elif target is None:
            target = ref
    if target is None:
        return None
    return Wrapper(method.name.rsplit(".", 1)[1], target, events)


def scan_method(
    method: Method,
    dex: bytes,
    dex_name: str,
    descriptor: Descriptor,
    counts: ApkCounts,
    invokes: _Invokes,
) -> None:
    """Accumulate measures (a)-inline, (c) and (d) of one application method.

    Invokes of wrappers and dispatched invokes are recorded in `invokes`, because whether
    they count for (a), (b) or (d) depends on wrappers that may live in a later DEX.
    """
    insns = method.insns
    targets = None
    caller = f"{method.name}:{method.descriptor}"
    for index, (_, addr, op, operands) in enumerate(insns):
        if not op.startswith("invoke"):
            continue
        ref = invoke_ref(operands)
        if ref is None or ref[0] == descriptor.monitor_class:
            continue
        owner, name, proto = ref
        if owner == WRAPPER_CLASS:
            invokes.wrapper_calls[name] += 1
            continue
        if op in DISPATCHED_INVOKES:
            entry = invokes.dispatched.setdefault(ref, [0, caller, dex_name])
            entry[0] += 1

        run, before = _hook_run(insns, index, descriptor)
        target_text = f"{owner}.{name}:{proto}"
        if owner == KEYSTORE_OWNER and name in KEYSTORE_ENTRY_METHODS:
            counts.keystore_entry_calls += 1
            counts.keystore_entry_woven += bool(run)
            counts.sites.append(
                [
                    counts.apk,
                    "keystore",
                    dex_name,
                    caller,
                    target_text,
                    "|".join(run),
                    "woven-inline" if run else "unwoven",
                ]
            )
        if not run:
            continue

        counts.before_hooks += 1
        parameters = parameter_count(proto)
        for event in run:
            if not arity_compatible(descriptor.events[event].args_clauses, parameters):
                counts.arity_inline_hooks += 1
                counts.sites.append(
                    [
                        counts.apk,
                        "arity-inline",
                        dex_name,
                        caller,
                        target_text,
                        event,
                        f"off={addr:04x}",
                    ]
                )
        if targets is None:
            targets = branch_targets(insns, dex)
        sources = [
            src
            for (k, src) in targets.get(addr, [])
            if not (k == before and insns[k][2].startswith("if-"))
        ]
        if sources:
            counts.branch_target_hooks += 1
            key = "+".join(run)
            counts.branch_detail[key] += 1
            counts.sites.append(
                [
                    counts.apk,
                    "branch",
                    dex_name,
                    caller,
                    target_text,
                    key,
                    f"off={addr:04x} srcs={'|'.join(f'{s:04x}' for s in sources)}",
                ]
            )


def _simple_matches(pattern_owner: str, descriptor: str) -> bool:
    """Whether a pointcut owner as written (`Key`, `java.security.Key`) names a DEX type."""
    dotted = descriptor[1:-1].replace("/", ".").replace("$", ".")
    return dotted == pattern_owner or dotted.endswith("." + pattern_owner)


def resolve_invokes(
    counts: ApkCounts,
    wrappers: list[Wrapper],
    invokes: _Invokes,
    apk_classes: set[str],
    descriptor: Descriptor,
    framework: FrameworkIndex,
) -> None:
    """Accumulate measures (a), (b) and the wrapper half of (d) once all wrappers are known."""
    counts.wrappers = len(wrappers)

    # (a) arity pairs of the wrappers, and the application invokes that reach them.
    for wrapper in wrappers:
        parameters = parameter_count(wrapper.target[2])
        bad = [
            event
            for event in wrapper.events
            if event in descriptor.events
            and not arity_compatible(descriptor.events[event].args_clauses, parameters)
        ]
        if not bad:
            continue
        counts.arity_wrappers += 1
        counts.arity_pairs += len(bad)
        wrapper_calls = invokes.wrapper_calls[wrapper.name]
        counts.arity_call_sites += wrapper_calls
        target_text = "{}.{}:{}".format(*wrapper.target)
        for event in bad:
            counts.arity_detail[f"{wrapper.name}>{event}"] += wrapper_calls
            counts.sites.append(
                [
                    counts.apk,
                    "arity",
                    "",
                    f"mop.MonitorWrappers.{wrapper.name}",
                    target_text,
                    event,
                    f"call_sites={wrapper_calls}",
                ]
            )

    # (d) KeyStore entry calls replaced by a wrapper.
    for wrapper in wrappers:
        owner, name, _ = wrapper.target
        if owner != KEYSTORE_OWNER or name not in KEYSTORE_ENTRY_METHODS:
            continue
        calls = invokes.wrapper_calls[wrapper.name]
        counts.keystore_entry_calls += calls
        counts.keystore_entry_woven += calls
        if calls:
            counts.sites.append(
                [
                    counts.apk,
                    "keystore",
                    "",
                    f"mop.MonitorWrappers.{wrapper.name}",
                    "{}.{}:{}".format(*wrapper.target),
                    "|".join(wrapper.events),
                    f"woven-wrapper calls={calls}",
                ]
            )

    # (b) framework subtypes of a wrapped owner left as plain invokes.
    admitting: dict[tuple[str, str], list[Wrapper]] = collections.defaultdict(list)
    for wrapper in wrappers:
        owner, name, proto = wrapper.target
        plus = any(
            has_plus and _simple_matches(pattern, owner)
            for event in wrapper.events
            if event in descriptor.events
            for pattern, has_plus in descriptor.events[event].owners
        )
        if plus:
            admitting[(name, proto)].append(wrapper)
    for (owner, name, proto), (count, caller, dex_name) in invokes.dispatched.items():
        candidates = admitting.get((name, proto))
        if not candidates or owner in apk_classes:
            continue
        ancestry = framework.ancestors(owner)
        if not ancestry:
            continue
        matched = [
            w for w in candidates if w.target[0] != owner and w.target[0] in ancestry
        ]
        if not matched:
            continue
        counts.subtype_unwoven += count
        counts.subtype_targets += 1
        target_text = f"{owner}.{name}:{proto}"
        counts.subtype_detail[target_text] += count
        counts.sites.append(
            [
                counts.apk,
                "subtype",
                dex_name,
                caller,
                target_text,
                "|".join(sorted({e for w in matched for e in w.events})),
                f"invokes={count} wrapper_owner={'|'.join(sorted({w.target[0] for w in matched}))}",
            ]
        )


def _excluded(method: Method, descriptor: Descriptor) -> bool:
    return method.class_descriptor.startswith(descriptor.excluded_prefixes)


def scan_apk(
    apk: Path, descriptor: Descriptor, dexdump: Path, android_jar: Path
) -> ApkCounts:
    """Measure one APK. Never raises: a failure is recorded in `error`."""
    counts = ApkCounts(apk.name)
    try:
        framework = _framework_index(android_jar)
        wrappers: list[Wrapper] = []
        invokes = _Invokes()
        apk_classes: set[str] = set()
        with tempfile.TemporaryDirectory() as scratch, zipfile.ZipFile(apk) as archive:
            dex_names = sorted(
                (n for n in archive.namelist() if re.fullmatch(r"classes\d*\.dex", n)),
                key=lambda n: int(re.sub(r"\D", "", n) or 1),
            )
            counts.dex_files = len(dex_names)
            for dex_name in dex_names:
                path = archive.extract(dex_name, scratch)
                dex = Path(path).read_bytes()
                defined = dex_class_descriptors(dex)
                apk_classes.update(defined)
                is_monitor_dex = WRAPPER_CLASS in defined
                with subprocess.Popen(
                    [str(dexdump), "-d", path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    errors="replace",
                    bufsize=1 << 20,
                ) as proc:
                    for method in parse_dexdump(proc.stdout):
                        if is_monitor_dex:
                            if method.class_descriptor == WRAPPER_CLASS:
                                wrapper = scan_wrapper(method, descriptor)
                                if wrapper is not None:
                                    wrappers.append(wrapper)
                        elif not _excluded(method, descriptor):
                            scan_method(
                                method, dex, dex_name, descriptor, counts, invokes
                            )
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"dexdump exited {proc.returncode} on {dex_name}"
                    )
                os.remove(path)
        resolve_invokes(counts, wrappers, invokes, apk_classes, descriptor, framework)
    except Exception as failure:  # noqa: BLE001 -- any unreadable APK keeps its row
        return ApkCounts(apk.name, error=f"{type(failure).__name__}: {failure}")
    return counts


@lru_cache(maxsize=1)
def _framework_index(android_jar: Path) -> FrameworkIndex:
    return FrameworkIndex(android_jar)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _detail(counter: collections.Counter) -> str:
    return "|".join(
        f"{key}:{count}"
        for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    )


def to_row(counts: ApkCounts) -> dict:
    row = {name: getattr(counts, name) for name in CSV_FIELDS}
    for name in ("arity_detail", "subtype_detail", "branch_detail"):
        row[name] = _detail(getattr(counts, name))
    return row


def totals(results: list[ApkCounts]) -> ApkCounts:
    """The trailer: sums of the numeric measures, merged details, errors counted.

    `wrappers` is the largest per-APK value rather than a sum: every APK woven with one
    monitor carries the same wrapper class, so a sum would only restate the APK count.
    """
    total = ApkCounts("TOTAL")
    for counts in results:
        for name in CSV_FIELDS:
            value = getattr(counts, name)
            if isinstance(value, int) and name != "wrappers":
                setattr(total, name, getattr(total, name) + value)
            elif isinstance(value, collections.Counter):
                getattr(total, name).update(value)
        total.wrappers = max(total.wrappers, counts.wrappers)
    failed = sum(1 for counts in results if counts.error)
    total.error = f"{failed} APK(s) failed" if failed else ""
    return total


def write_outputs(
    results: list[ApkCounts], out_csv: Path, sites_csv: Path | None
) -> ApkCounts:
    """Write the per-APK CSV with its trailer and, when asked, the sites CSV."""
    total = totals(results)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for counts in results:
            writer.writerow(to_row(counts))
        writer.writerow(to_row(total))
    if sites_csv is not None:
        sites_csv.parent.mkdir(parents=True, exist_ok=True)
        with sites_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(SITE_FIELDS)
            for counts in results:
                writer.writerows(counts.sites)
    return total


def _version_key(name: str) -> tuple:
    """Order `build-tools`/`platforms` directory names numerically, pre-releases first."""
    numbers = tuple(int(part) for part in re.findall(r"\d+", name.split("-rc")[0]))
    return numbers, "-rc" not in name


def newest_under(root: Path, relative: str) -> Path | None:
    """`root/<newest version dir>/relative`, among the directories where it exists."""
    if not root.is_dir():
        return None
    found = [d / relative for d in root.iterdir() if (d / relative).is_file()]
    return max(found, key=lambda p: _version_key(p.parent.name), default=None)


def main(argv: list[str] | None = None) -> int:
    """Run the sweep. Returns 1 when a tool is missing or any APK failed, 0 otherwise."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("apk_dir", type=Path)
    parser.add_argument("descriptor", type=Path, help="MultiSpec_1MonitorAspect.json")
    parser.add_argument("out_csv", type=Path)
    parser.add_argument(
        "--sites", type=Path, help="also write one row per counted item"
    )
    parser.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    parser.add_argument("--dexdump", type=Path)
    parser.add_argument("--android-jar", type=Path)
    args = parser.parse_args(argv)

    android_home = Path(os.environ.get("ANDROID_HOME", ""))
    dexdump = args.dexdump or newest_under(android_home / "build-tools", "dexdump")
    android_jar = args.android_jar or newest_under(
        android_home / "platforms", "android.jar"
    )
    if dexdump is None or android_jar is None:
        print(
            "dexdump or android.jar not found; set ANDROID_HOME or pass --dexdump/--android-jar",
            file=sys.stderr,
        )
        return 1
    descriptor = load_descriptor(args.descriptor)
    apks = sorted(args.apk_dir.glob("*.apk"))
    if not apks:
        print(f"no *.apk in {args.apk_dir}", file=sys.stderr)
        return 1

    with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = [
            pool.submit(scan_apk, apk, descriptor, dexdump, android_jar) for apk in apks
        ]
        results = []
        for number, future in enumerate(futures, start=1):
            results.append(future.result())
            print(
                f"[{number}/{len(apks)}] {results[-1].apk} {results[-1].error}",
                file=sys.stderr,
            )

    total = write_outputs(results, args.out_csv, args.sites)
    print(f"{len(results)} APK(s), dexdump {dexdump}, android.jar {android_jar}")
    print(
        f"(a) arity pairs {total.arity_pairs} (call sites {total.arity_call_sites}, "
        f"inline hooks {total.arity_inline_hooks})"
    )
    print(f"(b) framework-subtype invokes unwoven {total.subtype_unwoven}")
    print(
        f"(c) branch-target hooks {total.branch_target_hooks} of {total.before_hooks} before hooks"
    )
    print(
        f"(d) KeyStore getEntry/setEntry calls {total.keystore_entry_calls}, "
        f"woven {total.keystore_entry_woven}"
    )
    return 1 if total.error else 0


if __name__ == "__main__":
    raise SystemExit(main())
