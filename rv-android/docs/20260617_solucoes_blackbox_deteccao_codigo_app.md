# Soluções black-box para detecção de código-app (eliminar libs/sistema → resíduo = app) — análise de LibHunter e veredito ranqueado

**Data:** 2026-06-17
**Status:** ANÁLISE + soluções ranqueadas — **nada implementado**
**Restrição dura (do usuário):** o detector é **black-box — recebe um APK e testa**. Sem fonte, sem Gradle, sem metadata F-Droid em runtime. Ofuscação (R8 em ~41%) está em escopo.
**Método:** 5 subagentes paralelos com verificação em **fonte primária** (PDFs, repos, APIs) + 1 deep-dive dedicado ao LibHunter (leu o PDF + `analyzer.py`) + sequential-thinking + skill `scientific-critical-thinking`. UNVERIFIED marcado onde a fonte não confirmou.
**Estende:** `docs/20260617_veredito_abordagem_residual_deteccao_pacote.md` (que refutou a inversa via fingerprint clássico). **Este doc mostra a inversa que FUNCIONA** e responde diretamente à pergunta sobre LibHunter.
**Calibrado por:** rejeição ICST 2026 #65 (#65A#1 recall/accuracy/denominador; #65A#4 escopo app-vs-lib na comparação CogniCrypt).

---

## 0. TL;DR

**LibHunter (ASE 2024) NÃO resolve a proposta inversa** — por dois bloqueios independentes confirmados no PDF e no código: (1) ele **não localiza** a lib no APK (emite só `lib:nome_versão`; a correspondência de classes é computada e **descartada** em `analyzer.py`) → não há o que subtrair; (2) é **mundo-fechado** — um matcher 1:1 contra um banco que **você fornece** (o benchmark dele são **31 libs *vulneráveis***), incapaz de descobrir lib fora do banco → o seu 71,4% F1 é recall sobre libs *conhecidas* sob ofuscação, **não** sobre o conjunto de mundo-aberto de deps de um app F-Droid arbitrário. Ele ataca o eixo **ofuscação**, não o eixo **cobertura** — e é cobertura que quebra a inversa nos nossos casos (AppAuth/Flutter/TFLite).

**A inversa por *lista de prefixos* (AndroLibZoo+Exodus+top-up via AndroSpecter/Soot) é válida — MAS só no subconjunto NÃO-ofuscado.** Subtração por uma **lista curada e abrangente de prefixos de pacote de lib** — **AndroLibZoo** (MSR 2024, **34.813 prefixos**, MIT) + **Exodus** (432 trackers, API pública) + **top-up curado de ~20–50 prefixos modernos** — emite a fronteira a nível de **pacote/classe** (o que LibHunter não faz), roda black-box, e o `recall<50%` (artefato de *fingerprint binário*) **não se aplica** a uma lista curada.

**⚠️ Objeção decisiva (do usuário): boa parte dos APKs está ofuscada → AndroLibZoo NÃO funciona neles.** Prefixo-matching depende de nomes; o **R8-renaming** transforma `net.openid.appauth.X` em `a.b.c` → **nenhum** prefixo da lista casa → no subconjunto renomeado a subtração por lista **morre** (e degrada para o detector-manifest atual). Isso reabre o problema: **sob ofuscação, nenhuma solução black-box pronta resolve a inversa open-world.** As únicas que sobrevivem ao renaming são (a) **fingerprint mundo-fechado** (LibHunter, só libs conhecidas — não open-world) e (b) **decoupling estrutural** (A3Ident-style: topologia do grafo call/inheritance/ICC + âncora MainActivity, ~80% em apps ofuscados — open-world, mas **sem artefato**, exige ICC + reimplementação). Ver §3-bis. **Conclusão honesta:** o problema **se parte por status de ofuscação**; prefixo serve só o ~não-renomeado, e o renomeado exige decoupling estrutural (construir) ou se aceita o detector-manifest atual como "inerte sob ofuscação" + ameaça medida. Limitação adicional (vale em qualquer caso): **código vendored** não tem coordenada/prefixo → vaza (ameaça inerente).

**Enquadramento decisivo para o paper (agente de escopo cripto):** o método canônico do campo (CryptoGuard CCS'19 §6.2) é **exatamente o nosso** — partição por pacote do manifest — e **não reporta acurácia nenhuma** dela; o Soot, num APK, marca **tudo como application class** por padrão (a fronteira é imposta pelo analista). Logo **medir P/R da nossa fronteira está ACIMA da barra do campo, não abaixo** — é mais perto de contribuição do que de "baseline faltando".

---

## 1. LibHunter (ASE 2024) não resolve a inversa — definitivo

Paper: Xie, Wen, Li, Zhu, Hou, Jin, *"How Does Code Optimization Impact Third-party Library Detection for Android Applications?"*, ASE 2024. Repo: `github.com/CGCL-codes/LibHunter` (branch `new_master`, Python, **sem licença**, hist. resetado, último commit 2025-06-28).

### 1.1 Bloqueio mecânico — não emite localização

LibHunter computa a correspondência de classes `CM(app,tpl)` **durante** o matching, mas **não a persiste**. Em `module/analyzer.py` a saída gravada é só:
```python
result.write("lib: " + lib + "\n")              # ex.: com.squareup.okhttp3.okhttp_3.12.0
result.write("similarity: " + str(...[2]) + "\n\n")
```
O `lib_class_match_result` (classes do app que casam com a lib) **nunca vai a disco**. A subtração residual precisa saber *quais pacotes (renomeados) do dex* são a lib — LibHunter não diz. Recuperável só **modificando a ferramenta** (serializar `CM(app,tpl)`), sobre um protótipo sem licença e de proveniência fina. *(UNVERIFIED: se os identificadores de classe do app sobrevivem ao renaming do R8 de forma útil — sob Package-Flatten/Identifier-Renaming a noção de "prefixo" se dissolve.)*

### 1.2 Bloqueio fatal — mundo-fechado, banco minúsculo

- "takes an app and a TPL as input and outputs a verdict on the TPL's presence" (§4). Itera **TPLs candidatas que você fornece** (`tpls_jar/`) — uma lib sem entrada é **estruturalmente invisível**.
- Banco do benchmark = **31 TPLs *vulneráveis* / 3.447 versões** (§3.1), selecionadas por estarem em ≥1 CVE. O repo só traz **OkHttp**; o resto está no figshare. **Não é um inventário de libs; é um verificador de versão-vulnerável.**
- Sem evidência de AppAuth/Flutter/TFLite/Tink/UnifiedPush/mikepenz. RQ6 só cita OkHttp e Retrofit no mundo real.

### 1.3 Números — F1 só, eval único

- Sob **Opt+Obf+Srk** (R8 pleno), **library-F1 71,4% / version-F1 51,1%** (Tabela 3) — **só F1**; **precisão e recall separados de LibHunter NÃO são reportados** (as P/R separadas da Tabela 2 são dos *baselines*: LibScan 42,1%, LibScout 1,4%, LibPecker 4,0%, LibID 0,8% library-F1). **UNVERIFIED** o split P/R do próprio LibHunter — gap real para raciocínio residual (recall<1 → inflação; precisão<1 → deflação).
- Tudo é **auto-reporte único**: ofuscação R8 gerada pelo próprio script deles, limiares T₁=0,75/T₂=0,2 *grid-searched* em 20% dos mesmos dados.

### 1.4 Veredito

**LibHunter ataca o eixo ofuscação (casar lib conhecida renomeada), não o eixo cobertura (saber que a lib existe).** Completude residual exige remover **todas** as libs presentes; um matcher por referência só remove as do banco. `resíduo = tudo − (libs ∩ Banco) − sistema = app ∪ (libs − Banco)`, e `(libs − Banco)` infla o app silenciosa e ilimitadamente. **Serve, no máximo, como checagem secundária de *versão vulnerável específica*** (com banco fornecido + patch de localização) — **não** como o subtrator da inversa. Nem o paper nem o repo mencionam código-app/residual.

---

## 2. A inversa VÁLIDA: subtração por lista curada de prefixos

O erro era o instrumento. Trocar *fingerprint binário* (recall<50%, mundo-fechado) por uma **lista curada e abrangente de prefixos de pacote**, derivada de análise de dependências:

### 2.1 AndroLibZoo + AndroSpecter (MSR 2024) — o subtrator primário

- **AndroLibZoo** (Samhi/Bissyandé/Klein, **MSR 2024**, MIT, Zenodo 10.5281/zenodo.10072709): **34.813 prefixos** de pacote de lib (`AndroLibZoo.lst`), construídos por *dependency analysis* de `build.gradle` de F-Droid + coordenadas Maven Central. **Não é fingerprint** — é "case o pacote da classe contra o conjunto; casou → é lib".
- **AndroSpecter** (mesmo autor, **Java/Soot, LGPL**, atualizado 2025-07): `LibrariesManager.v().isLibrary(SootClass)`. **Encaixa direto no nosso pipeline GATOR/Soot.** Emite a fronteira a nível de **pacote/classe** — exatamente o que falta no LibHunter.
- Black-box (opera sobre os nomes do dex), runnable hoje, custo de integração **baixo**.

### 2.2 Exodus Privacy — complemento para SDKs Google/ad

- `GET https://reports.exodus-privacy.eu.org/api/trackers` (público, sem auth; respeitar 3 req/IP/min). **432 trackers, 428 com `code_signature`** = prefixos de pacote (ex.: `com.ad4screen.sdk`).
- **Complementaridade-chave (testada):** cobre o que AndroLibZoo perde — Firebase, Crashlytics, AdMob, Facebook, Adjust, AppsFlyer, Unity Ads. Licença ODbL (atribuição+share-alike; ok p/ uso interno).

### 2.3 Top-up curado (~20–50 prefixos) — fecha o long-tail

Empiricamente, AndroLibZoo (derivado de F-Droid open-source) **ainda perde**: `io.flutter`, `net.openid.appauth`, `com.google.crypto.tink`, `org.tensorflow.lite`, `okhttp3`, `com.bumptech.glide`, `com.google.android.gms`, `com.google.firebase`. **Inclui exatamente nossos 3 mis-picks.** Anexar à mão (custo trivial; AndroLibZoo aceita PRs). Resultado = subtrator de cobertura production-grade para F-Droid moderno.

**Stack final:** `app_packages = todos_os_pacotes_dex − (AndroLibZoo ∪ Exodus ∪ top-up) − (android/java framework)`, via AndroSpecter no Soot.

---

## 3. Limitações honestas + por que o híbrido (não residual puro)

| Limitação | Impacto | Mitigação |
|---|---|---|
| **R8-renaming (~41%)** derrota prefixo-matching (`a.b.c`) | nesses APKs a lista não casa nada → resíduo = tudo | **Âncora do manifest** (nomes de componente preservados sob R8) identifica o app **positivamente** → híbrido. Onde os nomes sobrevivem, a lista subtrai; onde não, o manifest ancora. |
| **Código vendored/copiado** (sem coordenada → sem prefixo) | vaza para o resíduo → **inflação** | Inerente e não-corrigível. **Declarar como ameaça de validade** (mesma que Gu/Lu 2025 reconhece). |
| **Long-tail de cobertura** | libs novas/nicho fora da lista vazam | top-up curado (§2.3); a lista é atualizável (vs catálogo fingerprint congelado) |
| **`com.google` quase ausente em AndroLibZoo** (derivado de F-Droid) | SDKs Google vazam | Exodus cobre a maioria; top-up cobre gms/firebase |

→ **Residual PURO continua descartado** (veredito anterior §1: vaza, viés p/ cima, catastrófico sob R8). O que vira viável é o **HÍBRIDO: âncora manifest (app+) + subtração por lista curada (lib−)** — que é o construto do A3Ident, agora **construível** com peças runnable.

---

## 3-bis. A objeção da ofuscação reabre o problema (boa parte do corpus está ofuscada)

Prefixo-matching (AndroLibZoo, Exodus, e o próprio detector-manifest no que toca à *cobertura* do app) opera sobre **nomes de pacote**. O **R8 com `minifyEnabled` + obfuscation** renomeia classes/pacotes para `a.b.c`. Efeito por método, sob renaming:

| Sinal | Sobrevive ao R8-renaming? | Por quê |
|---|---|---|
| **Lista de prefixos** (AndroLibZoo/Exodus/top-up) | ❌ **Não** | os nomes que a lista conhece não existem mais no dex → 0 matches |
| **Fingerprint mundo-fechado** (LibHunter) | ✅ p/ libs **conhecidas** | opcode/CFG/cross-inlining resistem ao renaming — mas só p/ libs no banco (não open-world) |
| **Decoupling estrutural** (A3Ident) | ⚠️ **parcial (~80%)** | a **topologia** do grafo (call/inheritance/ICC) e a âncora **MainActivity** (preservada no manifest) não dependem de nomes |
| **Âncora do manifest** (entry-point) | ✅ | componentes declarados são mantidos pelo R8 (referenciados por string) — mas dá só o ponto de entrada, não a fronteira completa |

**Distinção que precisa ser medida (M6), não assumida:** "ofuscado" ≠ "renomeado". R8 faz *shrinking* (remove código), *optimization* e *obfuscation/renaming* — e só o **renaming** mata o prefixo. Muitos apps F-Droid habilitam `minifyEnabled` mas a fração que de fato **renomeia pacotes** tem de ser contada no corpus (segmentos de 1–2 letras). A viabilidade da lista de prefixos é **exatamente o complemento da fração renomeada**.

**Implicações para a recomendação (honestas):**
1. **AndroLibZoo+Exodus+top-up** rebaixa de "recomendada" para **"válida só no subconjunto não-renomeado"**. Não é a solução geral.
2. **No subconjunto renomeado, não há ferramenta black-box pronta** que seja simultaneamente *open-world* e *robusta a renaming*. O fingerprint (LibHunter) é robusto mas mundo-fechado; a lista é open-world mas frágil a renaming.
3. **A única abordagem black-box que é open-world E degrada graciosamente sob ofuscação é o decoupling estrutural (A3Ident-style, §4)** — porque clusteriza por **estrutura**, não por nome. Custo: reimplementação + ICC + revalidação (não há artefato). A objeção da ofuscação **promove §4 de "futuro nice-to-have" para "o único caminho que ataca a restrição real".**
4. **Para a ressubmissão (gh63 pinado), o caminho realista permanece A′** — validar o detector-manifest atual contra o oráculo independente — **com o reframe da ofuscação a nosso favor**: sob renaming agressivo, um `code_package` errado (prefixo de lib) casa ~0 classes renomeadas → o mis-pick é **inerte** a jusante (não enviesa contagem); a medição (M6) quantifica em que fração isso vale. O decoupling estrutural fica como direção de pesquisa para experimento futuro.

→ Ou seja: a ofuscação **não** salva a lista de prefixos como solução geral; ela **estreita** o leque a (estrutural = construir) ou (validar o atual + ameaça medida). É a resposta honesta, não otimista.

---

## 4. Decoupling estrutural (A3Ident-style) — o único open-world + obfuscation-resiliente; futuro, não atalho

Decoupling de autoria black-box: grafo de pacotes do dex (call+inheritance+**ICC**) + âncora MainActivity (manifest) + Louvain → módulo primário. Números (ICSME'20, verificado): **96,11% em F-Droid** (Tab. IV) e **~80,4% em apps ofuscados** (abstract — a topologia do grafo sobrevive ao renaming). É o **único candidato black-box que é open-world E degrada graciosamente sob ofuscação** (por clusterizar por estrutura, não por nome) — daí ser o caminho que a objeção da ofuscação (§3-bis) promove.

**Mas, honestamente, três furos:** (1) **sem artefato público**; (2) a aresta **ICC** exige IC3/DialDroid (ausente do androguard 3.4.0a1) — largá-la degrada os números; (3) Algoritmo 1 linha 3 *"identify contained libraries"* é **subespecificado** — ele **pressupõe** um subtrator de lib (usa LibScout/LibD, que **colapsam sob R8** — F1 1–4%). Ou seja, mesmo o A3Ident herda a fragilidade do subtrator de lib sob ofuscação; o seu 80,4% vem do **clustering estrutural carregando o peso** quando a identificação de lib falha. Reimplementar = mini-projeto + revalidação + **descongela gh63**. **Veredito:** melhor candidato técnico para o subconjunto ofuscado, mas é **construir**, não usar — direção de pesquisa para experimento futuro, não jogada da ressubmissão.

---

## 5. Enquadramento para o rebuttal (fonte primária — agente de escopo cripto)

1. **CryptoGuard (CCS 2019, §6.2) — precedent direto e idêntico ao nosso, verbatim:**
   > *"We distinguished app's own code from libraries by using the package information from AndroidManifest.xml. Android also uses it during R.java file generation (robust against obfuscation). We found that on average 95% of the detected vulnerabilities come from libraries."*
   **Não reporta acurácia nenhuma** dessa partição. → cite como precedent de que "partição por pacote do manifest é o método aceito"; medir P/R (que eles não fizeram) nos torna **mais fortes** que o precedent.

2. **Soot, num APK, NÃO traça a linha app/lib (fato técnico load-bearing).** Tudo do `-process-dir` (= o APK) vira *application class* por padrão; `isApplicationClass()` é `true` para `okhttp`, libs Google etc. — só o runtime Java é excluído. Confirmado por Steven Arzt (soot-list): *"Your whole APK file is Soot's process dir and that makes all contents application classes."* → **a fronteira é imposta pelo analista**; justifica por que existe um detector de pacote e por que não é "só `isApplicationClass`". Responde a #65A#4 (CogniCrypt **não** controla app-vs-lib → comparação é confundida sem rescopar um lado).

3. **Janovsky et al. (SECRYPT 2022, 600K APKs)** rejeita matching ingênuo por nome (*"non-system packages could be renamed… especially frequent in malicious applications"*), usa **LibRadar/LiteRadar** para excluir libs e **herda** o P/R do LibRadar (Zhan 2020) em vez de revalidar. (>60% do código de APK é third-party — Wang et al.)

4. **BinSight (AsiaCCS 2018)** = "source attribution" é o nome do problema; ~90% das violações vêm de libs; heurístico/semi-automático (P/R exato **UNVERIFIED** — host inacessível).

**Insight estratégico:** quase **ninguém valida a fronteira com P/R** no nível da atribuição de cripto. **Reportar recall/accuracy da nossa fronteira atinge/excede a barra do campo** — enquadrar como fortalecimento do método padrão, não catch-up.

---

## 6. Matriz comparativa final — soluções black-box

| Solução | Emite fronteira a nível de pacote? | Black-box (APK)? | Robusto a R8? | Cobre nossas libs? | Runnable 2026 | Veredito |
|---|---|---|---|---|---|---|
| **AndroLibZoo+Exodus+top-up / AndroSpecter** | ✅ sim | ✅ | ❌ **morre sob renaming** | ✅ com top-up | ✅ MIT/LGPL, Soot | ⚠️ **válida só no subconjunto NÃO-renomeado** (§3-bis) |
| **Detector atual (manifest)** | ✅ (string única) | ✅ | ✅ (manifest preservado; mis-pick "inerte" sob ofusc.) | parcial (erra 4 lib-picks) | ✅ in-process | ✅ baseline; **validar (A′)** — jogada da ressubmissão |
| **LibHunter (ASE'24)** | ❌ (só nome+versão; sem localização) | ✅ | ✅ p/ libs *conhecidas* | ❌ mundo-fechado, 31 vuln-libs | ⚠️ sem licença | ↪️ só checagem de versão-vulnerável |
| **A3Ident reimplementado** | ✅ (cluster) | ✅ | ⚠️ **~80% (estrutural)** — único open-world+obfusc. | herda subtrator de lib (frágil sob R8) | ❌ sem artefato + ICC | 🔮 **futuro** — melhor candidato p/ subconjunto ofuscado, mas é construir |
| **Fingerprint clássico** (LibScout/Scan/Radar/D/ID/Pecker) | parcial | ✅ | ❌ (1–4% F1 sob R8; mortos) | ❌ catálogos 2017–19 | ❌ mortos/frágeis | ❌ descartado |
| **Build-graph (Gradle resolve)** | ✅ (alta recall) | ❌ **precisa de fonte** | n/a (pré-ofuscação) | ✅ | — | 🧪 **só oráculo offline** (§7) |

---

## 7. Plano de medição (os 169 + os 4 mis-picks) — não toca GATOR/parser/AJC, não descongela gh63

**Oráculo de ground truth (offline, legítimo — usa info que o detector runtime não tem):**
- **applicationId autoritativo** dos 169: sha256 do APK → `index-v2.json` do F-Droid, cruzado com o nome do arquivo `metadata/<id>.yml`. Cheap, 100% cobertura. (Resolve a circularidade: oráculo **independente** do detector.)
- **Conjunto de libs autoritativo (declarado):** parsear `build.gradle[.kts]`/`libs.versions.toml` do commit upstream (via tarball `_src.tar.gz` do F-Droid). Precedent publicável: **Gu/Lu 2025 (arXiv:2509.04091)** fez isso em 3.551 projetos F-Droid e validou contra a resolução do Gradle (r=0,99); limitação = código vendored. **Build-graph é o ORÁCULO, nunca o detector** (black-box proíbe em runtime).

**Medições:**
| # | Mede | Como | Responde |
|---|---|---|---|
| M1 | Acurácia do detector atual | `code_package` vs applicationId F-Droid, estratificado por `detection_method` + ofuscação, **Wilson CI** | #65A#1 |
| M2 | **A inversa (AndroLibZoo+Exodus+top-up) corrige os 4 mis-picks?** | rodar AndroSpecter nos 4 + amostra; comparar pick vs oráculo | valida §2 empiricamente |
| M3 | **A inversa introduz erro nos 99 `same_package`** (hoje corretos)? | rodar nos 99; quantos quebram (esp. thin-dex Flutter, vendored) | custo de trocar p/ inversa |
| M4 | κ detector × inversa × oráculo | concordância entre os 3 sinais | quantifica fronteira |
| M5 | Gap prefixo-vs-conjunto + matriz app-vs-lib + taxa lib-mis-pick | nos 46 não-triviais | #65A#1/#65A#4 |
| M6 | % do corpus sob R8 (onde a lista degrada) | detector de ofuscação (segmentos de 1–2 letras) | enquadra a limitação honestamente |

**Critério (pré-registrado):** M2 corrige os 4 **e** M3 baixo → adotar a inversa-híbrida em experimentos futuros (gh63 fica pinado; entra em re-run novo). M2/M3 ruins → manter detector atual validado (A′) + declarar a inversa como trabalho futuro com o gap medido.

---

## 8. Decisões propostas (discutir antes de implementar)

| # | Decisão | Recomendação |
|---|---|---|
| (a) | LibHunter como subtrator da inversa | ❌ **Não** (sem localização + mundo-fechado). Só checagem de versão-vulnerável, se um dia. |
| (b) | Instrumento da inversa por prefixo | **AndroLibZoo + Exodus + top-up via AndroSpecter/Soot** — **só para o subconjunto NÃO-renomeado** (morre sob R8-renaming). Não é solução geral. |
| (b') | Subconjunto **ofuscado/renomeado** | Sem ferramenta black-box pronta open-world. Opções: **decoupling estrutural (A3Ident, construir)** OU aceitar o detector-manifest atual como "inerte sob ofuscação" + ameaça medida (M6). |
| (c) | Construto | **Híbrido** (âncora manifest app+ ∧ lista curada lib−), não residual puro — e ciente de que o lado lib− só vale no não-renomeado. |
| (d) | Build-graph (Gradle) | **Só oráculo offline** de ground truth (Gu/Lu 2025 como precedent); nunca o detector runtime. |
| (e) | Validação | A′ + M1–M6; medir P/R da fronteira (acima da barra do campo — §5). |
| (f) | gh63 | **Pinado.** A inversa-híbrida é para experimento futuro; ressubmissão usa números atuais + eval. |
| (g) | Calibração | Detecção = 1 de 7 drivers; A′+inversa fecham #65A#1 e parte de #65A#4. Não super-investir. |

**Próximo passo (após aprovação):** dobrar M1–M6 + a integração AndroSpecter na `gh67-package-detector-eval` via skill OpenSpec (não editar artefatos à mão); registrar AndroLibZoo/Exodus como deps de avaliação; manter A3Ident/conjunto (D) no backlog.

---

## Apêndice — verificação (fonte primária)

**CONFIRMADO:**
- **LibHunter** ASE 2024 (PDF + `analyzer.py`): saída nome+versão sem localização; banco 31 vuln-libs/3447 versões, mundo-fechado; F1 71,4% lib / 51,1% versão sob Opt+Obf+Srk (Tab.3, **F1 só**); sem licença; nenhuma discussão de app-code.
- **AndroLibZoo** MSR 2024 (github.com/JordanSamhi/AndroLibZoo, Zenodo 10072709): 34.813 prefixos, MIT. **AndroSpecter** (github.com/JordanSamhi/AndroSpecter, Soot/Java, LGPL, `isLibrary(SootClass)`).
- **Exodus** API pública (reports.exodus-privacy.eu.org/api/trackers): 432 trackers, 428 com `code_signature`; ODbL.
- **CryptoGuard** CCS 2019 §6.2 (arXiv 1806.06881): partição por pacote do manifest, "95% vêm de libs", **sem acurácia**.
- **Soot/APK:** tudo vira application class por padrão (Arzt, soot-list; Soot usage docs).
- **Janovsky** SECRYPT 2022 (arXiv 2205.05573): rejeita nome ingênuo, usa LiteRadar, herda P/R.
- **Gu/Lu 2025** (arXiv 2509.04091): build-graph ground truth em 3.551 F-Droid, r=0,99 vs Gradle.
- **F-Droid:** `index-v2.json` (sha256→packageName), `metadata/<id>.yml` filename = applicationId; **sem campo de dependência**.
- **Zhan ASE 2020** (DOI 10.1145/3324884.3416582, **não** arXiv:2108.03787): recall<50% (C1), LibScout 49,03%/F1 65,2%.
- Empírico (testes do agente): AndroLibZoo perde io.flutter/appauth/tink/okhttp/gms/firebase; Exodus cobre os trackers Google/ad; LiteRadar `tag_rules.csv` obsoleto (762 linhas, ~2016).

**UNVERIFIED (não citar como exato):**
- Split P/R do próprio LibHunter sob R8 (paper dá só F1).
- BinSight (AsiaCCS'18) P/R de atribuição (host inacessível).
- CogniCrypt usar `isApplicationClass()` + excluir só android/androidx (sem quote primário).
- Venue do Gu/Lu 2025 (preprint arXiv); LibRadar/LibPecker recall 40,39%/36,85% (gráfico Zhan).
- Sobrevivência dos identificadores de classe do LibHunter sob R8; fração dos 169 com lockfile/`srclibs`.

**Artefatos locais:** `/tmp/androlibzoo.lst` (34.813 prefixos), `/tmp/exodus_trackers.json` (432), `out/sota_spike/` (LibScout), `out/package_detector_audit/` (169 APKs, 4 mis-picks).
