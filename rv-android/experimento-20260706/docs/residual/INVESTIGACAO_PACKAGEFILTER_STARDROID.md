# Investigação profunda — coverage zero por exclusão de namespace no `PackageFilter` (stardroid)

> **Natureza deste documento.** Isto **não** é um laudo fechado — é a **porta de entrada
> para uma investigação rigorosa** e serve como **prompt de análise**. Ele consolida o que
> já foi verificado (com evidência e âncoras `arquivo:linha`), delimita o que **ainda não**
> foi provado, e lista as hipóteses e experimentos que uma análise profunda deve executar
> **antes** de qualquer correção de código, re-weave ou decisão de escopo do dataset. Quem
> retomar isto deve tratar cada "Fato estabelecido" como reproduzível pelos comandos da
> §8, e cada "Questão aberta" (§3) como tarefa a fechar com evidência, não com suposição.
>
> **Princípio de rigor:** nenhuma afirmação de causa entra nas conclusões sem (a) comando
> reproduzível, (b) âncora `arquivo:linha` ou artefato, e (c) contraprova considerada.
> Onde a evidência é indireta, está marcado como **inferência** — a investigação deve
> convertê-la em evidência direta (ex.: desmontar o dex instrumentado).

---

## 0. TL;DR

Na consolidação offline do experimento-20260706 (dataset novo, 219 APKs, variante
`dexlib2`), o `summary_regen.csv` tem **334** linhas totalmente zero, não 235. As **99**
adicionais **lançaram** o app (têm `RVSEC-COV` no logcat) mas fecharam com coverage-alvo e
MOP zero. Delas, **98 são do `com.google.android.stardroid_1678.apk`** (Sky Map, app do
**próprio Google**) e **1 é uma execução avulsa transitória do `org.wikipedia_50595`**.

Causa-raiz **do stardroid** (verificada, ver §2): o `PackageFilter` do
`rvsec-instrumentation-dexlib2/coverage-weaver` é uma lista de **exclusão** que contém o
prefixo `"Lcom/google/"`; o pacote do app casa esse prefixo, então **todas as classes do
app são puladas no weave de coverage**. Só as classes `dagger.hilt.*` (não excluídas) foram
tecidas → o logcat cru só tem eventos `RVSEC-COV` de infraestrutura DI → coverage do app =
**0**, determinístico nas 11 tools. **Raio: exatamente 1/219 APKs.**

Este defeito é **distinto** da mudança `rvsec-dataset/openspec/changes/validate-package-detector`
(§6): lá o problema é a **eleição do detector / colapso do denominador**; aqui o detector
**acerta** e o denominador está **íntegro** — o defeito é no **numerador**, numa exclusão
*hardcoded* do weaver Java.

---

## 1. Como o problema apareceu

1. Consolidação offline reparsa todos os 21.681 logcats → `summary_regen.csv` (1 linha por
   identidade `apk,rep,timeout,tool`). Auditoria `verify.py --full`: **PASS (C1–C4)**.
2. Validação das linhas zero: esperava-se **235** (as sem `RVSEC-COV`, documentadas em
   `NOCOV_LOGCATS.md`). O consolidado tem **334**.
3. As 99 extras têm `RVSEC-COV` no logcat (app lançou) mas coverage/MOP zero. Distribuição
   por tool **plana** (~9 por tool) → assinatura de problema **por-APK**, não por-tool.
4. Concentração: **98 = stardroid**, **1 = wikipedia**.

---

## 2. Fatos estabelecidos (com evidência)

### 2.1 O detector elege o pacote CORRETO — determinístico
`PackageDetector.detect_package` sobre o APK **original** retorna
`code_package = com.google.android.stardroid` para `PYTHONHASHSEED` ∈ {0,1,7,42,99,1234}
(`method=no_app_components`, `confidence=low`). **Não** é o não-determinismo do detector.
- Código: `modules/rv-android-core/src/rv_android_core/util/android/package_detector.py:514`
  (`detect_package`), tie-break `similarity_match` em `:666`.
- Comando: §8.1.

### 2.2 O denominador da análise estática está ÍNTEGRO
`APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/com.google.android.stardroid_1678.apk.json`:
`package = com.google.android.stardroid`, `complete = true`, `reachability` com **705
classes, todas `com.google.android.stardroid.*`** (SplashScreenActivity, dialog fragments,
`MainApplication_HiltComponents$*`, …). **Não** há colapso de reachability.
- Comando: §8.2.

### 2.3 O weaver de coverage EXCLUI o namespace próprio do app
O `PackageFilter` é lista de **exclusão** (não inclusão por `code_package`); `CoverageWeaver`
pula toda classe cujo descritor casa `isExcluded(...)`.
- `…/coverage-weaver/src/main/java/br/unb/cic/rv/coverage/PackageFilter.java:22`
  (`EXCLUDED_PREFIXES`), **`:34` `"Lcom/google/"`**, `:51` `isExcluded`.
- `…/coverage-weaver/src/main/java/br/unb/cic/rv/coverage/CoverageWeaver.java:104`
  (loop `for (ClassDef …)`), **`:106` `if (PackageFilter.isExcluded(classDef.getType())) continue`**,
  `:72` `coverageMethod = Lmop/Coverage;.log(String)V`, `:159` `catch (RuntimeException …)`.
- Consequência: `Lcom/google/android/stardroid/…`.startsWith(`"Lcom/google/"`) = **true** →
  classes do app **não** recebem o `invoke-static Lmop/Coverage;.log`. As `Ldagger/hilt/…`
  (não excluídas) recebem.
- Evidência de runtime: o logcat cru tem **0** `RVSEC-COV` com `com.google.android.stardroid`
  e **>0** com `dagger` (só infra DI), **sem** crash/ANR. Comando: §8.3.

### 2.4 O filtro de análise (correto) zera o resto
No reparse, o coverage é atribuído ao `code_package`; eventos `dagger.*` (fora do
`code_package`) são corretamente descartados. Como o app não emitiu evento próprio, o
`coverage_regen.csv` **não tem nenhuma linha do stardroid** e o `summary` fica em 0.
- `scripts/regenerate_results/regenerate_container.py:17` (comentário: coverage atribuída
  pelo `code_package` real via `PackageDetector`).
- **Inferência a confirmar** na investigação: a cadeia GATOR/parser que aplica o
  `startsWith(code_package)` (a change `validate-package-detector` cita
  `RvsecAnalysisClient.java:277-286` e `static_analysis_parser.py:356-361` no lado SA;
  o drop de eventos runtime fora do `code_package` é citado como `coverage.py:546-548`).
  Verificar os âncoras exatos no estado atual da árvore.

### 2.5 Raio de impacto: exatamente 1/219
Varredura dos 219 `.apk.json` por `package` sob **qualquer** prefixo excluído pelo
`PackageFilter` (`com.google.`, `com.android.`, `org.apache.commons.`, `org.apache.geronimo.`,
`net.sf.cglib.`, `org.aspectj.`): **1 hit** — `com.google.android.stardroid`. Comando: §8.4.

### 2.6 stardroid = 99 execuções, 100% zero
99 execuções (11 tools × 3 reps × 3 timeouts). **98** zero por este defeito + **1**
transitória de infra (qtesting, já nas 235 de `NOCOV_LOGCATS.md`).

### 2.7 O caso wikipedia é SEPARADO
`org.wikipedia_50595`: 1/99 execuções zero (as outras 98 têm dado). Pacote `org.wikipedia`
**não** é excluído. Se fosse defeito de weave ou não-determinismo de detector, seria
**all-or-nothing** nas 99 — logo é **transitória de runtime**, não relacionada ao stardroid.

---

## 3. Questões abertas (fechar com evidência antes de concluir)

1. **Weave direto:** desmontar o `classes.dex` **instrumentado** do stardroid e confirmar,
   por inspeção de bytecode, que **nenhuma** classe `com.google.android.stardroid.*` contém
   `invoke-static Lmop/Coverage;.log` e que classes `dagger.*` **contêm**. (Hoje a prova é
   indireta, via logcat.) Ferramenta: `baksmali`/`apktool`.
2. **`no_app_components` / `confidence=low`:** por que o detector classifica assim mesmo com
   705 classes reachable? Há interação entre esse método de detecção e o filtro do weaver?
   (São subsistemas diferentes — confirmar que não há acoplamento oculto.)
3. **Outros prefixos de exclusão como risco latente:** `com.android.`, `org.apache.commons.`,
   `net.sf.cglib.`, `org.aspectj.` também engoliriam apps reais cujo código próprio vive
   nesses namespaces (ex.: forks AOSP sob `com.android.*` — a própria change cita
   `ws.xsoh.etar` como fork de Calendar `com.android.calendar.*`). Cruzar a lista de
   exclusão do weaver com os `G_final` reais do `validate-package-detector`: **quantos
   APKs, em qualquer dataset, têm código próprio sob um prefixo excluído pelo weaver?**
4. **Simetria ajc × dexlib2:** o `PackageFilter` diz replicar o filtro do legado
   `Coverage.aj` (INV-INS-53 / Layer-5). O **ajc** sofre o mesmo engolimento de
   `com.google.*`? Se sim, o defeito é do **contrato de exclusão**, não só do dexlib2.
5. **MOP:** o 0 MOP do stardroid é atribuído a "app não exercita JCA nos fluxos alcançados".
   Confirmar que o weave de MOP (aspecto JCA) **não** compartilha o `PackageFilter` de
   coverage — senão o MOP também estaria sendo suprimido por exclusão, não por ausência.
6. **Denominador vs numerador:** o `code_package` usado pela **instrumentação** é o mesmo
   objeto que o usado pela **SA**? Mapear o fluxo do `code_package` do detector até o
   parâmetro do weaver (se é que o weaver recebe `code_package` — pela §2.3 ele **não** usa
   `code_package`, só a exclusão; confirmar que não há um segundo filtro por inclusão).

---

## 4. Hipóteses e método

| # | Hipótese | Como testar | Predição se verdadeira |
|---|---|---|---|
| H1 | Exclusão `Lcom/google/` é a causa única | baksmali do dex instrumentado (§3.1) | 0 `Coverage.log` em classes do app; presente em `dagger.*` |
| H2 | Defeito é do contrato de exclusão (ajc também) | re-weave ajc do stardroid + rodar 1 execução | ajc também zera coverage do stardroid |
| H3 | Risco latente afeta >1 APK em outros datasets | cruzar EXCLUDED_PREFIXES × `G_final` (validate-package-detector) | lista de APKs sob `com.android.*` etc. com código próprio |
| H4 | MOP não é afetado (filtro independente) | inspecionar o weave de MOP (aspecto JCA) | MOP usa outro filtro; 0 MOP do stardroid é real |

---

## 5. Decisão sobre o stardroid — **está tudo zero, sim**

Confirmado: **as 99 execuções do stardroid são zero coverage útil** (98 pelo defeito + 1
transitória). Três caminhos, **decisão do usuário** (não altero escopo do dataset sem
autorização):

- **(A) Deixar como está** — 99 linhas como zero legítimo no `summary_regen.csv`.
  *Custo:* 1 APK contribui 0 coverage por um **defeito de instrumentação**, não por ausência
  real de cobertura. Isso **subestima a magnitude absoluta** da coverage média (todas as 11
  tools "comem" um 0 do stardroid). **Não** enviesa a **comparação entre tools** (o zero é
  simétrico entre elas). MOP não é afetado.
- **(B) Excluir o stardroid** (219 → 218 APKs) — remove o viés de magnitude; registrar como
  **threat to validity** ("1 APK excluído por defeito conhecido do `PackageFilter`,
  `com.google.*` colide com namespace do app"). Simétrico entre tools → **não** muda a
  comparação relativa. É o caminho **cientificamente mais limpo** para números **absolutos**
  de coverage, e barato (filtro na análise, sem re-rodar nada).
- **(C) Corrigir + re-weave + re-rodar** o stardroid — recupera o dado **real**. Mais caro
  (mudança no `PackageFilter` no lado Java `rvsec`, re-instrumentar, re-rodar 99 execuções).
  Fora do escopo desta campanha; vira issue/change própria.

**Recomendação (a decidir por você):** para o artigo, **(B)** como default (exclusão
documentada, barata, não altera a comparação) **e** abrir **(C)** como issue separada para
o `PackageFilter` (o defeito é real e latente para futuros datasets — ver §3.3). **(A)** só
se quiser preservar "dataset = 219" a todo custo, assumindo o viés de magnitude na redação.
Qualquer que seja, **é decisão sua** — não removo APK do experimento nem toco no
`PackageFilter` sem seu aval.

---

## 6. Relação com `validate-package-detector` (irmão, distinto)

Change: `rvsec-dataset/openspec/changes/validate-package-detector` (proposal + tasks, light
track). Ela mede **acurácia do detector** e o impacto da **eleição `code_package`** no
**denominador** SA (casos de colapso: `spencerpages`, `etar`, `catima`, `aard2`,
`ringdroid`, `govroam`; cita `org.wikipedia_50595` como **detector não-determinístico**).

Diferença essencial: **no stardroid o detector acerta e o denominador está íntegro** — o
colapso é do **numerador**, por exclusão *hardcoded* no weaver Java, independente do detector
Python. **Tema irmão** (namespace próprio do app colide com suposição de "namespace de
biblioteca"), **ponto de falha e correção diferentes**. Sugestão: registrar como
threat-to-validity irmão na change (via skill OpenSpec, se for editar a change), sem fundir
os dois problemas.

---

## 7. Correção potencial (NÃO aplicada)

No `PackageFilter`/`CoverageWeaver`: dar **precedência ao `code_package` do app** sobre a
lista de exclusão (não excluir classe cujo prefixo casa o `code_package`), **ou** refinar
`"Lcom/google/"` para os subpacotes de **biblioteca** conhecidos
(`Lcom/google/android/gms/`, `Lcom/google/android/material/`, `Lcom/google/common/`,
`Lcom/google/gson/`, …) em vez do guarda-chuva. Requer mudança no lado Java (`rvsec`) +
re-weave do(s) APK(s) afetado(s) + re-execução. **Fora do escopo da campanha.**

---

## 8. Reprodução

```bash
# 8.1 Detector elege o pacote correto (determinístico em vários seeds):
cd <rv-android>
for s in 0 1 42 1234; do PYTHONHASHSEED=$s uv run python - <<'PY'
from rv_android_core.util.android.package_detector import PackageDetector
from androguard.core.bytecodes.apk import APK
r=PackageDetector().detect_package(APK("<APKS>/com.google.android.stardroid_1678.apk"))
print(r.manifest_package, r.code_package, getattr(r,'detection_method',None))
PY
done

# 8.2 Denominador SA íntegro (705 classes, todas do app):
python3 - <<'PY'
import json
d=json.load(open("<STATIC>/com.google.android.stardroid_1678.apk.json"))
print(d["package"], len(d["reachability"]))
print({s[:26] for s in (x["className"] for x in d["reachability"])})  # -> só com.google.android.stardroid.*
PY

# 8.3 RVSEC-COV do logcat: só dagger, zero stardroid, sem crash:
f=<RESULTS>/m1/results/exp_03/exp_03/com.google.android.stardroid_1678.apk/*__1__300__ares.logcat
grep RVSEC-COV $f | grep -c com.google.android.stardroid   # 0
grep RVSEC-COV $f | grep -c dagger                         # >0
grep -E 'FATAL|ANR|E AndroidRuntime|VerifyError' $f        # (vazio)

# 8.4 Raio 1/219 (pacote sob prefixo excluído):
python3 - <<'PY'
import json,glob,os
EXC=["com.google.","com.android.","org.apache.commons.","org.apache.geronimo.","net.sf.cglib.","org.aspectj."]
for j in glob.glob("<STATIC>/*.apk.json"):
    p=json.load(open(j))["package"]
    if any(p.startswith(e) for e in EXC): print(p, os.path.basename(j))
PY

# 8.5 Exclusão no weaver:
grep -n 'Lcom/google/' <rvsec>/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/\
coverage-weaver/src/main/java/br/unb/cic/rv/coverage/PackageFilter.java
```

Placeholders: `<rv-android>` = este repo; `<rvsec>` = raiz do reator Java;
`<APKS>` = `RV_ANDROID_NOVO_DATASET/APKS`;
`<STATIC>` = `RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706`;
`<RESULTS>` = `RV_ANDROID_NOVO_DATASET/RESULTS`.

## 9. Referências

- Achado resumido: `ZEROCOV_STARDROID.md` (mesmo diretório).
- Balanço das 235 sem-COV: `NOCOV_LOGCATS.md` + `nocov_235.csv`.
- Consolidação: `experimento-20260706/scripts/consolidate_offline.sh`,
  `scripts/regenerate_results/{regenerate_container,concat_vm,concat_all,verify}.py`.
- Change irmã: `rvsec-dataset/openspec/changes/validate-package-detector/{proposal,tasks}.md`.
- Weaver: `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/coverage-weaver/…/{PackageFilter,CoverageWeaver}.java`.
- Detector: `modules/rv-android-core/src/rv_android_core/util/android/package_detector.py`.
- Bug irmão de instrumentação dexlib2: memória `dexlib2 65536 method-ceiling`.
