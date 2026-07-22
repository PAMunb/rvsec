# Prompt para a próxima sessão — veredito sobre detecção de pacote/código-app

> Cole o bloco abaixo como primeira mensagem de uma sessão nova (janela de contexto limpa). Ele é autocontido.

---

## TAREFA

Chegar a um **VEREDITO honesto e fundamentado** sobre como tratar o problema de **detecção de pacote / código-app** no projeto RV-Android, para a **ressubmissão** de um artigo que foi rejeitado no ICST 2026 — onde a detecção de pacote foi uma objeção **explícita** de revisor. NÃO é para implementar nada ainda; é para **decidir o caminho** com rigor.

**Atenção — não repita o erro da análise anterior:**
1. A investigação anterior buscou o SOTA de **detecção de BIBLIOTECA** (LibScout, LibRadar, LibD, LibPecker, LibID — *Third-Party Library detection*) e concluiu que essas ferramentas "só detectam libs, não servem". Isso está **incompleto**: o SOTA relevante para nós é o de **identificação do MÓDULO PRIMÁRIO / CÓDIGO-APP / host-app vs piggybacked** (ex.: PiggyApp, WuKong, DroidLegacy e sucessores), que **computa diretamente o código próprio do app** — exatamente o nosso problema. **Pesquise a fundo esse paradigma**, que foi só tangenciado antes.
2. **Não aceite a conclusão otimista "basta validar e escrever 3 parágrafos no artigo".** Esse foi o viés da recomendação anterior. O veredito desta vez precisa pesar honestamente, incluindo as opções mais custosas: melhorar o algoritmo do detector, adotar/cruzar com uma ferramenta real de módulo-primário, ou redefinir o construto. Se a conclusão for "validar+texto basta", ela tem de **sobreviver a uma tentativa séria de refutação**, não ser o ponto de partida.

## MÉTODO (obrigatório)

- Use **VÁRIOS SUBAGENTES em paralelo** + o **MCP sequential-thinking** para estruturar.
- **Pesquise na internet de novo**, agora mirando *primary module identification* / *app code identification* / *host app vs library partitioning* / *repackaging & app-clone detection* / *app-vs-library code separation* — não TPL detection.
- Verifique afirmações em **fontes primárias** (papers, venues, anos, números reais de acurácia). A rodada anterior teve subagente inventando citações; exija verificação primária.
- Ao final, traga o veredito como **matriz de opções com trade-offs** + um caminho recomendado + um fallback. Sem implementar.

## CONTEXTO — o que já fizemos/decidimos (LER OS DOCS)

**Artefatos a ler primeiro (no repo rv-android):**
- `docs/20260219_icst2026_pareceres_65.md` — pareceres verbatim do ICST 2026 (a objeção #65A#1 é o alvo).
- `docs/20260617_estrategia_deteccao_pacote_defensavel.md` — recomendação ANTERIOR (a que tem o viés otimista a ser refutado/confirmado); contém a "defesa de 3 pernas", a calibração pelos revisores (§1.5) e o mapa dos 7 drivers de rejeição.
- `docs/20260613_plano_package_detector_melhoria.md` — plano de melhoria: decisões D1–D6, Change A (eval), Change B (manifest-affinity).
- `docs/20260613_pesquisa_package_detection_sota.md` — pesquisa SOTA anterior (focada em TPL detection — o ponto cego).
- `docs/20260617_investigacao_sota_substituir_detector.md` — spike empírico do LibScout (substituição completa = inviável; 3 bloqueios B1/B2/B3).
- `openspec/changes/gh67-package-detector-eval/` — Change A já especificada (proposal/specs/design/tasks).
- `modules/rv-android-core/src/rv_android_core/package_detector.py` — o detector atual.
- Memórias: `project_package_detector_improvement_plan`, `project_icst2026_65_rejection`, `project_gator_ft_investigation`.

**O que o detector faz (`package_detector.py`):** infere o `code_package` (o pacote real do código-app, que difere do pacote do manifest em ~27,5% dos APKs) por uma cascata de 6 heurísticas priorizadas: same_package (~72,5% dos casos: todos os componentes Activity/Service/Receiver no pacote do manifest), game-engine, single_package, common_prefix, most_common (dominância ≥60%), similaridade (Jaro-Winkler/Levenshtein/SequenceMatcher) e fallback para o manifest. Filtra prefixos de framework. Retorna confiança + método.

**Contrato do `code_package`:** é usado como **UMA string de prefixo** pelo GATOR (`-clientParam codePackage=`), pelo parser de análise estática (INV-ANA-03) e pelo AJC. O experimento atual está **PINADO** (gh63) — qualquer mudança no detector vale só para experimentos futuros, não para os números já coletados.

**Fatos empíricos estabelecidos (não relitigar, mas pode revisitar se a pesquisa contradisser):**
1. Auditoria dos 169 APKs do experimento: **4 lib-picks reais** — readeckapp→`net.openid.appauth`; venera+webspace→plugin Flutter; whobird→`org.tensorflow.lite`; (+ passwordstore→`app.passwordstore.ui`, pick estreito). Taxa de erro ~2,4%.
2. **Achado contraintuitivo "inerte sob ofuscação":** a ofuscação MASCARA o erro em vez de amplificá-lo. Os components do manifest (input do detector) NÃO são ofuscados (R8 os preserva por serem referenciados); o estrago do R8 é a jusante — classes dex repackageadas (`I3.c`, `j2.a`) não casam com pacote nenhum (certo ou errado), então o pick errado fica **inerte**. CONFIRMAR/REFUTAR isto com rigor: vale só no subconjunto ofuscado; em apps não-ofuscados (~25%) um prefixo errado PODE casar código real.
3. **Substituir o detector por ferramenta TPL é inviável** (spike LibScout): (B1) TPL tools emitem conjunto de libs, não um `code_package`; a única "string de pacote" do LibScout é a do manifest. (B2) catálogo: 0/9 das libs dos mis-picks nos 8.542 perfis. (B3) custo: 31 s/APK, JDK 8 + Gradle 4.9, intrusivo no módulo-base Python.

**A objeção de revisor a resolver (ICST 2026 #65A, Soundness #1 — verbatim):**
> "The heuristic package-detection algorithm's effectiveness (e.g., recall, accuracy) is **not reported**, and it is unclear if the algorithm was applied to **all 557 apps or only the 103**, making it hard to properly assess the extent to which the detected packages contain the **application, rather than library, code**."

E reaparece em #65A#4: a comparação com CogniCrypt ignora "the **scope of analyzed code (application vs. library)**". O revisor pede 3 coisas: **(a)** acurácia/recall reportada; **(b)** denominador claro (a quais apps foi aplicado); **(c)** garantia app-vs-lib.

**Restrições estratégicas:**
- NÃO há tempo para um artigo dedicado a detecção de pacote → não pode ser posicionado como contribuição.
- O experimento gh63 está congelado → mudanças no detector não re-pinam os números atuais.
- Detecção de pacote é **1 de 7 drivers** de rejeição (os outros: cap de 300 s; contagem de unique-misuses; comparação CogniCrypt; novidade/reposicionamento; representatividade do subconjunto instrumentado; F-Droid-only; tool não-pública). NÃO criar visão-de-túnel, mas este prompt foca a fatia de detecção de pacote.

## LINHAS DE INVESTIGAÇÃO (refine/expanda)

1. **SOTA de identificação de módulo-primário / código-app** (o ponto cego): PiggyApp (CODASPY'13), WuKong (ISSTA'15), DroidLegacy (PPREW'14), e o que houver de mais recente (2018–2025). Como cada um computa o código próprio do app? Qual a acurácia reportada? Dá para **reusar como oráculo de validação**, **citar como precedent metodológico**, ou até **adotar**? Eles realmente resolvem o nosso problema (uma string de prefixo confiável) ou também esbarram nas mesmas heurísticas de manifest?
2. **Existe uma definição/ferramenta canônica de "app code package"** na literatura recente de análise Android? Como FlowDroid/CryptoGuard/Amandroid de fato delimitam código-app na prática (além de "usa o manifest e segue")?
3. **Avaliação honesta do nosso detector:** ele é bom o suficiente, ou tem fraqueza algorítmica real que um revisor explora? Onde quebra (multi-módulo, forks, namespaces de hospedagem tipo io.github)? A premissa de "um único prefixo" é defensável, ou o construto deveria ser "conjunto de pacotes-app"?
4. **Robustez dos resultados a erro de detecção:** dá para provar que os achados do experimento são invariantes aos 4 mis-picks (re-rodar com/sem) + bound de pior caso? Quão forte é esse argumento sozinho?
5. **Matriz de opções** (pese cada uma contra: rigor que satisfaz o revisor × tempo × risco de re-rodar experimento):
   - (A) Só validar (Change A) + threats + robustez — defesa textual.
   - (B) Validar + melhorar o detector (Change B manifest-affinity) para experimentos futuros.
   - (C) Validar cruzando com uma ferramenta SOTA de módulo-primário como oráculo independente.
   - (D) Redefinir o construto (conjunto de pacotes-app; ou definição operacional diferente).
   - (E) Combinações.

## ENTREGÁVEL

Documento em `docs/` com:
- **(a) o veredito**: como tratar a detecção de pacote para a ressubmissão — caminho recomendado + fallback, com a refutação séria da opção "só texto".
- **(b) o SOTA de detecção de pacote/módulo-primário** propriamente pesquisado (corrigindo o ponto cego), com citações primárias e números.
- **(c) o que escrever no artigo** (acurácia/denominador/app-vs-lib) que responde literalmente ao #65A#1 e #65A#4.
- **(d) quanto da Change A/B é necessário**, revisado à luz do SOTA de módulo-primário.
- **(e) o enquadramento threat-to-validity** (Wohlin: validade de construto), se aplicável.

Traga a recomendação para **discutir** antes de implementar. Sem implementar nada antes de aprovação.
