# Modelo semântico comum — equivalência CrySL → JavaMOP neste estudo

Data: 2026-08-08. Vale para todas as 23 specs e para os três agentes adversariais.
Nenhum parecer pode usar uma noção de equivalência diferente desta sem registrar desvio.

## 1. Traces e eventos observáveis

Um **trace** é uma sequência finita de chamadas Java observáveis. Cada chamada carrega,
quando aplicável: identidade do receptor (identidade de referência, não `equals`),
assinatura resolvida (classe declarante efetiva, nome, descritor), argumentos, valor de
retorno, exceção lançada, localização (`__LOC`) e posição na ordem do trace.

Três planos de eventos:

- **Chamada Java real**: o que a JVM/ART executa no APK instrumentado.
- **Evento CrySL**: rótulo da seção `EVENTS` da regra, possivelmente agregado
  (`ev := e1 | e2`), com parâmetros nomeados e `_` como argumento anônimo (não é defeito).
- **Evento MOP**: evento declarado na spec `.mop`, definido por pointcut + event body,
  com semântica `before`/`after`/`after returning`/`after throwing`.

## 2. Função de abstração α

`α` relaciona chamada Java real ↔ evento CrySL ↔ evento MOP. Para cada spec o agente
Alfa materializa `α` como tabela. Para **fusões** (vários métodos CrySL → um evento MOP)
registrar: a relação muitos-para-um, o predicado discriminante usado para recuperar a
distinção (`instanceof`, retorno, aridade, `condition(...)`), o agregado CrySL
correspondente e o perfil de binding preservado. Para **divisões** (um evento CrySL →
vários eventos MOP), registrar a união e provar disjunção dos pointcuts. Equivalência de
linguagem é sempre avaliada **módulo α**: `L(CrySL) ⊆ α(L(MOP))` e `α(L(MOP)) ⊆ L(CrySL)`.

## 3. Parametrização e ciclo de vida

- **Objeto da propriedade**: qual objeto parametriza/indexa cada monitor JavaMOP
  (`SpecName(Tipo obj)`), contra qual objeto a regra CrySL prende seu ciclo de vida.
- **Identidade**: o índice paramétrico do JavaMOP usa identidade de referência (weak
  refs); duas instâncias `equals` porém distintas por identidade devem ter monitores
  isolados. Boxing/cache de primitivas é ameaça a registrar quando o objeto indexado for
  wrapper.
- **Ciclo de vida CrySL**: criação (primeiro evento do `ORDER`), estados intermediários,
  aceitação (prefixo válido completo), violação, e descarte/GC do objeto. Mapear para:
  creation event do monitor, estados do FSM gerado, categoria `fail`/`match`, e
  `remove(Property)` — distinguindo remoção global de `remove(Property, object)` por
  instância.
- **Interleaving**: duas instâncias intercaladas não podem contaminar o estado uma da
  outra; reuso do mesmo objeto (novo ciclo) deve corresponder ao que a regra permite.

## 4. Predicados entre specs

`REQUIRES`/`ENSURES`/`NEGATES` de CrySL viram, na tradução, escritas/leituras de
`Property` sobre um `ExecutionContext`. Semântica auditável:

- **writer**: evento/handler que grava a `Property` (constante e objeto corretos);
- **reader**: `condition(...)` ou corpo que consome; reader sem producer possível é
  cláusula inalcançável; writer sem reader é efeito morto (registrar se semanticamente
  relevante);
- **NEGATES**: remoção/invalidação — escopo (global × por objeto) deve espelhar a regra;
- a identidade usada pelo `ExecutionContext` deve coincidir com a identidade usada pelo
  índice JavaMOP, senão o predicado liga instâncias erradas;
- edges que atravessam specs formam o grafo de composição do conjunto (auditoria de
  conjunto, não só por spec).

## 5. Distinções obrigatórias de não-ocorrência

Diferenciar sempre: (a) evento **não alcançado** (o código não executou o site);
(b) **pointcut não casado** (site executou, matcher não casou); (c) **suprimido** por
`condition(false)` (advice rodou, evento não foi ao monitor — supressão silenciosa, não
transição); (d) **emissão perdida** (advice/instrumentação deveria emitir e não emitiu —
hipóteses GH100); (e) **monitor não chamado** (evento emitido, dispatch falhou);
(f) trace **aceito** (monitor rodou e não violou). Ausência de firing nunca é evidência
de aceitação.

## 6. As sete equivalências (todas obrigatórias para `APROVADA`)

1. **Linguagem do `ORDER`**: dupla inclusão módulo α, verificada algoritmicamente sobre
   o autômato de referência (normalizado da regra) × autômato **efetivo** do monitor
   gerado (extraído do artefato, não da sintaxe `.mop`).
2. **Captura de eventos**: `Esperado ⊆ Capturado`, `Capturado ∩ Vizinhos = ∅`, sem
   zero-fire/double-fire, contra o `android.jar` API 30 real.
3. **Bindings e predicados de evento**: cada argumento requerido ligado na posição/objeto
   corretos e disponível onde o corpo o usa.
4. **Constraints**: `CONSTRAINTS` da regra ou traduzidas com o mesmo conjunto de valores,
   ou registradas como omissão deliberada (o que bloqueia aderência total).
5. **Paramétrica/ciclo de vida**: §3 acima.
6. **Diagnóstica**: violação atribuível a regra/cláusula/evento/estado/`__LOC`, sem
   `unknown` e sem `@fail` espúrio acompanhando erro específico.
7. **Observacional no pipeline Android**: o que o monitor decide é o que sobrevive a
   weaving (AJC e dexlib2), execução, logcat, parser e `errors.csv` — mesma
   cardinalidade, ordem e conteúdo.

Declarar equivalência global com apenas a dimensão 1 validada é proibido.

## 7. Estados da matriz normativa

`FIDELIDADE_DEMONSTRADA` · `DIVERGÊNCIA_EQUIVALENTE_COMPROVADA` ·
`LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA` · `OMITIDA` · `INCORRETA` · `INCONCLUSIVA`.
Fusão sintática não é defeito por si; deve, porém, preservar linguagem, agregado,
binding profile, corpo, efeitos laterais e diagnóstico — ou demonstrar formalmente a
discriminação que os recupera. Limitação registrada por GH101 continua bloqueando a
alegação de aderência total, salvo redução explícita de escopo pelo pesquisador.
