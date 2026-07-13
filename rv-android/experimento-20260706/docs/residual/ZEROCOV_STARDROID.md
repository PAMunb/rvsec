# Coverage zero apesar de RVSEC-COV — `PackageFilter` engole o namespace do app

Data da análise: 2026-07-12 (consolidação offline pós-campanha). Complementa
`NOCOV_LOGCATS.md`: aquele documenta os logcats **sem** RVSEC-COV (app nunca lançou);
este documenta execuções que **lançaram** (têm RVSEC-COV) mas fecharam com coverage e MOP
zerados no `summary_regen.csv`.

## Descoberta

A consolidação produziu **334** linhas totalmente zero no `summary_regen.csv` (todos os 8
campos `cov_*`/`mop_*` = 0), não 235. A diferença — **99 linhas** — são execuções com
RVSEC-COV no logcat mas coverage-alvo = 0 e MOP = 0. A quebra:

| N | APK | Natureza |
|---:|---|---|
| 98 | `com.google.android.stardroid_1678.apk` | **Determinística** (defeito de instrumentação, todas as 11 tools) |
| 1 | `org.wikipedia_50595.apk` | Transitória (1 execução avulsa; as outras 98 do wikipedia têm dado) |

O stardroid tem 99 execuções (11 tools × 3 reps × 3 timeouts) e **todas** fecham em zero:
98 por este defeito + 1 transitória de infra (qtesting, já contabilizada nas 235 de
`NOCOV_LOGCATS.md`). Ou seja, o stardroid contribui **zero coverage útil em 100% das
execuções**.

## Causa-raiz (fechada com evidência)

O detector e o denominador estão **corretos** — o defeito está no *weave* de coverage:

1. **Detector elege o pacote certo.** `PackageDetector.detect_package` sobre o APK original
   retorna `code_package = com.google.android.stardroid` de forma **determinística** em
   todos os `PYTHONHASHSEED` testados (0, 1, 7, 42, 99, 1234); `method=no_app_components`,
   `confidence=low`. Não é o bug de não-determinismo do detector.
2. **Denominador SA correto.** O `.apk.json` da análise estática traz `reachability` com
   **705 classes, todas `com.google.android.stardroid.*`** (SplashScreenActivity, dialog
   fragments, `MainApplication_HiltComponents$*` etc.). `package = com.google.android.stardroid`,
   `complete = true`. Não há colapso de reachability (≠ dos 6 casos de
   `validate-package-detector`).
3. **O weaver de coverage exclui o namespace do app.** O `PackageFilter` do
   `rvsec-instrumentation-dexlib2/coverage-weaver` é uma lista de **exclusão** (não de
   inclusão por `code_package`); `CoverageWeaver` pula toda classe cujo descritor casa
   `PackageFilter.isExcluded(...)`. Entre os prefixos excluídos:

   ```java
   // PackageFilter.java  (EXCLUDED_PREFIXES)
   "Landroid/", "Landroidx/", "Lkotlin/", ... , "Lcom/google/", ...
   ```

   O prefixo `Lcom/google/` existe para pular bibliotecas Google (Guava, Play Services,
   Material). Mas o **Sky Map é um app do próprio Google**, pacote `com.google.android.stardroid`
   → descritor `Lcom/google/android/stardroid/...` → **`startsWith("Lcom/google/")` = true**
   → **todas as classes do app são excluídas do weave.** Só as `dagger.hilt.*` / `dagger.internal.*`
   (descritor `Ldagger/...`, não excluído) foram tecidas — por isso o logcat cru mostra
   **apenas** eventos RVSEC-COV de infraestrutura DI (`dagger.hilt.android.internal.managers.*`),
   **zero** `com.google.android.stardroid.*`, sem crash/ANR.
4. **O filtro de análise (correto) zera o resto.** No reparse, o parser de coverage mantém
   só eventos sob `code_package` (`com.google.android.stardroid`) e descarta os `dagger.*`
   — comportamento correto. Como o app não emitiu nenhum evento próprio, o coverage
   consolidado fica em 0 (o `coverage_regen.csv` não tem **nenhuma** linha do stardroid).

**Verificação:** varredura dos 219 `.apk.json` — **exatamente 1** tem `package` sob um
prefixo excluído pelo `PackageFilter` (`com.google.android.stardroid`, casa `com.google.`).
Os demais 218 têm namespace próprio fora das exclusões, logo não são afetados.

## Relação com `validate-package-detector` (irmão, porém distinto)

A change `rvsec-dataset/openspec/changes/validate-package-detector` trata da **eleição do
detector** e do **denominador SA** (o `code_package` que vira denominador; eleição errada
colapsa reachability — casos `spencerpages`, `etar`, `catima`, `aard2`, `ringdroid`,
`govroam`). **O stardroid NÃO é um desses casos:** o detector acerta e o denominador está
íntegro. Aqui o defeito é do **lado do numerador**, numa lista de exclusão *hardcoded* do
weaver Java (`Lcom/google/`), independente do detector Python.

O tema é o mesmo — *um app cujo namespace próprio colide com uma suposição de "namespace de
biblioteca" faz o coverage colapsar* — mas o ponto de falha e a correção são outros. Vale
cross-referenciar como threat-to-validity irmão; a correção (se desejada) é no
`PackageFilter` do coverage-weaver, não no detector.

## Correção potencial (NÃO aplicada)

O `PackageFilter` precisaria não excluir uma classe cujo prefixo casa `code_package` do app
(ex.: passar o `code_package` ao weaver e dar-lhe precedência sobre a lista de exclusão),
ou refinar `Lcom/google/` para os subpacotes de biblioteca conhecidos
(`Lcom/google/android/gms/`, `Lcom/google/android/material/`, `Lcom/google/common/` …) em
vez do guarda-chuva `Lcom/google/`. É mudança de código no lado Java (`rvsec`) + re-weave do
stardroid — **fora do escopo desta campanha**; aqui apenas registrado como defeito e threat
to validity (1/219 APKs com coverage subnotificado a zero).

## Efeito na campanha

- Perda de **coverage** por este defeito: 1 APK (98 execuções determinísticas). MOP é
  medido por caminho separado; o 0 MOP do stardroid é consistente com o app não exercitar
  JCA nos fluxos alcançados (não é causado pelo `PackageFilter`).
- No `summary_regen.csv` essas 99 linhas aparecem como zero legítimo. Somadas às 235 de
  `NOCOV_LOGCATS.md`, fecham as **334** linhas totalmente-zero do consolidado.

## Reprodução

```bash
# 1. Detector elege o pacote correto (determinístico):
uv run python - <<'PY'
from rv_android_core.util.android.package_detector import PackageDetector
from androguard.core.bytecodes.apk import APK
r=PackageDetector().detect_package(APK("<APKS>/com.google.android.stardroid_1678.apk"))
print(r.manifest_package, r.code_package)   # com.google.android.stardroid  com.google.android.stardroid
PY

# 2. RVSEC-COV do logcat: só dagger.*, zero stardroid:
grep RVSEC-COV <logcat> | grep -c com.google.android.stardroid   # 0
grep RVSEC-COV <logcat> | grep -c dagger                         # >0

# 3. Exclusão no weaver:
grep -n 'Lcom/google/' rvsec/rvsec-android/rvsec-instrumentation-dexlib2/coverage-weaver/\
src/main/java/br/unb/cic/rv/coverage/PackageFilter.java
```
