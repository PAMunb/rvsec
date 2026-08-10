#!/usr/bin/env python3
"""Fail-crash sweep over the 23 merged monitors (EXEC-SET half).

Target pattern class (from FEN-KPG-NPE, batch D): a spec-authored member that
dereferences (or switches on) an object field which is only written by SOME
events (creation-initialized), reachable from an event that can arrive first.
Any uncaught throw inside Prop_1_event_* / condition helpers propagates to the
woven call site, i.e. crashes the app (dexlib2 wrappers add no try/catch).

Method:
  1. split MultiSpec_1RuntimeMonitor.java into monitor classes;
  2. per class: collect object-typed instance fields with no (or null) initializer;
  3. collect dereference sites: `switch(field)` and `field.member(...)`;
  4. collect writer sites: `field = ...` (excluding declaration);
  5. report every dereference with its enclosing method, plus whether writers
     exist and in which methods -- classification is then done in the report.
"""
import re, pathlib, collections

SP = pathlib.Path(__file__).parent
src = open(SP / "merge_run1" / "out" / "MultiSpec_1RuntimeMonitor.java").read()
lines = src.splitlines()

# class boundaries
bounds = []
for i, l in enumerate(lines):
    mm = re.match(r"(?:public final )?class (\w+Monitor)\b", l.strip())
    if mm:
        bounds.append((i, mm.group(1)))
bounds.append((len(lines), "EOF"))

SKELETON_TYPES = {"AtomicInteger"}  # RV skeleton state holder, never null-switched
PRIMS = {"int", "long", "boolean", "byte", "short", "char", "float", "double"}

def enclosing_method(idx, class_start):
    for j in range(idx, class_start, -1):
        mm = re.match(r"\s*(?:public |private |protected |final |static |synchronized |@Override )*"
                      r"(?:[\w\[\]<>., ]+)\s+(\w+)\s*\([^;]*\)\s*\{?\s*$", lines[j])
        if mm and not lines[j].strip().startswith(("if", "for", "while", "switch", "return", "else")):
            return mm.group(1)
    return "?"

print("### fail-crash sweep: creation-initialized field dereferences per monitor class")
total_derefs = 0
for (start, name), (end, _) in zip(bounds, bounds[1:]):
    if name == "EOF":
        break
    body = lines[start:end]
    fields = {}
    for j, l in enumerate(body):
        f = re.match(r"\t(?:final )?([A-Z][\w.<>\[\]]*)\s+(\w+)(\s*=\s*null)?\s*;\s*$", l)
        if f and f.group(1) not in SKELETON_TYPES and f.group(1).split("<")[0] not in PRIMS:
            fields[f.group(2)] = (f.group(1), start + j + 1)
        f2 = re.match(r"\t(?:final )?(List<[\w.<>\[\]]*>)\s+(\w+)\s*=", l)
        # initialized collections are safe; skip
    if not fields:
        continue
    hits = []
    for j, l in enumerate(body):
        for fname, (ftype, decl_ln) in fields.items():
            if re.search(rf"switch\s*\(\s*{fname}\s*\)", l):
                hits.append((start + j + 1, fname, ftype, "SWITCH", l.strip()))
            elif re.search(rf"(?<![\w.]){fname}\s*\.\s*\w+\s*\(", l):
                hits.append((start + j + 1, fname, ftype, "DEREF", l.strip()))
    writers = collections.defaultdict(list)
    for j, l in enumerate(body):
        for fname in fields:
            if re.search(rf"(?:this\.)?\b{fname}\s*=\s*[^=]", l) and f"{fname} =" not in l.split("//")[0].split(";")[-1]:
                if not re.match(rf"\t(?:final )?[A-Z][\w.<>\[\]]*\s+{fname}\b", l):  # skip declaration
                    writers[fname].append((start + j + 1, enclosing_method(start + j, start)))
    if hits:
        print(f"\n-- {name} (fields: {', '.join(f'{v[0]} {k}' for k, v in fields.items())})")
        for ln, fname, ftype, kind, txt in hits:
            meth = enclosing_method(ln - 1, start)
            print(f"   {kind:6s} {fname:12s} line {ln} in {meth}(): {txt[:100]}")
            total_derefs += 1
        for fname, ws in writers.items():
            print(f"   writers of {fname}: " + ", ".join(f"line {ln} in {m}()" for ln, m in ws))
print(f"\ntotal dereference sites flagged: {total_derefs}")
