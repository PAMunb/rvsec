# Spinners sem opções no `.apk.json` — cry.otp e faircode (07/10/2026)

Pergunta: por que muitos spinners saem do GATOR com `entries` vazio (cry.otp: 22 registros, nenhum
com opções; faircode: 42 registros, 18 com opções)? E o aperv-tool corta essa informação?

Fontes: código-fonte em `rvsec-dataset/repos/<apk>/`, JSON de setembro em
`rvsec-dataset/jca_android/static_analysis/`, JSONs do GATOR da gh120 em
`worktrees-gator/acc/out/`, extrator `rvsec-gator/client/.../SpinnerItemExtractor.java`.
Tudo abaixo foi conferido nessas fontes, salvo onde está marcado [hipótese].

## Resposta curta

1. **O aperv-tool não corta.** O derive copia `entries` para o artefato do APE-RV: 18 de 18 no
   faircode e 3 de 3 no treehouses.
2. **cry.otp: falta um padrão no GATOR.** Os 5 spinners do app são preenchidos com
   `ArrayAdapter.createFromResource(ctx, R.array.X, layout)`. As opções são estáticas (um
   `string-array` dos recursos), mas o `SpinnerItemExtractor` não reconhece essa chamada.
3. **faircode: os spinners ficavam fora das janelas.** Dos 39 ids de spinner que trazem
   `android:entries` no XML, só 7 aparecem no JSON de setembro, e esses 7 vêm com as opções. Os
   outros 32 estão em layouts de fragment e de diálogo, que o GATOR antigo não modelava. Os 37
   spinners sem `android:entries` são preenchidos em tempo de execução, e nenhuma análise estática
   recupera essas opções.

## cry.otp (`org.cry.otp_31`)

- 5 spinners no XML (`totpSHATypeSpinner`, `motpTimeZoneSpinner`, `hotpSeedTypeSpinner`,
  `totpSeedTypeSpinner`, `totpTimeIntervalSpinner`), nenhum com `android:entries`. Os 22 registros
  do JSON são esses 5 repetidos em várias janelas.
- Todos são preenchidos no código das activities `Home` e `ProfileSetup`, sempre do mesmo jeito:
  ```java
  ArrayAdapter<CharSequence> adapter = ArrayAdapter.createFromResource(getApplicationContext(), R.array.TimeZones, R.layout.spinner_layout);
  spinner.setAdapter(adapter);
  ```
  (`Home.java:145`, `ProfileSetup.java:422, 441, 459, 462, 478`).
- O `SpinnerItemExtractor` cobre só dois casos:
  - `new ArrayAdapter<>(ctx, layout, new String[]{…})` ou com `Arrays.asList(…)`;
  - `adapter.add(literal)` e `adapter.addAll(literal[])`.
  O próprio cabeçalho do extrator lista `getResources().getStringArray(R.array.X)` como "deferred".
  `createFromResource` não aparece em lugar nenhum.
- **Correção possível, no GATOR:** reconhecer `ArrayAdapter.createFromResource(ctx, R.array.X, …)`
  e `getResources().getStringArray(R.array.X)` como fonte de itens. A resolução seria
  `R.array.X` → `res/values/arrays.xml`, que já está decodificado. O `enrichFromXml` já faz isso
  para `android:entries="@array/X"`, então a resolução do array existe. O que falta é ligar o
  `setAdapter` ao array. Seria uma mudança no GATOR, fora da gh120.

## faircode (`eu.faircode.email_2322`)

- O XML tem 82 `<eu.faircode.email.SpinnerEx>`: 45 com `android:entries` (39 ids distintos) e 37 sem.
- **Com `android:entries`:** o JSON de setembro tem 7 desses 39 ids, todos com as opções. Os 32 que
  faltam estão em `fragment_options_*.xml`, `fragment_identity.xml`, `fragment_rule.xml` e
  `dialog_*.xml`, isto é, telas de fragment e de diálogo.
  - A gh120 cria janelas `FRAGMENT`/`HOSTED`, e o `enrichFromXml` agora aceita esses tipos. Logo,
    esses spinners devem entrar com opções no JSON novo [hipótese: o faircode não foi rodado hoje;
    a análise dos 163 desta noite responde].
- **Sem `android:entries`:** são preenchidos com listas montadas em tempo de execução, por exemplo:
  - pastas e contas do banco (`FragmentAccount.java:638`, `FragmentDialogSwipes.java:54`);
  - ações de regra (`FragmentRule.java:546`) e dias da semana (`FragmentRule.java:532`);
  - tamanhos calculados (`ActivityWidgetUnified.java:439`, `FragmentOptionsSend.java:276`).
  Não há texto estático para capturar; está correto saírem vazios.

## O que não foi medido

- A frequência de `createFromResource` e `getStringArray` nos 163 apps. Para isso seria preciso
  varrer `rvsec-dataset/repos`, o que no HDD só deve ser feito com uma lista de apps e por lote.
- Os spinners em classes que não são activity (fragments, listeners anônimos): o extrator só
  percorre métodos de activities.

## Atualização das 14:30: corrigido na gh120 (tarefa 2.7)

O extrator passou a ler `createFromResource` e `getStringArray`/`getTextArray`. No cry.otp,
três outros pontos impediam o resultado, e foram corrigidos juntos:
- os ids chegam como leitura de campo de `R$id`/`R$array` (R não final), não como constante;
- o registrador `$i0` guarda o id do spinner e depois o do array, então o id do `findViewById`
  passou a ser resolvido no próprio `findViewById`;
- a mesma variável guarda vários adapters, então os itens passaram a ser indexados pelo ponto
  de criação do adapter.

Resultado no cry.otp [conferido]: `totpSHATypeSpinner` (SHA-1, SHA-256, SHA-512),
`hotpSeedTypeSpinner` e `totpSeedTypeSpinner` (Hexadecimal, ASCII, Base32), `motpTimeZoneSpinner`
(40 fusos), `totpTimeIntervalSpinner` (30 Seconds, 60 Seconds). Janelas, widgets e as 255
transições ficaram iguais por conteúdo.
