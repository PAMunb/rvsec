# Manifesto de congelamento — auditoria `jca_android` (2026-08-08)

Consolida os três levantamentos independentes de Fase 0. Detalhes e tabelas completas:
`manifest_hashes.md` (proveniência/hashes), `inventario_pareamento.md` (23 specs ↔ regras),
`estado_gh100_gh101.md` (changes), `toolchain_ambiente.md` (componentes efetivos).
Critérios pré-registrados: `pre_registro.md`. Equivalência: `modelo_semantico.md`.

## Versões congeladas

| Artefato | Estado |
|---|---|
| monorepo `rvsec` (inclui rv-android, javamop, rv-monitor, rvsec/*) | HEAD `1dd1f4c5`, branch `modules`; working tree com 549 modificados, **mas todos os artefatos auditados limpos vs HEAD** |
| 23 `.mop` `jca_android` + 23 `.mop` `jca` (congelado) + 33 `.cryptsl` api30 | SHA-256 em `manifest_hashes.md`; bytes do working tree = HEAD |
| MetaCrySL | HEAD `fb1ecaba`, limpo |
| `errors.csv` | 26,3 MB, SHA-256 `78023def…`, ase-journal `f693a378` (branch jss-jca), limpo |
| JavaMOP jar | rebuilt 2026-08-08 10:35 com patches gh100/gh101 e `--emit-descriptor` |
| `rv-monitor-rt.jar` | `0fa65fbc…` (idêntico nas duas cópias); `aspectjweaver.jar` `4fe86fdc…` |
| `instr-cli.jar` (dexlib2) | `356e8b70…`; emissor: `MonitorInvokeBuilder.java:69` → `DexWeaver.java:303` |
| Ambiente | Temurin 25.0.3, Maven 3.9.9, Python 3.14.4, uv 0.12.0, 64 CPUs, 123 GiB |

## Inventário e pareamento (G1 — dados)

23/23 specs inventariadas; 22 pareiam 1:1 com regra CrySL **por conteúdo**
(`SecretKeySpec.mop` → `SecretKey.cryptsl`; `SecretKeySpecSpec.mop` → `SecretKeySpec.cryptsl`;
`IvParameterSpec.mop` declara `IvParameterSpecSpec`; `HMACParameterSpecSpec` confere FQCN
`javax.xml.crypto.dsig.spec`). `RandomStringPassword.mop` **não tem regra CrySL** —
auxiliar de propagação de `RANDOMIZED`; exige definição explícita de oráculo (candidata a
redução formal de escopo). **Decisão do pesquisador (2026-08-09): EXCLUÍDA da rodada de
auditoria** — sem regra CrySL não há oráculo normativo para o julgamento de fidelidade;
a exclusão é redução formal de escopo e será registrada também no juízo global. A rodada
audita, portanto, 22 specs (2 no piloto + 20 em lotes). **11 regras api30 sem spec**: AlgorithmParameters,
CertPathTrustManagerParameters, DSAGenParameterSpec, DigestInputStream, DigestOutputStream,
Key, KeyStoreBuilderParameters, PKIXBuilderParameters, PKIXParameters,
RSAKeyGenParameterSpec, SecretKeyFactory.

## Estado GH100/GH101

- GH101: 84/84 `[x]` (alegações). Registros localizados: 7 CSVs `data/gh101/`, 6 scripts
  `scripts/gh101_*.py`, gates `tests/parity/test_gh101_specset_gates.py`, evidência Grupo 8
  em `results/gh101_group8_*`. Lacunas: transition check sem saída commitada; sem pacote de
  replicação nomeado; INV-INS-110/115 sem gate pytest; teto do gerador sem output bruto.
- GH100: 55 `[x]` / 3 `[ ]`; tarefa 7.4 duplicada (`[x]` e `[ ]`); única dependência da
  GH101 (task 5.3) está `[x]` no commit `48b57fc5`.
- Decisões de maior risco (alvo de revisão adversarial §8): D-S11 (Cipher 24→14 via
  `instanceof` em runtime), D-S9 (resíduo desloca acusação uma chamada adiante, 13 specs),
  D-S10 (freeze byte-a-byte, não comportamental), D-S13 (`ByteBuffer` FN; cache de `Byte`
  sobre-reporta), remoção de `MessageDigestSpec.reset`.
- Contradições documentais: INV-INS-109/110 colidem entre deltas GH100/GH101; tabela
  D-S10 errada no design (corrigida só no README); proposal desatualizado (sem `MACED`,
  sem re-orçamento 17→14).

## Toolchain efetiva

- Seleção `jca_android`: mapeamento explícito `rv_experiment/config.py:685-712`, inválido
  rejeitado (`__main__.py:443`); **sem fallback silencioso**. Ressalva: omitir o flag ⇒
  default `jca`.
- **Risco G10 aberto**: variante dexlib2 resolve `android.jar` por máximo lexicográfico de
  `$ANDROID_HOME/platforms` (`ConfigResolver.java:111-127`) → `android-37.0` no host,
  `android-36` no Docker; **não** API 30. Só a variante ajc casa `android-30`
  (`ajc_instrumentation.py:1619-1655`). Mesmo defeito lexicográfico na escolha de
  d8/apksigner.
- `ajc` ausente do PATH do host — weaving ajc reproduzível apenas em Docker
  (AspectJ 1.9.25.1, coincide com o pin do pom).
- Runtime: `ExecutionContext`/`Property` em `rvsec-core` (store por identidade); logger
  efetivo `ErrorCollector` de `rvsec-logger-logcat` (`Log.v("RVSEC", …)`); parser
  `rv-coverage/parser/log/logcat_parser.py`.

## Anomalias registradas

1. `jca/MultiSpec_1MonitorAspect.aj` untracked gerado hoje 10:39 **dentro da árvore de
   specs** `jca/` — violação do procedimento (geração fora de scratch) anterior à
   auditoria; não contamina o corpus (specs limpas vs HEAD), mas fica registrado.
2. 4 specs byte-idênticas entre `jca` e `jca_android`: DHGen, GCM, HMAC,
   RandomStringPassword.
3. Heterogeneidade host×Docker (platforms 37.0 × 36; ajc só em Docker) ameaça qualquer
   reprodução fora de container.

## G0 — Proveniência: **PASS com ressalvas registradas** (itens acima).

## Piloto (§19.3)

- Spec complexa: `CipherSpec.mop` ↔ `Cipher.cryptsl` (concentra D-S9/D-S11 e orçamento).
- Spec simples: `GCMParameterSpecSpec.mop` ↔ `GCMParameterSpec.cryptsl` (byte-idêntica ao
  congelado — também testa a tese D-S10).
- Três pareceres independentes (Alfa/Beta/Gama), mesmo esquema de claims, sem leitura
  cruzada antes da primeira rodada. Execuções de geração somente em scratch.
