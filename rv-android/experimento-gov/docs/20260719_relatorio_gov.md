# Relatório — Runtime Verification de misuse de JCA em apps do governo brasileiro (gov.br)

**Data:** 2026-07-19 · **Autor da condução:** experimento RV4Android · **Solicitante:** orientador
**Execução:** local (1 host, 8 containers Docker) · **Imagem:** `phtcosta/rvandroid:0.9.2`
**Artefatos:** `experimento-gov/results/consolidado_gov/` · **Memória de condução:** `RV_ANDROID_DATASET_GOV/REGISTRO.md`

---

## 1. Sumário executivo

Aplicamos **verificação em runtime (RV4Android)** para detectar **mau uso da API de
criptografia Java (JCA — Java Cryptography Architecture)** em **33 aplicativos oficiais
do governo brasileiro (gov.br)**, dirigindo a UI de cada app com o explorador **APE** por
**1 hora** cada, sobre APKs **instrumentados com monitores JCA** (variante dexlib2).

**Resultado principal:** **30 dos 33 apps (91%) dispararam ≥1 violação MOP de JCA** durante
a execução. Foram registradas **424 violações distintas** (por local de chamada), com
**~80 mil ocorrências brutas** no total. O achado **mais defensável** é o uso de
**algoritmos de hash fracos (SHA-1 / MD5)**: presente em **30/33 apps**. As violações vêm
**majoritariamente de bibliotecas Java empacotadas** (Google Play Services, OkHttp, Firebase,
Tink, flutter_secure_storage) — não necessariamente de código de criptografia próprio do app,
mas executando **dentro do processo** do app.

**Ressalva importante (§9):** os dois tipos dominantes em contagem bruta
(`InvalidSequenceOfMethodCalls` e `InvalidKeyStoreType`) contêm padrões conhecidamente
**ruidosos** no conjunto de specs JCA quando aplicado a Android (ex.: o uso legítimo de
`AndroidKeyStore` é sinalizado como "keystore inválido"). O resultado deve ser lido como
**superfície de misuse observada**, com o SHA-1/MD5 como o sinal forte.

---

## 2. Objetivo e enquadramento

O orientador pediu uma demonstração de RV4Android sobre um **dataset novo de apps gov.br**.
A métrica de interesse é **quantas e quais violações MOP de JCA** cada app dispara em runtime —
**não** cobertura de código. "MOP" aqui = *monitored operations* (operações monitoradas pelos
specs JCA), não terminologia de segurança genérica.

**Por que RV em runtime, e não análise estática de misuse?** O monitor JCA instrumentado
observa **chamadas reais** à API de criptografia enquanto o app roda, capturando o **contexto de
execução** (sequência de métodos, argumentos como o nome do algoritmo). Isso detecta misuse que
depende de fluxo dinâmico, e independe de o código estar ofuscado.

---

## 3. Dataset e critério de inclusão

- **Origem:** 37 APKs coletados via canal oficial da Play Store (`adb pull` num AVD
  `RVSecPlay`, API 30 / google_apis_playstore / x86_64), ~1,6 GB. Single-APK preserva o
  `base.apk` genuíno; splits foram mesclados (`APKEditor m`), realinhados e re-assinados.
- **Critério de inclusão — "existe superfície JCA?"** Contamos **call sites de JCA** (instruções
  `invoke-*` cujo *callee* é classe de `javax.crypto.*`, `java.security.*`,
  `android.security.keystore.*`, `javax.net.ssl.*`) em **todos os dex**, com androguard.
  - Essas classes são **de plataforma → não-ofuscáveis**, logo a contagem é **sólida sob
    ofuscação**.
  - **Todos os 37 apps têm superfície JCA > 0.** Nenhum app é excluído por "não usar cripto".
  - **Refutação registrada:** a triagem herdada rejeitava apps React-Native/Flutter alegando
    "cripto em Dart/JS". Isso é **irrelevante** para MOP — o monitor dispara em **qualquer**
    chamada JCA no **bytecode Java** que executa, inclusive de libs empacotadas. Framework do
    app ≠ ausência de JCA em Java. (Vários apps RN/Flutter estão entre os de **maior** superfície.)
  - Reachability estática "de verdade" foi **descartada**: exigiria call graph = a análise
    estática pesada que este experimento **pula** de propósito.

---

## 4. Exclusões (34 elegíveis → 33 executados)

Dos 37, **4** ficaram de fora, por **dois motivos distintos**:

### 4.1 Três apps PAIRIP — excluídos de propósito, sem tentar
`br.gov.dataprev.carteiradigital` (83 MB), `br.gov.serpro.cnhe` (57 MB),
`com.goodbarber.exercitobr` (35 MB). Todos têm o anti-tamper **PAIRIP** (`libpairipcore.so`),
que verifica integridade de DEX/assinatura em runtime. Como a instrumentação **modifica o DEX** e
**re-assina** com chave de debug, o PAIRIP mataria o app no launch. Exclusão por
**instrumentabilidade**, não por ausência de JCA.

### 4.2 `receita.rfb` — falha determinística do teto de 65.536 method-refs (forense)
`br.gov.economia.receita.rfb` (flutter, 81 MB) **falhou a instrumentação em 2 tentativas**.
**Causa-raiz medida** (não inferida): o formato DEX limita cada arquivo `.dex` a **65.536
method-refs** (índice `uint16`). O APK tem 5 dex, e **`classes3.dex` já está em 65.536** (teto
absoluto) e `classes4.dex` em 65.533. O weaver dexlib2 injeta a referência a `Coverage.log` em
cada dex; a saída woven **trunca exatamente no 3º dex** (`woven_classes3.dex` = 0 methods),
provando o overflow. A falha é **silenciosa** (exit 0, `instrument_errors.json` vazio) — o bug
conhecido de decoupling do exit-code da dexlib2. **Não-contornável** na config atual; descartado.
(Detalhe completo: `REGISTRO.md §9.2`.)

---

## 5. Metodologia de execução

| Parâmetro | Valor |
|---|---|
| Apps | **33** (instrumentados, dexlib2) |
| Ferramenta de exploração | **APE** (builtin vanilla; dirige a UI automaticamente) |
| Instrumentação | **dexlib2** (DEX-native), pré-aplicada 1× no host (resume-safe) |
| Specs | **JCA** (23 specs: MessageDigest, Cipher, KeyStore, SecureRandom, SSL/TLS…) |
| Timeout por task | **3600 s (1 h)** |
| Repetições | **1** |
| Paralelismo | **8 containers** `exp_00..07` (round-robin: exp_00=5 apps, demais=4) |
| Análise estática | **PULADA** de propósito |
| Total de tasks | **33** |

**Por que não há cobertura (%).** A cobertura precisaria de um **denominador** = o conjunto de
métodos monitoráveis do app, que só a **análise estática** (GATOR) produz. Como a static foi
pulada (pesada e fora do foco), **não há denominador** → cobertura seria vazia por construção. O
numerador (métodos executados, linhas `RVSEC-COV`) existe nos logcats mas é apenas informativo. O
**entregável é violações MOP por app**, não cobertura.

**Pipeline:** pré-instrumentação no host (8 workers Docker) → smoke de instrumentação (gate G1) →
smoke de execução (gate G2: confirmou que o APE roda o APK instrumentado **sem** `.apk.json`, 0
VerifyError, MOP dispara) → run 8× (3600 s) → resume de transitórios → consolidação offline via
logcats.

---

## 6. Condução e verificações de sanidade

A run começou 2026-07-18 ~22:52 e as tasks limpas terminaram entre ~03:00 e ~04:00 de 19/07.
Monitor horário via **cron** (`hourly_monitor.sh`) fez snapshot + auto-resume a cada hora cheia.

Verificações **medidas** (não assumidas):

- **Cada task COMPLETED durou 3.668–3.712 s** = os 3.600 s do timeout + ~65–110 s de overhead
  (boot do emulador + install + teardown). Nenhuma terminou cedo — APE só encerra por timeout.
- **APE ativo a hora toda:** o span de cada logcat ≈ 60 min e a **última violação MOP acontece
  perto do fim da hora** (ex.: meclivros, última violação 01:54:55 num run 00:55→01:54).
- **Integridade dos artefatos:** **33 logcats, 0 vazios**; **33 `.trace`, 0 vazios** (≥4 MB, com
  log real do APE). **0 VerifyError, 0 FATAL EXCEPTION, 0 ANR** em todos os logcats — a
  instrumentação não corrompeu nenhum app.

---

## 7. O caso `eSocial.Android` (1 de 33) — falha intermitente, recuperada pelo auto-resume

A 5ª task do container mais cheio, **`eSocial.Android_5.0.0`**, **falhou 11 vezes seguidas** com
`EmulatorError: Failed to start emulator RVSec` — cada tentativa rodava 27–58 min e encerrava em
ERROR perto do fim (provável restart interno de emulador do APE que falha). O monitor horário
**reiniciou o container automaticamente a cada hora**, de 03:00 a 14:00.

**Desfecho: recuperado.** Na **12ª tentativa (14:00→15:01, 3.662 s = hora cheia), a task
COMPLETOU limpa** — o `EmulatorError` era **intermitente**, não 100% determinístico, e a
insistência do auto-resume horário acabou pegando um boot bom. O dataset final é **33/33 COMPLETED,
0 FAILED**. O logcat COMPLETED (14:00) tem a hora inteira de exploração; os números do eSocial no
relatório são desse run limpo (não mais parciais). Distinto de §4.2 (aquela é determinística de
instrumentação; esta era de execução e se resolveu por retry).

---

## 8. Resultados — misuse de JCA observado

**30 de 33 apps** dispararam ≥1 violação MOP de JCA. **424 violações distintas** (dedup por
`spec+classe+método+local+tipo`); ~80 mil ocorrências brutas.

### 8.1 Por tipo de violação

| Tipo | Apps afetados | Ocorrências brutas | Leitura |
|---|---:|---:|---|
| **UnsafeAlgorithm** | **30/33** | 18.800 | **hash fraco (SHA-1/MD5)** — o achado forte |
| InvalidSequenceOfMethodCalls | 30/33 | 53.960 | ordem de chamadas fora do esperado (ver §9) |
| UnsafeProtocol | 17/33 | 3.565 | protocolo SSL/TLS inseguro/legado |
| InvalidKeyStoreType | 6/33 | 3.612 | tipo de keystore inesperado (inclui `AndroidKeyStore`, ver §9) |

**Algoritmo fraco (UnsafeAlgorithm) — o sinal mais defensável:** dos sites distintos, **SHA-1**
em 39, **MD5** em 29, outros em 49. Presente em **30/33 apps**.

### 8.2 Origem das violações (biblioteca da classe chamadora)

As violações distintas concentram-se em **libs Java empacotadas**, confirmando que o misuse
detectável não depende de cripto própria do app:

| Origem | Violações distintas |
|---|---:|
| App/obfuscado/outros | 179 |
| Google Play Services (`gms`) | 80 |
| OkHttp | 70 |
| Firebase | 63 |
| Flutter (flutter_secure_storage etc.) | 19 |
| Google Tink (`crypto.tink`) | 12 |
| AndroidX Security | 1 |

### 8.3 Top apps por violações distintas

| # | app | estado | distintas |
|--:|---|---|---:|
| 1 | br.com.valid.rnm (Carteira de Documentos) | COMPLETED | 45 |
| 2 | br.gov.mec.jornada.estudante | COMPLETED | 31 |
| 3 | br.gov.mec.meclivros | COMPLETED | 25 |
| 4 | br.gov.anac.superapp | COMPLETED | 23 |
| 5 | br.gov.saude.esusaps.vacinacao | COMPLETED | 23 |
| 6 | eSocial.Android | COMPLETED | 22 |
| 7 | br.gov.dataprev.meuimovelrural | COMPLETED | 18 |
| 8 | com.app.foraareabrasileira | COMPLETED | 18 |
| 9 | br.gov.fazenda.receita.eprocesso | COMPLETED | 17 |
| 10 | br.gov.mds.meusocial | COMPLETED | 17 |

Lista completa: `results/consolidado_gov/per_app.csv`.

### 8.4 Três apps com zero violações

`br.gov.bcb.mobile.android.calculadoracidadao`, `com.celularlegal`, `com.datasus.MedSUSAPP`
executaram **sem disparar nenhuma chamada JCA monitorada** na janela de 1 h. Têm superfície JCA
estática > 0, mas o APE não alcançou (ou o app não exercitou) esses caminhos no tempo dado.

---

## 9. Interpretação e ameaças à validade

**Leitura honesta dos tipos.** Nem toda violação MOP é uma falha de segurança inequívoca:

- **UnsafeAlgorithm (SHA-1/MD5)** — sinal **forte**. Hash fraco é misuse reconhecido (embora
  muitos usos sejam para checksums/IDs não-sensíveis dentro de libs como Firebase/GMS).
- **InvalidKeyStoreType** — dispara ao ver `AndroidKeyStore`, que é a **prática correta** no
  Android; o spec JCA foi escrito para JSE (espera JKS/PKCS12). Aqui é majoritariamente
  **falso-positivo de contexto** (Tink, flutter_secure_storage, AndroidX Security usando o
  keystore de hardware corretamente).
- **InvalidSequenceOfMethodCalls** — o mais numeroso em bruto, com mensagem "unknown"
  frequente; sensível à modelagem do autômato do spec e propenso a ruído. Trate como
  **indicador de superfície**, não prova de bug.

Portanto, a afirmação segura é **"91% dos apps exercitam a API JCA de forma que o monitor
sinaliza, com uso de hash fraco disseminado"**, e **não** "91% dos apps são inseguros".

**Outras ameaças:**
- **Exploração não-exaustiva:** APE por 1 h, 1 repetição, sem static-guidance → cobertura de
  telas parcial; os 3 apps "zero" podem ter misuse não-alcançado. Números são **piso**, não teto.
- **App vs. lib:** não atribuímos a violação ao código do app vs. biblioteca; ambos executam no
  processo do app. A coluna `classe` na planilha permite essa análise a posteriori.
- **eSocial** (§7): recuperado (COMPLETED na 12ª tentativa); custou 11 retries do emulador.
- **Ofuscação:** parte das classes chamadoras está renomeada (`a.a.b`), o que limita a atribuição
  de origem mas **não** afeta a detecção (a classe JCA *callee* é de plataforma).

---

## 10. Artefatos gerados

Em `experimento-gov/results/consolidado_gov/`:

| Arquivo | Conteúdo |
|---|---|
| **`all_violations.csv`** | **Planilha detalhada — 424 violações distintas**: app, estado, spec, classe, método, local, tipo, mensagem, ocorrências |
| `all_violations_by_type.csv` | Ocorrências brutas por tipo de violação |
| `per_app.csv` | Agregado por app: `mop_unique`, `mop_total`, métodos executados, tipos |
| `summary.md` | Resumo em markdown (tabela por app) |

Dados brutos preservados: `experimento-gov/results/exp_NN/exp_NN/<apk>/*.logcat` e `*.trace`
(um por app). Memória de condução: `RV_ANDROID_DATASET_GOV/REGISTRO.md`.

---

## 11. Conclusão e próximos passos

O experimento **demonstra RV4Android end-to-end sobre um dataset real de apps gov.br**: dos 34
apps instrumentáveis, **33 executaram** com 0 VerifyError, e o monitor JCA capturou misuse em
runtime em **30 deles**, com **uso de hash fraco (SHA-1/MD5) disseminado** como achado central.
A pré-instrumentação dexlib2 + APE vanilla + specs JCA, sem análise estática, é um pipeline
**leve e reprodutível** para esse tipo de triagem.

**Próximos passos sugeridos:**
1. **Filtrar falsos-positivos de contexto** (`InvalidKeyStoreType` sobre `AndroidKeyStore`;
   `InvalidSequenceOfMethodCalls` "unknown") para um número de misuse **acionável**.
2. **Atribuição app-vs-lib** usando a coluna `classe` (separar Firebase/GMS/OkHttp do código do
   app) — mede o que é responsabilidade do desenvolvedor gov.br.
3. Opcional: **repetições e/ou tempo maior** para reduzir o piso de exploração dos apps "zero".

> **Nota de robustez:** o `EmulatorError` intermitente do eSocial (11 falhas antes de fechar)
> sugere revisitar a estabilidade do boot/restart de emulador do APE para apps pesados — o
> auto-resume horário mascarou o custo (12 h de wall-clock para 1 app), mas não é a solução ideal.
