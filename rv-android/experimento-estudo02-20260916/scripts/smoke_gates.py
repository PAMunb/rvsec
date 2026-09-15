#!/usr/bin/env python3
"""Confere os portões do smoke da re-execução da estudo02 (docs/20260916_plano.md §7).

    uv run python experimento-estudo02-20260916/scripts/smoke_gates.py

Rodar com os containers do smoke já parados e ANTES do `down`: o portão 4 lê o log do sidecar
`rv-humanoid` e o portão 9 lê `docker inspect` de cada container.

O smoke tem dois trabalhos:

- **Os mesmos seis portões da estudo02** (identidades, tempo, traço, cobertura, infraestrutura
  fora da imagem, violações legíveis, zero VerifyError). Os doze APKs daqui não são os dois da
  estudo02, e alguns pares (APK, braço) terminaram numa categoria declarada na estudo02: zero
  estrutural do `qtesting`, parada da ferramenta, lançamento fora do app. Esses pares não
  reprovam os portões 1–3; aparecem marcados `conhecido`, com a categoria que tiveram lá
  (`experimento-estudo02/docs/20260914_admissibilidade.json`). Categoria nova reprova.
- **O que a gh114 mudou e a campanha lê** (portões 7–9): códigos rotulados e evidência só em
  `-NOBS-`; o fim do disparo duplo; a exportação final escrita pelo próprio container.

Por fim, **calibra a contenção com 12 containers** (não bloqueante, com limiares no plano §4):
a mediana de boot + install e o overhead total por task, e a projeção em dias.

A regra de contagem é a de sempre: identidade `(apk, braço, rep, orçamento)`, registro
COMPLETED quando houver, nunca `task_id` e nunca grep cru no `tasks.json`.
"""
import csv
import json
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campanha import (ARMS, CONTAINERS, ROOT, RESULTS, SMOKE_APKS, SMOKE_CONTAINERS,  # noqa: E402
                      SMOKE_NAME, SMOKE_TIMEOUT, TIMEOUTS, REPS, FILTERS, containers)

SMOKE = containers(SMOKE_NAME, SMOKE_CONTAINERS)
HUMANOID_CONTAINER = "rv-humanoid"
EXPECTED_IDENTITIES = len(SMOKE_APKS) * len(ARMS)
TOOL_GRACE_S = 5  # o mesmo piso do C2 do admissibility.py: orçamento menos 5 s de tempo da ferramenta
ESTUDO02_ADM = ROOT / "experimento-estudo02" / "docs" / "20260914_admissibilidade.json"
CODES_CSV = ROOT.parent / "rvsec" / "rvsec-mop" / "src" / "main" / "resources" / "jca_android" / "codes.csv"

#: O vocabulário fechado de rótulos da gh114 (INV-INS-164).
LABELS = {"platform-default", "upstream-refused", "application-manager", "random-key-material",
          "creation-unobserved", "reuse-after-final"}
#: As três specs em que `getInstance(String)` disparava também o evento de dois argumentos (A1).
A1_SPECS = {"TrustManagerFactorySpec", "KeyManagerFactorySpec", "SecureRandomSpec"}
#: Os seis arquivos da exportação final que a estudo02 teve de regerar offline (A6).
EXPORTS = ("app_events.csv", "coverage.csv", "errors.csv", "performance.csv", "results.json", "summary.csv")
TRACE_LINES_SUSPECT = 10
MUTE_MESSAGE = "unknown"
EMPTY_OBSERVED_SUFFIX = "but found ."
EVIDENCE_RE = re.compile(r" (vfp|vcls)='")

COV_RE = re.compile(r"RVSEC-COV\s*:\s*(?P<sig>.+?)\s*$")
VIOLATION_RE = re.compile(r"\bRVSEC\s+:\s*(?P<body>.+?)\s*$")
MSG_RE = re.compile(r"msg='(?P<msg>(?:\\'|[^'])*)'")
SIBLING_RE = re.compile(r"^(ares|qtesting)_[0-9a-f]{8}$")

fails = []


def gate(n, title, ok, evidence):
    print(f"[{'PASS' if ok else 'FAIL'}] Portão {n} — {title}")
    for line in evidence:
        print(f"        {line}")
    if not ok:
        fails.append(n)
    print()


def arm_label(name, variant):
    return name if not variant or variant == "default" else f"{name}:{variant}"


def ts(value):
    return datetime.fromisoformat(value) if value else None


def sh(*args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        return r.stdout + r.stderr
    except Exception as e:
        return f"!! {e}"


def artifact(container, res, key):
    rel = res.get(key) or ""
    return RESULTS / container / rel.replace("results/", "", 1) if rel else None


# --- Identidades ------------------------------------------------------------
by_ident = {}
for c in SMOKE:
    p = RESULTS / c / c / "tasks.json"
    if not p.exists():
        print(f"!! tasks.json ausente: {p}")
        continue
    doc = json.loads(p.read_text())
    for t in (doc["tasks"] if isinstance(doc, dict) else doc):
        cfg, res = t["config"], t["result"]
        tc = cfg["tool_config"]
        ident = (cfg["apk_name"], arm_label(tc["name"], tc.get("variant")), cfg["repetition"], cfg["timeout"])
        if ident not in by_ident or res.get("state") == "COMPLETED":
            by_ident[ident] = (c, res)
print(f"identidades distintas: {len(by_ident)} (esperadas {EXPECTED_IDENTITIES})\n")

adm02 = json.loads(ESTUDO02_ADM.read_text()) if ESTUDO02_ADM.exists() else {}


def conhecido(ident):
    """Categoria declarada que o mesmo (APK, braço, rep, orçamento) teve na estudo02, ou ''."""
    v = adm02.get("|".join(str(x) for x in ident)) or {}
    for key, nome in (("structural", "zero estrutural"), ("tool_stop", "parada da ferramenta"),
                      ("foreign_launcher", "lançamento fora do app")):
        if v.get(key):
            return nome
    return ""


# --- Portão 1: C1 + completude ---------------------------------------------
esperadas = {(a, arm, 1, SMOKE_TIMEOUT) for a in SMOKE_APKS for arm in ARMS}
faltando = sorted(esperadas - set(by_ident))
sobrando = sorted(set(by_ident) - esperadas)
clean = [i for i, (_, r) in by_ident.items() if r.get("state") == "COMPLETED" and not r.get("error_message")]
ev = [f"identidades={len(by_ident)} limpas={len(clean)}/{EXPECTED_IDENTITIES}"]
ev += [f"AUSENTE: {i[1]} {i[0]}" for i in faltando] + [f"INESPERADA: {i[1]} {i[0]}" for i in sobrando]
ev += [f"{i[1]:<20} {i[0][:34]:<34} {r.get('state')} {r.get('error_message') or ''}"
       for i, (_, r) in sorted(by_ident.items()) if i not in clean]
gate(1, f"{EXPECTED_IDENTITIES} identidades COMPLETED com error_message vazio",
     not faltando and not sobrando and len(clean) == EXPECTED_IDENTITIES, ev)

# --- Portão 2: C2 (tempo da ferramenta) + C3 (traço) ------------------------
ev, ok = [], len(by_ident) == EXPECTED_IDENTITIES
for ident, (c, r) in sorted(by_ident.items()):
    start, end = ts(r.get("tool_execution_start")), ts(r.get("end_time"))
    tool_s = int((end - start).total_seconds()) if start and end else 0
    tf = artifact(c, r, "trace_file")
    linhas = sum(1 for ln in tf.read_text(errors="ignore").splitlines() if ln.strip()) if tf and tf.exists() else -1
    c2, c3 = tool_s >= ident[3] - TOOL_GRACE_S, linhas >= 2
    marca = "" if c2 else "  << C2"
    marca += "  << C3 traço AUSENTE" if linhas < 0 else ("  << C3" if not c3 else
                                                         ("  ? traço curto" if linhas < TRACE_LINES_SUSPECT else ""))
    k = conhecido(ident)
    if not (c2 and c3):
        marca += f"  (conhecido: {k})" if k else ""
        ok &= bool(k)
    ev.append(f"{ident[1]:<20} {ident[0][:30]:<30} ferramenta={tool_s:>4} s traço={linhas:>6} linhas{marca}")
gate(2, f"C2 tempo da ferramenta ≥ {SMOKE_TIMEOUT - TOOL_GRACE_S} s e C3 traço com passo", ok, ev)

# --- Portão 3: C4 + C5 -------------------------------------------------------
ev, ok = [], len(by_ident) == EXPECTED_IDENTITIES
for ident, (c, r) in sorted(by_ident.items()):
    lf = artifact(c, r, "logcat_file")
    sigs = set()
    if lf and lf.exists():
        sigs = {m.group("sig") for ln in lf.read_text(errors="ignore").splitlines() if (m := COV_RE.search(ln))}
    m = r.get("coverage_metrics") or {}
    cm, ca = m.get("method_coverage") or 0, m.get("activities_coverage") or 0
    bom = len(sigs) >= 1 and cm > 0 and ca > 0
    k = "" if bom else conhecido(ident)
    ok &= bom or bool(k)
    ev.append(f"{ident[1]:<20} {ident[0][:30]:<30} sigs={len(sigs):>4} cov_method={cm:6.2f} cov_act={ca:6.2f}"
              + ("" if bom else f"  << C4/C5{f' (conhecido: {k})' if k else ''}"))
gate(3, "C4 ≥ 1 assinatura RVSEC-COV e C5 cov_method > 0 e cov_act > 0", ok, ev)

# --- Portão 4: infraestrutura fora da imagem --------------------------------
logs = sh("docker", "logs", HUMANOID_CONTAINER)
pedidos = [ln for ln in logs.splitlines() if "HTTP/1" in ln or re.search(r"\b(POST|GET)\b", ln)]
orfaos = [n for n in sh("docker", "ps", "-a", "--format", "{{.Names}}").split() if SIBLING_RE.match(n)]
gate(4, "humanoid falou com o sidecar; ares/qtesting sem irmão órfão", bool(pedidos) and not orfaos,
     [f"{HUMANOID_CONTAINER}: {len(pedidos)} linhas com requisição HTTP",
      f"irmãos ares_*/qtesting_* remanescentes: {len(orfaos)} {orfaos if orfaos else ''}"])

# --- Portão 5: violações legíveis --------------------------------------------
ev, ok, por_apk, mudas = [], len(by_ident) == EXPECTED_IDENTITIES, defaultdict(int), []
for ident, (c, r) in sorted(by_ident.items()):
    lf = artifact(c, r, "logcat_file")
    if not (lf and lf.exists()):
        continue
    for ln in lf.read_text(errors="ignore").splitlines():
        if not (m := VIOLATION_RE.search(ln)):
            continue
        por_apk[ident[0]] += 1
        msg = MSG_RE.search(m.group("body"))
        texto = msg.group("msg") if msg else None
        if texto is None or texto == MUTE_MESSAGE or texto.endswith(EMPTY_OBSERVED_SUFFIX):
            mudas.append(f"{ident[1]} {ident[0]}: {m.group('body')[:110]}")
sem = [a for a in SMOKE_APKS if not por_apk.get(a)]
ok &= not sem and not mudas
ev += [f"{a[:40]:<40} violações={por_apk.get(a, 0)}" for a in SMOKE_APKS]
ev += [f"mensagens mudas: {len(mudas)}"] + [f"   {s}" for s in mudas[:5]]
gate(5, "≥ 1 violação RVSEC por APK, com mensagem legível", ok, ev)

# --- Portão 6: zero VerifyError ----------------------------------------------
ev = []
for c in SMOKE:
    for p in (RESULTS / c).rglob("*.logcat"):
        if (n := p.read_text(errors="ignore").count("VerifyError")):
            ev.append(f"{p.name}: {n} VerifyError")
    ae = RESULTS / c / c / "app_events.csv"
    if ae.exists():
        ve = [e for e in csv.DictReader(ae.open(newline="")) if e.get("category") == "verify_error"]
        ev += [f"{c}: verify_error {e.get('process')} {e.get('exception_class')}" for e in ve[:5]]
gate(6, "zero VerifyError nos logcats e no app_events.csv", not ev, ev or ["nenhum"])

# --- Portões 7 e 8: errors.csv com o vocabulário da gh114 ----------------------
rows = []
for c in SMOKE:
    p = RESULTS / c / c / "errors.csv"
    if p.exists():
        rows += list(csv.DictReader(p.open(newline="")))
label_of = {}
if CODES_CSV.exists():
    cols = csv.DictReader(CODES_CSV.open(newline=""))
    if "label" in (cols.fieldnames or []):
        label_of = {r["code"]: r["label"] for r in cols}
rotulados = Counter(label_of.get(r["code"], "") for r in rows if label_of.get(r["code"]) in LABELS)
evid = [r for r in rows if EVIDENCE_RE.search(r.get("message", ""))]
evid_fora = [r for r in evid if "-NOBS-" not in r["code"]]
nobs = [r for r in rows if "-NOBS-" in r["code"]]
evid_uniq = [r for r in rows if EVIDENCE_RE.search(r.get("unique_msg", "").rsplit(":::", 1)[-1])]
ev = [f"codes.csv local com coluna label: {'sim' if label_of else 'NÃO'} ({CODES_CSV})",
      f"linhas do errors.csv: {len(rows)}; com código rotulado: {sum(rotulados.values())} {dict(rotulados)}",
      f"linhas -NOBS-: {len(nobs)}; com vfp/vcls: {sum(1 for r in nobs if EVIDENCE_RE.search(r['message']))}",
      f"evidência fora de -NOBS-: {len(evid_fora)}",
      f"evidência dentro do unique_msg (inflaria o mop_unique): {len(evid_uniq)}"]
ev += [f"   {r['spec']} {r['code']} {r['message'][:90]}" for r in evid_fora[:5]]
gate(7, "códigos rotulados presentes; vfp/vcls só em -NOBS- e fora do unique_msg",
     bool(label_of) and sum(rotulados.values()) > 0 and bool(evid) and not evid_fora and not evid_uniq, ev)

g2 = [r for r in rows if r["spec"] in A1_SPECS and "-ORDER-" in r["code"] and r.get("event") == "g2"]
gate(8, "fim do disparo duplo: nenhum -ORDER- de TrustManagerFactory/KeyManagerFactory/SecureRandom com gatilho g2",
     not g2, [f"{len(g2)} linha(s)"] + [f"   {r['apk']} {r['tool']} {r['class']}.{r['method']}" for r in g2[:8]])

# --- Portão 9: exportação final pelo próprio container, sem OOM ----------------
ev, ok = [], True
for c in SMOKE:
    base = RESULTS / c / c
    faltam = [f for f in EXPORTS if not (base / f).exists()]
    insp = sh("docker", "inspect", c, "--format", "{{.State.ExitCode}} {{.State.OOMKilled}} {{.RestartCount}}").split()
    oom = len(insp) >= 2 and insp[1] == "true"
    bom = not faltam and not oom and bool(insp) and insp[0] == "0"
    ok &= bom
    ev.append(f"{c}: exit/oom/restarts={' '.join(insp[:3]) or '?'} faltam={faltam or '-'}" + ("" if bom else "  <<"))
gate(9, "cada container saiu 0, sem OOM, e escreveu os seis arquivos da exportação", ok, ev)

# --- Calibração da contenção (não bloqueante) ---------------------------------
print("--- contenção com", SMOKE_CONTAINERS, "containers (plano §4) ---")
pre, total = [], []
for ident, (_, r) in by_ident.items():
    s, t, e = ts(r.get("start_time")), ts(r.get("tool_execution_start")), ts(r.get("end_time"))
    if r.get("state") == "COMPLETED" and s and t and e:
        pre.append((t - s).total_seconds())
        total.append((e - s).total_seconds() - ident[3])
if pre:
    mp, mt = statistics.median(pre), statistics.median(total)
    print(f"  boot+install mediana {mp:.1f} s (estudo02 com 10: 54,0 s; limiar ≤ 60 s)")
    print(f"  overhead total mediana {mt:.1f} s (estudo02 com 10: 65,3 s; limiar ≤ 75 s; > 90 s: voltar a 10–11)")
    corpus = (FILTERS / "corpus.txt")
    n_apks = len(corpus.read_text().split()) if corpus.exists() else 163
    maior = -(-n_apks // CONTAINERS)
    # Base medida na estudo02: 6,86 h por APK (pior container, retentativas incluídas) com overhead
    # mediano de 65,3 s; cada segundo a mais de overhead custa uma vez por run do APK.
    runs_apk = len(ARMS) * len(REPS) * len(TIMEOUTS)
    h_apk = 6.86 + runs_apk * (mt - 65.3) / 3600
    print(f"  projeção: {n_apks} APKs, maior lote {maior} × {h_apk:.2f} h/APK → {maior * h_apk / 24:.2f} dias de "
          f"máquina em {CONTAINERS} containers (sem religamentos, reparo e a espera antes dele; plano §4.2)")

print()
if fails:
    print(f"SMOKE REPROVADO — portões que falharam: {fails}")
    sys.exit(1)
print("SMOKE APROVADO — os nove portões passaram")
