# Experimentos do GATOR em 07/10: estado e resultados

**Arquivo vivo**: atualizado ao longo do dia. A última atualização está no topo de cada seção.
**Rótulos**:
- **[conferido]**: aberto ou recontado por mim;
- **[relato]**: trazido por subagente e não reaberto;
- **[hipótese]**: inferência.

**Sessão 7 (a partir de 12:15)**:
- issues abertas: **#120** (GATOR) e **#121** (carimbo no instrumentador);
- changes OpenSpec **`gh120-gator-distance-hosted-windows`** e **`gh121-instr-handler-stamp`** com os 4 artefatos, ambas válidas (`--strict`). A implementação da gh120 começou às 12:47: Java na worktree `int`, Python no checkout principal, em paralelo. Alvo: jar pronto ~15:30, aceitação, build do reator e hand-off antes das 19:00;
- **a análise estática da noite passa a ser dos 163 APKs**, não dos 89 (decisão do Pedro, 12:20: "senão não pega as novas análises"). A instrumentação fica com o Pedro;
- o lado do APE-RV (ler o carimbo e consumir a distância) vem depois de hoje e antes da campanha.

**Onde está o código** (nada comitado): worktrees de `rvsec` em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/`:

| worktree | branch | o quê | estado |
|---|---|---|---|
| `dist` | `wip/gator-dist` | distância por alvo, aresta de lambda, exclusões efetivas | **pronto** (11:54); falta a rodada do 7.5 |
| `frag` | `wip/gator-frag` | fragments F1/F2 + ViewBinding | **pronto** (11:27) |
| `dlg` | `wip/gator-dlg` | diálogos, DataBinding, adapters | em curso (previsto 12:45) |
| `stamp` | `wip/instr-stamp` | instrumentador: carimbo do handler (View + Compose) | **pronto** (12:16), View e Compose; ver §6 |
| `int` | `wip/gh120-int` | integração da change #120: `frag` + `dist` (depois `dlg`) | `frag` + `dist` aplicados sem conflito e compilando (12:24) |

---

## 1. Experimento das exclusões (C0) — concluído

**Como rodou**: cópia do `lib/gator` com o `Main.class` alterado só nas três strings do `-exclude`. Configurações:
- linha de base;
- (i) `kotlin.*`, `kotlinx.*`, `androidx.compose.*`;
- (ii) `kotlin.*`, `kotlinx.*`, `androidx.*`.

Comparação contra os `.apk.json` de setembro. Script: `scratchpad/c0/c0_compare.py`.

**Resultado** [conferido]:
- **A linha de base reproduz setembro exatamente** nos 5 APKs válidos:

  | APK | métodos com as mesmas flags | widgets iguais |
  |---|---:|---|
  | giggity | 780/780 | sim |
  | cry.otp | 97/97 | sim |
  | treehouses | 5.002/5.002 | sim |
  | droid_scep | 174/174 | sim |
  | password.monitor | 832/832 | sim |

- **As exclusões com `.*` não mudam nada.** Nas três configurações, o call graph (vértices e arestas), as contagens de classes e as flags saem idênticos nos 8 APKs que terminaram, mesmo com `androidx.*` inteiro excluído.
- **Causa** [conferido no bytecode do `soot-4.7.1.jar`]: o `Scene` lê a lista de exclusões só no construtor (`Scene.determineExcludedPackages`, chamado apenas de `Scene.<init>`). O GATOR cria o `Scene` em `PrerunEntrypoint.run()` (`Scene.v().addBasicClass…`) antes de `soot.Main.main(args)` interpretar os argumentos (`Main.java:248-289`). O `-exclude` nunca chega ao Soot, com ou sem `.*`. A explicação de 28/08 ("falta o `.*`") estava incompleta.
- **Consequência**: a correção das exclusões exige código, passando as exclusões antes do prerun. Ela foi para a worktree `dist` (`RVSEC_EXCLUDE_MODE`) e é medida no experimento de distância.
- **Variáveis da campanha**: rodei sem `RV_STRIP_BUILD_TYPE_SUFFIX=true`, e freeotp, criticalmaps e wifianalyzer foram recusados por denominador implausível. A campanha de setembro usava `RV_STRIP_BUILD_TYPE_SUFFIX=true` e `RV_PACKAGE_DETECTOR=false` (`rvsec-dataset/jca_android/FUNIL.md:434-436`). **A análise da noite precisa das duas.**

## 2. Chegada à activity × interação (offline, E6) — concluído

Script: `doutorado-tese/.../20261005_e6_graduacao_marca/m18_distance_validation/` (`summary.txt`) [conferido].

| | primeiras execuções de chamador direto na exploração | na janela de chegada (3 passos) | depois (interação) |
|---|---:|---:|---:|
| todos os braços | 270 (42 APKs) | 87 (32,2 %) | 183 (67,8 %) |
| sem guia | 80 | 19 (23,8 %) | 61 (76,2 %) |
| MOP | 90 | 32 (35,6 %) | 58 (64,4 %) |
| MOP+LLM | 100 | 36 (36,0 %) | 64 (64,0 %) |

- 136 das 406 primeiras execuções ocorrem antes da exploração (startup).
- **Leitura**: dois terços disparam durante a interação, não na chegada. O canal por widget pesa mais que o lançador e o canal por activity.

## 3. Fragments (F1 + F2) — pronto, 11:27

**O que foi feito** [relato, com conferência por amostra]:
- **F1**: mapa activity → fragments, a partir de transações (`add`/`replace`), de `<fragment>`/`FragmentContainerView` no layout, de grafos de Navigation e de paginadores. Uma activity base é mapeada para as subclasses declaradas no manifesto.
- **F2(b)**: os widgets e listeners de cada fragment saem numa janela `Host#Fragment` de tipo `FRAGMENT` (nunca `DIALOG`), também quando a WTG não termina.
- **Achado**: o GATOR não modelava ViewBinding (`ViewBindings.findChildViewById`), nem a ligação do framework entre `onCreateView` e `onViewCreated(view)`/`getView()`. O agente modelou as duas. Isso recupera `binding.botao.setOnClickListener` **também em activities**.

**Resultado nos 6 APKs de teste** (contra setembro; derive de produção):

| APK | janelas de fragment | listeners | ids M15 de fragment presentes | widgets marcados no artefato, antes → depois |
|---|---:|---:|---|---:|
| wifianalyzer | 7 | 34 | 5 (38 cliques) | 0 → 0 |
| treehouses | 19 | 192 | **14 de 29** [conferido; o agente disse 14/14 com denominador mais estreito] | 0 → 26 |
| criticalmaps | 5 | 54 | 12 (705 cliques) | 0 → 4 |
| freeotp | 3 | 1 | 1 (7 cliques) | 5 → 5 |
| droid_scep | 3 | 58 | **29 de 29** [conferido] | 0 → 7 |
| password.monitor | 3 | 179 | 16 (3.219 cliques) | 0 → 44 |

- **Nada existente se perdeu**: 0 janelas, 0 widgets e 0 listeners.
- Os widgets marcados no artefato que o APE-RV recebe sobem de 5 para 86 nos 6 APKs.
- O tempo do GATOR subiu (password.monitor de 204 s para ~400 s), mas a máquina estava dividida com outras JVMs. Não separado.
- **Não coberto**:
  - fragments criados por reflexão, `FragmentFactory`/Hilt e Navigation montado em código;
  - arestas fragment → fragment (F3) e sementes (F4);
  - `DialogFragment`, que é da worktree `dlg`;
  - `Fragment(R.layout.x)` sem `onCreateView`.
- Colisões de id entre janelas do mesmo host: 0 a 12 por APK. O efeito na flag não foi medido.

## 4. Distância ao alvo (7.5) — veredito às 12:45 (sessão 7)

**Rodada** [conferido]: GATOR da worktree `dist`, `--skip-wtg`, variáveis da campanha, 13 APKs × modo de exclusão `current`/`fixed`. As saídas brutas e a validação estavam no scratchpad em `/tmp` e se perderam no reboot de 13:15; ficam só os números abaixo.
- Terminaram em `current`: 12 de 13. Bitbanana precisou de 32 GB. Faircode falhou com 12 GB nos dois modos e terminou com 32 GB (924 s). **Openbible (só Compose) bateu nos 1.800 s mesmo com `--skip-wtg`**, sem chegar ao JSON pré-WTG. Nesse APK, o tempo vai antes da WTG, no Soot ou no solver.
- **Exclusões efetivas (`fixed`)**:
  - derrubam o GATOR no openbible (Compose) e no redreader. Causa [conferido, rodando o java direto]: `RuntimeException: ... androidx.compose.ui.tooling.PreviewActivity is at resolving level SIGNATURES`. O grafo de fluxo pede o corpo de uma activity do manifesto que está excluída;
  - nos 6 APKs em que os dois modos terminaram, todas as medidas saem idênticas.
  - **Decisão do Pedro (12:40): remover os `-exclude`**. O grafo continua o de setembro.
- **Grafo inteiro × só do app**: idênticos em todas as medidas nos 10 APKs. Fica o grafo inteiro: é o mesmo do `reachesTarget`, e no password.monitor ele acha 102 métodos a ≤ 10 chamadas de um alvo, contra 6 do grafo só do app.
- **Aresta de lambda**:
  - dos 12 eventos úteis de "handler que disparou" (2 APKs), o handler tem distância finita em 3 com a aresta e em 1 sem ela;
  - no redreader, 71 wrappers têm corpo que alcança e wrapper que não alcança.
  - **Entra**, também no `reachesTarget`. Com ela, o derive só recupera pela classe o wrapper ausente (decisão do Pedro, 12:40).
- **Lift por clique** (7 APKs, 2.800 cliques casados):
  - clique num widget cujo handler está a ≤ 3 chamadas de um alvo ainda não executado: um alvo novo roda nos 3 passos seguintes em 9,8 % de 61 cliques (3,6 % de 165 com a aresta de lambda);
  - nos outros cliques: 0,2 %;
  - contagens pequenas (6 eventos).
- **Fronteira B** (12 APKs, com faircode e bitbanana; validação em `.../g75/val_cur12/`):
  - mediana de 6 métodos (0 a 531), mediana de 0,4 % dos métodos do app;
  - extremos: password.monitor 70 de 832 (8,4 %); faircode 531 de 17.250 (3,1 %), app com muita biblioteca;
  - as medidas de C não mudam com os 2 APKs a mais (lift com d ≤ 3: 9,8 % de 61 cliques contra 0,3 %);
  - **entra como segundo tipo de alvo** (`kind: "boundary"`).
- **Custo da distância**: ≤ 2,8 s por APK.

## 5. Diálogos, DataBinding e adapters — pronto (relato do agente, 12:35)

- Em 11 APKs: 0 pares (id, host) perdidos; 146 de 158 ids-alvo ausentes recuperados [relato].
- **Problema 1**: as janelas `HOSTED` também trazem as views de fragment, duplicando as `FRAGMENT`. No merge, fica uma janela por (host, dono).
- **Problema 2**: explosão de listeners em activity base abstrata (sexytopo 137 → 3.069). Será medida na aceitação.
- **Problema 3**: o screenshottile perde metadados de 4 widgets porque a árvore sai duplicada. O conserto vai no `enrichFromXml`.

## 6. Carimbo do handler no instrumentador (Variante A) — pronto, 12:16

Relatório do agente: estava no scratchpad em `/tmp` e se perdeu no reboot de 13:15 [relato]. O código continua na worktree `worktrees-gator/stamp`.
- View e Compose implementados atrás da flag `--stamp-handlers`, que fica desligada por padrão. **Desligada, os DEX saem byte-idênticos aos do corpus** (parceltracker, 10 de 10).
- Em 4 APKs, 120 s de APE pelo rv-platform: 0 crash, 0 `VerifyError`.
- No Compose (parceltracker), o carimbo traz as lambdas reais do app.
- **Limites**:
  - `android:onClick` do XML carimba o despachante genérico (42 de 134 linhas no scep);
  - toolbar, menu e `SearchView` carimbam classes da biblioteca;
  - não foi conferido se o UiAutomation entrega os extras ao APE-RV.
- **Para a instrumentação de vocês**: o wrapper Python não repassa a flag. Ou se chama o `instr-cli` direto com `--stamp-handlers`, ou se faz a mudança pequena no `_common_cli_args`, que é tarefa da change #121. A imagem Docker clona o GitHub, então não tem o código não comitado.

Desenho e perguntas: `docs/20261007_variante_a_carimbo_handler.md`.

## 7. Para a análise da noite (outra sessão)

- **Conjunto: os 163 APKs** (decisão de 12:20). A lista dos 89 (`doutorado-tese/docs/estudo-03/analise/scripts/20261005_e6_graduacao_marca/m18_scope89.txt`, custo de setembro 38,8 h, 29 no teto) fica só como referência de custo.
- **Variáveis obrigatórias**: `RV_STRIP_BUILD_TYPE_SUFFIX=true`, `RV_PACKAGE_DETECTOR=false`.
- **O GATOR a usar**: `rv-android/lib/gator`, deployado pelo build do reator de 13:36 (ver §8).

## 8. Checagem do GATOR da change e deploy — sessão 8, 13:30–13:45

- **Build** da worktree `int`: 230 testes do client verdes. **Port** para o checkout principal (só os caminhos do GATOR, nada comitado). **Build do reator**: BUILD SUCCESS, e os jars estão em `rv-android/lib/gator`, com as mesmas classes do build testado [conferido, md5]. Paridade `tests/parity/test_json_keys.py`: 4 verdes. Client no checkout principal: 230 verdes.
- **4 APKs pequenos** (no lugar da aceitação de 20, por causa do prazo), 4 × 12 g em paralelo. Saídas em `worktrees-gator/acc/out/`; comparação com setembro, por conteúdo, feita por `worktrees-gator/acc/compare.py` [conferido]:

| APK | s (set → hoje) | janelas/widgets/pares/listeners perdidos | FRAGMENT/HOSTED | widgets marcados (derive set → novo) |
|---|---|---|---|---|
| giggity_769 | 35 → 38 | 0 / 1* / 0 / 0 | 0 / 16 | 0 → 0 |
| cry.otp_31 | 65 → 80 | 0 / 0 / 0 / 0 | 0 / 5 | 3 → 3 (recuperados 2 → 0) |
| treehouses.remote_6098 | 115 → 130 | 0 / 0 / 0 / 0 | 19 / 79 | 0 → 62 |
| dsub2000_217 | 375 → 177 | 0 / 0 / 0 / 0 | 6 / 36 | 11 → 11 |

\* giggity: o mesmo widget `title` da `ScheduleViewActivity` com outro texto; setembro tinha "The first talk you may actually consider attending", hoje "Giggity". Provável ordem de anotação do XML [hipótese, não conferido]; não é widget perdido.

- **Dedupe (`dropRepeatedOwnedWindows`) no dsub2000**: FRAGMENT 61 → 6, listeners 28 238 → 2 610, JSON 11 MB → 2,9 MB (setembro: 1,8 MB), mesmo derive (11 → 11).
- **Não rodado hoje**: os APKs grandes (faircode, bitbanana, redreader), os do protótipo de diálogos (o risco de listeners em excesso no sexytopo continua sem medida), o INV-ANA-75 (`--skip-wtg`) e a igualdade das distâncias com o experimento (já conferida na sessão 7 em giggity, treehouses e dsub).
- **JSON de setembro + derive novo**: no sexytopo, 20 → 7 widgets marcados (com o JSON novo, 16). Explicação em `worktrees-gator/acc/pergunta2_derive_setembro.md`; regra no hand-off.
- **Hand-off da noite**: `rv-android/docs/handoff/20261007_sa163_gh120_handoff.md`. Runner corrigido para 6 × 12 g e 2 × 32 g. Estimativa da rodada a pelo custo de setembro: cerca de 9 h de relógio (85 dos 163 levaram 1 800 s ou mais em setembro).
- **Spinners com array de recurso (tarefa 2.7, decisão sua de 14:10)**: o extrator agora lê `createFromResource` e `getStringArray`/`getTextArray`. Para o cry.otp funcionar, foram precisas mais três correções no mesmo extrator:
  - ids lidos de campo `R$…` não final;
  - o id do `findViewById` resolvido no próprio statement, porque o registrador é reaproveitado;
  - itens indexados pelo ponto de criação do adapter, porque a mesma variável guarda vários adapters.
  
  No cry.otp, os 5 spinners passam a ter opções (3, 3, 3, 40, 2), e o resto é igual por conteúdo [conferido]. Jar reinstalado às 14:30; 236 testes do client e paridade verdes. Detalhe em `docs/20261007_spinners_sem_opcoes_gator.md`.
