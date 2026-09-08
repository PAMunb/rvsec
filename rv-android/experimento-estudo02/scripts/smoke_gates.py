#!/usr/bin/env python3
"""Confere os seis portões do smoke `estudo02smoke` (docs/20260908_estudo02.md §7).

    uv run python experimento-estudo02/scripts/smoke_gates.py

O smoke existe para provar, antes de comprometer ~6,2 dias de máquina, as três
ferramentas que dependem de infraestrutura **fora** da imagem `rvandroid`:
`humanoid` (sidecar HTTP `rv-humanoid`), `ares` e `qtesting` (containers irmãos
criados pelo daemon do host via `/var/run/docker.sock`). As outras oito rodam
dentro da imagem e já têm precedente local; estas três não têm nenhum, e é
justamente por isso que o portão 4 lê o log do sidecar e o `docker ps -a` em vez
de acreditar no `COMPLETED`.

Cada portão é bloqueante. A regra de contagem é a de sempre: **identidade**
`(apk, ferramenta, variante, repetição, timeout)`, último/melhor registro, nunca
`task_id` (o resume acrescenta UUIDs novos) e nunca grep cru em `tasks.json` (o
estado COMPLETED também aparece em `result.state_transitions[]` e conta em dobro).

Sobre o portão 2 (C3, "o traço carrega pelo menos um passo"): quatro das onze
ferramentas — `droidbot` nas quatro políticas, `droidmate`, `ares`, `qtesting` —
não têm **nenhum** traço anterior nesta árvore, então não há formato conhecido
para casar. O portão reprova o caso inequívoco (traço ausente ou vazio) e
**reporta** a contagem de linhas de todas as 22 identidades, marcando `?` as que
ficam abaixo de TRACE_LINES_SUSPECT para leitura humana. Congelar aqui um
limiar por ferramenta seria inventar um oráculo que o smoke ainda vai produzir.
"""
import csv
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "data" / "results"
CONTAINERS = ["estudo02smoke_00", "estudo02smoke_01"]
HUMANOID_CONTAINER = "rv-humanoid"

TIMEOUT = 60
TEARDOWN_GRACE = 45  # APERV_TEARDOWN_GRACE_S — o piso de C2 é o orçamento menos a folga
FLOOR = TIMEOUT - TEARDOWN_GRACE

APKS = ["app.michaelwuensch.bitbanana_79.apk", "com.tananaev.passportreader_22.apk"]
ARMS = [
    "monkey", "droidbot:dfs_greedy", "droidbot:bfs_greedy", "droidbot:dfs_naive",
    "droidbot:bfs_naive", "ape", "droidmate", "humanoid", "ares", "fastbot", "qtesting",
]
EXPECTED_IDENTITIES = len(APKS) * len(ARMS)

#: Abaixo disto o traço vira `?` no relatório — não reprova, só pede olho humano.
TRACE_LINES_SUSPECT = 10

#: O literal que a E0 do `jca_android` substituiu (gh104 G1); se voltar, a mensagem é muda.
MUTE_MESSAGE = "unknown"
#: O que sobra quando o sítio interpola um valor observado vazio.
EMPTY_OBSERVED_SUFFIX = "but found ."

COV_RE = re.compile(r"RVSEC-COV\s*:\s*(?P<sig>.+?)\s*$")
VIOLATION_RE = re.compile(r"\bRVSEC\s+:\s*(?P<body>.+?)\s*$")
MSG_RE = re.compile(r"msg='(?P<msg>(?:\\'|[^'])*)'")
#: Nomes dos irmãos: `ares_<8 hex do task id>` / `qtesting_<8 hex>` (rv_tools/builtin/*/tool.py).
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
    """`ape`/`monkey` gravam `variant='default'`; o consolidador colapsa para o nome seco."""
    return name if not variant or variant == "default" else f"{name}:{variant}"


# --- Identidades ------------------------------------------------------------
by_ident = {}
for c in CONTAINERS:
    p = RES / c / c / "tasks.json"
    if not p.exists():
        print(f"!! tasks.json ausente: {p}")
        continue
    doc = json.loads(p.read_text())
    for t in (doc["tasks"] if isinstance(doc, dict) else doc):
        cfg, res = t["config"], t["result"]
        tc = cfg["tool_config"]
        ident = (cfg["apk_name"], arm_label(tc["name"], tc.get("variant")),
                 cfg["repetition"], cfg["timeout"])
        if ident not in by_ident or res.get("state") == "COMPLETED":
            by_ident[ident] = (c, res)

print(f"identidades distintas: {len(by_ident)} (esperadas {EXPECTED_IDENTITIES})\n")


def artifact(container, res, key):
    """Resolve um caminho de `tasks.json` (relativo a `results/`) no host."""
    rel = res.get(key) or ""
    return RES / container / rel.replace("results/", "", 1) if rel else None


def sh(*args):
    """Roda um comando e devolve stdout+stderr; nunca levanta."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        return r.stdout + r.stderr
    except Exception as e:  # docker ausente ou container já removido
        return f"!! {e}"


# --- Portão 1: C1 + completude (C6) ----------------------------------------
esperadas = {(a, arm, 1, TIMEOUT) for a in APKS for arm in ARMS}
faltando = sorted(esperadas - set(by_ident))
sobrando = sorted(set(by_ident) - esperadas)
clean = [i for i, (_, r) in by_ident.items()
         if r.get("state") == "COMPLETED" and not r.get("error_message")]
ev = [f"identidades={len(by_ident)} limpas={len(clean)}/{EXPECTED_IDENTITIES}"]
ev += [f"AUSENTE: {i[1]} {i[0]}" for i in faltando]
ev += [f"INESPERADA: {i[1]} {i[0]}" for i in sobrando]
ev += [f"{i[1]:<20} {i[0][:34]:<34} {r.get('state'):<10} {r.get('error_message') or ''}"
       for i, (_, r) in sorted(by_ident.items())]
gate(1, f"{EXPECTED_IDENTITIES}/{EXPECTED_IDENTITIES} identidades COMPLETED com error_message vazio",
     not faltando and not sobrando and len(clean) == EXPECTED_IDENTITIES, ev)

# --- Portão 2: C2 (tempo) + C3 (traço) -------------------------------------
# `ok` nasce da existência de identidades: um portão sobre conjunto vazio não passa.
ev, ok = [], len(by_ident) == EXPECTED_IDENTITIES
for ident, (c, r) in sorted(by_ident.items()):
    el = r.get("execution_time_seconds") or 0
    tf = artifact(c, r, "trace_file")
    if tf and tf.exists():
        linhas = sum(1 for ln in tf.read_text(errors="ignore").splitlines() if ln.strip())
        tamanho = tf.stat().st_size
    else:
        linhas, tamanho = -1, -1
    c2 = el >= FLOOR
    c3 = linhas >= 2
    ok &= c2 and c3
    marca = "" if c2 else f"  << C2: abaixo do piso ({FLOOR} s)"
    if linhas < 0:
        marca += "  << C3: traço AUSENTE"
    elif not c3:
        marca += "  << C3: traço sem passo"
    elif linhas < TRACE_LINES_SUSPECT:
        marca += "  ? traço curto — conferir à mão"
    ev.append(f"{ident[1]:<20} {ident[0][:30]:<30} {el:>5} s  traço={linhas:>6} linhas"
              f" / {tamanho:>9} B{marca}")
gate(2, f"C2 execução ≥ {FLOOR} s e C3 traço com ao menos um passo", ok, ev)

# --- Portão 3: C4 (assinatura RVSEC-COV) + C5 (cobertura) ------------------
ev, ok = [], len(by_ident) == EXPECTED_IDENTITIES
for ident, (c, r) in sorted(by_ident.items()):
    lf = artifact(c, r, "logcat_file")
    sigs = set()
    if lf and lf.exists():
        for ln in lf.read_text(errors="ignore").splitlines():
            m = COV_RE.search(ln)
            if m:
                sigs.add(m.group("sig"))
    m = r.get("coverage_metrics") or {}
    cm, ca = m.get("method_coverage") or 0, m.get("activities_coverage") or 0
    bom = len(sigs) >= 1 and cm > 0 and ca > 0
    ok &= bom
    ev.append(f"{ident[1]:<20} {ident[0][:30]:<30} cov_sigs={len(sigs):>4} "
              f"cov_method={cm:6.2f} cov_act={ca:6.2f} "
              f"cov_mop={m.get('methods_mop_reachable_coverage', 0) or 0:6.2f} "
              f"mop_unique={m.get('total_errors', 0) or 0:.0f}"
              + ("" if bom else "  << C4/C5"))
gate(3, "C4 ≥ 1 assinatura RVSEC-COV distinta e C5 cov_method > 0 e cov_act > 0", ok, ev)

# --- Portão 4: a infraestrutura fora da imagem -----------------------------
ev, ok = [], True
logs = sh("docker", "logs", HUMANOID_CONTAINER)
pedidos = [ln for ln in logs.splitlines() if "HTTP/1" in ln or re.search(r"\b(POST|GET)\b", ln)]
falou = len(pedidos) > 0
ok &= falou
ev.append(f"{HUMANOID_CONTAINER}: {len(logs.splitlines())} linhas de log, "
          f"{len(pedidos)} com requisição HTTP"
          + ("" if falou else "  << o braço humanoid NÃO falou com o sidecar"))
ev += [f"   {ln[:120]}" for ln in pedidos[-3:]]

nomes = [ln.strip() for ln in sh("docker", "ps", "-a", "--format", "{{.Names}}").splitlines()]
orfaos = [n for n in nomes if SIBLING_RE.match(n)]
ok &= not orfaos
ev.append(f"irmãos ares_*/qtesting_* remanescentes: {len(orfaos)}"
          + ("" if not orfaos else f"  << ÓRFÃOS: {orfaos}"))
gate(4, "humanoid falou com o sidecar; ares/qtesting sem irmão órfão", ok, ev)

# --- Portão 5: ≥ 1 violação por APK, sem mensagem muda ---------------------
ev, ok = [], len(by_ident) == EXPECTED_IDENTITIES
por_apk = defaultdict(int)
mudas = []
for ident, (c, r) in sorted(by_ident.items()):
    lf = artifact(c, r, "logcat_file")
    if not (lf and lf.exists()):
        continue
    n = 0
    for ln in lf.read_text(errors="ignore").splitlines():
        m = VIOLATION_RE.search(ln)
        if not m:
            continue
        n += 1
        corpo = m.group("body")
        msg = MSG_RE.search(corpo)
        texto = msg.group("msg") if msg else None
        if texto is None or texto == MUTE_MESSAGE or texto.endswith(EMPTY_OBSERVED_SUFFIX):
            mudas.append(f"{ident[1]} {ident[0]}: {corpo[:110]}")
    por_apk[ident[0]] += n
    if n:
        ev.append(f"{ident[1]:<20} {ident[0][:30]:<30} violações={n}")
for a in APKS:
    if not por_apk.get(a):
        ok = False
        ev.append(f"SEM VIOLAÇÃO em nenhuma ferramenta: {a}")
if mudas:
    ok = False
    ev.append(f"mensagens mudas ('{MUTE_MESSAGE}' ou terminadas em '{EMPTY_OBSERVED_SUFFIX}'): "
              f"{len(mudas)}")
    ev += [f"   {s}" for s in mudas[:5]]
else:
    ev.append("nenhuma mensagem muda")
gate(5, "≥ 1 violação RVSEC por APK em alguma ferramenta, com mensagem legível", ok, ev)

# --- Portão 6: zero VerifyError --------------------------------------------
ev = []
for c in CONTAINERS:
    for p in (RES / c).rglob("*.logcat"):
        n = p.read_text(errors="ignore").count("VerifyError")
        if n:
            ev.append(f"{p.name}: {n} VerifyError no logcat")
    ae = RES / c / c / "app_events.csv"
    if not ae.exists():
        ev.append(f"!! {ae} ausente — diagnósticos deveriam estar ligados (RV_LOGCAT_DIAGNOSTICS)")
        continue
    with ae.open(newline="") as fh:
        eventos = list(csv.DictReader(fh))
    ve = [e for e in eventos if (e.get("category") or "") == "verify_error"]
    if ve:
        ev.append(f"{c}/app_events.csv: {len(ve)} verify_error")
        ev += [f"   {e.get('process')} {e.get('exception_class')} {str(e.get('message'))[:80]}"
               for e in ve[:5]]
    crashes = [e for e in eventos if (e.get("category") or "") in ("crash", "anr")]
    print(f"        (informativo) {c}/app_events.csv: {len(eventos)} eventos, "
          f"{len(crashes)} crash/anr")
gate(6, "zero VerifyError nos logcats e no app_events.csv", not ev,
     ev or ["nenhum VerifyError em nenhum logcat nem no app_events.csv"])

# --- Calibração do ciclo (não bloqueante) ----------------------------------
print("--- ciclo por run (calibra o wall-clock da campanha) ---")
els = [r.get("execution_time_seconds") for _, r in by_ident.values()
       if r.get("execution_time_seconds")]
if els:
    media = sum(els) / len(els)
    sobrecarga = media - TIMEOUT
    print(f"  média {media:.1f} s para orçamento de {TIMEOUT} s -> sobrecarga ~{sobrecarga:.1f} s/run")
    for t in (60, 180, 300):
        print(f"  => ciclo projetado a {t:>3} s: {t + sobrecarga:.0f} s/run")
    # 11 braços × 163 APKs × 3 reps × 3 timeouts em 10 containers.
    total_s = 11 * 163 * 3 * sum(t + sobrecarga for t in (60, 180, 300))
    print(f"  => 16 137 tasks em 10 containers: {total_s / 10 / 86400:.1f} dias")

print()
if fails:
    print(f"SMOKE REPROVADO — portões que falharam: {fails}")
    sys.exit(1)
print("SMOKE APROVADO — todos os seis portões passaram")
