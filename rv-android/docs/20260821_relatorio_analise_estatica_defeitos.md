# Relatório de ideação — três defeitos no acoplamento entre experimento e análise estática

**Data**: 2026-08-21 · **Autor**: sessão de aplicação da change gh105 (tarefa 4.3)
**Natureza**: Fase 0 do `docs/WORKFLOW.md` — material de referência, não artefato OpenSpec
**Procedência**: observados durante a sonda de alcance da gh105, evidência em
`data/gh105/evidence/f2-reach-probe.md`
**Status**: nenhum reparo feito; nenhuma issue aberta; nenhuma change criada
**Eixo de avaliação**: eficácia de especificação no sentido de Legunsen et al. (ASE'16) — ver §6 e §11

---

## 0. Sumário para quem vai decidir

Três defeitos, todos no acoplamento entre o orquestrador de experimentos e a análise estática do
GATOR. Não são da change gh105 — ela apenas os fez disparar juntos, num run onde dava para vê-los.

| # | Defeito | Já conhecido? | Impacto numérico medido | Onde repara |
|---|---|---|---|---|
| **D1** | O caminho de experimento não fornece `ANDROID_SDK_HOME` ao GATOR, e o `gator` lê a variável com subscrito nu | **Sim**, desde a gh91 (2026-07-31) | **Total**: `coverage.csv` sem uma linha sequer, `called_methods = 0`, num run que cobriu 27 métodos | `rv-static-analysis/config.py:340-400` |
| **D2** | A análise estática mira `resources/jca` mesmo sob `--specification-set jca_android` | **Sim**, catalogado como bloqueador **B4** em 2026-08-18 | **Zero neste corpus hoje** — medido, não argumentado | `rv-static-analysis/config.py:199-208` + `rv-experiment/config.py:949-957` |
| **D3** | O INV-EXP-16 não é aplicado: um APK sem `.apk.json` é executado assim mesmo | **Não** — achado desta sessão | É o multiplicador: converte a falha do D1 em run silenciosamente degradado em vez de run recusado | `experiment_controller.py:267-276` + `execution_controller.py:260-262` |

**A tese do relatório**: D1 e D2 são conhecidos, documentados e nunca reparados, e cada um sozinho
é defensável como dívida aceita. O que muda a conta é **D3**, que não estava catalogado: sem ele,
D1 produziria um run **recusado** — barulhento, óbvio, corrigido em cinco minutos. Com ele, D1
produz um run **concluído com sucesso declarado** cujas colunas de cobertura são zeros
indistinguíveis de uma medição legítima. O defeito que importa não é nenhum dos dois que eu
reportei primeiro; é o terceiro, que só apareceu porque os dois primeiros dispararam juntos.

**A pergunta da Fase 0 respondida em uma frase**: *quero que o pipeline recuse — alto e cedo — um
run cuja análise estática não produziu dados, e que a análise estática mire o conjunto de
especificações que o run declarou.*

---

## 1. Como isto apareceu

A tarefa 4.3 da change gh105 é uma sonda de alcance: uma execução de dispositivo que responde se
um relato derivado de predicate chega ao `errors.csv`. Ela rodou duas vezes em 2026-08-21:

* **Execução A** — `ape`, 60 s, `jca_android`, dexlib2, análise estática **ligada**
  (`results/gh105_reach_probe`). A análise estática morreu no primeiro segundo (D1). O run
  continuou (D3) e terminou "com sucesso", reportando cobertura zero.
* **Execução B** — `aperv:sata_mop`, 300 s, mesma configuração, com `ANDROID_SDK_HOME` exportado
  à mão (`results/gh105_reach_probe_b`). A análise estática completou em 33 s, mirando `jca` (D2).

Nenhuma das duas execuções foi feita para encontrar estes defeitos. Eles apareceram porque a
sonda foi construída com três camadas de oráculo em vez de uma pergunta binária — e a camada que
pergunta "o sítio executou?" obriga a olhar a cobertura, que é justamente onde D1 e D3 moram.

---

## 2. D1 — `ANDROID_SDK_HOME` não chega ao GATOR

### 2.1 O mecanismo

`lib/gator/gator:62-64`:

```python
sdk_path = args.sdkpath
if not sdk_path:
    sdk_path = os.environ['ANDROID_SDK_HOME']
```

Subscrito nu: `KeyError` se a variável não existir. O `sdk_path` é usado para `-sdkDir`, para
localizar `platforms/android-<N>/android.jar` e para chamar o `sdkmanager` — sem ele o GATOR não
tem como começar.

O script **aceita** `--sdk` (`lib/gator/gator:195-199`, `dest='sdkpath'`), que dispensa a variável
inteiramente. O construtor de linha de comando do lado Python
(`modules/rv-static-analysis/src/rv_static_analysis/config.py:340-400`) monta doze argumentos e
**nunca emite `--sdk`**.

### 2.2 A ironia da configuração

O `RVStaticAnalysisConfig` **já sabe** onde está o SDK. Em `config.py:180-194` ele lê
`ANDROID_HOME` do ambiente, deriva `android_platforms_dir`, varre `["33","29","28","27","26"]`
procurando um `android.jar`, grava o resultado em `self.android_jar` — e em `config.py:274-280`
**valida** que o diretório existe, falhando a configuração se não existir.

Nenhum dos dois campos entra na linha de comando. São configuração morta para a invocação real:
o Python resolve e valida um caminho que não usa, e a raiz do SDK, que é o que o GATOR precisa,
ele não passa. A informação está a duas linhas de distância do lugar onde falta.

### 2.3 O que já se sabia

Este defeito está documentado desde a change gh91, com o reparo já nomeado:

> `openspec/changes/archive/2026-07-31-gh91-sa-rerun-manifest-key/design.md:141-143`
> **`ANDROID_SDK_HOME` must be exported.** `lib/gator/gator:64` does `os.environ['ANDROID_SDK_HOME']`
> — a bare subscript, `KeyError` if unset. It is `ANDROID_SDK_HOME`, **not** `ANDROID_HOME`, which
> is the one usually exported. Alternatively pass `--sdkpath`.

E aparece em mais cinco lugares: `openspec/changes/archive/2026-08-02-gh92-emulator-boot-gating/tasks.md:223-225`,
`docs/20260730_gh91_handoff_proxima_sessao.md:169-170`, `docs/20260802_prompt_gh92_logcat_device.md:124,172`,
`docs/20260810_plano_prontidao_estudo03.md:405` e `docs/20260811_handoff_fase_a_analise_estatica.md:240`.

Dois consumidores **já resolveram**, cada um do seu jeito:

1. **Docker** — `docker/android/Dockerfile:34` faz `ENV ANDROID_SDK_HOME=/opt/android`. Registrado
   na change `resume-docker` como correção explícita. **Toda execução em container é imune.**
2. **O driver de re-análise da gh91** — `scripts/gh91_sa_rerun.py:333-346` implementa exatamente o
   fallback que falta:

```python
def _gator_env() -> dict[str, str]:
    env = dict(os.environ)
    if "ANDROID_SDK_HOME" not in env:
        sdk = env.get("ANDROID_HOME") or env.get("ANDROID_SDK_ROOT")
        if not sdk:
            raise SystemExit("neither ANDROID_SDK_HOME nor ANDROID_HOME/ANDROID_SDK_ROOT is set")
        env["ANDROID_SDK_HOME"] = sdk
    return env
```

Nove linhas, com docstring citando o `gator:64`. Escritas em julho, jamais aplicadas ao caminho de
experimento. **Há três portas de entrada para o GATOR e duas foram consertadas.** A terceira — a
que qualquer `rv-experiment run` usa — ficou.

### 2.4 A consequência medida

Não é "a análise estática falha". É o que acontece **depois** dela falhar. Execução A:

| artefato | conteúdo |
|---|---|
| logcat | 27 linhas `RVSEC-COV`, métodos reais do `br.unb.cic.cryptoapp` |
| `coverage.csv` | **só o cabeçalho** — zero linhas |
| `summary.csv` | `cov_act=0, cov_class=0, cov_method=0, cov_reachable=0, cov_reaches_target=0, cov_directly_reaches_target=0` |
| `results.json` | `called_activities: 0, called_methods: 0, method_coverage: 0.0` |
| `experiment_completion.json` | `post_processing_completed: true` |
| saída do CLI | `✅ Experiment completed successfully!`, código de saída **0** |

Um run que cobriu 27 métodos reporta zero métodos cobertos e se declara bem-sucedido.

O ponto onde a perda ocorre é `modules/rv-android-core/src/rv_android_core/domain/coverage.py:742-748`:

```python
# Without static analysis data, coverage is undefined (0/0).
# This happens when --skip-static is used without pre-existing data.
if not self.classes:
    self.logger.warning("No static analysis data available, returning 0% for all metrics")
    return metrics
```

O comentário declara a premissa: *isto acontece quando se usa `--skip-static`* — uma escolha
explícita do pesquisador, que sabe o que está abrindo mão. D1 viola essa premissa: o pesquisador
**pediu** análise estática, o run **diz** que a fez ("Static analysis completed", linha 267 do log
da execução A) e a saída é a de quem pediu para pulá-la. O código está correto para o caso que ele
descreve; o caso que ele não descreve é o que acontece na prática.

Note que `metrics.total_errors` e `unique_errors` são atribuídos **antes** do retorno antecipado
(`coverage.py:739-740`). Isso é uma boa notícia com uma armadilha: o `errors.csv` sobrevive intacto
a D1, então um run degradado ainda produz contagem de violações correta — e portanto parece
*parcialmente* válido, que é pior do que parecer inteiramente inválido.

### 2.5 Superfície de exposição

| Caminho | Exposto a D1? | Por quê |
|---|---|---|
| `rv-experiment run` / `rv-platform run` no host | **Sim** | nada exporta a variável |
| Qualquer execução em container | Não | `docker/android/Dockerfile:34` |
| `scripts/gh91_sa_rerun.py`, `scripts/gh91_campaign.py` | Não | `_gator_env()` |
| Suítes de teste que tocam GATOR | Sim | quatro testes documentados em `docs/handoff/20260820_gh104_grupo9_prompt.md:197` "querem `ANDROID_SDK_HOME`" |

O padrão da campanha de produção é Docker, e é por isso que este defeito atravessou seis meses sem
morder: **ele só morde o desenvolvimento local**, que é exatamente onde ninguém confere `cov_*`.

### 2.6 Nota de risco sobre o nome da variável

`ANDROID_SDK_HOME` não é, no vocabulário do Android, a raiz do SDK. Historicamente ela nomeia o
diretório que contém `.android/` (AVDs, `adb_usb.ini`, chaves de depuração); a raiz do SDK é
`ANDROID_HOME`, hoje `ANDROID_SDK_ROOT`. O Google depreciou `ANDROID_SDK_HOME` em favor de
`ANDROID_USER_HOME`. O `gator` usa o nome com o sentido trocado.

Isso importa para o reparo: **exportar `ANDROID_SDK_HOME=$ANDROID_HOME` no ambiente do processo
inteiro** — que foi o que fiz à mão na execução B, e o que o Dockerfile faz — pode fazer o emulador
e o `adb` procurarem AVDs em `$ANDROID_HOME/.android/avd`. Na execução B não mordeu (o emulador
subiu e o AVD `RVSec` foi encontrado), mas o risco é estrutural, e é um argumento forte para
preferir `--sdk` a variável de ambiente, ou para setar a variável **apenas no `env` do subprocesso
do GATOR**, como o `_gator_env()` faz.

### 2.7 Opções de reparo

| # | Opção | Custo | Efeito colateral |
|---|---|---|---|
| **A** | Emitir `--sdk <raiz>` na linha de comando (`config.py:370-395`), derivando a raiz de `ANDROID_HOME`/`ANDROID_SDK_ROOT` | ~5 linhas | Nenhum: o argumento tem precedência sobre a variável no `gator:62`. Não polui o ambiente. **Recomendada.** |
| B | Portar `_gator_env()` para o executor do `rv-static-analysis` | ~10 linhas | Seta a variável no `env` do filho apenas. Reusa código provado. Mantém o nome ambíguo vivo. |
| C | Falhar a configuração quando a raiz do SDK não for resolvível | ~3 linhas | Transforma degradação em recusa. **Complementar a A, não alternativa** — ver D3. |
| D | Documentar a variável como pré-requisito e não mudar código | 0 | É o que se fez seis vezes desde julho. Não funcionou. |

---

## 3. D2 — a análise estática mira o conjunto congelado

### 3.1 O mecanismo

`modules/rv-static-analysis/src/rv_static_analysis/config.py:196-208`:

```python
# Only default mop_dir when targets_file is not set — the two are mutex (INV-ANA-33).
if not self.mop_dir and not self.targets_file:
    self.mop_dir = str(rvsec_path / "rvsec" / "rvsec-mop" / "src" / "main" / "resources" / "jca")
```

O literal `jca` é o default. Isso, sozinho, é razoável — todo default escolhe alguma coisa. O
defeito está em quem constrói o objeto: `ExperimentConfig.get_static_analysis_config()`
(`modules/rv-experiment/src/rv_experiment/config.py:899`, retorno em `:949-957`) instancia

```python
return RVStaticAnalysisConfig(
    rvsec_root=rvsec_root, lib_dir=lib_dir, gator_dir=gator_dir,
    analysis_client_jar=analysis_client_jar, output_dir=self.output_dir,
    working_dir=self.output_dir, validate_on_init=False, **kwargs,
)
```

sem `mop_dir`, **tendo `self.specification_set` à mão**. E a mesma classe, cinquenta linhas acima,
faz o mapeamento certo para o outro consumidor: `get_monitor_generation_config()`
(`config.py:695-719`) despacha `jca` → `resources/jca`, `jca_android` → `resources/jca_android`,
`generic` → `resources/generic`, `custom` → `custom_specs_dir`, e levanta `ConfigurationError` no
default.

**A mesma classe resolve o conjunto para a geração de monitores e o descarta para a análise
estática.** Não é um default mal escolhido; é um acoplamento que existe de um lado e não do outro.

Consequência para `custom`: um experimento com `--specification-set custom --custom-specs-dir X`
gera monitores de `X` e analisa alcançabilidade contra `jca`. O mesmo vale para `generic`, onde a
divergência seria total — `generic` não monitora API de criptografia nenhuma.

### 3.2 O que já se sabia

Catalogado como **bloqueador B4** em `experimento-gh104/CONTEXTO.md:147`, com data de 2026-08-18:

> | B4 | `mop_dir` da análise estática deixa de apontar para `jca` fixo |
> `modules/rv-static-analysis/src/rv_static_analysis/config.py:199-208` fixa o literal `jca`;
> `get_static_analysis_config()` (`modules/rv-experiment/src/rv_experiment/config.py:941-950`)
> nunca passa `mop_dir` | **NÃO MORDE nesta corrida** |

E a justificativa, em `CONTEXTO.md:153-162`, é boa: o estágio 2 da campanha gh104 reusa os
`.apk.json` da `comp162`, com os três skips ligados, então a análise estática não roda e o
`mop_dir` nunca é consultado. O documento inclusive **declara o preço** — "`cov_mop` continua
medindo o alcance das 23 specs do `jca`... é a mesma régua da `comp162`, aplicada aos dois lados de
propósito". Isso é rigor: o defeito foi visto, avaliado, e neutralizado por desenho experimental.

O que este relatório acrescenta é (a) a primeira observação do B4 disparando de fato, com a linha
de comando capturada, e (b) a medição do delta, que ninguém tinha feito.

### 3.3 A medição — e por que ela desarma a urgência

O cliente `RvsecAnalysisClient` resolve alvos por `MopSpecsTargetSource` com política **LENIENT**:
casamento por `(className, methodName)`, ignorando assinatura, porque curingas do AspectJ deixam a
assinatura semanticamente indefinida (`openspec/specs/analysis/spec.md:418`, INV-ANA-35). Então a
pergunta certa não é "os dois diretórios são diferentes?" — é "os conjuntos de pares
`(classe, método)` que eles produzem são diferentes?".

Extraindo os pares dos pointcuts `call(...)` dos dois diretórios:

| conjunto | pares `(classe, método)` |
|---|---|
| `jca` | 70 |
| `jca_android` | 69 |
| interseção | 69 |
| só em `jca` | **1** — `(MessageDigest, reset)` |
| só em `jca_android` | 0 |

A diferença é um único alvo: `jca/MessageDigestSpec.mop:74-75` declara `event reset` sobre
`call(void MessageDigest.reset())`; o `jca_android/MessageDigestSpec.mop` não o declara (8 eventos
contra 9). Os 23 arquivos têm nomes idênticos nos dois conjuntos.

Depois medi o efeito de ponta a ponta, rodando o mesmo GATOR sobre o mesmo APK trocando só o
`mopDir`:

```
jca          reachable=55  reachesTarget=32  directlyReachesTarget=21
jca_android  reachable=55  reachesTarget=32  directlyReachesTarget=21
métodos com veredito diferente: 0 de 106
```

Os dois JSON diferem em cinco bytes de ordenação de eventos implícitos do WTG (`home`/`power`/
`back`) — não determinismo de iteração, sem relação com o `mopDir`. **Semanticamente idênticos.**

Ou seja: hoje, neste corpus, D2 custa zero. Todo método que alcança `MessageDigest.reset` alcança
outro alvo do `MessageDigest` pelo mesmo caminho, então nenhum veredito muda.

### 3.4 Por que ainda assim é preciso decidir

Três razões, em ordem crescente de força:

1. **O delta é do estado de hoje, não uma propriedade.** Uma medição de "zero" válida em
   2026-08-21 sobre um APK não é um contrato. Nada no código impede que o delta cresça, e nada o
   mede continuamente.

2. **A gh105 vai aumentá-lo, por construção.** O Grupo 5 da change em andamento cria
   `<Chain>Junction.mop` — arquivos novos, **só no `jca_android`**, com pointcuts sobre
   `SecureRandom`, `IvParameterSpec` e `Cipher` (`tasks.md` 5.1, e o comentário do grupo: "cada um
   deles cresce o universo enumerado, que é por isso que nenhum gate pode ter contagem literal").
   Cada junction spec é um alvo novo que o `mopDir=jca` não conhece. O defeito que hoje custa um
   alvo passará a custar tantos quantos o Grupo 5 criar — e passará a custá-los **exatamente na
   campanha que vai medir se a gh105 funcionou.**

3. **A régua não é declarada em lugar nenhum da saída.** `coverage.csv` e `summary.csv` trazem
   `cov_reachable`, `cov_reaches_target` e `cov_directly_reaches_target` sem uma coluna que diga
   contra qual conjunto foram calculados. O `experiment_config.json` grava
   `specification_set: jca_android`, o que faz o leitor concluir — corretamente, pela documentação,
   e erradamente, pelo código — que as três colunas se referem àquele conjunto. O `CONTEXTO.md`
   declara o preço para a campanha gh104 porque um humano se lembrou; nada no artefato o declara.

### 3.5 O que **não** é afetado

Vale delimitar, porque a versão que eu reportei primeiro exagerava o alcance:

* **`cov_class`, `cov_act`, `cov_method`** não dependem dos alvos — vêm do inventário de classes e
  métodos do APK. D2 não os toca.
* **`errors.csv`** não depende da análise estática. As violações nascem do monitor tecido.
* **`results/gh101_group8_jca_android`** (8 de agosto, o único experimento `jca_android` anterior
  a este) rodou com `run_static_analysis: false`. **Não foi contaminado por D2** — eu afirmei o
  contrário na conversa antes de conferir; a afirmação estava errada.
* A **campanha gh104**, como planejada, também não é afetada — os três skips ligados, `.apk.json`
  reusados da `comp162`, decisão B4.

Varrendo `results/` e `experimento-*/`, os únicos experimentos que já combinaram
`specification_set: jca_android` com `run_static_analysis: true` são as **duas sondas de hoje**.
O passivo histórico de D2 é, até onde a árvore registra, nulo.

### 3.6 Opções de reparo

| # | Opção | Custo | Observação |
|---|---|---|---|
| **A** | `get_static_analysis_config()` passa `mop_dir` derivado de `specification_set`, reusando o mapeamento de `get_monitor_generation_config()` | ~10 linhas + extrair o mapa | Fecha o acoplamento na origem. Cobre `custom` e `generic` de graça. **Recomendada.** |
| B | Remover o default `jca` e exigir `mop_dir` explícito | ~5 linhas | Mais rigoroso, mas quebra os chamadores que hoje dependem do default (`gh91_sa_rerun.py` tem o seu próprio, então sobrevive) |
| C | Registrar o `mop_dir` efetivo numa coluna nova do `summary.csv` | ~15 linhas | Não repara; torna auditável. Vale **junto** com A, não no lugar |
| D | Manter e declarar por documento, como o B4 fez | 0 | Funcionou para uma campanha porque alguém escreveu. Não escala, e o Grupo 5 muda a aritmética |

---

## 4. D3 — o INV-EXP-16 não é aplicado (achado novo)

### 4.1 O invariante

`openspec/specs/experiment/spec.md:207`:

> **INV-EXP-16**: The PreProcessor MUST filter APKs for execution based on static analysis data
> presence. `get_instrumented_apks()` MUST return only APKs from `instrumented_apks/` that have a
> corresponding `.apk.json` file (static analysis output) in the same directory. APKs without
> static analysis data MUST be logged with a warning and **excluded from execution**.

E em `:225`, a razão: "APKs without static analysis data produce meaningless coverage results and
MUST be excluded from execution."

O invariante existe exatamente para impedir o que a execução A produziu.

### 4.2 Onde ele se perde

O filtro está implementado e funciona. `pre_processor.py:456-470` exclui o APK sem `.apk.json` e
loga; `:483-491` cai para os APKs originais. A execução A registrou os dois passos:

```
08:52:57,141  WARNING  No instrumented APKs found, using original APKs
```

Mas a lista que o filtro devolve **é usada só como teste de vazio**.
`experiment_controller.py:267-276`:

```python
apks = self.pre_processor.get_instrumented_apks()
# ... "these APKs are what rv-platform will install on emulators for task execution."
if not apks:
    self.logger.error("No APKs available for execution")
    return False
```

O comentário afirma que `apks` é o que a plataforma vai instalar. A variável não é passada adiante.
Quem decide o que instalar é `execution_controller.py:260-262`, que refaz a escolha por conta
própria e por outro critério:

```python
apks_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
if not os.path.exists(apks_dir) or not os.listdir(apks_dir):
    apks_dir = self.config.apks_dir
```

**Diretório não vazio.** O diretório contém o `.apk` instrumentado, o `.idsig`, o
`instrument_results.json` e o `instrument_errors.json` — não está vazio, e nunca estaria mesmo que
o APK tivesse sido excluído pelo filtro. A plataforma recebe `apks_dir = instrumented_apks/` e
instala o APK instrumentado.

O log da execução A tem as duas linhas em sequência, uma contradizendo a outra:

```
08:52:57,141  WARNING  No instrumented APKs found, using original APKs
08:52:57,151  INFO     Platform initialized with config: results/gh105_reach_probe/instrumented_apks
```

Que o APK instalado foi o **instrumentado** está provado pelas 27 linhas `RVSEC-COV` do logcat: um
APK original não tem instrumentação de cobertura e não emite nenhuma.

### 4.3 Por que este é o defeito que importa

D1 é uma variável de ambiente faltando — cinco minutos de reparo, e seis meses de documentação
dizendo isso. O que o transforma de inconveniência em risco de medição é D3:

| | com D3 (hoje) | sem D3 |
|---|---|---|
| análise estática falha | run continua | run recusado |
| saída | `coverage.csv` vazio, `summary` zerado, `✅ completed`, exit 0 | erro, exit ≠ 0 |
| quem percebe | ninguém, a menos que compare o logcat com o CSV | quem rodou, na hora |
| custo | uma campanha inteira de resultados inutilizáveis descobertos tarde | cinco minutos |

E há um agravante de leitura: como o `errors.csv` **sobrevive** a D1 (§2.4), o run degradado produz
contagem de violações correta ao lado de cobertura zerada. Um leitor que confira só as violações
conclui que o run está bom.

Vale notar que o `platform.components.static_analysis` também avisou —
`WARNING  No static analysis files found for cryptoapp.apk` (linha 213) — e também não parou nada.
São **três** avisos sobre a mesma ausência, em três camadas, e nenhum deles é uma barreira.

### 4.4 Opções de reparo

| # | Opção | Custo |
|---|---|---|
| **A** | `ExecutionController.setup()` recebe a lista de `App` filtrada em vez de refazer a escolha por diretório | ~20 linhas, toca duas assinaturas. Faz o INV-EXP-16 valer de fato. **Recomendada.** |
| B | Fazer o PreProcessor abortar a fase 2 quando a análise foi pedida e não produziu dado para nenhum APK | ~10 linhas. Cobre D1 sem tocar a passagem de APKs; não cobre o caso misto (alguns APKs com dado, outros sem) |
| C | Marcar o run como degradado em `summary.csv`/`results.json` e seguir | ~15 linhas. Preserva o comportamento; torna o dano legível. Vale como complemento |
| D | Corrigir o comentário de `experiment_controller.py:264-266` para descrever o que o código faz | 1 linha. Não repara nada, mas hoje o comentário **desinforma** quem for ler |

---

## 5. Como os três interagem

```
D1 ─ análise estática morre em silêncio (aviso, não erro)
 │
 └─► D3 ─ o run executa assim mesmo, contra o invariante que existe para impedi-lo
      │
      └─► saída "bem-sucedida" com cobertura zerada e violações corretas
           = um resultado que parece parcialmente válido

D2 ─ análise estática, quando roda, mira o conjunto errado
 │
 └─► colunas de alcançabilidade contra outra régua, sem nada declarar qual
      (hoje: delta de 1 alvo, efeito medido nulo — amanhã: + as junction specs do Grupo 5)
```

D1 e D3 compõem: o primeiro produz a ausência, o segundo a torna invisível. D2 é independente e
opera no caminho feliz — ele só aparece quando a análise **funciona**.

Uma consequência prática de os três serem independentes: **repará-los em ordem inversa de custo
não é a ordem certa.** D1 sozinho (o mais barato) faz D3 parar de disparar por esta causa, mas
deixa D3 armado para a próxima causa — timeout do GATOR, `OutOfMemoryError` do Soot, APK que o
apktool não decodifica. D3 é a barreira; D1 é uma das coisas que ela deveria barrar.

---

## 6. Escopo, e as três perguntas da Fase 0

### O que exatamente quero mudar

1. Que o GATOR receba a raiz do SDK do processo que o invoca, e não de uma variável de ambiente
   que ninguém exporta (D1).
2. Que a análise estática mire o conjunto de especificações que o experimento declarou (D2).
3. Que um run cuja análise estática não produziu dado seja **recusado**, não silenciosamente
   degradado (D3).

### Por que importa

O produto do pipeline é medição. As três colunas de alcançabilidade e o denominador de cobertura
entram em tabelas de tese e de artigo. Um defeito que devolve zeros com aparência de medição, num
run que se declara bem-sucedido, é da categoria mais cara: não custa tempo de execução, custa
credibilidade de resultado, e o custo só aparece quando alguém pergunta por que a cobertura daquele
braço ficou baixa.

#### Por que isto é ameaça à validade, e não só defeito de pipeline

A pergunta que este programa de pesquisa faz é a de Legunsen, Hassan, Xu, Roşu e Marinov,
*How Good Are the Specs? A Study of the Bug-Finding Effectiveness of Existing Java API
Specifications* (ASE'16) — o trabalho que fixou o método de avaliar especificações de verificação
em tempo de execução pela sua eficácia empírica, e cuja linhagem o artigo do próprio grupo
continua (Torres, Cavalcanti, Ribeiro, Bonifácio, Souza, **Legunsen**, *Runtime Verification of
Crypto APIs: An Empirical Study*). Aquele estudo monitorou 199 especificações JavaMOP — 182
escritas à mão e 17 mineradas — contra 200 projetos, inspecionou 652 violações das primeiras e
200 das segundas, reportou 95 bugs dos quais 74 já foram corrigidos, e mediu taxas de falso
alarme de **82,81 %** e **97,89 %**. A conclusão é que a tecnologia amadureceu no *custo* (sobrecarga
média abaixo de 4,3×) mas não na *eficácia*: apenas 11 das 182 especificações escritas à mão
levaram à descoberta de algum bug, e os autores encerram pedindo que a comunidade repense
"spec finding" e "spec engineering".

É nesse eixo — eficácia da especificação, não corretude do software sob teste — que os três
defeitos deste relatório mordem, e é por isso que eles são mais caros do que o tamanho do reparo
sugere. Numa avaliação de eficácia, uma execução sem violação é ambígua por natureza: ou a
especificação não pegou nada, ou o teste nunca chegou à API monitorada. **O que desfaz essa
ambiguidade é exatamente a medição de alcance** — `cov_reachable`, `cov_reaches_target`,
`cov_directly_reaches_target` — que é o que D1 zera em silêncio e o que D2 calcula contra a
régua errada.

Concretamente, para os dois lados do juízo:

* **D1 + D3** produzem uma execução com cobertura zerada e violações intactas. Lida de fora, ela
  descreve um app que o testador não explorou. Se essa linha entrar numa tabela de eficácia, ela
  empurra a conclusão para "a especificação não teve oportunidade" quando a oportunidade existiu
  — 27 métodos foram cobertos e o `Cipher.init` foi alcançado.
* **D2** desloca o denominador do alcance para um conjunto de alvos que não é o do experimento.
  Numa comparação pareada em que o conjunto de especificações é *o único fator que varia* — que é
  literalmente o desenho declarado da campanha gh104 (`experimento-gh104/manifest.json`) — medir o
  alcance dos dois braços contra a mesma régua velha é defensável **se declarado**, e é o que a
  decisão B4 fez. Não declarado, é o fator confundidor entrando pela porta que o desenho fechou.

O ponto não é que os números de hoje estejam errados — a §3.3 mede que, neste corpus, D2 não muda
nenhum veredito. É que a classe de erro é a que mais custa num estudo de eficácia: ela não produz
um resultado obviamente quebrado, produz um resultado plausível com o denominador errado.

Há também um custo imediato e datado: a campanha conjunta gh104+gh105 roda depois que as duas
changes aterrissarem, com dois dos três braços (`aperv:mop_off_llm_off` e `aperv:mop_on_llm_off`)
consumindo `mop_data: static_analysis` sobre `spec_set: jca_android`
(`experimento-gh104/manifest.json`). A decisão B4 a protege **enquanto** ela reusar os `.apk.json`
da `comp162`. Se esse desenho mudar — e ele muda se alguém quiser cobertura medida contra as specs
novas — D2 passa a morder na campanha que decide se a gh105 funcionou.

### Que partes do sistema são afetadas

| Módulo | Papel | Arquivos |
|---|---|---|
| `rv-static-analysis` | onde D1 e o default de D2 vivem | `src/rv_static_analysis/config.py` (`:180-208`, `:340-400`) |
| `rv-experiment` | onde D2 perde o conjunto e D3 perde a lista | `src/rv_experiment/config.py:899-957`; `experiment/experiment_controller.py:267-276`; `experiment/workflow/execution_controller.py:260-262`; `experiment/workflow/pre_processor.py:430-491` |
| `rv-android-core` | onde a degradação vira zero | `src/rv_android_core/domain/coverage.py:742-748` |
| `lib/gator/gator` | binário de terceiro, versionado aqui | `:62-64`, `:195-199` — evitar editar; o `--sdk` já existe |
| `rv-platform` | terceiro aviso não-barreira | `components/static_analysis.py` |
| Specs OpenSpec | INV-EXP-16 (não aplicado), INV-ANA-33 (respeitado) | `openspec/specs/experiment/spec.md:207,225`; `openspec/specs/analysis/spec.md:290-291,365-369,418,450` |

Nenhum dos três toca a árvore Java, o weaver, os monitores ou o conjunto de especificações. São
todos do lado Python do orquestrador.

---

## 7. Encaminhamento sugerido

### Uma change ou três?

**Uma**, com três tarefas. Os três compartilham módulo, tema e teste de aceitação — um run com
análise estática pedida ou produz dado correto ou falha. Fatiar em três issues multiplica cerimônia
sobre um reparo que cabe em ~50 linhas, e a tabela de seleção do `WORKFLOW.md` §3 é explícita em
que contagem de arquivos não escolhe trilha.

### Qual trilha

Pelo guia de decisão do `WORKFLOW.md` §3:

* *Introduz comportamento novo que precisa ser documentado em spec?* — **Sim, para D3**: fazer o
  INV-EXP-16 valer muda o comportamento observável (um run que hoje completa passa a falhar), e o
  invariante existente descreve algo que o código não faz. Isso é delta de spec, não só correção.
* *Cruza fronteira de módulo com implicação arquitetural?* — **Sim, mas raso**: `rv-experiment` ↔
  `rv-static-analysis`, dois módulos, sem redesenho.
* *É correção de bug com escopo mecânico?* — D1 e D2, sim; D3, não.

**Recomendação: Fast-Forward SDD.** D1 e D2 sozinhos seriam Quick Path; D3 puxa para cima porque
tem decisão de desenho (recusar o run inteiro? recusar por APK? marcar como degradado e seguir?) e
porque um invariante publicado precisa ou passar a valer, ou ser reescrito. Full SDD é excessivo:
dois módulos, sem nova capacidade, sem escolha arquitetural de fundo.

### Ordem de execução sugerida dentro da change

1. **D3 primeiro** — é a barreira. Com ela de pé, qualquer falha futura da análise estática (não só
   D1) para o run em vez de degradá-lo, e os testes dos outros dois passam a ter oráculo.
2. **D1** — o reparo mais barato, e o que faz D3 parar de disparar na prática.
3. **D2** — o de maior alcance conceitual e menor efeito medido hoje; entra com o registro do
   `mop_dir` efetivo na saída (opção 3.6-C) para que a régua fique auditável.

### Decisões que precisam do pesquisador

1. **D3 recusa o run inteiro ou só o APK afetado?** Num corpus de 162 APKs, um GATOR que estoura o
   timeout em três deles não deveria matar a campanha. Mas "seguir com 159" precisa aparecer no
   artefato, senão o `n` muda em silêncio.
2. **O `mop_dir` efetivo vira coluna de `summary.csv`?** É mudança de header, e o `aperv-tool`
   declara header fixo (`analysis/violations.py:62-80`, o bloqueador B5 do gh104 é exatamente sobre
   isso). Baratinho tecnicamente, mas mexe num contrato que já tem um leitor congelado.
3. **Reabrir o B4 do gh104 ou deixar a decisão de pé?** A decisão continua correta para o desenho
   atual da campanha. A pergunta é se ela deve deixar de ser necessária antes da campanha rodar.
4. **Isto entra antes ou depois da gh105 aterrissar?** A gh105 está em 28/74, com o Grupo 5 —
   o que cria as junction specs — liberado e ainda não iniciado. Reparar D2 **antes** do Grupo 5
   significa que as junction specs nascem já contadas; **depois** significa que a primeira medição
   com elas usa a régua velha.

---

## 8. Evidência

### Artefatos commitados

| Caminho | O que carrega |
|---|---|
| `data/gh105/evidence/f2-reach-probe.md` | o relatório da sonda, com os dois defeitos na §"Two pipeline defects" |
| `data/gh105/evidence/reach-probe/probe-a.logcat` | as 27 linhas `RVSEC-COV` da execução degradada |
| `data/gh105/evidence/reach-probe/probe-a-errors.csv` | o `errors.csv` da execução A |
| `data/gh105/evidence/reach-probe/coverage.csv`, `summary.csv` | as saídas da execução B, para contraste |
| `data/gh105/evidence/reach-probe/experiment_config.json` | a configuração declarada da execução B |

Os diretórios `results/gh105_reach_probe` e `results/gh105_reach_probe_b` têm o material completo,
mas `results/` é ignorado pelo git.

### Reproduzir D1

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
export ANDROID_HOME=/home/pedro/desenvolvimento/aplicativos/android/sdk
unset ANDROID_SDK_HOME
uv run rv-experiment run --tools ape --timeouts 60 --apks-dir ./apks_examples \
    --specification-set jca_android --instrumentation-variant dexlib2 \
    --name d1_repro --no-window
# esperado: "KeyError: 'ANDROID_SDK_HOME'" no log, "Static analysis completed" logo depois,
#           coverage.csv só com cabeçalho, e "✅ Experiment completed successfully!" no fim
```

### Reproduzir a medição de D2

```bash
SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources
export ANDROID_SDK_HOME=$ANDROID_HOME
for SET in jca jca_android; do
  .venv/bin/python lib/gator/gator a -p $PWD/apks_examples/cryptoapp.apk \
    --client-jar $PWD/lib/gator/rvsec-analysis-client.jar --out /tmp/cryptoapp.$SET.json \
    -client RvsecAnalysisClient -clientParam mopDir=$SPECS/$SET \
    -cgAlgorithm spark --timeout 600 --jvm-memory 12G \
    -clientParam codePackage=br.unb.cic.cryptoapp
done
# comparar os campos reachable/reachesTarget/directlyReachesTarget por assinatura:
# medido em 2026-08-21 — 106 métodos, 0 vereditos diferentes
```

### Reproduzir a contagem de alvos

Extração dos pares `(classe, método)` dos pointcuts `call(...)` dos dois diretórios, com
neutralização de comentários de linha. Medido: 70 / 69 / interseção 69 / delta
`(MessageDigest, reset)`. A extração é uma aproximação por expressão regular do que o
`MopSpecsTargetSource` faz em Java; a checagem de sanidade é que ela reproduz a diferença de
contagem de eventos entre `jca/MessageDigestSpec.mop` (9) e `jca_android/MessageDigestSpec.mop` (8).

---

## 9. Correções a afirmações anteriores desta sessão

Duas coisas que eu disse na conversa antes de conferir, e que a investigação desmentiu:

1. **"Vale para todo experimento `jca_android` já rodado por esse caminho, o `gh101_group8`
   inclusive."** Errado. O `gh101_group8` rodou com `run_static_analysis: false`; a análise estática
   não rodou e o `mop_dir` não foi consultado. Varrendo `results/` e `experimento-*/`, os únicos
   runs `jca_android` com análise estática ligada são as duas sondas de hoje. O passivo histórico
   de D2 é nulo.

2. **Apresentar D1 e D2 como achados novos.** Os dois são conhecidos e documentados — D1 desde a
   gh91 em julho, em seis lugares, com dois consumidores já corrigidos; D2 desde 2026-08-18, como
   o bloqueador B4, com decisão registrada. O que esta sessão acrescenta é a primeira observação
   dos dois disparando no caminho de experimento, a medição do delta de D2, e o D3, esse sim não
   catalogado.

---

## 10. Índice de referências no código

| Referência | Papel |
|---|---|
| `lib/gator/gator:62-64` | o subscrito nu de `ANDROID_SDK_HOME` |
| `lib/gator/gator:195-199` | o argumento `--sdk`, que dispensa a variável |
| `modules/rv-static-analysis/src/rv_static_analysis/config.py:180-194` | resolve `ANDROID_HOME` e `android_jar`, que não são usados na linha de comando |
| `modules/rv-static-analysis/src/rv_static_analysis/config.py:196-208` | o default `jca` de `mop_dir` |
| `modules/rv-static-analysis/src/rv_static_analysis/config.py:340-400` | o construtor da linha de comando, sem `--sdk` |
| `modules/rv-experiment/src/rv_experiment/config.py:695-719` | o mapeamento `specification_set` → diretório, feito certo, para monitores |
| `modules/rv-experiment/src/rv_experiment/config.py:899-957` | `get_static_analysis_config()`, que não passa `mop_dir` |
| `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:356-378` | falha da análise tratada como `warning` |
| `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:430-491` | o filtro do INV-EXP-16 e o fallback |
| `modules/rv-experiment/src/rv_experiment/experiment/experiment_controller.py:267-276` | a lista filtrada usada só como teste de vazio |
| `modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py:260-262` | a escolha paralela do `apks_dir` por diretório não vazio |
| `modules/rv-android-core/src/rv_android_core/domain/coverage.py:739-748` | onde a ausência de dado vira 0 %, com a premissa `--skip-static` no comentário |
| `scripts/gh91_sa_rerun.py:333-346` | `_gator_env()`, o reparo de D1 já escrito e nunca aplicado |
| `scripts/gh91_sa_rerun.py:326-330` | `_mop_dir()`, que fixa `jca` também |
| `docker/android/Dockerfile:34` | `ENV ANDROID_SDK_HOME=/opt/android`, a imunidade do Docker |
| `experimento-gh104/CONTEXTO.md:147,153-162` | o bloqueador B4 e a decisão de por que não morde |
| `experimento-gh104/manifest.json` | `spec_set: jca_android`, dois braços com `mop_data: static_analysis` |
| `openspec/specs/experiment/spec.md:207,225` | INV-EXP-16 |
| `openspec/specs/analysis/spec.md:290-291,365-369,418,450` | contrato de `mop_dir`/`targets_file`, INV-ANA-33/35, política LENIENT |

---

## 11. Referências

* Owolabi Legunsen, Wajih Ul Hassan, Xinyue Xu, Grigore Roşu, Darko Marinov.
  **How Good Are the Specs? A Study of the Bug-Finding Effectiveness of Existing Java API
  Specifications.** ASE'16, Singapura, setembro de 2016, p. 602-613.
  DOI [10.1145/2970276.2970356](http://dx.doi.org/10.1145/2970276.2970356).
  PDF local: `/home/pedro/Downloads/LegunsenETAL16SpecEval.pdf`.
  199 especificações JavaMOP (182 escritas à mão, 17 mineradas) × 200 projetos; 18.065 testes
  manuais e 2.135.081 gerados; sobrecarga média < 4,3×; 652 + 200 violações inspecionadas;
  95 bugs reportados, 74 corrigidos; falso alarme de 82,81 % e 97,89 %. É o trabalho que define
  o eixo de avaliação — *eficácia* da especificação, não eficiência do monitoramento — em que
  este relatório situa o custo dos três defeitos (§6).

* Pedro Torres, Ismael Cavalcanti, Marcelo Ribeiro, Rodrigo Bonifácio, Diego Souza, Owolabi
  Legunsen. **Runtime Verification of Crypto APIs: An Empirical Study.** O artigo do próprio
  grupo, na mesma linhagem. PDF local:
  `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal-jss-jca/main.pdf`
  (registrado em `docs/20260421_problema_dex2jar.md:14`).

**Nota sobre vocabulário.** A seção 3 do `docs/WORKFLOW.md` cita literatura de *spec-driven
development* assistido por IA, onde "spec" nomeia o documento de requisitos que precede a geração
de código. Não é o sentido em uso aqui. Neste projeto "especificação" é o objeto formal —
`.mop`/`.rvm`, autômato paramétrico, monitor tecido — avaliado pela sua eficácia empírica em
achar defeitos, no sentido de Legunsen et al. e, antes deles, de Robillard et al.: *"a way to use
an API as asserted by the developer or analyst, and which encodes information about the behavior
of a program when an API is used"*. As duas literaturas usam a mesma palavra para coisas
diferentes; o `WORKFLOW.md` é autoridade sobre a cerimônia de trilha e não sobre o que uma
especificação é neste sistema.
