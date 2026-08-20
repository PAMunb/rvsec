import re, glob, os, collections

DIR = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30"
SECTIONS = {"SPEC","OBJECTS","EVENTS","ORDER","CONSTRAINTS","FORBIDDEN","FORBIDDEN:","REQUIRES","ENSURES","NEGATES"}

def top_level_commas(s):
    depth = 0; n = 0
    for ch in s:
        if ch in "({": depth += 1
        elif ch in ")}": depth -= 1
        elif ch == "," and depth == 0: n += 1
    return n

rules = {}
for path in sorted(glob.glob(os.path.join(DIR, "*.cryptsl"))):
    name = os.path.basename(path).replace(".cryptsl","")
    sec = None
    buf = collections.defaultdict(list)
    for raw in open(path):
        line = raw.strip()
        if not line: continue
        head = line.split()[0].rstrip(":")
        if head in {"SPEC","OBJECTS","EVENTS","ORDER","CONSTRAINTS","FORBIDDEN","REQUIRES","ENSURES","NEGATES"} and (line == head or head in ("SPEC",) or line.rstrip(":") == head):
            sec = head
            rest = line[len(head):].lstrip(": ").strip()
            if rest and sec in ("REQUIRES","ENSURES","NEGATES"):
                buf[sec].append(rest)
            continue
        if sec in ("REQUIRES","ENSURES","NEGATES"):
            buf[sec].append(line)
    # join and split clauses on ';'
    parsed = {}
    for sec in ("REQUIRES","ENSURES","NEGATES"):
        text = " ".join(buf[sec])
        clauses = [c.strip() for c in text.split(";") if c.strip()]
        out = []
        for c in clauses:
            m = re.search(r'(!?)([A-Za-z_]\w*)\[([^\]]*)\]', c)
            if not m:
                print(f"WARN no predicate in clause: {name} {sec}: {c!r}")
                continue
            neg, pred, args = m.group(1)=="!", m.group(2), m.group(3)
            arity = top_level_commas(args) + 1 if args.strip() else 0
            out.append((pred, arity, neg, c))
        parsed[sec] = out
    rules[name] = parsed

tot = {s: sum(len(rules[r][s]) for r in rules) for s in ("ENSURES","REQUIRES","NEGATES")}
print("regras:", len(rules))
print("clausulas:", tot)

all_preds = set()
for r in rules:
    for s in ("ENSURES","REQUIRES","NEGATES"):
        for (p,a,n,c) in rules[r][s]:
            all_preds.add(p)
print("predicados distintos (E+R+N):", len(all_preds))
er_preds = set(p for r in rules for s in ("ENSURES","REQUIRES") for (p,a,n,c) in rules[r][s])
print("predicados distintos (E+R):", len(er_preds))

# arity histogram over ENSURES+REQUIRES clauses
ar = collections.Counter()
for r in rules:
    for s in ("ENSURES","REQUIRES"):
        for (p,a,n,c) in rules[r][s]:
            ar[a] += 1
print("aridade (E+R):", dict(sorted(ar.items())))
ar_n = collections.Counter()
for r in rules:
    for (p,a,n,c) in rules[r]["NEGATES"]:
        ar_n[a] += 1
print("aridade (NEGATES):", dict(sorted(ar_n.items())))

# producers / consumers
producers = collections.defaultdict(set)   # pred -> set of rules ENSURING it
consumers = collections.defaultdict(set)   # pred -> set of rules REQUIRING it
for r in rules:
    for (p,a,n,c) in rules[r]["ENSURES"]:
        producers[p].add(r)
    for (p,a,n,c) in rules[r]["REQUIRES"]:
        consumers[p].add(r)

req_preds = set(consumers)
print("\npredicados exigidos (REQUIRES):", len(req_preds), sorted(req_preds))
no_producer = sorted(p for p in req_preds if p not in producers)
print("exigidos sem produtor:", no_producer)
connectable = sorted(p for p in req_preds if p in producers)
print("predicados conectaveis:", len(connectable))

pairs = [(p, r) for p in connectable for r in sorted(consumers[p])]
print("pares (predicado, regra-consumidora):", len(pairs))
edges = [(prod, p, cons) for p in connectable for cons in sorted(consumers[p]) for prod in sorted(producers[p])]
print("arestas regra-produtora -> regra-consumidora (via predicado):", len(edges))

print("\n--- detalhe pares ---")
for p in connectable:
    print(f"  {p}: produtores={sorted(producers[p])} consumidores={sorted(consumers[p])}")

print("\n--- NEGATES ---")
for r in rules:
    for (p,a,n,c) in rules[r]["NEGATES"]:
        print(f"  {r}: {c};")

print("\n--- clausulas quaternarias ---")
for r in rules:
    for s in ("ENSURES","REQUIRES"):
        for (p,a,n,c) in rules[r][s]:
            if a >= 3: print(f"  {r} {s} arity={a}: {c};")

# duplicate (pred, rule) REQUIRES clauses (clause count vs distinct pair count)
cl_pairs = collections.Counter()
for r in rules:
    for (p,a,n,c) in rules[r]["REQUIRES"]:
        cl_pairs[(p,r)] += 1
dups = {k:v for k,v in cl_pairs.items() if v>1}
print("\npares REQUIRES duplicados (mesma regra exige mesmo predicado 2x):", dups)
