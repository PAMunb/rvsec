# Tarefa 11.9 — as duas disposições que a D-17 re-deriva, e o censo que vem com elas

**Data**: 2026-08-26 · **Grupo**: 11 (F8, D-16/D-17) · **Espécie**: re-derivação, sem mudança de acusação
**Oráculo único**: `RVSec-replication-package/tools/rules/` (49 regras, sha256 `d7bcc019…`)
**Par de arnês**: nenhum devido — nenhuma linha de programa mudou

## 1. Por que a tarefa existe

A 11.1 pediu que **toda** disposição fosse re-derivada contra o oráculo e não copiada. Duas não
podiam ser derivadas do texto da regra: as duas `unreachable-composition`, que dizem que os dois
lados existem e a plataforma se recusa a compô-los. Elas entraram no instrumento como *overrides*
nomeados, com a medição citada, e é aí que mora o modo de falha que uma re-derivação existe para
pegar — **uma delas chegou com a conclusão certa e a razão de outra classe**, que é exatamente a
forma da D-17 e é o que um ledger verde não mostra.

A tarefa é **só registro**: `predicate_ledger.csv`, `predicate_graph.csv` e a prosa que os cita.
Nenhum evento muda, nenhuma leitura abre, nenhuma acusação muda de classe — e é por isso que não
há par de arnês devido. As edições de comentário do `KeyPairGeneratorSpec.mop` re-chavearam um
hunk e ele foi re-chaveado; nenhuma linha de programa foi tocada.

## 2. (a) `KeyPairGenerator preparedDH` — a disposição se move

`predicate_ledger.csv` linha 34, `KeyPairGenerator.crysl:37`
(`algorithm in {"DiffieHellman", "DH"} => preparedDH[params]`):
**`unreachable-composition` → `unmonitored-producer`.**

A medição da 5.8 fica de pé e é re-citada, não repetida. Foi re-rodada em 26/08 sobre Temurin 21,
e o que ela diz é isto:

```
KeyPairGenerator.getInstance("DH").initialize(new DHGenParameterSpec(2048, 0))
  -> InvalidAlgorithmParameterException: Inappropriate parameter type
KeyPairGenerator.getInstance("DH").initialize(new DHParameterSpec(p, g))   [RFC 3526, grupo 14]
  -> ACEITO
```

**O que cai é a frase em que a disposição se apoiava**: *"A DH key pair is initialised from a
`DHParameterSpec`, which no rule ensures."* O catálogo gerado não declara `DHParameterSpec.cryptsl`
nenhuma; o oráculo declara `DHParameterSpec.crysl:21 ENSURES preparedDH[this]` — e é precisamente
o tipo que o `initialize` aceita.

A linha já carregava a evidência nas suas próprias colunas, o que é o que torna isto uma
re-derivação e não uma descoberta: `counterparts` lê `DHGenParameterSpec|DHParameterSpec` e
`counterparts_with_mop` lê `DHGenParameterSpec` sozinho.

Continua **não fiada**, e a razão agora é a honesta: uma leitura em
`KeyPairGeneratorSpec.init3/init4` responde `NOT_OBSERVED` para todo programa DH conforme **porque
o produtor que esse programa usa não é monitorado**, e não porque produtor algum pudesse existir. O
que fecharia a cláusula é um `.mop` para `DHParameterSpec`, e escrever um é classe de acusação
nova, que a D-16 mantém fora desta mudança.

Onde a correção ficou escrita: a linha 34 do ledger (pelo override do instrumento, não à mão), a
linha do `DHGenParameterSpecSpec` no `predicate_graph.csv`, o parágrafo do
`KeyPairGeneratorSpec.mop` que fechava com a frase falsa, e o `predicate_ledger.md`.

Um efeito lateral do mesmo parágrafo: ele descrevia `preparedEC` como `unclosable`. Isso valia
contra o catálogo gerado e deixou de valer na **11.1** — o oráculo o garante em
`ECGenParameterSpec.crysl:25` e `ECParameterSpec.crysl:17`, nenhum com `.mop`, então é
`unmonitored-producer` e `unclosable` sumiu do ledger inteiro. Re-citado, não re-derivado: o
crédito é da 11.1.

## 3. (b) `Mac preparedHMAC` — a disposição sobrevive verbatim

`predicate_ledger.csv` linha 38, `Mac.crysl:53`: **`unreachable-composition` fica onde estava**, e
é isso que faz de (a) um achado em vez de um palpite.

O produtor é `javax.xml.crypto.dsig.spec.HMACParameterSpec` (`HMACParameterSpec.crysl:14`), do
módulo `java.xml.crypto`, e o `android.jar` da android-30 não carrega entrada alguma sob
`javax/xml/crypto`. **É fato sobre a plataforma e não sobre um catálogo**, e é por isso que a troca
de oráculo não o toca.

A metade JVM da medição foi refeita, porque a antiga corria sobre os doze nomes da lista retirada.
Sobre os nove da `Mac.crysl:44`, em Temurin 21:

```
HmacSHA256 / HmacSHA384 / HmacSHA512      -> "HMAC does not use parameters"
HmacPBESHA1 / PBEWithHmacSHA1 / 224 / 256 / 384 / 512 -> "PBEParameterSpec type required"
```

Todos os nove resolvem — a única diferença contra a medição antiga, que nomeava `PBEwithHmacSHA`,
que nenhum provedor tem. A linha é re-citada contra as linhas expert e a disposição fica.

**A tarefa fecha só se as duas metades forem derivadas**: uma linha que se moveu e uma que não é a
forma de uma re-derivação. Duas que se movem, ou nenhuma, quer dizer que a varredura respondeu a
outra pergunta.

## 4. A aritmética não se move

| | antes | depois |
|---|---:|---:|
| cláusulas varridas | 135 | **135** |
| `wireable` | 25 | **25** |
| `unmonitored-producer` | 8 | 9 |
| `unreachable-composition` | 2 | 1 |

As duas contagens que mudam são uma linha atravessando entre elas, e não uma linha aparecendo ou
saindo. É a checagem mais barata de que uma re-derivação continuou re-derivação, e é o que a 11.7
verifica.

O `--emit ledger` reproduz o `predicate_ledger.csv` commitado byte a byte; o
`predicate_ledger_delta.csv` **não muda**, porque a delta compara presença e forma de cláusula, não
disposição.

## 5. (c) e (d) O censo, emitido e não digitado

O censo passa a sair do instrumento:

```bash
python scripts/gh105_expert_ledger.py --emit census
```

É a diferença entre um registro e um backlog: uma lista digitada à mão em agosto não se move quando
o ledger se move, e pode omitir uma linha em silêncio. Uma cláusula `REQUIRES` de regra que o
conjunto especifica é **inobservável** a menos que a disposição seja `wireable`; uma `ENSURES` ou
`NEGATES` de regra especificada é **ilegível** quando nada que o conjunto observa a exige.

**REQUERIDO E NÃO OBSERVÁVEL: 10 cláusulas, 9 predicados.**
**GARANTIDO E NÃO LEGÍVEL: 18 cláusulas, 12 predicados.**
A saída completa está reproduzida verbatim em `data/jca_android/predicate_ledger.md`.

### A derivação é mais larga que o esboço, e é para isso que emiti-la serve

A 11.9(c) nomeava **seis** predicados: `preparedRSA`, `preparedDSA`, `preparedEC`, `preparedOAEP`,
`preparedAlg` e `generatedManagerFactoryParameters`. A varredura acha **nove**, sobre dez cláusulas:

- `generatedManagerFactoryParameters` é exigido por **duas** regras (`KeyManagerFactory.crysl:32` e
  `TrustManagerFactory.crysl:29`), não uma;
- `preparedDH` entra na classe, porque a 11.9(a) o moveu para ela;
- `preparedHMAC` pertence à classe: `unreachable-composition` é outra maneira de ser inobservável,
  não uma isenção;
- `preparedKeyMaterial` (`SecretKeySpec.crysl:23`) pertence a ela porque o seu produtor
  (`SecretKey.crysl:17`) não tem `.mop` — o `SecretKeySpec.mop` é o propagador e não especifica
  regra nenhuma.

A 11.9(d) nomeava seis e a varredura acha **doze**: entram `wrappedKey`, `cipheredInputStream`,
`cipheredOutputStream`, `generatedSSLContext`, `generatedSSLEngine` e `generatedMessageDigest`.

E uma entrada do esboço já estava resolvida antes desta tarefa: `preparedEC` aparece nele como
`unclosable`, que é o que era contra o catálogo gerado — a **11.1** já o re-derivou, e a tabela de
delta do `predicate_ledger.md` registra o movimento.

**A conclusão de pé não muda com o alargamento**: fechar qualquer um deles significa uma
especificação para uma regra que o conjunto não tem, que a D-16 mantém fora desta mudança. A metade
recíproca está no registro para que a metade requerente não se leia como unilateral —
`preparedPBE`, `speccedKey` e `generatedMessageDigest` são exigidos só por regras sem `.mop`,
enquanto `digested`, `signed`, `verified`, `generatedKeypair`, `wrappedKey`, `cipheredInputStream`,
`cipheredOutputStream`, `generatedSSLContext` e `generatedSSLEngine` são exigidos por **nenhuma das
49**. Esses nove são becos sem saída do oráculo e não deste conjunto, e dizê-lo é o que impede um
leitor futuro de propor fiação para eles.

## 6. Observação encontrada e não reparada

A isenção do `gh105_sole_oracle_gate.py` para o `predicate_ledger.csv` diz "reproduced by its
`--check`". O `--check` do `gh105_expert_ledger.py` afirma que **a aritmética fecha**, não que o
arquivo commitado é o que o instrumento emite — quem reproduz o arquivo é
`--emit ledger --out <arquivo>` seguido de um `diff`, que foi o que esta tarefa fez e o que está
escrito no `predicate_ledger.md`. A garantia existe e é forte, mas a frase da isenção promete uma
checagem mais estreita do que a que roda. Apertar o `--check` para comparar o arquivo é uma linha
de instrumento e pertence à **11.7**, que é quem verifica o grupo.

## 7. Bateria, ao fechar a tarefa

```
gh105_sole_oracle_gate      exit=0     gh104_divergence_record   exit=0
gh105_expert_ledger         exit=0     gh104_message_gate        exit=0
gh105_expert_alphabet       exit=0     gh104_mop_lint            exit=0
gh105_expert_conformance    exit=0     gh105_predicate_graph     exit=0
gh105_spec_gates            exit=0     gh105_order_gate          exit=1  ← as duas da 11.6
```

**Paridade: 185 passed / 3 failed** — a linha de base, com as mesmas três falhas pré-existentes de
outras frentes. Sem quarta falha.
