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
