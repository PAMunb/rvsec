# gh104 — Fase 8 confrontada com as regras CrySL (api30)   [REESCRITO após perda do original]

Fontes: `.mop` de `rvsec-mop/src/main/resources/jca/` (23, congelado);
regras `MetaCrySL/generated/api30/` (33). Pareamento de
`audit/20260808_validacao_jca_android/fase0/inventario_pareamento.md`.
Monitor de referência: `results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`.

## 1. GCMParameterSpecSpec — o diagnóstico da proposta estava invertido
A regra declara `c1: GCMParameterSpec(tLen, src)` e `c2: GCMParameterSpec(tLen, src, offset, len)`,
com `Cons := c1 | c2` e `ORDER Cons`. O `ere : c1 | c2` do `.mop` transcreve CERTO.
O defeito é a declaração do segundo evento (`GCMParameterSpecSpec.mop:33`) nomeada `c1`.
No monitor gerado: dois overloads `GCMParameterSpecSpec_c1Event` (`:10342` e `:10394`), ids de
evento 0 e 1, MESMA tabela `Prop_1_transition_c1 = {1,2,2}`; `grep -c GCMParameterSpecSpec_c2` = 0.
Como o monitor é per-objeto, `estado 1 --c1--> 2 (fail)` é inalcançável; e as violações reais
estão no `condition(...)`, que impede o disparo. A spec não consegue acusar nada.
Reparo: 1 token. Classe: estrutural, provável.

## 2. Os 18 "eventos órfãos" do G-2 — 17 são codificação CORRETA
O CrySL separa `ORDER` (sequência) de `CONSTRAINTS`/`REQUIRES`/`FORBIDDEN` (condições pontuais).
Evento que codifica condição pontual NÃO deve estar no `ere`.

| órfão | cláusula CrySL | acusa? | veredicto |
|---|---|---|---|
| `IvParameterSpec:41 c3`, `:50 c4` | `REQUIRES randomized[iv]` | sim | correto |
| `KeyPairGeneratorSpec:91 initError` | `CONSTRAINTS alg=>keySize` | sim | correto |
| `PBEKeySpecSpec:44 err1` | `CONSTRAINTS iterationCount>=10000` | sim | correto |
| `PBEKeySpecSpec:52 err2` | `CONSTRAINTS neverTypeOf(password,String)` | sim | correto |
| `PBEKeySpecSpec:60 err3` | `REQUIRES randomized[salt]` | sim | correto |
| `PBEKeySpecSpec:20 f1`, `:26 f2` | **`FORBIDDEN`** ctors `(char[])` e `(char[],byte[],int)` | sim | correto |
| `PBEParameterSpecSpec:41 c3` | `CONSTRAINTS` + `REQUIRES` | sim | correto |
| `SecretKeySpecSpec:40 c3`, `:51 c4` | `CONSTRAINTS length>=off+len` | sim | correto |
| `SecureRandomSpec:76 g4` | `CONSTRAINTS randAlg in {SHA1PRNG}` | sim | correto |
| `SecureRandomSpec:94 setSeed3` | `REQUIRES randomized[seed]` | sim | correto |
| `SecureRandomSpec:41 c3` | `REQUIRES randomized[seed]` | **nao** (so `sr = r`) | assimetria |
| `SignatureSpec:44 g3` | `CONSTRAINTS alg in {...}` | **nao** (grava campo) | acusacao diferida |
| `TrustManagerFactorySpec:43 g3` | `CONSTRAINTS algo in {PKIX}` | **nao** (grava campo) | acusacao diferida |
| `SSLContextSpec:45 unsafe_protocol` | `CONSTRAINTS protocol in {...}` | **nao** (grava campo) | acusacao diferida |
| **`MessageDigestSpec:73 reset`** | **nenhuma** — corpo vazio `{ }` | nao | **CODIGO MORTO** |

Consequencia: o gate G-2 como especificado reprova 17 casos corretos. Precisa da regra CrySL
como entrada. O item "18 eventos que acusam incondicionalmente" sai do plano por diagnostico errado.

## 3. Acusacao diferida por campo — onde a Fase 7 encosta na 8
`SignatureSpec.g3`, `TrustManagerFactorySpec.g3`, `SSLContextSpec.unsafe_protocol` detectam no
`getInstance` mas so gravam campo; a acusacao sai depois interpolando o campo -> `but found .`
quando o campo nunca foi escrito. Nesses tres sitios o argumento NAO existe no evento que acusa,
entao a tarefa 7.2 (campo -> argumento) nao se aplica. `SecureRandomSpec.g4` mostra a forma certa.

## 4. `SecureRandomSpec.c3` — assimetria provavel
Mesma cláusula que `setSeed3`, guarda identica, mas nao acusa. Reparo adiciona acusacao -> comportamental.

## 5. `remove(Property)` — 9 sitios contra 2 `NEGATES` em toda a api30
`NEGATES` existe so em `PBEKeySpec` (`speccedKey` after `cP`) e `SecretKey` (`generatedKey` after `d`).
Os 9 `remove` do `jca` estao todos em `@fail`. So `PBEKeySpecSpec:72` tem contrapartida, e mesmo
essa o CrySL revoga apos `clearPassword()`, nao por falha de sequencia. Materia da Fase 9 (cortada).

## 6. Extra-oraculo
`SecretKeySpec.cryptsl` tem so `CONSTRAINTS length(keyMaterial) >= off + len` e nada sobre algoritmo;
a `.mop` (`SecretKeySpecSpec.mop:40,51`) testa `algorithms.contains(...)`. Acusacao sem base no oraculo.

## 7. Fase 8 encurtada — os 7 reparos que entram
1. `GCMParameterSpecSpec:33` evento `c1` -> `c2`
2. `SecretKeySpecSpec:27-30` parentese sobrando no `condition`
3. `MessageDigestSpec:73` evento `reset` morto -> remover
4. `KeyPairGeneratorSpec:26` `String algorithm` nao inicializado
5. pointcuts mortos `SignatureSpec:99,:106`, `SSLContextSpec:64` (tipo de retorno)
6. `KeyPairGeneratorSpec:71-72` ramo inalcancavel
7. `KeyGeneratorSpec:47` e `MessageDigestSpec:55` testam `contains(currentAlgorithmInstance)`
   em vez de `contains(alg)` — o argumento recem-recebido nunca e avaliado

Saem: replay dos 51 hunks `layer-2`, os 42 `predicate-graph`, reescrita de alfabeto, split de
`init`, rebinding de `target`, migracao da acusacao do `g3`, os 4 `remove` de um argumento.

## 8. Gate novo proposto (Fase 6)
**Todo simbolo citado no `ere` tem declaracao de evento** — pega o `GCMParameterSpecSpec` sozinho,
zero falso positivo. Vale so para specs com `ere`; em specs com `fsm` os nomes de estado
apareceriam como falsos positivos.
