# Investigação — Substituir o package_detector por uma ferramenta SOTA?

**Data**: 2026-06-17 · **Objetivo**: avaliar a viabilidade de **substituir completamente** o
`package_detector` (rv-android-core) por uma ferramenta estado-da-arte de detecção de bibliotecas
(LibScout/LibRadar/LibD/LibPecker/LibID/LIBLOOM). Inclui spike empírico real (LibScout buildado e
executado num APK nosso). Insumos: `docs/20260613_pesquisa_package_detection_sota.md` (SOTA),
auditoria `out/package_detector_audit/`.

## Veredito

**Substituição completa NÃO é viável.** Três bloqueios independentes, dois deles confirmados
empiricamente no spike. A razão de fundo é uma **incompatibilidade de categoria**: as ferramentas
SOTA detectam *bibliotecas* (um conjunto), enquanto o `package_detector` produz *o pacote do app*
(uma string). Nenhuma ferramenta emite um `code_package` — no máximo emitem o conjunto de libs, do
qual o app seria o complemento residual (e isso é exatamente a nossa Change B, não a ferramenta).

## 1. O contrato que um substituto precisa cumprir

`code_package` é consumido como **uma única string de prefixo** em três pontos (grep em `modules/`):

| Consumidor | Uso | Arquivo |
|---|---|---|
| GATOR (análise estática, Java) | `-clientParam codePackage=<pkg>` | `rv-static-analysis/config.py:397` |
| Parser de análise estática | filtro de classes/janelas por prefixo (INV-ANA-03) | `static_analysis_parser.py:356` |
| Instrumentação AJC | garante que o pointcut não casa o próprio pacote do app | `ajc_instrumentation.py:849` |
| `App.code_package` | propriedade lazy, in-process, via androguard | `domain/app.py:119-145` |

Implicações para um substituto:
- Tem de devolver **uma string** (o contrato — GATOR clientParam, prefixo do parser, AJC — está
  embutido). Mudar para partição classe-a-classe é uma re-arquitetura cross-module (inclui Java do GATOR).
- `App.code_package` é computado **in-process** a partir do APK androguard já carregado. Uma ferramenta
  SOTA é processo externo Java/Docker → injetaria dependência de subprocesso no módulo-base (hoje puro
  Python + androguard).

## 2. Spike empírico — LibScout (melhor candidato)

LibScout escolhido por ser o mais usável (Apache-2.0, 8.542 perfis prontos, JSON, documentado).

**Setup** (reproduzível em `out/sota_spike/`): clone + build com **JDK 8** (Gradle 4.9 não suporta
JDK 11+; temos 8 via sdkman), perfis `LibScout-Profiles` (402 libs / 8.542 versões), `android.jar`
do SDK, APK `de.readeckapp_900.apk` (um dos 4 mis-picks). Build OK (exit 0).

**Resultados** (`out/sota_spike/json_out/`):
- **Latência: 31 s de processamento/APK** (1 min 16 s wall com carga do android.jar). O nosso
  detector é instantâneo (microssegundos, in-process). Para 169 APKs ≈ 1,5–3,5 h; para 400 ≈ 3,5–8 h.
- **`appInfo.packagename` = `de.readeckapp`** — mas isto é só o **pacote do manifest**
  (`APK.get_package()`), exatamente o que o `code_package` existe para corrigir. LibScout **não**
  emite um pacote de código detectado.
- **Match obfuscation-resilient (perfil Merkle): só Facebook** (mapeou pacote ofuscado `E1` →
  `com.facebook.all` — prova que a abordagem resiste a ofuscação). **Não detectou `net.openid.appauth`**
  — o exato mis-pick que precisamos corrigir. Não está no catálogo.
- **Matches por nome de pacote** (`lib_packageOnlyMatches`, 40): OkHttp→okhttp3, androidx.* etc. — mas
  isto é matching por NOME (frágil, só funciona porque esses pacotes não foram ofuscados); é
  precisamente o que o nosso `FRAMEWORK_PREFIXES` já faz.

**Conclusão do spike**: rodar LibScout no readeckapp **não corrige** o mis-pick (appauth continua
invisível) e custa 31 s/APK.

## 3. Os três bloqueios

**B1 — Incompatibilidade de categoria (fundamental).** Ferramentas TPL emitem conjunto de libs, não
`code_package`. O único campo de "pacote" do LibScout é o do manifest. Para obter `code_package`
seria preciso lógica residual (app = pacote afim ao manifest que NÃO está no conjunto de libs) — que
é a nossa Change B (manifest-affinity), não a ferramenta. A ferramenta só pode ser **insumo**, nunca
substituta.

**B2 — Cobertura de catálogo (empírico).** 0/9 das libs merged que causam nossos mis-picks (AppAuth,
Tink, ZXing, Flutter, unifiedpush, mikepenz…) estão nos 8.542 perfis; só OkHttp. O catálogo está
congelado em 2019 e não cobre libs modernas de F-Droid. É o recall <50% da literatura, concretizado:
a detecção profile-based perde justamente os casos que temos.

**B3 — Custo de integração (empírico).** JAR Java buildado com JDK 8 (Gradle 4.9 trava em JDK ≥11) +
android.jar + 8.542 perfis, invocado como subprocesso a partir do `App.code_package` (hoje Python
puro). 31 s/APK → horas por experimento. Pesado e arquiteturalmente intrusivo no módulo-base.

## 4. As ferramentas de clustering mudam algo? (LibRadar/LibD/LIBLOOM)

Evitam **B2** (não usam catálogo — agrupam por estrutura/frequência, pegariam libs desconhecidas
como o plugin Flutter). MAS:
- **B1 permanece**: continuam emitindo conjunto de libs, não `code_package`.
- Manutenção/ambiente: **LibRadar** = Python 2.7 + Redis (morto, incompatível com 3.12/3.13);
  **LibD/LIBLOOM** = Java research-grade (JDK 8); **LibID** = precisa Gurobi (licença).
- Recall <50% (literatura) → complemento residual incompleto.

## 5. Opções de planejamento

- **Opção A — RECOMENDADA: manter o nosso detector; usar ferramenta SOTA só como oráculo offline.**
  Change B (manifest-affinity) corrige 4/5 mis-picks com lógica in-process barata. Uma ferramenta TPL
  (LibScout, alta precisão no que está no catálogo) entra **apenas na Change A (eval)** como
  anotador independente de cross-check — reduz a ameaça do anotador único. Custo controlado (offline,
  uma vez). É a única opção em que o custo/risco se paga.
- **Opção B — re-arquitetar o downstream para partição classe-a-classe app/lib** alimentada por um
  clustering TPL. É a abordagem "SOTA pura", mas: toca GATOR (Java, troca o `codePackage` por lista
  de classes), o parser e o AJC; limitada por recall <50%; multi-módulo e cara. Não é "substituir o
  detector" — é trocar todo o contrato de identificação de código-app. Fora de escopo agora.
- **Opção C — híbrido**: detector manifest-affinity como primário + sinal de clustering como
  desempate só nos casos `foreign_namespace`. Mais simples que B, mas ainda traz a dependência
  externa Java/Docker ao caminho quente. Considerar só se a Change B sozinha não bastar (medido pela
  Change A).

## 6. Impacto nas changes

- **Change A (gh67, eval)**: usar LibScout como **oráculo independente** nos 42 mismatches reforça a
  mitigação de anotador único. Caveat empírico a declarar: LibScout só cobre ~1 das nossas libs merged
  → corrobora os mis-picks de libs conhecidas (okhttp/facebook), os demais ficam com a evidência
  manual + nota de recall. Spike em `out/sota_spike/` já dá a baseline de viabilidade (31 s/APK).
- **Change B (detector)**: confirmada como manifest-affinity in-process — NÃO trocar por ferramenta
  externa. A investigação valida a decisão D1 (catálogo curado barato) sobre a alternativa "usar TPL
  tool".

## 7. Artefatos do spike

`out/sota_spike/` (gitignored): `LibScout/` (buildado), `LibScout-Profiles/` (8.542 perfis),
`json_out/de/readeckapp/...json` (saída). Reproduzir: build com `JAVA_HOME=~/.sdkman/candidates/java/8.0.482-tem`,
run `java -jar build/libs/LibScout.jar -o match -c config/LibScout.toml -p ../LibScout-Profiles/profiles -a $ANDROID_HOME/platforms/android-36/android.jar -j ../json_out <apk>` de dentro de `LibScout/`.
