# Handoff — próxima sessão sobre as mensagens de violação JavaMOP

**Data de escrita:** 2026-08-15
**Uso:** cole este arquivo inteiro como primeira mensagem da nova sessão.
**Estado:** nada implementado. Nenhum commit feito. Dois arquivos novos, não rastreados.

---

## 0. Instruções operacionais para a sessão (leia primeiro)

1. **Use diversos subagentes.** O trabalho abaixo é largo e paralelizável por recorte disjunto
   (weaver Java / gerador JavaMOP / specs `.mop` × oráculos CrySL / camada Python de transporte e
   consumidores / consistência documental / processo OpenSpec). Despache-os em paralelo, num único
   bloco de chamadas, com escopos que não se sobreponham. Foi assim que a análise anterior foi
   produzida e funcionou bem.
2. **Verifique os subagentes.** Na sessão anterior, três conclusões de subagente estavam erradas e só
   caíram por medição direta (registradas em §8 do relatório de análise). Não aceite resultado de
   agente sem conferir os números que sustentam decisão.
3. **Siga `docs/WORKFLOW.md` rigorosamente.** Regra não-negociável do `CLAUDE.md`: para qualquer
   mudança sob `openspec/changes/gh<N>-*/`, os artefatos OpenSpec são criados **exclusivamente** via
   as skills (`Skill` tool: `openspec-new-change`, `openspec-continue-change`, `openspec-propose`,
   `openspec-apply-change`, `openspec-verify-change`, `openspec-archive-change`). **Nunca** use
   `Write`/`Edit` direto para criar ou reescrever `proposal.md`, `design.md`, `tasks.md` ou delta
   specs.
4. **Princípios P1–P4 valem para tudo** (simplicidade; documentação narrativa que explica o *porquê*;
   sem retrocompatibilidade — código superado é deletado, com backup em `backup/`; comentários
   descrevem o estado atual, sem histórico de migração).
5. **Nunca gerencie emulador à mão.** Validação em device só via `rv-experiment run` /
   `rv-platform run`.
6. **"MOP" = monitored operations.** Nunca use terminologia de "segurança" para MOP.
7. **Português com acentuação correta** quando escrever em português.
8. **Sem `Co-Authored-By`** em mensagens de commit.

---

## 1. O que estamos fazendo

Os relatórios de violação do RVSEC são ilegíveis: no dataset de referência, 72,93 % dos 97.018
registros carregam o literal `unknown`, e existem apenas 19 mensagens distintas. O ensaio pós-reparo
do Estudo 03 (`experimento-comp162`, `jca` congelado + weaver gh100) é **pior**: 79,91 %
(15.714 de 19.664).

Existe um documento de design que consolida um plano, uma revisão adversarial dele e quatro
validações externas por LLM, e que se propõe a ser o insumo de Fase 0 do workflow OpenSpec —
`docs/20260815_javamop_mensagens_FINAL.md` (521 linhas). Ele propõe oito mudanças (C-0, C-1a, C-1,
C-V, C-2, C-3, C-4, C-5), nove decisões de pesquisador (D-A..D-I), oito gates formais (G-1..G-8) e
nove opções em aberto (O-1..O-9).

**A sessão anterior produziu uma análise adversarial independente desse documento.** O objetivo agora
é decidir o que fazer com as conclusões dela — não implementar código.

---

## 2. O que foi feito

### 2.1 Artefato produzido

`docs/20260815_javamop_mensagens_FINAL_analise.md` (645 linhas, **não commitado**). Estrutura:
veredito; o achado ausente; defeitos bloqueantes de design; correções factuais; defeitos
metodológicos; viabilidade do plano e processo; 10 recomendações priorizadas; onde a análise corrigiu
os próprios verificadores; referências.

### 2.2 Método usado

Seis subagentes de verificação com recortes disjuntos, mais medições próprias sobre os datasets e
sobre as tabelas de transição dos monitores compilados. Somente-leitura em tudo.

### 2.3 Conclusões que já estão firmes (não precisam ser refeitas)

**Verificado como exato no documento alvo:** 97.018 / 70.760 / 72,93 % / 19 mensagens; a
bicondicional `unknown ⇔ InvalidSequenceOfMethodCalls` no dataset de referência; 19.664 / 15.714 /
79,91 % no comp162; TMF 2.916 = 2.855 + 61; 8.371 `found .`; 98 = 55 + 39 + 4; "21 `@fail` + 4 sítios
não-`@fail`" (idêntico nos dois conjuntos); 15/23 e 18/23 de monitores atômicos; `.aj` git-ignored;
os quatro defeitos de tradução de §5.3 contra os dois oráculos; o mecanismo de §5.1 (wrapper mesclado
+ `args()` inerte); e a suposição central de §7.2 (**o corpo do evento roda antes da transição** —
verdadeira nas duas formas de monitor).

**O achado novo, ausente do documento alvo:** rodando o próprio gate G-2 do documento
(`INV-INS-110`) sobre as tabelas compiladas — o **`jca` congelado tem 18 eventos órfãos em 10 de 23
specs**; `jca_android` pós-gh101 tem **0**; `jca_android` pré-gh101 tinha os mesmos 18. O maior é
`SSLContextSpec.unsafe_protocol` (`Prop_1_transition_unsafe_protocol[] = {3,3,3,3}`), responsável por
**2.916 linhas mudas** — mais que as 2.855 do achado principal de §5.1 — e reparável com duas linhas
de FSM, sem weaver, sem D-C, sem reinstrumentação. Isso inverte a recomendação de D-A (ver §3.1
abaixo).

**Defeitos bloqueantes de design identificados:** `st=<stateOrClause>` é inimplementável do lado do
`.mop` (índices de estado são atribuídos pelo gerador pós-minimização, não seguem ordem de
declaração, e mudam a cada edição); três caminhos produzem mensagem confiantemente errada (prólogo da
condição antes do corpo; `KeyPairGeneratorSpec` sem `__RESET`; clones herdam a escrituração); a
proibição de vírgula em §7.1 é insatisfazível (27,06 % das mensagens têm vírgula, geradas por
`String.join(",", …)` em ≥11 sítios `.mop` do conjunto congelado) **e** desnecessária (os quatro
parsers já rejuntam o campo 6+); a identidade de dedup exclui `ev`/`st`/`val`, anulando o objetivo da
mudança; a matriz de consumidores está incompleta em ~uma ordem de grandeza.

---

## 3. Próximos passos

### 3.1 Decisões que só o pesquisador pode tomar (bloqueiam o resto)

1. **D-A — inverter o default para (i)?** A análise recomenda sim. Medição: 19 de 23 specs diferem
   entre `jca` e `jca_android`, ~880 linhas. A opção (ii) (derivar `jca_v2` do `jca` congelado)
   significa re-derivar essas ~880 linhas e re-reparar os 18 eventos órfãos que a gh101 já reparou.
   Ressalva honesta: isso é sobre *ponto de partida*, não atestado de prontidão — a auditoria reprova
   `jca_android` 22/22.
2. **`st=` — cair de §7.1 ou promover O-1 a pré-requisito de C-3?** Não há terceira opção.
3. **C-3 antes ou depois de O-1?** O gatilho declarado de O-1 já está satisfeito no dia zero. Se a
   razão real para preferir edição manual é não bifurcar um toolchain fixado para reprodutibilidade
   de E2/E3, essa razão precisa estar escrita — hoje a decisão é tomada implicitamente pelo
   cronograma.
4. **D-C** — a decisão sobre landing do reparo de aridade `args()` continua em aberto e depende do
   estado das corridas finais do Estudo 03, que nada no plano observa.

### 3.2 Trabalho de verificação ainda pendente (bom para subagentes)

Ver §4 — é exatamente a lista do que **não** foi analisado.

### 3.3 Trabalho de correção no documento alvo

As 10 recomendações estão em §7 do relatório de análise. As três estruturais, que devem preceder a
abertura de qualquer issue:

- publicar o censo dos 18 eventos órfãos em C-0 e reconhecer o reparo já feito pela gh101;
- transformar C-0 de "linha de base" em "orçamento residual" — com a ressalva de que isso exige uma
  corrida de calibração com nome de evento (O-1/O-2), porque as 15.295 linhas mudas colapsam em
  apenas **296 sítios distintos**, todas com `message = unknown`: a atribuição por *evento* é
  impossível com os dados atuais, já que o nome de evento ausente **é** o defeito medido;
- resolver `st=` e reescrever a gramática de §7.1.

### 3.4 Quando for abrir issues

Não há mapeamento `C-x → gh<N>` em lugar nenhum, embora o cabeçalho do documento alvo declare que
cada mudança vira uma issue e um diretório `gh<N>-<nome>`. Defina-o antes, ou toda referência cruzada
de §8/§9 vira re-chaveamento manual. `C-1a` como sub-mudança de `C-1` não tem representação no
OpenSpec — serão duas issues sem relação além da prosa.

Atenção também: `INV-INS-109/110/115` **só existem dentro de deltas não arquivados** —
`openspec/specs/instrumentation/spec.md` para em `INV-INS-103`. G-2, o gate de C-3 e §7.4 dependem de
texto de contrato que o spec principal não contém. Ou fixe o arquivamento de gh100/gh101 como
predecessor duro, ou copie o texto do invariante para a delta de C-V. A gh100 ainda tem 3 tarefas de
verificação abertas sobre `WrapperEmitter.java` — o mesmo arquivo que C-1a editaria.

---

## 4. O que NÃO foi analisado (lacunas conhecidas)

Estas lacunas estão registradas no cabeçalho do relatório e devem ser fechadas por quem continuar:

1. **Não reabri os quatro relatórios externos item a item contra o §4** do documento alvo. A lacuna
   está *caracterizada*, não *resolvida*: os quatro relatórios-fonte enumeram **116 itens**, o §4 cita
   **225 IDs** num esquema `A/B/C` que **nenhuma fonte usa**, e o artefato intermediário que criou
   esses IDs (a "passagem de extração independente" citada no cabeçalho do FINAL) **não está na
   tabela de linhagem**. Consequência: `d-B2` identifica o relatório mas não uma linha localizável
   nele. Fechar isso significa republicar as quatro listas de extração ou renumerar o §4 pela
   enumeração própria de cada fonte. **É a correção mais cara e a que mais afeta a confiabilidade do
   §4.**
2. **Não verifiquei o limite de ~4.068 B do logcat contra fontes do Android.** A aritmética
   (`4076 − 1 − 6 − 1`) reproduz o número citado, e a folga medida é confortável (mediana 131 B, p99
   209 B, máximo 349 B nas 97.018 linhas; o envelope proposto ~dobra isso, ≈16 % do limite), mas o
   limite em si permanece **não verificado**. Nenhum dos dois coletores trunca; qualquer corte vem do
   Android. Riscos residuais registrados: `msg` é o último campo, então um corte produz envelope não
   terminado; e `val` vem da aplicação e não tem teto em nenhum coletor.
3. **Nada foi executado em device.** Todas as conclusões vêm de leitura de fonte, de artefatos
   gerados já existentes e de datasets já coletados.

Lacunas menores, também não fechadas: não reabri os três scripts sinalizados pela validação externa 4
(`regenerate_container.py`, `gh91_compare_consolidation.py`, `rv_oracle_common.py`) além de confirmar
que existem e como leem; não verifiquei empiricamente a afirmação "dexlib2 only — AspectJ enforces
`args` arity" (é propriedade da linguagem AspectJ, não do repo, e não há medição pareada em árvore);
e não reabri os itens do §4 marcados `U` que a análise não precisou usar.

---

## 5. Arquivos relacionados

### 5.1 Produzidos pela sessão anterior (não commitados)

| Arquivo | Papel |
|---|---|
| `docs/20260815_javamop_mensagens_FINAL_analise.md` | o relatório de análise (645 linhas) |
| `docs/20260815_javamop_mensagens_FINAL_analise_handoff_prompt.md` | este arquivo |

### 5.2 Linhagem (todos em `rv-android/docs/`)

| Arquivo | Papel | Prefixo no §4 |
|---|---|---|
| `20260815_javamop_mensagens_FINAL.md` | **o documento analisado** | — |
| `20260815_javamop_mensagens.md` | o plano (L1–L8, WS-1..8, D-1..8, D01–D50) | — |
| `20260815_javamop_mensagens_analise.md` | revisão adversarial do plano ("o review") | `R` |
| `20260815_javamop_mensagens_analise_handoff_prompt.md` | brief da revisão adversarial | — |
| `20260815_javamop_mensagens_validacao_prompt.md` | brief dado aos quatro LLMs | — |
| `20260815_javamop_mensagens_claude_fable5.md` | validação externa 1 | `c-` |
| `20260815_javamop_mensagens_deepseek_v4_flash.md` | validação externa 2 | `d-` |
| `20260815_javamop_mensagens_gemini36flash.md` | validação externa 3 | `g-` |
| `20260815_javamop_mensagens_gpt5_codex.md` | validação externa 4 | `x-` |

### 5.3 Fontes de evidência

- **Datasets:** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv`
  (97.018 linhas, **10 colunas**, sem `source`); `rv-android/experimento-comp162/results/*/*/errors.csv`
  (8 arquivos, 19.664 linhas, **11 colunas**). Atenção: **dois headers vivos** — `read_errors_csv` já
  falha contra o dataset do artigo.
- **Oráculos de monitor gerado:** `rv-android/results/{gh56-smoke,gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control}/monitors/`
- **Specs:** `rvsec/rvsec-mop/src/main/resources/{jca,jca_android}/` (23 `.mop` cada;
  `generic` 118; `generic_new` 27, ausente do `click.Choice` da CLI)
- **CrySL 1.5.2:** `/home/pedro/.../workspace-rv/Crypto-API-Rules/JavaCryptographicArchitecture/src/`
- **MetaCrySL api30:** `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/`
- **Gerador:** `rv-monitor/`, `javamop/` · **Weaver:** `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`
- **Runtime:** `rvsec/rvsec-core/`, `rvsec/rvsec-logger-csv/`, `rvsec/rvsec-android/rvsec-logger-logcat/`
- **Auditoria:** `audit/20260808_validacao_jca_android/` (§7 = as dez decisões de D-H; §10 = veredito
  REPROVADA 22/22; `fase0/pre_registro.md` §7 = a conjunção READY do critério de aceitação 8)
- **Trabalho anterior:** `openspec/changes/gh10{0,1,2,3}-*/`, `data/gh101/README.md`

---

## 6. Comandos úteis (reproduzem as medições da análise)

Todos somente-leitura. Rode a partir de `rv-android/`.

**Números de cabeçalho do dataset de referência:**
```bash
python3 -c "
import csv,collections
r=list(csv.DictReader(open('/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv')))
c=collections.Counter((x.get('message') or '').strip() for x in r)
print(len(r),'linhas |',len(c),'mensagens |',c['unknown'],'unknown =',round(100*c['unknown']/len(r),2),'%')
"
```

**Decomposição do comp162 (mostra que `unknown` = InvSeq + 419 UnsatisfiedConstraint):**
```bash
python3 -c "
import csv,glob,collections
rows=[]
for f in sorted(glob.glob('experimento-comp162/results/*/*/errors.csv')): rows+=list(csv.DictReader(open(f)))
def et(r):
    p=(r.get('unique_msg') or '').split(':::'); return p[3] if len(p)>3 else '?'
print(len(rows),'linhas')
print('unknown:',collections.Counter(et(r) for r in rows if (r.get('message') or '').strip()=='unknown').most_common())
print('por spec:',collections.Counter(r['spec'] for r in rows).most_common(8))
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

**Divergência entre os dois conjuntos de specs:**
```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources
for f in jca/*.mop; do b=$(basename $f); n=$(diff "$f" "jca_android/$b" 2>/dev/null | grep -c '^[<>]'); \
  [ "$n" != "0" ] && printf "%-32s %4d\n" "$b" "$n"; done
```

**`@fail` sem `__RESET`** (retorna `KeyPairGeneratorSpec`; os extras em `jca_android` são menções em
comentário):
```bash
for f in jca/*.mop jca_android/*.mop; do awk '/@fail/{i=1} i{b=b $0 "\n"; if(/^\s*}/){if(b !~ /__RESET/) print FILENAME; i=0; b=""}}' "$f"; done | sort -u
```

**Testes** (contrato de CI — sem estas flags a coleta quebra):
```bash
uv run pytest --import-mode=importlib -o "addopts=" modules/<modulo>/tests
```

---

## 7. Aprendizados a carregar

1. **Meça antes de aceitar um número, mesmo de um verificador.** Três conclusões de subagente caíram
   por medição direta: um contou `InvalidSequenceOfMethodCalls` (15.295) quando a alegação era sobre
   `unknown` (15.714) e concluiu erradamente que o documento não reproduzia; outro confundiu dois
   números iguais a 2.916 que medem coisas diferentes; um terceiro comparou contagem de arquivos com
   contagem de sítios `Log.v`.
2. **Rodar o gate que o próprio documento propõe é o teste mais barato e mais revelador.** O achado
   mais importante da análise saiu de executar G-2 (`INV-INS-110`) sobre as tabelas compiladas — algo
   que o documento propõe como gate futuro mas nunca aplicou ao conjunto que está em produção.
3. **Extrair semântica das tabelas geradas, não do texto-fonte.** Os índices de estado não seguem a
   ordem de declaração do `.mop`, símbolos ERE não declarados somem em silêncio, e eventos duplicados
   fundem. Só o artefato gerado diz a verdade.
4. **Distinga "registro que precisa de mensagem melhor" de "registro que não deveria existir".** É a
   distinção que falta no documento alvo e a razão de C-3 estar sem dimensionamento.
5. **Um documento cujo próprio cabeçalho diz que a consolidação "deve ser refeita" não é FINAL.**
   Vale checar sempre a coerência entre o status declarado de um artefato e as ressalvas que ele
   mesmo faz.

---

## 8. Primeira ação sugerida para a nova sessão

Leia `docs/20260815_javamop_mensagens_FINAL_analise.md` (o relatório) e
`docs/20260815_javamop_mensagens_FINAL.md` (o alvo), decida com o pesquisador as quatro decisões de
§3.1 deste handoff, e só então escolha entre: (a) corrigir o documento alvo antes de abrir issues, ou
(b) abrir as issues já com as correções registradas como parte de C-0. Não comece a implementar
nenhuma das mudanças C-* antes dessas decisões — três delas mudam o escopo de C-3 e C-4.
