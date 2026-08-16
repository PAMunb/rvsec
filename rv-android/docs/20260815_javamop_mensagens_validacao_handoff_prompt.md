# Handoff — validação rigorosa da linhagem de documentos sobre mensagens JavaMOP

**Data de escrita:** 2026-08-15
**Uso:** cole este arquivo inteiro como primeira mensagem da nova sessão.
**Estado:** nada implementado, nada commitado. Cinco artefatos novos, todos untracked.
**Objetivo desta sessão:** validar rigorosamente a linhagem inteira — está tudo consistente entre os
documentos? deixamos passar alguma sugestão que melhore o sistema?

---

## 0. Instruções operacionais (leia primeiro)

1. **Use subagentes com recortes disjuntos**, despachados em paralelo num único bloco de chamadas.
   O trabalho é largo e paralelizável (consistência intra-documento / consistência entre documentos /
   itens ausentes como candidatos a melhoria / conformidade de processo OpenSpec / verificação de
   números contra os artefatos).
2. **LEITURA INTEGRAL, NÃO AMOSTRAGEM.** Este é o aprendizado mais caro das duas sessões anteriores.
   Instrua cada subagente a ler os arquivos **de ponta a ponta** com a ferramenta Read em blocos
   sequenciais, cobrindo 100% do arquivo, e proíba explicitamente "grep para amostrar". Na sessão
   anterior, uma conclusão baseada em amostragem produziu uma acusação falsa que só caiu quando os
   quatro relatórios foram lidos inteiros. Use grep apenas para *confirmar* ausência, nunca para
   estabelecer presença ou contagem.
3. **Verifique os subagentes — inclusive o denominador.** Na sessão anterior, três conclusões de
   agente foram descartadas por medição direta, e **duas afirmações do próprio orquestrador caíram
   por denominador não verificado**. Verificar uma contagem exige verificar o universo sobre o qual
   ela é feita, não só o valor contado.
4. **Siga `docs/WORKFLOW.md` rigorosamente.** Regra não-negociável do `CLAUDE.md`: para qualquer
   mudança sob `openspec/changes/gh<N>-*/`, os artefatos OpenSpec são criados **exclusivamente** via
   as skills (`Skill` tool: `openspec-new-change`, `openspec-continue-change`, `openspec-propose`,
   `openspec-apply-change`, `openspec-verify-change`, `openspec-archive-change`). **Nunca** use
   `Write`/`Edit` direto para criar ou reescrever `proposal.md`, `design.md`, `tasks.md` ou delta
   specs. Esta sessão é de validação — não deve criar nenhuma change, mas se a validação levar a
   isso, é por skill.
5. **Princípios P1–P4 valem para tudo** (simplicidade; documentação narrativa que explica o *porquê*;
   sem retrocompatibilidade — código superado é deletado, com backup em `backup/`; comentários
   descrevem o estado atual, sem histórico de migração).
6. **Nunca gerencie emulador à mão.** Validação em device só via `rv-experiment run` / `rv-platform run`.
7. **"MOP" = monitored operations.** Nunca use terminologia de "segurança" para MOP.
8. **Português com acentuação correta** quando escrever em português.
9. **Sem `Co-Authored-By`** em mensagens de commit.

---

## 1. O que estamos fazendo

Os relatórios de violação do RVSEC são ilegíveis: no dataset de referência, **72,93 %** dos 97.018
registros carregam o literal `unknown`, e existem apenas **19 mensagens distintas**. O ensaio
pós-reparo do Estudo 03 (`experimento-comp162`, `jca` congelado + weaver gh100) é **pior**:
**79,91 %** (15.714 de 19.664), com **16** mensagens distintas.

Existe uma linhagem de onze documentos que vai de um plano inicial até um documento de design que se
propõe a ser o insumo de Fase 0 do workflow OpenSpec — `docs/20260815_javamop_mensagens_FINAL.md`
(521 linhas), que propõe oito mudanças (C-0, C-1a, C-1, C-V, C-2, C-3, C-4, C-5), nove decisões de
pesquisador (D-A..D-I), oito gates formais (G-1..G-8) e nove opções em aberto (O-1..O-9).

Duas sessões adversariais já rodaram sobre ele. **Esta terceira sessão é de validação da linhagem
inteira, incluindo os artefatos que as duas anteriores produziram.**

---

## 2. O que foi feito

### 2.1 Sessão 1 — análise adversarial do documento alvo

Produziu `docs/20260815_javamop_mensagens_FINAL_analise.md` (645 linhas). Achado principal: rodando o
**próprio gate G-2 do documento** (`INV-INS-110`) sobre as tabelas dos monitores compilados, o `jca`
congelado tem **18 eventos órfãos em 10 de 23 specs**; `jca_android` pós-gh101 tem **0**. Identificou
defeitos bloqueantes de design (`st=` inimplementável; três caminhos com mensagem confiantemente
errada; gramática de §7.1 auto-contraditória; identidade de dedup que anula o objetivo da mudança).

### 2.2 Sessão 2 — fechamento das lacunas e decisões

Produziu `docs/20260815_javamop_mensagens_FINAL_analise_lacunas.md` (818 linhas) e
**`docs/20260815_javamop_extracao/`** (quatro arquivos, 1.269 linhas).

**As três lacunas registradas pela sessão 1 foram fechadas** (a de device permanece aberta por
decisão):

- **§4 contra os quatro originais.** Fechada por **leitura integral** dos quatro relatórios (751 +
  480 + 286 + 237 linhas) e do `FINAL.md`, com casamento item a item. Resultado: **581 itens**;
  **450 carregados (77,5 %)**, **70 parciais (12,0 %)**, **61 ausentes (10,5 %)**. A alegação
  `"without filtering"` de `FINAL:25` é falsa, mas a perda é limitada e **enviesada**: some o que a
  validação externa mediu por conta própria, sobrevive o que ela corrigiu. **As listas de extração —
  o artefato que nunca existiu e cuja falta era a raiz do problema — agora existem.**
- **Limite do logcat.** `LOGGER_ENTRY_MAX_PAYLOAD = 4068 B` para API ≥ 24 (o projeto roda API 30),
  verificado em quatro tags do AOSP. A conta `4076 − 1 − 6 − 1` do documento parte do limite do
  Android ≤ 5.1 e conta a subtração duas vezes; o orçamento real de `msg` é **4060 B**. O corte é
  silencioso, na cauda, feito pela `liblog` — e `msg=` é o último campo do envelope. Envelope medido
  sobre 97.018 violações: mediana 274 B, máximo **696 B = 17,1 %** do limite. **Não é risco.**
  Resolve a metade "verificar limite" da claim **GAMA-SET-05** da auditoria, que estava INCONCLUSIVA.
- **Matriz de consumidores.** A §7.3 lista 10; existem **≥ 78 sítios em ~55 arquivos**. E há **três**
  formatos de `errors.csv` vivos (730 arquivos com 10 colunas, 54 com 11, e um de 12 sem `message`).
  **Executado:** `read_errors_csv` do `aperv-tool` **falha hoje** contra o dataset do artigo publicado.

**Seis achados que nenhum documento anterior contém:**

1. **30,5 % do volume mudo é registro que não deveria existir** (4.788 de 15.714), em duas classes de
   gêmeos: 3.950 linhas em sítios onde o mesmo defeito já é reportado legivelmente (101 sítios, 98
   deles com razão exatamente 1:1, e o total iguala o total de linhas legíveis do corpus), e 838 em
   `IvParameterSpecSpec`, onde o mesmo sítio emite dois mudos de `ErrorType` diferentes.
2. **A regra de reparo de C-1a, como escrita, apagaria 66,6 % das linhas legíveis.** Dos 114
   after-advices com `call()` no `jca`, **16 têm `call()` com parâmetros e nenhum `args()`** — entre
   eles `SSLContextSpec.init` (1.466 linhas legíveis) e `MessageDigestSpec.update` (1.163).
3. **`INV-INS-109` e `INV-INS-110` estão definidos duas vezes**, com significados incompatíveis, em
   gh100 e gh101 — ambas ativas. G-2 e §7.4 citam "INV-INS-110" no sentido gh101. Primeiro ID livre:
   **INV-INS-116**.
4. **A auditoria nunca cobriu o `jca`** (`audit/.../fase0/pre_registro.md:10` delimita o escopo a
   `jca_android`).
5. **As corridas finais do Estudo 03 não começaram** (`experimento-comp162/README.md:3`: *"Isto não é
   o experimento final do Estudo 03. É um ensaio"*).
6. **Existe medição pareada AspectJ × dexlib2 em árvore** e nenhum documento a cita:
   `experimento-comp162-ajc/consolidado/mop_diff_ajc_x_dexlib2.csv`, 115 linhas, **63 `ambos`,
   46 `so_dexlib2`, 6 `so_ajc`**.

### 2.3 As quatro decisões do pesquisador — TOMADAS, são vinculantes

| Decisão | Escolha | Consequência registrada |
|---|---|---|
| **D-A** | **(ii)** — conjunto sucessor `jca_v2` derivado do `jca` congelado. **Não mexer em `jca_android`.** | `jca_v2` = `jca` + lista de reparos nomeados (não convergir para `jca_android`). Como não herda cobertura de auditoria, **C-V passa de paralela a pré-requisito duro de C-4**. |
| **`st=`** | **Sai do contrato.** | Envelope fica `v=1 code=… ev=… obj=… val='…' exp='…' msg='…'`. **O-1 deixa de ser pré-requisito de C-3.** |
| **D-C** | **Landar agora, com a regra corrigida.** | Três cláusulas: ausência de `args()` = não filtrar; comprimento de `ArgsPC.types()`; filtro em `WrapperEmitter.java:270-273`. Fechar antes as tarefas 7.4–7.6 da gh100. |
| **Ordem** | **Corrigir o documento antes de abrir issues.** | Lista de 11 correções ordenadas em §7.1 do `_lacunas.md`. |

**Decisão ainda pendente: D-B (oráculo).** Ficou mais urgente porque `jca_v2` deriva do `jca`, cuja
âncora é CrySL 1.5.2, não a api30. Evidência que dá consequência a ela e que estava perdida na
compressão: **5.891 de 6.048 linhas de `UnsafeAlgorithm` nomeiam algoritmos que a api30 não proíbe —
97 % da categoria desapareceria sob aquele oráculo.**

### 2.4 Três retratações da sessão 2 (registre-as; não as repita)

1. **"111 dos 225 IDs do §4 não podem ter referente"** — **falso**. Denominador contado em três
   blocos por relatório (116 itens) quando a leitura integral encontra **581**. Nenhum ID alto é
   fantasma.
2. **"O falso negativo do `KeyGeneratorSpec` desapareceu"** — **falso**. Sobrevive como o token opaco
   `D11` (`FINAL:359`); `D11` no plano (`20260815_javamop_mensagens.md:923`) **é** esse defeito. O
   problema real é mais estreito: chega ilegível e é atribuído via `c-C34` com status `U` e a glosa
   *"audit items cited by neither doc"*, quando o gemini o citou por inspeção direta.
3. **A decomposição de gêmeos estava incompleta** — pareava só muda × legível, perdendo a família
   muda × muda. Subiu de 25,1 % para 30,5 %.

E uma correção à sessão 1: **"8.371 `found .`" conta o fenômeno errado.** São **8.843** linhas
terminando em `but found .`, em cinco specs (TMF 8.371, Signature 234, MessageDigest 156, SSLContext
51, Mac 31). A colisão de wrapper que F11 usa para explicar cobre a fatia de **uma** spec.

---

## 3. O que esta sessão deve fazer

O objetivo é **validação rigorosa**, em duas frentes.

### 3.1 Frente A — consistência

Verificar se a linhagem é internamente coerente e se os documentos concordam entre si. Recortes
sugeridos para subagentes (todos exigindo **leitura integral** dos arquivos em escopo):

1. **Consistência interna do `_lacunas.md`** (818 linhas, o documento novo). Ele foi editado quatro
   vezes durante a sessão 2 — §1, §2.1, §3.1, §5, §6, §7.1 e §9 sofreram reescritas. Procure:
   números que ficaram desatualizados após as correções (especialmente 25,1 % → 30,5 %, 116 → 581,
   3.950 → 4.788); referências cruzadas `§X` que apontam para seção errada; itens de §7.1
   renumerados cujo texto ainda cita a numeração antiga; afirmações em §6 que contradizem §2.1
   depois das retratações.
2. **Consistência entre `_lacunas.md` e `_analise.md`** (a análise da sessão 1). A sessão 2 corrigiu
   quatro afirmações da sessão 1 (o efeito colateral de `SecureRandom` em §4.4c é empiricamente
   vazio; "50 sítios com dois status" não se sustenta; a folga de truncamento subestimava o payload;
   "8.371 `found .`" conta o fenômeno errado). Verifique se há **outras** afirmações da sessão 1 que
   as medições da sessão 2 tornam falsas e que ninguém retratou.
3. **Consistência entre os dois documentos de análise e o `FINAL.md`.** As 11 correções de §7.1 do
   `_lacunas.md` cobrem tudo que as duas análises acharam? Alguma recomendação da sessão 1 (as 10 de
   §7) ficou órfã, sem correspondente em §7.1 da sessão 2?
4. **Consistência das listas de extração** (`docs/20260815_javamop_extracao/`, 1.269 linhas em quatro
   arquivos). Elas foram produzidas por quatro agentes independentes com formatos ligeiramente
   diferentes. Verifique: os totais batem com os declarados (581/450/70/61)? Há item marcado
   AUSENTE numa lista que na verdade aparece no `FINAL.md`? Há duplicação entre listas (o mesmo fato
   medido por dois relatórios contado duas vezes)?
5. **Consistência dos números contra os artefatos.** Reexecute os comandos de §5 abaixo e confira
   cada número citado nos três documentos de análise contra a medição. Não aceite número não medido.

### 3.2 Frente B — deixamos passar alguma sugestão que melhore o sistema?

Esta é a pergunta mais valiosa e a mais fácil de tratar mal. Duas fontes concretas:

1. **Os 61 itens AUSENTES e os 70 PARCIAIS**, listados em detalhe nos quatro arquivos de
   `docs/20260815_javamop_extracao/`. A sessão 2 destacou **doze** ausências que mudam trabalho
   (§2.1 do `_lacunas.md`). **As outras 49 ausências e as 70 perdas parciais nunca foram trabalhadas
   uma a uma.** Cada uma é candidata a: (a) melhoria real do sistema que ninguém agendou; (b) item
   que pertence a alguma mudança C-* e não está no escopo dela; (c) ruído legitimamente descartado.
   Classifique **todas**, com justificativa por item.
2. **As nove opções em aberto (O-1..O-9) do `FINAL.md` §9** e as propostas classificadas como
   "option" no §4.3. Com as decisões de §2.3 tomadas, alguns gatilhos mudaram: `st=` saiu do
   contrato, então **O-1 deixou de ser pré-requisito de C-3** — isso o torna menos ou mais atrativo?
   D-A = (ii) significa conjunto sucessor escrito a partir do `jca`, o que **satisfaz o gatilho
   declarado de O-3** (`fsm:` `default -> S`, cujo gatilho é "um conjunto sucessor escrito do zero").

Além disso, procure ativamente por melhorias que **nenhum** documento da linhagem propõe. Pistas
concretas já levantadas e não agendadas por nenhuma mudança C-*:

- O precedente interno de `jca/MessageDigestSpec.mop:48-51` — os autores já corrigiram **uma**
  instância do mecanismo dos sítios gêmeos e documentaram o padrão no conjunto congelado. Isso é
  método de reparo pronto para as outras instâncias, e nenhum documento o cita.
- `jca/PBEKeySpecSpec.mop:48-50` testa `iterationCount < 10000` e a mensagem diz *"should be >= 1000"*
  — contradiz a própria checagem por fator de 10, e a mensagem aparece **52 vezes** no comp162.
  `jca/PBEParameterSpecSpec.mop:49` tem a mesma mentira e ainda usa `ErrorType.UnsafeAlgorithm` para
  uma restrição de parâmetro. São defeitos **de mensagem** — o assunto do documento — e a §7.1 não
  os discute.
- `jca/CipherSpec.mop:72` lê `Property.GENERATED_PRIVATE_KEY`, que **nenhuma spec do conjunto
  escreve**. Aresta morta do grafo de predicados.
- `rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java:39-40` tem a chamada de escape
  **comentada**; o coletor CSV, três linhas abaixo, a aplica. Um `\n` no valor quebra a linha em duas.
- **9 das 23 specs do `jca` emitem zero linhas** no comp162 (`CipherInputStreamSpec`,
  `CipherOutputStreamSpec`, `DHGenParameterSpecSpec`, `GCMParameterSpecSpec`, `HMACParameterSpecSpec`,
  `KeyGeneratorSpec`, `PBEParameterSpecSpec`, `RandomStringPasswordSpec`, `SecretKeySpec`). Emissão
  zero é sintoma — de falso negativo, de pointcut morto, ou de ausência legítima no corpus. Ninguém
  separou os três casos.

### 3.3 O que esta sessão NÃO deve fazer

- **Não implementar nenhuma mudança C-\*.** As decisões estão tomadas mas o documento alvo ainda não
  foi corrigido, e a correção é o passo anterior à abertura de issues.
- **Não abrir issues nem criar changes OpenSpec.** Há três bloqueios de processo pendentes (§7.2 do
  `_lacunas.md`): a colisão `INV-INS-109/110`, quatro pares track/template contraditórios na §8, e a
  capability `aperv` nunca marcada.
- **Não editar `jca_android`.** Decisão D-A.
- **Não rodar experimento em device.**

---

## 4. Arquivos relacionados

### 4.1 Produzidos pelas sessões anteriores (nenhum commitado)

| Arquivo | Papel | Linhas |
|---|---|---|
| `docs/20260815_javamop_mensagens_FINAL_analise.md` | análise adversarial da sessão 1 | 645 |
| `docs/20260815_javamop_mensagens_FINAL_analise_handoff_prompt.md` | handoff da sessão 1 → 2 | 308 |
| `docs/20260815_javamop_mensagens_FINAL_analise_lacunas.md` | **fechamento de lacunas + decisões, sessão 2** | 818 |
| `docs/20260815_javamop_extracao/claude_fable5.md` | lista de extração, 193 itens | 509 |
| `docs/20260815_javamop_extracao/gpt5_codex.md` | lista de extração, 202 itens | 423 |
| `docs/20260815_javamop_extracao/deepseek_v4_flash.md` | lista de extração, 113 itens | 169 |
| `docs/20260815_javamop_extracao/gemini36flash.md` | lista de extração, 73 itens | 168 |
| `docs/20260815_javamop_mensagens_validacao_handoff_prompt.md` | **este arquivo** | — |

### 4.2 Linhagem original (todos em `rv-android/docs/`)

| Arquivo | Papel | Prefixo no §4 |
|---|---|---|
| `20260815_javamop_mensagens_FINAL.md` | **o documento de design** (521 l.) | — |
| `20260815_javamop_mensagens.md` | o plano (L1–L8, WS-1..8, D-1..8, D01–D50) (982 l.) | — |
| `20260815_javamop_mensagens_analise.md` | revisão adversarial do plano (797 l.) | `R` |
| `20260815_javamop_mensagens_analise_handoff_prompt.md` | brief da revisão adversarial | — |
| `20260815_javamop_mensagens_validacao_prompt.md` | brief dado aos quatro LLMs | — |
| `20260815_javamop_mensagens_claude_fable5.md` | validação externa 1 (751 l.) | `c-` |
| `20260815_javamop_mensagens_deepseek_v4_flash.md` | validação externa 2 (237 l.) | `d-` |
| `20260815_javamop_mensagens_gemini36flash.md` | validação externa 3 (286 l.) | `g-` |
| `20260815_javamop_mensagens_gpt5_codex.md` | validação externa 4 (480 l.) | `x-` |

### 4.3 Fontes de evidência

- **Datasets:** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv`
  (97.018 linhas, **10 colunas**, sem `source`); `rv-android/experimento-comp162/results/*/*/errors.csv`
  (8 arquivos, 19.664 linhas, **11 colunas**);
  `rv-android/experimento-comp162-ajc/consolidado/mop_diff_ajc_x_dexlib2.csv` (pareado AspectJ×dexlib2)
- **Oráculos de monitor gerado:** `rv-android/results/{gh56-smoke,gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control}/monitors/`
- **Specs:** `rvsec/rvsec-mop/src/main/resources/{jca,jca_android}/` (23 `.mop` cada;
  `generic` 118; `generic_new` 27, ausente do `click.Choice` da CLI)
- **CrySL 1.5.2:** `/home/pedro/.../workspace-rv/Crypto-API-Rules/JavaCryptographicArchitecture/src/`
- **MetaCrySL api30:** `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/`
- **Gerador:** `rv-monitor/`, `javamop/` · **Weaver:** `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`
- **Runtime:** `rvsec/rvsec-core/`, `rvsec/rvsec-logger-csv/`, `rvsec/rvsec-android/rvsec-logger-logcat/`
- **Auditoria:** `audit/20260808_validacao_jca_android/` (`fase0/pre_registro.md` §7 = conjunção READY
  e escopo; `global/juizglobal_relatorio.md` §10 = veredito REPROVADA 22/22; `pilot/` = GAMA-SET-05)
- **Trabalho anterior:** `openspec/changes/gh10{0,1,2}-*/` (ativas), `archive/…gh103-*`, `data/gh101/README.md`

---

## 5. Comandos úteis (reproduzem as medições)

Todos somente-leitura. Rode a partir de `rv-android/`.

**Números do dataset de referência:**
```bash
python3 -c "
import csv,collections
r=list(csv.DictReader(open('/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv')))
c=collections.Counter((x.get('message') or '').strip() for x in r)
print(len(r),'linhas |',len(c),'mensagens |',c['unknown'],'unknown =',round(100*c['unknown']/len(r),2),'%')
print('terminando em \"but found .\":',sum(n for m,n in c.items() if m.endswith('but found .')))
"
```

**Decomposição do comp162 e as duas classes de gêmeos (o orçamento residual):**
```bash
python3 -c "
import csv,glob,collections
rows=[]
for f in sorted(glob.glob('experimento-comp162/results/*/*/errors.csv')): rows+=list(csv.DictReader(open(f)))
def et(r):
    p=(r.get('unique_msg') or '').split(':::'); return p[3] if len(p)>3 else '?'
mute=lambda r:(r.get('message') or '').strip()=='unknown'
site=lambda r:(r['spec'],r['class'],r['method'],r['source'])
m=collections.Counter(site(r) for r in rows if mute(r)); l=collections.Counter(site(r) for r in rows if not mute(r))
print(len(rows),'linhas |',sum(m.values()),'mudas |',len(m),'sitios')
print('gemeas muda-legivel:',sum(m[s] for s in m if s in l),'em',len([s for s in m if s in l]),'sitios')
per=collections.defaultdict(collections.Counter)
for r in rows:
    if mute(r): per[site(r)][et(r)]+=1
mm=[(s,c) for s,c in per.items() if len(c)>1 and min(c.values())==max(c.values())]
print('gemeas muda-muda  :',sum(sum(c.values()) for s,c in mm),'em',len(mm),'sitios')
"
```

**Censo de eventos órfãos (o gate G-2 do documento) sobre qualquer monitor gerado:**
```bash
python3 -c "
import re,collections,sys
f=sys.argv[1]; cur=None; res=collections.defaultdict(dict)
for l in open(f):
    m=re.match(r'\s*(?:final )?class (\w+SpecMonitor) extends', l)
    if m: cur=m.group(1)
    m2=re.match(r'\s*static final int Prop_\d+_transition_(\w+)\[\] = \{([0-9, ]+)\};', l)
    if m2 and cur: res[cur][m2.group(1)]=[int(x) for x in m2.group(2).split(',')]
bad=[(mon,ev,row) for mon,tbl in sorted(res.items()) for ev,row in tbl.items()
     if all(v==max(max(r) for r in tbl.values()) for v in row)]
print(len(res),'monitores |',len(bad),'eventos orfaos em',len(set(b[0] for b in bad)),'specs')
[print('  ',*b) for b in bad]
" results/gh56-smoke/monitors/MultiSpec_1RuntimeMonitor.java
```

**Advices sem cláusula `args()` (o que a regra ingênua de C-1a derrubaria):**
```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources
python3 - <<'EOF'
import re,glob
noargs=[]
for f in sorted(glob.glob('jca/*.mop')):
    src=open(f).read()
    for m in re.finditer(r'event\s+(\w+)\s+(after|before)\s*\(', src):
        if m.group(2)!='after': continue
        i=m.end(); d=1; j=i
        while d>0 and j<len(src):
            if src[j]=='(': d+=1
            elif src[j]==')': d-=1
            j+=1
        pc=src[j:src.find('{',j)]
        if 'call(' not in pc: continue
        cm=re.search(r'call\([^)]*\(([^)]*)\)', pc)
        params=cm.group(1).strip() if cm else ''
        if not re.search(r'\bargs\s*\(', pc) and params: noargs.append((f,m.group(1),params))
print(len(noargs),'advices com call() parametrizado e SEM args():')
for f,n,p in noargs: print(f'   {f:34s} {n:12s} ({p})')
EOF
```

**Divergência entre os dois conjuntos de specs (19/23, 882 linhas):**
```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources
tot=0; for f in jca/*.mop; do b=$(basename $f); n=$(diff "$f" "jca_android/$b" 2>/dev/null | grep -c '^[<>]'); \
  tot=$((tot+n)); [ "$n" != "0" ] && printf "%-32s %4d\n" "$b" "$n"; done; echo "total: $tot"
```

**Colisão de invariantes entre gh100 e gh101:**
```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
grep -oE "INV-INS-[0-9]+" openspec/specs/instrumentation/spec.md | sort -u -V | tail -3
grep -nE "INV-INS-1(09|10|15)" openspec/changes/gh10{0,1}-*/specs/instrumentation/spec.md | cut -c1-120
```

**`read_errors_csv` contra os dois datasets (o teste que falha hoje):**
```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
uv run python -c "
from aperv_tool.analysis.violations import read_errors_csv, ERRORS_CSV_HEADER
print('header esperado:',len(ERRORS_CSV_HEADER),'colunas')
for lbl,p in [('ARTIGO','/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv'),
              ('COMP162','experimento-comp162/results/comp162_00/comp162_00/errors.csv')]:
    try: read_errors_csv(p); print(lbl,'OK')
    except Exception as e: print(lbl,type(e).__name__,str(e)[:120])
"
```

**Testes** (contrato de CI — sem estas flags a coleta quebra):
```bash
uv run pytest --import-mode=importlib -o "addopts=" modules/<modulo>/tests
```

---

## 6. Aprendizados a carregar

1. **Leitura integral vence amostragem, e a diferença não é marginal.** A amostragem de três blocos
   por relatório contou 116 itens; a leitura integral encontrou **581**. A conclusão errada derivada
   dos 116 sobreviveu a uma rodada de verificação por amostragem e só caiu quando os arquivos foram
   lidos inteiros. Quando a pergunta é "o que foi deixado de fora", **só leitura integral responde**.
2. **Verificar uma contagem exige verificar o denominador.** O numerador (225 IDs citados) estava
   certo; o denominador estava errado por omissão de blocos inteiros. Duas afirmações caíram por isso.
3. **Rodar o gate que o próprio documento propõe é o teste mais barato e mais revelador.** O achado
   mais importante da sessão 1 saiu de executar G-2 (`INV-INS-110`) sobre as tabelas compiladas —
   algo que o documento propõe como gate futuro e nunca aplicou ao conjunto em produção.
4. **Extrair semântica das tabelas geradas, não do texto-fonte.** Os índices de estado não seguem a
   ordem de declaração do `.mop` (`TrustManagerFactorySpec` declara `start, waitingInit, final` e o
   gerador produz `start=0, final=1, waitingInit=2`), símbolos ERE não declarados somem em silêncio,
   e eventos duplicados fundem. Só o artefato gerado diz a verdade.
5. **Distinga "registro que precisa de mensagem melhor" de "registro que não deveria existir".** É a
   distinção que falta no documento alvo e a razão de C-3 estar sem dimensionamento. 30,5 % do volume
   mudo é da segunda categoria e some por deleção, sem design de mensagem nenhum.
6. **Um número verificado como "exato" pode estar contando o fenômeno errado.** "8.371 `found .`"
   é exato para o que conta e é o denominador errado do fenômeno (8.843, em cinco specs).
7. **As fontes pedem para não serem citadas como certificação.** `codex:478-480` declara-se de
   primeiro estágio; `codex:75` diz que concordância entre passes **nunca** vale como prova, *"as
   citações é que valem"*. O `FINAL.md` faz o oposto. Vale para esta sessão também: não trate
   concordância entre subagentes como evidência — peça a citação.

---

## 7. Primeira ação sugerida

Leia integralmente, nesta ordem: `docs/20260815_javamop_mensagens_FINAL_analise_lacunas.md` (818 l.,
o mais recente e o alvo principal da validação), depois `docs/20260815_javamop_mensagens_FINAL.md`
(521 l., o documento de design), depois `docs/20260815_javamop_mensagens_FINAL_analise.md` (645 l.).
Só então despache os subagentes das duas frentes de §3, com recortes disjuntos e instrução explícita
de leitura integral.

O produto desta sessão deve ser um relatório de validação que responda, com evidência medida, às
duas perguntas do pesquisador: **está tudo consistente?** e **deixamos passar alguma sugestão que
melhore o sistema?** — mais, se a resposta à segunda for sim, a lista das sugestões perdidas com o
destino proposto (qual mudança C-* deve absorvê-las, ou por que devem virar opção nova).
