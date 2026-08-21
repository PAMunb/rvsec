# Handoff — auditoria de consistência e triagem de escopo do plano de correção da análise estática

**Data**: 2026-08-21 · **Branch**: `modules` · **Último commit**: `5222a5d9` (gh105, não relacionado)
**Objeto**: `docs/20260821_plano_correcao_analise_estatica.md`, revisão 4, 424 linhas
**Estado**: nada implementado, **nenhuma issue aberta, nenhuma change criada**. A gh105 não foi tocada.
**Predecessores**: revisão 1 em `backup/20260821_plano_correcao_analise_estatica.v1.md`,
revisão 3 em `backup/20260821_plano_correcao_analise_estatica.v3.md`.

---

## O que estamos fazendo

Um relatório de defeitos (`docs/20260821_relatorio_analise_estatica_defeitos.md`) alegou treze
problemas no acoplamento entre o experimento e a análise estática. O plano acima é a destilação
desse relatório depois de quatro revisões: sobraram **quatro reparos** com dano demonstrável e
**cinco itens de faxina**, que juntos darão origem a **UMA ÚNICA change**, trilha Quick Path.

Isto é **Fase 0** do `docs/WORKFLOW.md` — material de referência, não artefato OpenSpec. A change
ainda não existe.

### Os quatro reparos, em português, sem apelido

O plano usa apelidos (J1, D2, P3, D1/G1, G2–G5). Eles são atalhos de escrita, não vocabulário do
projeto — **use os nomes reais quando falar com o pesquisador.**

| Apelido | O que é, em uma frase | Prova |
|---|---|---|
| **J1** | O marcador de "análise completa" é gravado no fim de **toda** escrita bem-sucedida, inclusive a escrita parcial que acontece antes do grafo de janelas. Um run que estourou o timeout deixa em disco um artefato marcado como completo. | **Único item com prova em artefato real**: cinco APKs reais, verificados duas vezes |
| **D2** | O denominador da cobertura sai de um conjunto de especificações e o numerador de outro. A análise estática sempre pergunta pelo conjunto de criptografia, qualquer que seja o conjunto que o experimento escolheu. | Verificado por leitura: o parâmetro nunca é passado; o default fixo responde |
| **P3** | A linha de comando descarta o booleano de sucesso e imprime "experimento concluído com sucesso" sempre. Nenhum código de saída serve para automação. | Verificado: é o **único** chamador da função no repositório inteiro |
| **D1/G1** | A raiz do SDK Android que o config Python resolve nunca chega ao GATOR, que recalcula a sua a partir de outra variável, não validada. | Verificado por execução, os dois ramos |

Faxina (`G2`–`G5` + um parâmetro morto): exit code da JVM descartado; timeout externo e interno
com o mesmo valor, de modo que um ramo do lançador é código morto; caminho legado do `sdkmanager`
que só funciona por causa de um symlink no Dockerfile; flags desconhecidas repassadas em silêncio
à JVM; e um parâmetro recebido e nunca lido.

---

## O que foi feito, e o que **não** foi

### Revisões 1 → 4

- **Revisão 1**: 24 alegações levantadas, 11 mortas na hora.
- **Revisões 2 e 3**: mais 4 mortas; sobraram os 4 + 5 atuais.
- **Revisão 4** (esta sessão): auditoria de consistência independente, contra a árvore, com as
  quatro reproduções executadas. **Nenhum defeito mudou de veredito.** A aritmética fecha:
  24 alegações − 15 mortas = 4 defeitos + 5 itens de faxina.

### Corrigido na revisão 4 (oito itens)

| # | O que estava errado | Como estava | Como ficou |
|---|---|---|---|
| 1 | Contagem de edições locais no lançador do GATOR | "as duas únicas edições" | são **três** — `cf649214` (2024-10-05) trocou o nome do jar e acrescentou `-outputFile`, antes das duas conhecidas |
| 2 | Citação que sustenta a refutação de um item | `experiment/spec.md:238-241` — intervalo que **não contém** a obrigação citada | `:239-244`, com o ponteiro em `:244`, a linha que de fato nomeia a função e diz "6 de 7" |
| 3 | Citação do contexto da campanha gh104 | `CONTEXTO.md:147` (só a célula "não morde" da tabela) | `:159-161`, onde o preço está declarado |
| 4 | Bloco de contagem de alvos da §7 | tinha `<scratch>` literal no classpath e apontava para a §5 de outro documento | roda: aponta para a §8.1 do handoff correto, e o resultado foi **reexecutado** — 120/68/22 e 119/67/22 |
| 5 | Pendência dos logs das sondas | "copiar de `/tmp`" — os dois arquivos **não existem mais** | registro da perda, com a lista do que sobrevive em `data/gh105/evidence/reach-probe/` |
| 6 | Sítios de `--sdkpath` a corrigir | três | **quatro** — o próprio relatório de origem reproduz a nota errada |
| 7 | Defeito documental não listado | — | `docs/architecture/static-analysis.md:85` afirma uma validação que `validate_on_init=False` impede de rodar |
| 8 | "três deles somam menos de dez linhas" | otimista com um item pesado dentro | dois somam quatro linhas; o terceiro é um parâmetro, uma guarda e dois chamadores |

### Decisão do pesquisador, já tomada — **não reabrir**

Houve uma discussão sobre trilha: como a especificação nunca escreveu que a análise estática deve
seguir o conjunto escolhido, alguém pode ler o reparo do denominador como comportamento novo, o que
pediria trilha maior. **O pesquisador decidiu: uma change só, Quick Path.** A tabela de alternativas
que eu tinha acrescentado foi **removida** por ser drama. O que restou é um parágrafo curto que
responde a objeção — o acoplamento já existe de fato, com o valor errado; o reparo faz o código
parar de contradizer a decisão 7, que já manda um conjunto por experimento.

Continua de pé, porque é factual e curto: **se** ficar decidido *remover* o default em vez de só
passar o valor certo, aí muda o comportamento de todo chamador standalone e a trilha escala.

---

## Próximo passo: a auditoria que esta sessão deve fazer

**Missão**: análise rigorosa de consistência do que vai virar a change — **e triagem de necessidade.**

O pesquisador foi explícito: *"eh pouca coisa … descartamos ja a maioria do seu drama … e ainda nao
tenho certeza se tudo que esta ai vai entrar"*. Portanto a auditoria tem **duas** perguntas, e a
segunda é a que importa mais.

### Pergunta 1 — consistência

Para cada item ainda no plano, e para cada linha da §8:

1. A citação `arquivo:linha` existe e **contém** o que o texto diz que ela contém? (Foi exatamente
   aqui que a revisão 3 escorregou duas vezes.)
2. O comando da §7 roda como está escrito, sem placeholder e sem dependência não declarada?
3. A instrução prescrita é **executável hoje**? (A dos logs das sondas não era.)
4. O texto contradiz outro trecho do próprio plano?

### Pergunta 2 — necessidade, ou drama

Para **cada** item, incluindo os quatro reparos, responda com veredito explícito:

| Critério | Pergunta a fazer |
|---|---|
| **Dano** | Existe dano medido em artefato real, ou só dano possível? Qual a frequência real observada? |
| **Guarda** | Existe invariante, spec ou guarda que **já** cobre isto? (Foi essa pergunta que matou 15 de 24 alegações. É obrigatória.) |
| **Consumidor** | Alguém **lê** o que este reparo conserta? Um campo sem leitor conserta observabilidade, não comportamento. |
| **Custo do não-reparo** | Se ficar como está, o que quebra, quando, e para quem? |
| **P1 do CLAUDE.md** | O reparo é complexidade mínima, ou é validação para cenário impossível / helper para operação única? |

Critérios de drama, neste projeto: item sem dano demonstrado; validação defensiva para cenário que
não tem como acontecer; correção documental que ninguém vai ler; abstração criada para um único
chamador; e **qualquer coisa que o plano descreva em três parágrafos e o código resolva em uma
linha**.

Suspeitos declarados de antemão, para você examinar sem constrangimento — a lista abaixo é o
**ponto de partida da triagem**, não um veredito:

- **A §8 inteira.** São oito linhas de pendência documental. Duas editam artefatos **arquivados**,
  o que altera registro histórico; uma delas fecha uma issue no GitHub, que não é edição de arquivo.
  Pergunte item a item se vale carregá-las dentro de uma change de código.
- **A faxina (`G2`–`G5`)**. O próprio plano admite que um deles "muda a linha de log e um campo sem
  leitor: é observabilidade pura". Isso é reparo ou é ruído?
- **O parâmetro morto**. Três linhas. Vale abrir tarefa?
- **`G4`** — caminho legado do `sdkmanager` que funciona hoje por causa de um symlink no Dockerfile.
  Consertar o caminho remove o symlink, ou só adiciona um segundo jeito de funcionar?
- **A parte B do reparo do SDK.** O plano propõe *duas* camadas (fallback no lançador **e** emitir o
  flag no config). A parte A cobre mais portas de entrada por três linhas e zero testes; a parte B
  custa asserções de argv. Duas camadas para o mesmo defeito é robustez ou é redundância?

Entregue: veredito por item (**entra** / **fica de fora** / **vira issue separada**), com a razão em
uma frase e o número que a sustenta. Não peça decisão sobre item que a evidência já resolve.

### Depois da triagem — e só depois

Com o escopo cortado, aí sim: abrir a issue no GitHub, criar a change pelo workflow, e implementar.
Não faça isso nesta sessão sem o de-acordo do pesquisador sobre o escopo final.

---

## REGRA NÃO NEGOCIÁVEL DE WORKFLOW

Seguir `docs/WORKFLOW.md` rigorosamente. **NUNCA** escrever ou reescrever artefatos OpenSpec com
`Write`/`Edit` — invocar as skills (`openspec-new-change`, `openspec-apply-change`,
`openspec-update-change`) pela ferramenta `Skill`. A única edição manual permitida em `tasks.md` é
marcar `- [ ]` → `- [x]` ao concluir cada tarefa.

Trilha desta change: **Quick Path**, schema `quick-path`, 3 fases, artefatos `plan` → `tasks`,
arquiva com `openspec archive "gh<N>-nome" --skip-specs` (não há delta spec para sincronizar).
Guia de decisão em `docs/WORKFLOW.md` §3 (linhas 150-196); o passo a passo da trilha em §8 (:567).

Convenção de nome do diretório: `gh<N>-<nome-curto>`, minúsculas, sem prefixo de data.
`proposal.md`/`plan.md` levam `GitHub Issue: #N`; commits usam `refs #N` e `closes #N` no final.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes — explicam *por quê*.

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente, em nenhum contexto.

**Decisões de projeto vão ao pesquisador antes de editar**, em opções com recomendação **e
medição**. Se a medição mata uma opção, apresente a opção morta com o número que a matou.

---

## Como falar com este pesquisador

Aprendido nesta sessão, e vale mais que qualquer checklist técnica:

1. **Trate por "você"**, nunca "o senhor".
2. **Português com acentuação correta**, sempre — o pesquisador omite acentos, você não.
3. **Nada de apelido sem tradução.** Ele disse, literalmente: *"voce acha que vou lembrar o que eh
   d2, z6, xxx??"*. Quando explicar, use o nome real do problema. Os apelidos servem para indexar
   o documento, não para conversar.
4. **Corte o drama antes de ele cortar.** Ele já removeu a maior parte das alegações e removeu uma
   tabela de alternativas que eu tinha acrescentado. Se você está escrevendo o terceiro parágrafo
   sobre um reparo de uma linha, pare.
5. **Recomendação, não survey.** Uma opção primeiro, com o número que a sustenta.

---

## Aprendizados que valem carregar

1. **A pergunta que mata alegação**: *"existe invariante, spec ou guarda que já cobre isto?"*.
   Quinze das vinte e quatro alegações morreram por não ter sido feita antes de chamar algo de
   defeito. **É obrigatória para qualquer achado novo neste sistema.**
2. **Citação não é prova — o intervalo tem que conter a frase.** Duas citações da revisão 3
   apontavam para trechos vizinhos ao que sustentava o argumento. O argumento sobrevivia; o
   ponteiro não. Sempre abra o arquivo na linha citada.
3. **Comentário mente.** Um comentário no cliente de análise afirma exatamente o oposto do que o
   código faz. Uma doc de arquitetura afirma uma validação que uma flag desliga. Leia o código, não
   o comentário.
4. **Reproduza, não confie no registrado.** Todas as quatro reproduções foram reexecutadas nesta
   sessão e todas conferiram — mas uma delas *não rodava* como estava escrita, e um dos números
   nunca tinha sido reverificado.
5. **Instrução prescrita envelhece.** A pendência dos logs mandava copiar arquivos de `/tmp` que
   já tinham sido apagados. Antes de prescrever, confira que o alvo ainda existe.
6. **Uma assinatura, várias causas.** O sintoma "arquivo de cobertura só com cabeçalho" já tem
   **pelo menos três** causas distintas conhecidas. Um diagnóstico futuro não pode assumir a causa.

---

## Arquivos relacionados

### Leitura obrigatória, nesta ordem

| Arquivo | Papel |
|---|---|
| `docs/20260821_plano_correcao_analise_estatica.md` | **o objeto da auditoria** (revisão 4) |
| `docs/WORKFLOW.md` §3 (seleção de trilha, linha 150) e §8 (Quick Path, linha 567) | trilha, fases, arquivamento |
| `CLAUDE.md` (raiz do `rv-android`) | princípios P1–P4, regras de commit e emulador |

### Contexto, se precisar

| Arquivo | Papel |
|---|---|
| `docs/20260821_relatorio_analise_estatica_defeitos.md` | relatório de origem; **contém erros já catalogados** na §8 do plano |
| `backup/20260821_plano_correcao_analise_estatica.v1.md` | revisão 1, com a tabela integral das onze refutações originais |
| `backup/20260821_plano_correcao_analise_estatica.v3.md` | revisão 3, para ver o que a revisão 4 mudou (`diff -u`) |
| `docs/20260821_verificacao_relatorio_analise_estatica.md` | **superseded** pelo plano; não derivar dele |
| `docs/20260821_handoff_gh69_coringas.md` §8.1 | o instrumento `Count.java` que mede alvos por conjunto |
| `docs/architecture/static-analysis.md` | arquitetura do subsistema; §3, §4 e §7 são citadas pelo plano |
| `experimento-gh104/CONTEXTO.md` §B4 e linhas 159-161 | por que o reparo do denominador **não** muda a campanha gh104 |

### Precedentes de trilha (verificados: só `plan.md` + `tasks.md`, zero toques em `openspec/specs/`)

- `openspec/changes/archive/2026-07-22-gh86-dexlib2-apk-paths-contract/`
- `openspec/changes/archive/2026-05-25-gh59-fix-wide-slot-binding/`

---

## Comandos — todos reexecutados em 2026-08-21 e conferindo

### O marcador de "análise completa" que mente

```bash
python3 - <<'EOF'
import json, glob, os
D = "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg"
for p in glob.glob(os.path.join(D, "_progress", "*.json")):
    d = json.load(open(p))
    if not d.get("timed_out"): continue
    name = os.path.basename(p)   # o registro e o artefato tem o MESMO nome
    hits = [h for h in glob.glob(os.path.join(D, "**", name), recursive=True) if "_progress" not in h]
    if hits:
        a = json.load(open(hits[0]))
        print(name, "complete=", a.get("complete"), "reach=", len(a.get("reachability", [])),
              "trans=", len(a.get("transitions", [])), "rc=", d.get("returncode"))
EOF
# esperado: 5 APKs, todos complete=True, trans=0, rc=206
```

### A precedência real dos argumentos do lançador do GATOR

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/lib/gator
env -u ANDROID_SDK_HOME python3 ./gator a --sdkpath /tmp/fake -p x.apk --out /tmp/o.json
#   -> KeyError: 'ANDROID_SDK_HOME'  (o flag NAO existe; foi engolido em silencio)
env -u ANDROID_SDK_HOME python3 ./gator a --sdk /tmp/fake -p x.apk --out /tmp/o.json
#   -> passa da resolucao do SDK e morre adiante por outro motivo
```

### O tamanho dos conjuntos de especificações

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources
for d in jca jca_android generic; do echo "$d: $(ls $d/*.mop | wc -l) specs"; done
# jca: 23 / jca_android: 23 / generic: 118
```

### Contagem de alvos por conjunto

Compile o `Count.java` pelo bloco de `docs/20260821_handoff_gh69_coringas.md` §8.1 primeiro — só a
linha do `java` não roda sem a classe compilada. Resultado esperado, medido duas vezes:
`jca signatures=120 pairs=68 owners=22` e `jca_android signatures=119 pairs=67 owners=22`.

### Build do reator Java (só se o reparo do marcador entrar)

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
mvn clean install -DskipMopAgent -DskipTests
```
Use caminhos `/home/pedro/...`; o alias `/pedro/...` **não abre** na JVM.

### Testes Python (contrato de CI, obrigatório)

```bash
cd <modulo> && uv run pytest --import-mode=importlib -o "addopts=" tests/
```

---

## Restrições de contexto

- A **campanha gh104 está em preparação**. O reparo do denominador é seguro de aterrissar antes
  dela, porque naquela campanha a análise estática não roda — os artefatos são reusados. Está
  declarado em `experimento-gh104/CONTEXTO.md` §B4.
- Um dos reparos tem **raio maior que o tamanho**: fazer a linha de comando devolver código de saída
  ≠ 0 é uma linha, mas os dois entrypoints Docker executam essa linha de comando diretamente, de
  modo que o código de saída do container passa a refletir falha parcial. O critério de aceitação
  precisa verificar que nenhum orquestrador de campanha trata container ≠ 0 como fatal ou como
  gatilho de re-run. **Isto é do escopo da triagem: pode ser motivo para o item sair.**
- A change **gh105** está em andamento no mesmo branch (`modules`), em 33/74 tarefas. **Não tocar.**
