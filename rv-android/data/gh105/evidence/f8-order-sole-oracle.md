# Tarefa 11.6 — as divergências de ORDER contra o oráculo único

**Data**: 2026-08-26 · **Grupo**: 11 (F8, D-16) · **Espécie**: decisão do pesquisador, por spec
**Oráculo único**: `RVSec-replication-package/tools/rules/` (49 regras, sha256 `d7bcc019…`)
**Disciplina**: 9.B — par de arnês, linha de divergência e go/no-go por especificação

O G-ORDER reancorado (11.2 + 11.3) varreu as 24 especificações do conjunto e reportou **duas**
divergências sem perdão: `MacSpec`, testemunha `g1 i1 f1`, e `KeyPairSpec`, testemunha a sequência
vazia. As sete perdoadas foram rejustificadas na 11.4 e não são desta tarefa. As duas abertas foram
adjudicadas pelo pesquisador em 26/08, as duas para o mesmo lado — **reparar o `ere`** — sob a
regra de decisão que rege o grupo: *manter aderência à regra CrySL como está na regra*.

Este documento cresce por commit. Cada seção diz o que foi **medido antes de propor**, o que o
reparo custa em acusação, e onde está o par de arnês que mede o custo.

---

## 1. O mapa antes do autômato: `MacSpec.updateBuffer`

`Mac.crysl:9,30` (`u4: update(preInputByteBuffer)`), dentro de `Update` (`:31`)
**registro** · sem par de arnês · commit separado, e **primeiro**

A 11.2 achou três linhas `order-unmapped` cujo apagamento se apoiava na api30 e que o catálogo
expert nomeia — `MacSpec.updateBuffer`, `SecureRandomSpec.next1` e `next3` — e as deixou onde
estavam, dizendo em `f8-order-alphabet-expert.md §4` que reabrir qualquer uma entra por 11.5/11.6.
Esta seção reabre **uma**: a do `MacSpec`, porque é a que a divergência desta tarefa toca. As duas
do `SecureRandomSpec` continuam apagadas e continuam sem decisão — reabrir cada uma alarga a
linguagem que o G-ORDER compara e pede decisão própria, que esta tarefa não carrega.

**O apagamento estava certo contra a api30 e está errado contra o oráculo.** Aquela regra não
declarava a sobrecarga de `ByteBuffer`; o `u4` dela era uma segunda declaração de `update(byte[])`,
e é por isso que o `order_alphabet_map.csv` — o registro da api30, que ninguém lê (INV-INS-118) —
fica como está. A restauração é só do lado expert, e o instrumento a expressa como tal: uma tabela
nova, `RESTORED_ROWS`, chaveada por (`spec`, `mop_event`) porque a linha que ela reabre não tem
símbolo pelo qual ser chaveada.

### O que a medição desmentiu

A tarefa foi escrita esperando que a restauração fosse neutra no veredito. **É e não é**, e a
diferença é o reparo do `ere` da seção seguinte:

| `ere` | `updateBuffer` apagado | `updateBuffer` mapeado em `u4` |
|---|---|---|
| como estava (`(...)* `) | `g1 i1 f1` diverge | `g1 i1 f1` diverge |
| reparado (`(...)+ `) | `g1 i1 f1` **diverge** | `MacSpec` passa |

Medido em 26/08, as quatro células. Contra o `ere` como estava a restauração não move nada, porque
aquele `ere` aceitava zero `update` de qualquer jeito. Contra o `ere` reparado ela é o que faz o
reparo valer: **o G-ORDER apaga um evento não mapeado como movimento epsilon**
(`gh105_order_gate.py:810`), e um símbolo apagado dentro de um `+` satisfaz o `+` sem chamada
nenhuma — de modo que `g1 i1 f1` sobreviveria ao reparo intacto.

É por isso que os dois vão em commits separados **e nesta ordem**. Um move acusação e o outro não;
mas o que não move acusação vem primeiro, porque é premissa do que move. Um registro cujo efeito só
aparece quando o autômato alcança não deixa de ser registro.

### Reprodução

```bash
python3 scripts/gh105_expert_alphabet.py --emit map
python3 scripts/gh105_expert_alphabet.py --emit delta
python3 scripts/gh105_expert_alphabet.py --check      # exit 0; RESTORED_ROWS gasta
python3 scripts/gh105_order_gate.py --sets jca_android
```

O `--check` ganhou a asserção que faltava: uma entrada de `RESTORED_ROWS` escrita e nunca aplicada
reprova, do mesmo modo que já reprovava um `REASON_OVERRIDES` ou um `DUPLICATE_OVERRIDES` órfão.
A linha do delta sai com `klass` nova, `restored-under-expert`, e a linha
`uncovered-expert-symbol` que dizia que nenhum evento do conjunto cobria o `Mac.crysl:u4`
desaparece — porque agora um cobre. O mapa fica com as mesmas 137 associações; o delta cai de 152
para 151, e a linha que sumiu é exatamente essa. Nenhuma associação foi acrescentada nem removida:
uma mudou de disposição, e o símbolo que ela passou a cobrir deixou de constar como descoberto.

---

## 2. `MacSpec` — o `ere` que aceitava um MAC sobre nada

`Mac.crysl:41` · testemunha `g1 i1 f1` · **reparar** · par de arnês devido e commitado

### A regra, lida como está escrita

```
FinalWU  := f2;                              (Mac.crysl:36)   f2: output2 = doFinal(input)
FinalWOU := f1 | f3;                         (:37)            f1: doFinal()   f3: doFinal(out, off)
Final    := FinalWU | FinalWOU;              (:38)
ORDER      Get, Init, (FinalWU | (Update+, Final))            (:41)
```

A regra separa os três finais em dois grupos e usa a separação: **o único final que dispensa
`update` é o que traz o próprio dado**. `doFinal()` e `doFinal(out, off)` sem `update` autenticam a
entrada vazia, e a regra os põe atrás de `Update+`. A numeração é cruzada entre os dois arquivos —
o `f1Input` do `.mop` é o `f2` da regra, e o `f2` do `.mop` é o `f3` dela; o mapa de alfabeto é
onde isso está escrito.

```
antes:  ere : (g3* g1 | g3* g2) (i1 | i2) ((f1 | f1Input | f2) | ((update | ... )* (f1 | f1Input | f2)))
depois: ere : (g3* g1 | g3* g2) (i1 | i2) (f1Input | ((update | ... )+ (f1 | f1Input | f2)))
```

O que estava aqui aceitava um MAC sobre nada por dois caminhos ao mesmo tempo: o ramo da esquerda,
que admitia os três finais nus, e o `*`, que admite zero `update`. O G-ORDER reportava exatamente
isso, `g1 i1 f1`.

### O custo, medido

Par de arnês: `data/gh105/evidence/harness/f8f-MacSpec.md`, 14 traces do corpus que tocam esta
especificação. **Três `moved`, onze `unchanged`**, e as três que se moveram ganham a mesma coisa:

| trace | A acusa | B acusa |
|---|---|---|
| `MacSpec-decrypt-buffer` | `f2:MAC-CONSTR-00` (+2 de outras specs) | idem **+ `f2:MAC-ORDER-00`** |
| `MacSpec-encrypted-buffer` | `f2:MAC-CONSTR-00` (+2) | idem **+ `f2:MAC-ORDER-00`** |
| `MacSpec-fresh-buffer` | — (só 2 de outras specs) | idem **+ `f2:MAC-ORDER-00`** |

As três são `init` seguido direto de `doFinal(buf, 0)` — o `f3` da regra, sem `update`. Elas
existem para testemunhar `!encrypted[output1, _]` no sítio `f2`, e escolheram a sobrecarga com
buffer por conveniência, não porque a entrada vazia importasse a elas. **Não foram editadas**: são
o instrumento de medição, e editá-las apagaria a única prova do que o reparo custa.

### As três traces irmãs

`MacSpec-{decrypt,encrypted,fresh}-buffer-updated.txt`, acrescentadas no mesmo commit, cada uma
igual à sua irmã mais um `m.update(msg)` antes do final. O arnês as lê `unchanged` nos dois lados,
que é o que se queria provar: a cláusula `!encrypted` continua com testemunha sob uma sequência de
chamadas que a regra admite, e o `MAC-CONSTR-00` chega sozinho em vez de ao lado de um
`MAC-ORDER-00`. O `msg` é array próprio e não o buffer onde a tag é escrita — autenticar o mesmo
buffer confundiria as duas coisas. É o precedente da 11.5(e), aplicado pela mesma razão.

### Ressalva que fica registrada

Em campanha sobre apps reais, todo `Mac` que finaliza sem `update` passa a emitir `MAC-ORDER-00` —
e `doFinal()` sobre um `Mac` recém-inicializado é chamada que existe. A regra é explícita a
respeito, e a decisão de 26/08 foi aderir a ela; a linha de divergência do hunk `b579733c6909` diz
isso, para que a próxima medição não leia o número como surpresa.

### O portão

```
antes:  G-ORDER: 13 passadas, 2 falhas, 7 perdoadas, 2 puladas
depois: G-ORDER: 14 passadas, 1 falha,  7 perdoadas, 2 puladas
```

A que resta é a do `KeyPairSpec`, seção 3. Nenhuma linha entrou no `gate_allowlist.csv`: as duas
divergências desta tarefa estavam sem perdão, e o reparo fecha em vez de perdoar.
