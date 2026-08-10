# Pré-registro — auditoria de fidelidade das specs `jca_android`

Data: 2026-08-08. Protocolo-fonte: `docs/20260808_validar_specs_jca_android.md`.
Este documento é escrito **antes** de qualquer parecer de aderência. Alterações posteriores
a critérios aqui definidos devem ser registradas em `fase0/desvios.md` como desvio do
pré-registro, com justificativa e data.

## 1. Perguntas de pesquisa

- **RQ1 (fidelidade por spec)**: para cada uma das 23 specs `.mop` de `jca_android`, a
  tradução preserva a semântica da regra CrySL correspondente de
  `MetaCrySL/generated/api30/`, nas sete dimensões de equivalência do modelo semântico
  (`fase0/modelo_semantico.md`)?
- **RQ2 (fidelidade do conjunto)**: o conjunto completo — incluindo composição entre specs
  via predicados (`REQUIRES`/`ENSURES`/`NEGATES`), geração conjunta, weaving e observação
  em Android — satisfaz os gates G0–G13 para a decisão `READY`?
- **RQ3 (classificação das divergências)**: cada diferença encontrada é
  `DIVERGÊNCIA_EQUIVALENTE_COMPROVADA`, `LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA`, `OMITIDA`,
  `INCORRETA` ou `INCONCLUSIVA` — e com que impacto em falsos positivos (FP), falsos
  negativos (FN), diagnóstico e reprodutibilidade?

O oráculo normativo são as regras CrySL de `api30`. A change GH101 é hipótese de
implementação; seus registros são alegações até reprodução. As regras CrySL entram
**cruas** — o perfil Android modela disponibilidade, não recomendação — e o viés
disso deve ser registrado, não corrigido no oráculo.

## 2. Unidades de análise

Cláusula CrySL → evento (CrySL e MOP) → spec → trace → site instrumentado → APK →
conjunto. Resultados relatados sempre na unidade em que foram medidos; proibido agregar
entre unidades sem declarar a agregação (em especial no `errors.csv`: linhas ≠
`unique_msg` ≠ APKs ≠ sites).

## 3. Critérios de decisão por teste

| Teste | PASS | FAIL | INCONCLUSIVE |
|---|---|---|---|
| Inclusão `L(CrySL) ⊆ α(L(MOP))` | verificação algorítmica sobre autômatos, sem contraexemplo | menor trace separador exibido | autômato efetivo não extraível |
| Inclusão `α(L(MOP)) ⊆ L(CrySL)` | idem | idem | idem |
| Captura de pointcut | `Esperado ⊆ Capturado` e `Capturado ∩ Vizinhos = ∅` contra `android.jar` real | membro esperado não casado, vizinho casado, zero-fire ou double-fire não justificado | matcher de produção não executável |
| Binding/cláusula | argumento requerido ligado no objeto/posição corretos, observável no handler | não ligado, posição errada, `condition` inalcançável | não determinável por leitura + execução |
| Predicados/composição | writer/reader/`remove` consistentes no grafo inter-specs, constantes corretas | writer sem reader com efeito semântico, constante errada, escopo errado | grafo incompleto |
| Gerabilidade | ≤17 eventos; geração limpa em scratch; tempo/RSS medidos | >17 eventos, erro/warning relevante | geração não reproduzível |
| Diagnóstico | mensagem atribui regra/cláusula/evento/estado/`__LOC`; sem `unknown`; dedupe estável | `unknown`, atribuição ambígua, `@fail` espúrio junto a erro específico | handler não exercitado |
| Teste diferencial/mutação | corpus discriminante sem FP/FN; mutantes não equivalentes mortos | FP/FN observado | mutante sobrevivente ⇒ adequação da suíte INCONCLUSIVA |

Regras transversais: ausência de firing nunca é aceitação (distinguir evento não
alcançado, pointcut não casado, `condition(false)`, emissão perdida, monitor não chamado,
trace aceito); `INCONCLUSIVE` nunca vira aprovação; não há compensação entre dimensões;
equivalência global exige as sete dimensões, não apenas o `ORDER`.

## 4. Severidade

- **Crítica**: FP ou FN demonstrável em trace realizável; cláusula `INCORRETA`; perda de
  emissão; fail-open. Bloqueia `APROVADA` da spec e `READY` do conjunto.
- **Major**: cláusula `OMITIDA` sem registro de omissão deliberada; diagnóstico
  inatribuível; double-fire não justificado; divergência sem classificação.
- **Minor**: resíduo diagnóstico (mensagem subótima, porém atribuível), custo de geração
  próximo do teto, ameaça de observabilidade documentada.

Nenhum achado crítico ou major pode permanecer aberto após a refutação (G13).

## 5. Política de repetição e flakiness

- Verificações determinísticas (hash, parsing, autômato, matcher estático): 1 execução,
  com comando e hash do input registrados.
- Execuções dinâmicas (harness, APK): 3 repetições com seeds fixos e pré-declarados;
  divergência entre repetições ⇒ o teste é marcado flaky e o claim fica `INCONCLUSIVE`
  até isolamento da causa. Emuladores somente via `rv-experiment`/`rv-platform`
  (nunca gerenciados manualmente).
- Toda execução de JavaMOP/RV-Monitor ocorre em diretório scratch por execução —
  **nunca** sobre a árvore de specs (JavaMOP escreve `.rvm` ao lado da fonte).

## 6. Score descritivo — pesos e denominador (publicados antes de pontuar)

Subpontuações e pesos: linguagem formal 20; captura de eventos 20; bindings/cláusulas 15;
predicados/composição 15; toolchain Android 15; diagnóstico 10; reprodutibilidade 5.
Denominador: claims **resolvidos pelo juiz** naquela dimensão; claims `INCONCLUSIVE`
ficam fora do denominador e impedem chamar o score de completo. Sem média entre agentes.
`score descritivo ≠ probabilidade de correção ≠ veredito`; nunca arredondar para 100;
score não abre gate.

## 7. Vereditos e gate final

Por spec: `APROVADA` / `REPROVADA` / `INCONCLUSIVA`. `READY` do conjunto é conjunção:
23/23 `APROVADA`, gates G0–G13 todos `PASS`, nenhuma cláusula `OMITIDA`/`INCORRETA`/
`INCONCLUSIVA`, nenhum contraexemplo aberto, evidência reproduzível. Divergência aceita
pelo pesquisador exige redução formal e explícita do escopo do oráculo — nunca
"100% aderente" silencioso.

## 8. Pacote de replicação

Manifesto com hashes; comandos exatos com working directory; scripts de auditoria;
autômatos e contraexemplos em formato textual; suítes e fixtures; outputs brutos
citados por `arquivo:linha`; versões de toolchain. Tudo sob
`audit/20260808_validacao_jca_android/`.
