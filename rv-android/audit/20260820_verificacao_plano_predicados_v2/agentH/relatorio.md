# Agente H — auditoria de coerência do plano corrigido

Mandato: §6 do handoff v2. Leitura integral do plano (1.082 linhas à época), da primeira
auditoria (550) e do handoff.

## Constatação preliminar

A premissa do handoff ("a decisão §3.1-bis ainda não está no plano") estava parcialmente
desatualizada: F0, R1, D3 e D4 já a incorporavam. Sobraram 8 problemas, todos emendados no plano
com a marca `[auditado-v2]` (aplicadas pelo orquestrador da segunda passada):

1. §4.4 concluía com a formulação superseded "uma implementação de store por conjunto de specs".
2. §7.4 dizia "store **corrigido**" — sob a decisão, nada é corrigido; o mecanismo A é a classe nova.
3. §5 (três valores) não dizia o custo (27 sítios + envelope) nem onde a decisão o confina.
4. §7.4 apresentava a `IvChainSpec(…byte[] iv…)` sem aviso de que a assinatura não compila (§7.5).
5. §4.2 dizia "não é critério de escolha" sem apontar o critério real (a assimetria da §7.5).
6. §7.2 condicionava F0 só à §7.4, ignorando que o piloto (D4) decide e precede.
7. Faltava risco para o mapeamento de alfabeto do G-ORDER — entrou como R7.
8. F5 citava `conformance_record.csv` como irmão do `predicate_graph.csv`; o irmão é
   `constraint_table.csv`.

## Verificado e OK

- Varredura de resíduo numérico limpa (24 valores, 19 arestas, 17/33, 255/354 fora do rótulo de
  estimativa, GENERATED_TRUST_MANAGERS, Mac/Key como decisor, 74/60 nas citações).
- F1 e F2 íntegras; F3 em 35 itens consistente em §2.1, §7.2 e §7.4; F5 com os 4 gates.
- R1/F0/D3/D4 já refletiam a decisão §3.1-bis.
- §7.6 coerente com §7.5 e D4; §8-bis presente com as seis lacunas (a sétima veio do agente B).
- Referências cruzadas internas conferidas, sem número desatualizado.
