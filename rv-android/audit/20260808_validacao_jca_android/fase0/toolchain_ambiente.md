# Fase 0 — Toolchain e Ambiente Efetivos (auditoria jca_android)

Data: 2026-08-08. Host: Linux 7.0.0-28-generic. Modo: somente leitura (nenhum binário da toolchain foi executado sobre a árvore de especificações; apenas `sha256sum`, leitura de manifests e inspeção de código).

Raízes:
- `RVSEC_HOME = /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec` (confirmado no ambiente do shell)
- rv-android: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android`
- `ANDROID_HOME = /home/pedro/desenvolvimento/aplicativos/android/sdk`

Convenção: caminhos abaixo abreviam `RVSEC` = `$RVSEC_HOME` e `RVA` = `.../rvsec/rv-android`.

---

## 1. Geração de monitores (JavaMOP + RV-Monitor)

### 1.1 Como o pipeline invoca as ferramentas

- `RVGeneratorConfig` resolve os binários a partir de `RVSEC_HOME` quando não recebem caminho explícito:
  - `javamop_bin = $RVSEC_HOME/javamop/bin/javamop` — `RVA/modules/rv-monitor-generator/src/rv_monitor_generator/config.py:165`
  - `rvmonitor_bin = $RVSEC_HOME/rv-monitor/bin/rv-monitor` — `config.py:168-170`
- O rv-experiment **sempre** passa os dois caminhos explicitamente (mesmos valores) ao construir o config JIT — `RVA/modules/rv-experiment/src/rv_experiment/config.py:734-742`.
- Invocação do JavaMOP: `Command(javamop_bin, ["-d", output_dir, "-merge", "--emit-descriptor"(default), "<specs_dir>/*.mop"])` — `RVA/modules/rv-monitor-generator/src/rv_monitor_generator/runtime_verification_generator.py:211-217`. O flag `--emit-descriptor` (JavaMOP com patch local) escreve o descritor `MultiSpec_*MonitorAspect.json` consumido pela variante dexlib2; controlado por `RVGeneratorConfig.emit_descriptor` (default `True`) — `config.py:70-80`.
- Invocação do RV-Monitor: `Command(rvmonitor_bin, ["-d", output_dir, "-merge", "<output_dir>/*.rvm"])` — `runtime_verification_generator.py:267-272`.
- Ambos os scripts `bin/` são wrappers que delegam para a árvore `target/release`:
  - `RVSEC/javamop/bin/javamop` → `RVSEC/javamop/target/release/javamop/javamop/bin/javamop` → `java -cp lib/*.jar javamop.JavaMOPMain`
  - `RVSEC/rv-monitor/bin/rv-monitor` → `RVSEC/rv-monitor/target/release/rv-monitor/bin/rv-monitor` → `java -Xss1g -cp lib/*.jar com.runtimeverification.rvmonitor.java.rvj.Main`

### 1.2 Jars efetivos (congelados)

| Componente | Caminho | Versão | SHA-256 | Referenciado por |
|---|---|---|---|---|
| JavaMOP (jar principal) | `RVSEC/javamop/target/release/javamop/javamop/lib/javamop-0.9.3-SNAPSHOT.jar` | 0.9.3-SNAPSHOT (build 2026-08-08 10:35 — inclui patches gh100/gh101 e `--emit-descriptor`) | `ab4e3765b68ca03502265d892d22bbd1e598ccb2c1ae6142d6413e205bd98c0a` | launcher `RVSEC/javamop/bin/javamop`; `rv_monitor_generator/config.py:165` |
| logicrepository (lado JavaMOP) | `RVSEC/javamop/target/release/javamop/javamop/lib/logicrepository-0.9.3-SNAPSHOT.jar` | 0.9.3-SNAPSHOT (2026-07-29) | `0c3976a341472fe525beba792c969fd75a19abb8fa9045680650203887593f98` | classpath do launcher javamop |
| RV-Monitor (gerador) | `RVSEC/rv-monitor/target/release/rv-monitor/lib/rv-monitor.jar` | 0.9.3-SNAPSHOT (2026-07-29 10:14) | `fab403190246e8f330ac79e091662f4c3ebd2ed0c14d343d4266652b1634dd55` | launcher `RVSEC/rv-monitor/bin/rv-monitor`; `rv_monitor_generator/config.py:168` |
| rv-monitor-rt (runtime) | `RVSEC/rv-monitor/target/release/rv-monitor/lib/rv-monitor-rt.jar` **e** `RVA/lib_tmp/rv-monitor-rt.jar` (idênticos) | 0.9.3-SNAPSHOT (2026-08-08 10:35) | `0fa65fbc2a1e01fc4789df0bb1670e47617796d588d932c2c6022383c5441e8c` | resolvido por `_resolve_runtime_libs` via `mvn dependency:copy-dependencies` sobre `RVA/pom.xml:24-27` — `RVA/modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py:53+` |
| Plugins de lógica (fsm/ere/…) | `RVSEC/rv-monitor/target/release/rv-monitor/lib/plugins/{cfg,ere,fsm,ltl,pda,po,ptcaret,ptltl,srs,tfsm}.jar` (mesma lista no lado javamop) | 0.9.3-SNAPSHOT | fsm: `f88b066bfe0b6e09fa38c15e603a015cf04117445edb3c440096f80646b2af00`; ere: `eb2c92dcea8ecdb1ed48a5db2ec6cf6002b368b29fb3ceb702325b8d8ebd0237` (demais registrados no shell, disponíveis sob o mesmo diretório) | `LOGICPLUGINPATH` nos launchers; harness `CoenableProbe` da skill |
| aspectjweaver (lado rv-monitor) | `RVSEC/rv-monitor/target/release/rv-monitor/lib/aspectjweaver.jar` | 1.9.25.1 (idêntico ao de `lib_tmp`) | `4fe86fdc18faea571f29129c70eaad5d121363504a06d7907be88f6c60ba3116` | classpath do launcher rv-monitor |

Nota: `rv-monitor-rt.jar` da árvore de release e o de `RVA/lib_tmp/` têm o **mesmo** SHA-256 — não há duplicidade ambígua do runtime.

---

## 2. Instrumentação

### 2.1 Variante ajc (`rv-instrumentation-ajc`)

| Item | Localização |
|---|---|
| Classe | `AjcInstrumentation` — `RVA/modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/ajc_instrumentation.py:23`; entrada em lote `instrument_apks` (`:113`), por APK `instrument` (`:442`) |
| Config | `AjcInstrumentationConfig` — `RVA/modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/config.py:131` |
| Invocação do ajc | `Command("ajc", ...)` — **binário do PATH** — `ajc_instrumentation.py:1093`, executado em `:1103` |
| Invocação do d8 | `Command("d8", ...)` — **binário do PATH** — `ajc_instrumentation.py:1408-1409` |
| dex2jar | suite em `RVA/lib/dex2jar/` (default `dex2jar_home` — `config.py:461-463`) |
| frame-computer | `RVA/lib/frame-computer/rv-frame-computer.jar` — localizado em `ajc_instrumentation.py:1219-1223`, invocado em `:1118+` |

**`ajc` NÃO está no PATH do host** (`which ajc` falha). O compilador AspectJ efetivo vem do Docker: `RVA/docker/base/Dockerfile:37-47` instala AspectJ **1.9.25.1** em `/opt/aspectj` — coincide com `aspectj.version=1.9.25.1` do `rvsec/pom.xml` (o TODO do CLAUDE.md raiz está, hoje, satisfeito). O `aspectjtools.jar` resolvido em `lib_tmp` também é 1.9.25.1 (manifest). No Docker, `d8` resolve via PATH para `build-tools/35.0.1` (`RVA/docker/android/Dockerfile:35`).

### 2.2 Variante dexlib2 (`rv-instrumentation-dexlib2` + CLI Java)

| Item | Localização |
|---|---|
| Classe Python | `DexlibInstrumentation` — `RVA/modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py:25`; `instrument` (`:139`), `instrument_apks` (`:155`) |
| Jar do CLI | `RVA/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` — default de `cli_jar_path` (`config.py:13-21`); invocado como `java -jar instr-cli.jar` (`dexlib_instrumentation.py:521-527`) |
| Main-Class | `br.unb.cic.rv.cli.InstrumentationCli` (manifest; Java-Version 21, Build-Jdk-Spec 25) |
| Resolução de ferramentas no lado Java | `ConfigResolver` — `RVSEC/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/src/main/java/br/unb/cic/rv/cli/ConfigResolver.java:26` (android.jar `:111-127`; d8/zipalign/apksigner por `latestUnder` em `$ANDROID_HOME/build-tools` `:149-186`) |
| Weaver DEX | `DexWeaver.weave(...)` — `RVSEC/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/src/main/java/br/unb/cic/rv/mutator/DexWeaver.java:303` |
| Emissor do monitorCall | `MonitorInvokeBuilder.buildInvoke` — `RVSEC/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter/src/main/java/br/unb/cic/rv/emitter/MonitorInvokeBuilder.java:69` (um `invoke-static` por entrada de `monitorCalls`, na ordem do descritor; instância única por chamada em `:81-116`) |

### 2.3 Binários auxiliares congelados

| Componente | Caminho | Versão | SHA-256 | Referenciado por |
|---|---|---|---|---|
| instr-cli (fat jar) | `RVA/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` | 0.9.3-SNAPSHOT (Java 21) | `356e8b7066ae0aa70db6d0c653f510c290d2fec6a1c06f1ecaa1705ab52a9b1c` | `dexlib_instrumentation.py:521-527` |
| rv-frame-computer | `RVA/lib/frame-computer/rv-frame-computer.jar` | 0.9.3-SNAPSHOT (Main: `br.unb.cic.rvsec.frame.FrameComputer`) | `baf06d58c2fc6f3c65fe0d644d69b1b028df87d2bdc38d3d60a138fafda221ca` | `ajc_instrumentation.py:1219-1223` |
| apktool | `RVA/lib/apktool/apktool.jar` | 2.10.0 (`properties/apktool.properties`) | `e8c6e2d93061e0059fe3dc2a943a0924b25ca43780f70f9bb507099545c60fa0` | `rvsec-apk` / análise estática (não usado na tecelagem ajc/dexlib2) |
| dex2jar (dex-tools) | `RVA/lib/dex2jar/lib/dex-tools-v2.4.jar` | v2.4 | `93b2adf1e39448dc1f1ba9268096f1bf3e05813f1fcbde7a883eace70cceed02` | `AjcInstrumentationConfig.dex2jar_home` → `config.py:461-463` |
| dex2jar (dex-translator) | `RVA/lib/dex2jar/lib/dex-translator-v2.4.jar` | v2.4 | `fb64bbf0eb9b37031ddeb78803d48f0826ce057cb251d28aa50e7b601a0f6f8c` | idem |
| GATOR (análise estática) | `RVA/lib/gator/rvsec-gator.jar` | 0.9.3-SNAPSHOT (Main: `presto.android.Main`) | `30160481ee3dbc19def68e4036c781377a3f111ce0c479be86b73d547f4b9f19` | rv-static-analysis (pré-processamento) |
| GATOR client | `RVA/lib/gator/rvsec-analysis-client.jar` | 0.9.3-SNAPSHOT | `207b61f7fb9cc29b721fc8b357b8b7566b90fb09c4ce7f199348b0e9793847a4` | idem |
| aspectjrt | `RVA/lib_tmp/aspectjrt.jar` | 1.9.25.1 | `5765d5c8fbf94a895350f2643bb7543bc5b774de987bf12b92f63809b4d21a71` | `_resolve_runtime_libs` (dexlib2 filtra-o do classpath) |
| aspectjtools | `RVA/lib_tmp/aspectjtools.jar` | 1.9.25.1 | `b07ce76ce7c7234f47ffa7651b6ecb6ad5144240bb320998de6280fe926b2615` | dependência declarada em `RVA/pom.xml` (o `ajc` efetivo é o do Docker, mesma versão) |
| rvsec-core (runtime) | `RVA/lib_tmp/rvsec-core.jar` | 0.9.3-SNAPSHOT (2026-08-08 10:35) | `7b4d72aac8527ac8f5a832e249a2b16d617d22e9c3207cfc5854b01948601f3e` | `_resolve_runtime_libs`; dexado no APK |
| rvsec-logger-logcat (runtime) | `RVA/lib_tmp/rvsec-logger-logcat.jar` | 0.9.3-SNAPSHOT (2026-08-07 18:54) | `65908fefd7ba79618eaeec230c179b8ac1ce7da329750f82d5866320609b669d` | idem |

---

## 3. Runtime Java (classes usadas pelos event bodies das specs)

| Classe | Caminho | Papel (1 linha) |
|---|---|---|
| `ExecutionContext` | `RVSEC/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` | Store por **identidade** (IdentityHashMap) que mimetiza ensures/requires do CrySL — marca objetos em estado aceitante e propriedades associadas. |
| `Property` | `RVSEC/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/Property.java` | Enum das propriedades (GENERATED_KEY, DIGESTED, ENCRYPTED, generatedCipher etc.) usadas como marcas no ExecutionContext. |
| `ErrorCollector` (logcat) | `RVSEC/rvsec/rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` | Singleton que deduplica violações e as emite via `Log.v("RVSEC", ...)` — é o "RVSecLogger" efetivo no Android. |
| `ErrorCollector` (csv/JSE) | `RVSEC/rvsec/rvsec-logger-csv/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` | Contraparte JSE (CSV); não é a usada no APK instrumentado (o pom de runtime referencia a logcat). |
| `Coverage.aj` | `RVSEC/rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj:156` | Aspecto de cobertura que emite `Log.v("RVSEC-COV", assinatura)` por método monitorável atingido. |
| Parser logcat (Python) | `RVA/modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py:218` (linha a linha), `:404` (RVSEC-COV) | Extrai entradas `RVSEC` (violação) e `RVSEC-COV` (cobertura) do logcat; tags canônicas em `RVA/modules/rv-android-core/src/rv_android_core/util/logging/constants.py:23-24`. |

---

## 4. android.jar efetivo (matching de pointcuts / instrumentação)

Dois mecanismos distintos, um por variante:

1. **ajc** (`RVA/modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/`):
   - Default do config: `android-29` (hardcoded) — `config.py:416-423`.
   - Na tecelagem, seleção **por APK**: `__get_android_jar` tenta `platforms/android-<targetSdk>/android.jar` exato e cai para a plataforma **numérica** mais alta ≥ 26 — `ajc_instrumentation.py:1619-1655`. Para um APK com targetSdk 30, o efetivo é `android-30/android.jar`.
   - Obs.: `_find_highest_android_platform` usa `int(name.split("-")[1])`, portanto ignora diretórios como `android-37.0` (ValueError) — no host o fallback numérico máximo é `android-37`.

2. **dexlib2** (CLI Java): o wrapper Python **não** passa `--android-jar` (`_common_cli_args`, `dexlib_instrumentation.py:469-497` — ausente da lista). O CLI resolve por `ConfigResolver.resolveAndroidJarFromEnv()` — `ConfigResolver.java:111-127` — que toma o **máximo LEXICOGRÁFICO** dos diretórios de `$ANDROID_HOME/platforms` que contêm `android.jar`:
   - Host: resolve para `android-37.0` ("android-37.0" > "android-36.1" na ordem de string).
   - Docker (`RVA/docker/android/Dockerfile:24`): plataformas instaladas android-10…android-36 → resolve `android-36`.
   - **Em nenhum dos ambientes o default é android-30.** API 30 só é usada no caminho dexlib2 se `--android-jar` for passado explicitamente (nenhum call-site em rv-android o faz).

| Candidato | Caminho | SHA-256 | Quem usa |
|---|---|---|---|
| android-30 | `$ANDROID_HOME/platforms/android-30/android.jar` | `96ccfdc84d15fad4e22d76cbb8ef38b150a4b56327957067875ca7e18113a424` | ajc, para APKs targetSdk 30 (match exato) |
| android-37.0 | `$ANDROID_HOME/platforms/android-37.0/android.jar` | `bf1b4387cc7ca94fc6ef684f040d9d16fbf16248e181819f020736ea2053f177` | dexlib2 CLI no host (máximo lexicográfico) |

A mesma comparação lexicográfica (`latestUnder`, `ConfigResolver.java:172-186`) escolhe d8/zipalign/apksigner em `build-tools/` — no host resolve `37.0.0-rc1` (que ordena acima de `37.0.0`); no Docker só existe `35.0.1`.

---

## 5. Resolução de `--specification-set jca_android`

Cadeia completa, com o código citado:

1. **CLI**: `type=click.Choice(["jca", "jca_android", "generic", "custom"])` — `RVA/modules/rv-experiment/src/rv_experiment/__main__.py:440-444`. Valor fora da lista é rejeitado pelo Click antes de qualquer execução. `DEFAULT_SPEC_SET = SPEC_SET_JCA` (`constants.py:100`) — omitir o flag seleciona `jca` **por default declarado**, não por fallback.
2. **Validação do modelo**: `ExperimentConfig` valida `specification_set` contra os quatro valores (INV-EXP-03 (f)) — `config.py:428-440`.
3. **Mapeamento JIT** (`get_monitored_operations_config`) — `RVA/modules/rv-experiment/src/rv_experiment/config.py:685-712`:

```python
mop_base_dir = os.path.join(rvsec_root, "rvsec", "rvsec-mop", "src", "main", "resources")
if self.specification_set == SPEC_SET_JCA:
    mop_specs_dir = os.path.join(mop_base_dir, SPEC_SET_JCA)
elif self.specification_set == SPEC_SET_JCA_ANDROID:
    mop_specs_dir = os.path.join(mop_base_dir, SPEC_SET_JCA_ANDROID)   # <- jca_android
elif self.specification_set == SPEC_SET_GENERIC:
    mop_specs_dir = os.path.join(mop_base_dir, SPEC_SET_GENERIC)
elif self.specification_set == SPEC_SET_CUSTOM:
    if self.custom_specs_dir:
        mop_specs_dir = self.custom_specs_dir
        if not self.validate_specs_dir(mop_specs_dir):
            raise ConfigurationError(f"Invalid specs dir: {mop_specs_dir}")
    else:
        raise ConfigurationError(f"Unsupported specification set: {self.specification_set}")
else:
    raise ConfigurationError(f"Unsupported specification set: {self.specification_set}")
```

4. O `RVGeneratorConfig` resultante recebe `mop_specs_dir` **explicitamente** (`config.py:734-742`), o que desativa o default interno do `RVGeneratorConfig` (prioridade 1 da resolução — `rv_monitor_generator/config.py:112-127`).
5. Diretório efetivo: `RVSEC/rvsec/rvsec-mop/src/main/resources/jca_android/` — **23 arquivos `.mop`** confirmados por listagem.

**Conclusão sobre fallback silencioso**: no caminho rv-experiment **não existe** fallback silencioso de `jca_android` para `jca` ou `custom` — todo valor desconhecido ou `custom` sem diretório levanta `ConfigurationError`, e o diretório é sempre passado explicitamente ao gerador. A única regressão possível para `jca` está fora desse caminho: (a) o default declarado `DEFAULT_SPEC_SET="jca"` quando o flag é omitido, e (b) o default interno do `RVGeneratorConfig` standalone, que assume `.../resources/jca` quando construído sem `mop_specs_dir` (`rv_monitor_generator/config.py:174-179`) — nunca exercido pelo rv-experiment.

---

## 6. Skill baseline `.claude/skills/rv-analyze-spec/`

| Arquivo | Função (1 linha) |
|---|---|
| `SKILL.md` | Skill de análise/redesenho de specs JavaMOP: alfabeto de eventos, autômato, pointcuts, conformidade CrySL e custo de geração; lema "measure the tool, do not reason about it". |
| `reference/crysl-to-mop.md` | De uma regra CrySL a um `.mop` dentro do orçamento do gerador. |
| `reference/generated-artifacts.md` | O que os artefatos gerados (.aj/.rvm/.java/.json) revelam que o `.mop` não revela. |
| `reference/generator-pipeline.md` | O gerador como pipeline de reescrita e onde fica sua parede de complexidade. |
| `reference/pointcut-semantics.md` | O que o weaver realmente casa (semântica de pointcuts, dialeto AspectJ vs. weaver DEX). |
| `reference/triangulation.md` | Checagem do mesmo fato por vários ângulos (por que harness sobre código de produção > modelo mental). |
| `scripts/CoenableProbe.java` | Harness sobre o logicrepository de produção (plugins fsm/ere): precifica uma propriedade antes de gerar — estados após minimização, conjuntos coenable, tamanho da string para o rv-monitor. |
| `scripts/PointcutBudget.java` | Harness sobre as classes de pointcut de produção (`br.unb.cic.rv.pointcut` + dexlib2): mede o casamento de pointcuts contra membros reais da API. |
| `scripts/api_members.py` | Converte saída do `javap` sobre o android.jar na tabela de membros consumida pelo PointcutBudget (nunca escrever overloads à mão). |
| `scripts/README.md` | Como compilar/rodar os dois harnesses **em scratch** (nunca dentro da árvore de specs). |

---

## 7. Ambiente

| Item | Valor |
|---|---|
| Java (host) | OpenJDK Temurin **25.0.3+9 LTS** (`java -version`); reator Maven alveja Java 21 (`rvsec/pom.xml`) e os jars 0.9.3-SNAPSHOT trazem `Java-Version: 21`, `Build-Jdk-Spec: 25` |
| Python | 3.14.4 |
| uv | 0.12.0 |
| `RVSEC_HOME` | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec` |
| `ANDROID_HOME` | `/home/pedro/desenvolvimento/aplicativos/android/sdk` |
| SDK platforms (host) | android-10, 14–19, 21–36, 36.1, **37**, **37.0** (26 diretórios) |
| SDK build-tools (host) | 25.0.2 … 35.0.1, 36.0.0, 36.1.0, 37.0.0, 37.0.0-rc1 |
| `ajc` no host | **ausente do PATH** — tecelagem ajc só é reprodutível no Docker (`docker/base/Dockerfile`: AspectJ 1.9.25.1 em `/opt/aspectj`) |
| Docker android | platforms android-10…36, build-tools 35.0.1 no PATH (`docker/android/Dockerfile:24,35`) |
| Repositório Maven local | `/home/pedro/desenvolvimento/repository` (via `~/.m2/settings.xml`); jars de runtime efetivos materializados em `RVA/lib_tmp/` (stripVersion) |
