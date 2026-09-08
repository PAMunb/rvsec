#!/usr/bin/env python3
"""Gera os artefatos de uma comparacao multi-tool no rv-platform.

Saidas (todas com o mesmo --name, para nada ficar solto):
  data/<name>_filters/batch_NN.txt        split round-robin dos APKs (1 por container)
  data/<name>_filters/.gitkeep
  docker/docker-compose.<name>.yml        compose com N containers + SGLang condicional
  docs/<YYYYMMDD>_<name>.md               plano (padrao docs/20260619_comparacao_aperv.md)
  data/results/<name>_compare_meta.json   metadados lidos por monitor/consolidate

Exemplo (comparacao APE x APE-RV, como a de 2026-06-19):
  python3 .claude/skills/rv-experiment-compare/scripts/gen_compare.py \
    --name cmp --dataset /caminho/APKS_FINAL_JCA_DEXLIB_20260604 \
    --tools "ape,aperv:sata,aperv:sata_mop,aperv:sata_mop_llm@llm_percentage=0.9" \
    --timeout 300 --reps 3 --containers 6 --spec-set jca --with-sglang

Exemplo (comparacao sem LLM, sem GPU):
  python3 .../gen_compare.py --name baseline --dataset /caminho/apks \
    --tools "monkey,droidbot:dfs_greedy,aperv:sata" --containers 4
"""
import argparse, json, os, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # rv-android/
SKILL_DIR = Path(__file__).resolve().parents[1]


def list_apks(dataset: Path, avd_abi: str, filter_abi: bool, exclude: set, only: set):
    """Lista .apk do dataset, opcionalmente filtrando por ABI compativel com a AVD.

    ABI: em API 30 x86_64 com NDK Translation, sao elegiveis x86_64, arm64-v8a e
    apps sem codigo nativo. Le 'native_code_abis'/'abis' do <apk>.json se existir;
    na ausencia de info, inclui o APK (com aviso).

    `exclude` retira APKs pelo nome do arquivo sem copiar o dataset: um corpus de 4 GB
    montado :ro nao precisa de uma segunda copia so para tirar um APK que derruba o
    emulador (o `stardroid` da gh104). `only` e' o inverso, para um smoke sobre 2 APKs do
    mesmo diretorio. Nome ausente do dataset e' erro, nao aviso — um typo excluiria (ou
    selecionaria) nada em silencio."""
    compat = {"x86_64", "arm64-v8a"} if avd_abi == "x86_64" else {avd_abi}
    apks, skipped, no_info = [], [], 0
    names = {f for f in os.listdir(dataset) if f.endswith(".apk")}
    missing = (exclude | only) - names
    if missing:
        sys.exit(f"--exclude/--only cita APK(s) que nao existem no dataset: {sorted(missing)}")
    chosen = (only if only else names) - exclude
    for f in sorted(chosen):
        if not filter_abi:
            apks.append(f)
            continue
        meta = dataset / (f + ".json")
        abis = None
        if meta.exists():
            try:
                d = json.loads(meta.read_text())
                abis = d.get("native_code_abis") or d.get("abis") or d.get("native_abis")
            except Exception:
                abis = None
        if abis is None:
            no_info += 1
            apks.append(f)  # sem info -> nao descarta
        elif not abis or (set(abis) & compat):
            apks.append(f)  # sem nativo OU intersecta arch compativel
        else:
            skipped.append(f)
    if filter_abi:
        print(f"[abi] {len(skipped)} APK(s) descartados (arch incompativel com {avd_abi}); "
              f"{no_info} sem info de ABI (incluidos).", file=sys.stderr)
    return apks


def arms_of(tools: str):
    """Expande a string RV_TOOLS na lista de BRACOS, que e' o que se conta.

    Um spec pode carregar varios variants ('aperv:v1:v2'), e cada variant e' um braco
    separado no tasks.json. Contar specs em vez de bracos subestima o total de tasks e
    faz o monitor_compare.sh reportar 150% de progresso — a pegadinha que o
    consolidate_compare.py ja' contornava com um expand() proprio.
    """
    labels = []
    for spec in tools.split(","):
        spec = spec.split("@")[0].strip()
        if not spec:
            continue
        parts = [x.strip() for x in spec.split(":") if x.strip()]
        labels.extend([parts[0]] if len(parts) == 1 else
                      [f"{parts[0]}:{v}" for v in parts[1:]])
    return labels


def write_filters(apks, n, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = [[] for _ in range(n)]
    for i, a in enumerate(apks):
        groups[i % n].append(a)
    for i, g in enumerate(groups):
        (out_dir / f"batch_{i:02d}.txt").write_text("\n".join(g) + "\n")
    return [len(g) for g in groups]


def needs_docker_sock(arms) -> bool:
    """ares e qtesting rodam como containers IRMAOS (docker create/start via o daemon do
    host), entao o container precisa do socket e o host precisa ter as imagens
    `phtcosta/ares:latest` e `phtcosta/qtesting:latest`."""
    return any(a.split(":")[0] in ("ares", "qtesting") for a in arms)


def needs_humanoid(arms) -> bool:
    """humanoid e' o droidbot falando HTTP com um servico separado; o default do variant
    (127.0.0.1:50405) nao alcanca um sidecar, por isso o compose sobe o servico e aponta
    RV_HUMANOID_URL para ele."""
    return any(a.split(":")[0] == "humanoid" for a in arms)


def gen_compose(args, n):
    has_llm = args.with_sglang
    arms = arms_of(args.tools)
    sock, humanoid = needs_docker_sock(arms), needs_humanoid(arms)
    env = [
        f'    RV_TOOLS: "{args.tools}"',
        f'    RV_TIMEOUTS: "{",".join(str(t) for t in args.timeouts)}"',
        f'    RV_REPETITIONS: "{args.reps}"',
        '    RV_NO_WINDOW: "true"',
        f'    RV_SPEC_SET: "{args.spec_set}"',
    ]
    if args.full_chain:
        # Cadeia completa DENTRO do container: geracao de monitores, instrumentacao e
        # analise estatica rodam por container, sobre a fatia de APKs dele. As tres
        # variaveis RV_SKIP_* sao OMITIDAS (nao postas em "false"): o entrypoint so
        # traduz o valor "true" para a flag negativa, entao ausencia == default do
        # Click, que e' fazer as tres etapas.
        #
        # Paralelizar isto e' seguro porque cada container tem o SEU /opt/rvsec: a
        # geracao de monitores estagia os .rvm no diretorio de specs compartilhado e
        # os MOVE de la', o que quebra em silencio quando dois processos dividem o
        # mesmo diretorio — mas containers nao dividem nenhum.
        env.append(f'    RV_INSTRUMENTATION_VARIANT: "{args.instrumentation_variant}"')
        if args.sa_timeout:
            env.append(f'    RV_SA_TIMEOUT: "{args.sa_timeout}"')
        if args.jvm_memory:
            env.append(f'    RV_JVM_MEMORY: "{args.jvm_memory}"')
        if args.strip_build_type_suffix:
            env.append('    RV_STRIP_BUILD_TYPE_SUFFIX: "true"')
        if args.package_detector:
            env.append('    RV_PACKAGE_DETECTOR: "true"')
    else:
        env += [
            '    RV_SKIP_MONITORS: "true"',
            '    RV_SKIP_INSTRUMENT: "true"',
            '    RV_SKIP_STATIC_ANALYSIS: "true"',
        ]
    env += [
        '    RV_APKS_DIR: "/opt/rvsec/rv-android/apks"',
        '    RV_DEVICE_PORT: "5554"',
    ]
    if has_llm:
        env.append('    RVSMART_LLM_MODE: "true"')
    if humanoid:
        env.append('    RV_HUMANOID_URL: "rv-humanoid:50405"')
    # gh72 — opt-in diagnostics. Emitido APENAS quando --logcat-diagnostics e passado
    # (ato deliberado por campanha, D9); ausente = baseline byte-identico preservado.
    if getattr(args, "logcat_diagnostics", False):
        env.append('    RV_LOGCAT_DIAGNOSTICS: "true"')
    dep_lines = []
    if has_llm:
        dep_lines.append("    sglang:\n      condition: service_healthy")
    if humanoid:
        dep_lines.append("    humanoid:\n      condition: service_started")
    depends = ("  depends_on:\n" + "\n".join(dep_lines) + "\n") if dep_lines else ""
    L = []
    L.append(f"# Comparacao '{args.name}' — gerado por rv-experiment-compare.")
    L.append(f"# Tools: {args.tools}")
    L.append(f"# {n} containers, timeouts {args.timeouts}s, {args.reps} reps, specs {args.spec_set}.")
    if sock:
        L.append("# ares/qtesting rodam como containers irmaos via /var/run/docker.sock:")
        L.append("#   o HOST precisa ter phtcosta/ares:latest e phtcosta/qtesting:latest.")
    if humanoid:
        L.append(f"# humanoid: sidecar rv-humanoid ({args.humanoid_image}), RV_HUMANOID_URL=rv-humanoid:50405.")
    if args.full_chain:
        L.append(f"# Cadeia COMPLETA por container (monitores + instrumentacao {args.instrumentation_variant}")
        L.append(f"# + analise estatica), sem reuso de artefato pre-computado.")
        L.append("# ATENCAO ao monitor_compare.sh: use --no-resume ate' os containers entrarem em")
        L.append("# execucao. O pre-processamento fica dezenas de minutos sem mover a contagem, e o")
        L.append("# auto-resume leria isso como travamento e reiniciaria a cadeia do zero.")
    L.append(f"# Plano: docs/{args.date}_{args.name}.md")
    L.append("# Uso:")
    L.append(f"#   docker compose -f docker/docker-compose.{args.name}.yml up -d")
    L.append(f"#   .claude/skills/rv-experiment-compare/scripts/monitor_compare.sh {args.name}")
    L.append("#   # passada de resume final ao terminar: re-rodar o up -d (recupera FAILED transientes)")
    L.append("#   # NAO dar 'down' antes de extrair traces (artefatos efemeros no device)")
    L.append("")
    L.append("x-rvandroid: &rvandroid-base")
    L.append(f"  image: {args.image}")
    L.append("  environment: &rvandroid-env")
    L += env
    L.append("  devices:")
    L.append("    - /dev/kvm:/dev/kvm")
    L.append("  deploy:")
    L.append("    resources:")
    L.append("      limits:")
    L.append(f'        cpus: "{args.cpus}"')
    L.append(f'        memory: "{args.memory}"')
    if depends:
        L.append(depends.rstrip("\n"))
    L.append("")
    L.append("services:")
    if humanoid:
        L += [
            "  humanoid:",
            f"    image: {args.humanoid_image}",
            "    container_name: rv-humanoid",
            "",
        ]
    if has_llm:
        L += [
            "  sglang:",
            f"    image: {args.sglang_image}",
            "    container_name: sglang-server",
            "    volumes:",
            f"      - ${{HF_CACHE:-{args.hf_cache}}}:/root/.cache/huggingface",
            "    ipc: host",
            '    shm_size: "16g"',
            "    deploy:",
            "      resources:",
            "        reservations:",
            "          devices:",
            "            - driver: nvidia",
            "              count: 1",
            "              capabilities: [gpu]",
            "    command: >",
            "      python3 -m sglang.launch_server",
            f"      --model-path {args.sglang_model}",
            "      --host 0.0.0.0",
            f"      --port {args.sglang_port}",
            "      --trust-remote-code",
            "      --attention-backend flashinfer",
            "      --tool-call-parser qwen",
            "      --enable-multimodal",
            "      --context-length 8192",
            "    healthcheck:",
            f'      test: ["CMD", "curl", "-f", "http://localhost:{args.sglang_port}/health"]',
            "      interval: 30s",
            "      timeout: 10s",
            "      retries: 10",
            "      start_period: 120s",
            "",
        ]
    for i in range(n):
        nn = f"{i:02d}"
        L += [
            f"  {args.name}_{nn}:",
            "    <<: *rvandroid-base",
            f"    container_name: {args.name}_{nn}",
            "    environment:",
            "      <<: *rvandroid-env",
            f"      RV_EXPERIMENT_NAME: {args.name}_{nn}",
            f'      RV_APKS_FILTER: "/opt/rvsec/rv-android/filters/batch_{nn}.txt"',
            f'      RV_DELAY: "{i * 10}"',
            "    volumes:",
            f"      - {args.dataset}:/opt/rvsec/rv-android/apks:ro",
            f"      - ../data/{args.name}_filters:/opt/rvsec/rv-android/filters:ro",
            f"      - ../data/results/{args.name}_{nn}:/opt/rvsec/rv-android/results",
        ]
        if sock:
            L.append("      - /var/run/docker.sock:/var/run/docker.sock")
        L.append("")
    return "\n".join(L)


def gen_plan(args, n, sizes, n_apks, n_tools, total):
    tmpl = (SKILL_DIR / "templates" / "plan.md.tmpl").read_text()
    arms = "\n".join(f"| {a} | `{a}` | ? | ? | ? |" for a in arms_of(args.tools))
    if args.full_chain:
        pre = (
            f"- **Cadeia completa por container** — nenhum artefato pre-computado e' reusado.\n"
            f"  As tres variaveis `RV_SKIP_*` estao AUSENTES do compose (o entrypoint so traduz\n"
            f"  o valor `\"true\"`, entao ausencia = default do Click = fazer as tres etapas).\n"
            f"- **Dataset de APKs ORIGINAIS** (nao instrumentados), sem `.apk.json` co-locado:\n"
            f"  o `.apk.json` nasce na etapa 3, dentro do container.\n"
            f"- Etapa 1 monitores -> `results/<name>_NN/monitors/` (+ `specification_set.txt`).\n"
            f"- Etapa 2 instrumentacao `{args.instrumentation_variant}` -> `results/<name>_NN/instrumented_apks/`.\n"
            f"- Etapa 3 analise estatica (GATOR) -> `<apk>.json` ao lado do APK instrumentado.\n"
            f"  Timeout: `RV_SA_TIMEOUT={args.sa_timeout or 600}` s; heap `RV_JVM_MEMORY={args.jvm_memory or '12g'}`.\n"
            f"- Chave de escopo: `RV_STRIP_BUILD_TYPE_SUFFIX="
            f"{'true' if args.strip_build_type_suffix else 'ausente (off)'}`, "
            f"`RV_PACKAGE_DETECTOR={'true' if args.package_detector else 'ausente (off)'}`.\n"
            f"- **Spec set:** `{args.spec_set}`.\n"
            f"- Paralelizar a geracao de monitores so e' seguro porque cada container tem o seu\n"
            f"  proprio `/opt/rvsec`; N geracoes sobre UM diretorio de specs se roubam os `.rvm`\n"
            f"  e o lote sai tecido sem monitores reportando sucesso."
        )
    else:
        pre = (
            "- Skip integral do pre-processamento: `RV_SKIP_MONITORS/INSTRUMENT/STATIC_ANALYSIS=true`.\n"
            f"- **Spec set:** `{args.spec_set}`.\n"
            "- Gotcha: o platform copia o `<apk>.json` co-locado para o results-dir de cada task\n"
            "  (`StaticAnalysisComponent.copy_static_analysis_files`) — `--skip-static` nao priva os\n"
            "  bracos MOP do dado."
        )
    sub = dict(
        name=args.name, date=args.date, tools=args.tools, n_tools=n_tools,
        n_apks=n_apks, reps=args.reps, containers=n,
        timeouts=", ".join(str(t) for t in args.timeouts), n_timeouts=len(args.timeouts),
        total_tasks=total, spec_set=args.spec_set, dataset=args.dataset,
        image=args.image, arms_table=arms,
        sglang=("sim — " + args.sglang_model) if args.with_sglang else "nao",
        sizes=", ".join(str(s) for s in sizes),
        preprocessing=pre,
    )
    for k, v in sub.items():
        tmpl = tmpl.replace("{{" + k + "}}", str(v))
    return tmpl


def main():
    p = argparse.ArgumentParser(description="Gera artefatos de uma comparacao multi-tool.")
    p.add_argument("--name", required=True, help="prefixo do experimento (containers <name>_NN)")
    p.add_argument("--dataset", required=True, help="dir com .apk (+ .apk.json co-localizado)")
    p.add_argument("--tools", required=True, help="string RV_TOOLS (virgula)")
    p.add_argument("--timeout", default="300",
                   help="timeout(s) de task em segundos; lista CSV = varios timeouts na MESMA "
                        "corrida (RV_TIMEOUTS, gh75), ex. '60,180,300'. A ordem de execucao e' "
                        "apk -> tool -> rep -> timeout, entao cada APK fecha os tres antes de trocar")
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--containers", type=int, default=6)
    p.add_argument("--spec-set", default="jca")
    p.add_argument("--image", default="phtcosta/rvandroid:0.9.3")
    p.add_argument("--cpus", default="4")
    p.add_argument("--memory", default="10g")
    p.add_argument("--with-sglang", action="store_true", help="inclui servico SGLang (braco LLM)")
    p.add_argument("--sglang-image", default="lmsysorg/sglang:v0.5.6.post2")
    p.add_argument("--sglang-model", default="Qwen/Qwen3-VL-4B-Instruct")
    p.add_argument("--sglang-port", type=int, default=30000)
    p.add_argument("--hf-cache", default="/pedro/desenvolvimento/.cache/huggingface")
    p.add_argument("--avd-abi", default="x86_64")
    p.add_argument("--filter-abi", action="store_true", help="filtra APKs por ABI compativel (le .apk.json)")
    p.add_argument("--exclude", default="",
                   help="nomes de .apk (CSV) a retirar do dataset sem copia-lo; nome inexistente aborta")
    p.add_argument("--only", default="",
                   help="nomes de .apk (CSV): usa SO estes (smoke sobre o mesmo diretorio); nome inexistente aborta")
    p.add_argument("--humanoid-image", default="phtcosta/humanoid:1.0",
                   help="imagem do sidecar, emitido automaticamente quando ha braco 'humanoid'")
    p.add_argument(
        "--logcat-diagnostics",
        action="store_true",
        help=(
            "liga a captura opt-in de eventos diagnosticos (crashes/VerifyError/ANR) "
            "-> RV_LOGCAT_DIAGNOSTICS=true + app_events.csv (gh72). Default OFF: "
            "captura byte-identica ao baseline RVSEC/RVSEC-COV (D9). Ligar e ato "
            "deliberado por campanha."
        ),
    )
    p.add_argument(
        "--full-chain",
        action="store_true",
        help=(
            "roda a cadeia COMPLETA dentro de cada container (monitores + instrumentacao "
            "+ analise estatica) em vez de reusar artefatos pre-computados. Omite as tres "
            "RV_SKIP_* do compose. Exige um dataset de APKs ORIGINAIS."
        ),
    )
    p.add_argument(
        "--instrumentation-variant",
        default="dexlib2",
        choices=["ajc", "dexlib2"],
        help="tecelagem usada no --full-chain (default dexlib2)",
    )
    p.add_argument("--sa-timeout", type=int, default=None,
                   help="RV_SA_TIMEOUT: teto por APK da analise estatica, em segundos (default do codigo: 600)")
    p.add_argument("--jvm-memory", default=None,
                   help="RV_JVM_MEMORY: heap da JVM do GATOR (default do codigo: 12g). "
                        "O limite de memoria do container tem de ser MAIOR que isto")
    p.add_argument("--strip-build-type-suffix", action="store_true",
                   help="RV_STRIP_BUILD_TYPE_SUFFIX=true: neutraliza o sufixo de build-type do "
                        "applicationId antes de usa-lo como chave de escopo (gh111)")
    p.add_argument("--package-detector", action="store_true",
                   help="RV_PACKAGE_DETECTOR=true: elege o pacote de implementacao pelas classes "
                        "compiladas. Tem PRECEDENCIA sobre o strip (INV-CORE-18)")
    p.add_argument("--force", action="store_true", help="sobrescreve artefatos existentes")
    args = p.parse_args()
    args.date = datetime.now().strftime("%Y%m%d")
    try:
        args.timeouts = [int(t) for t in args.timeout.split(",") if t.strip()]
    except ValueError:
        sys.exit(f"--timeout invalido: {args.timeout!r} (inteiros separados por virgula)")
    if not args.timeouts or any(t <= 0 for t in args.timeouts):
        sys.exit(f"--timeout invalido: {args.timeout!r}")
    exclude = {x.strip() for x in args.exclude.split(",") if x.strip()}
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    dataset = Path(args.dataset)
    if not dataset.is_dir():
        sys.exit(f"dataset inexistente: {dataset}")

    apks = list_apks(dataset, args.avd_abi, args.filter_abi, exclude, only)
    if not apks:
        sys.exit("nenhum .apk encontrado no dataset")
    n = min(args.containers, len(apks))
    arms = arms_of(args.tools)
    n_tools = len(arms)  # BRACOS, nao specs: 'aperv:v1:v2' sao dois bracos, nao um
    total = n_tools * len(apks) * args.reps * len(args.timeouts)

    if args.full_chain:
        stray = [a for a in apks if (dataset / (a + ".json")).exists()]
        if stray:
            print(f"[full-chain] AVISO: {len(stray)} APK(s) do dataset ja' tem .apk.json "
                  f"co-locado (ex.: {stray[0]}). A cadeia completa gera o seu proprio "
                  f"artefato em results/; o co-locado nao sera' lido pelo pre-processamento.",
                  file=sys.stderr)

    filters_dir = ROOT / "data" / f"{args.name}_filters"
    compose_path = ROOT / "docker" / f"docker-compose.{args.name}.yml"
    plan_path = ROOT / "docs" / f"{args.date}_{args.name}.md"
    meta_path = ROOT / "data" / "results" / f"{args.name}_compare_meta.json"

    for path in (compose_path, plan_path):
        if path.exists() and not args.force:
            sys.exit(f"ja existe (use --force): {path}")

    sizes = write_filters(apks, n, filters_dir)
    # corpus.txt e' a lista ordenada que os filtros repartem; o sha256 do seu conteudo e' o
    # que uma campanha ecoa como corpus_basis (ver experimento-gh104/scripts/corpus.py).
    (filters_dir / "corpus.txt").write_text("\n".join(apks) + "\n")
    compose_path.parent.mkdir(parents=True, exist_ok=True)
    compose_path.write_text(gen_compose(args, n))
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(gen_plan(args, n, sizes, len(apks), n_tools, total))
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(dict(
        name=args.name, tools=[t.strip() for t in args.tools.split(",") if t.strip()],
        n_tools=n_tools, reps=args.reps, timeouts=args.timeouts,
        n_timeouts=len(args.timeouts), containers=n,
        n_apks=len(apks), total_tasks=total, dataset=str(dataset),
        excluded_apks=sorted(exclude),
        with_sglang=args.with_sglang, filters_dir=str(filters_dir),
        arms=arms, spec_set=args.spec_set, image=args.image,
        full_chain=args.full_chain,
        instrumentation_variant=args.instrumentation_variant if args.full_chain else None,
        sa_timeout=args.sa_timeout, jvm_memory=args.jvm_memory,
        strip_build_type_suffix=args.strip_build_type_suffix,
        package_detector=args.package_detector,
    ), indent=2))

    print(f"OK — comparacao '{args.name}' gerada:")
    print(f"  filtros : {filters_dir}/batch_00..{n-1:02d}.txt  ({len(apks)} APKs, sizes {sizes})")
    print(f"  compose : {compose_path}")
    print(f"  plano   : {plan_path}")
    print(f"  meta    : {meta_path}")
    print(f"  corpus  : {filters_dir}/corpus.txt ({len(apks)} APKs"
          f"{', excluidos: ' + ', '.join(sorted(exclude)) if exclude else ''})")
    print(f"  total de tasks: {n_tools} bracos ({', '.join(arms)}) x {len(apks)} APKs "
          f"x {args.reps} reps x {len(args.timeouts)} timeouts = {total}")
    if needs_docker_sock(arms):
        print("  ares/qtesting: containers irmaos via docker.sock — confira "
              "`docker images phtcosta/ares phtcosta/qtesting` no HOST")
    if needs_humanoid(arms):
        print(f"  humanoid: sidecar rv-humanoid ({args.humanoid_image})")
    if args.full_chain:
        print(f"  cadeia completa: monitores + instrumentacao ({args.instrumentation_variant}) "
              f"+ analise estatica DENTRO de cada container")
    print(f"\nProximo: revisar o plano, depois:")
    print(f"  docker compose -f docker/docker-compose.{args.name}.yml up -d")


if __name__ == "__main__":
    main()
