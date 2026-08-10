# Retomada — validação das specs jca_android

Projeto de doutorado (RV-Android): verificação de conformidade entre 23 especificações
JavaMOP e as regras CrySL que as originaram. Sessão anterior: "validar-specs"
(2026-08-08), interrompida por limite de tokens.

## Documentos que governam o trabalho

1. Protocolo: `docs/20260808_validar_specs_jca_android.md` (seguir a ordem da seção 19)
2. Critérios pré-registrados: `audit/20260808_validacao_jca_android/fase0/pre_registro.md`
3. Definição de equivalência: `audit/20260808_validacao_jca_android/fase0/modelo_semantico.md`
4. Manifesto do corpus: `audit/20260808_validacao_jca_android/fase0/manifesto.md`

## Estado atual

- Fase 0 (congelamento): completa. Ver `fase0/manifesto.md`.
- Piloto (2 specs: CipherSpec e GCMParameterSpecSpec): pareceres dos 3 revisores,
  síntese do juiz, revisão independente e respostas do juiz — tudo pronto em
  `audit/20260808_validacao_jca_android/pilot/`. Resultado provisório: as duas specs
  não passaram nos gates cobertos. Detalhes: `pilot/juiz_sintese.md`,
  `pilot/juiz_respostas_refutacao.md`, `pilot/juiz_claims_resolvidos.csv` (rev. 2).
- Falta apenas: a seção "Decisão final pós-refutação" no fim de
  `pilot/juiz_sintese.md` (o agente parou antes de escrevê-la).

## Próximos passos

1. Fechar o piloto (mecânico): re-somar o score a partir de
   `pilot/juiz_claims_resolvidos.csv` com os pesos da seção 6 do `pre_registro.md`,
   escrever a seção "Decisão final pós-refutação" em `pilot/juiz_sintese.md`
   (vereditos, score, tabela de mudanças vs primeira síntese) e criar
   `fase0/desvios.md` com os desvios D-piloto-1..4 (texto já proposto em
   `juiz_sintese.md` e `juiz_respostas_refutacao.md`, objeção REF-06).
2. Aplicar os ajustes de processo recomendados pelo juiz (listados no fim de
   `juiz_sintese.md`) na rodada seguinte.
3. Auditar as 21 specs restantes em lotes, com 3 revisores independentes por lote,
   como no piloto (o pareamento spec↔regra está em `fase0/inventario_pareamento.md`).
   Antes de auditar `RandomStringPassword.mop`, perguntar ao pesquisador qual é o
   oráculo dela (não tem regra CrySL).
4. Verificações de conjunto (seção 19.5 do protocolo) e análise do errors.csv
   (hipóteses iniciais em `pilot/gama_historico.md`).
5. Juízo global, revisão independente, vereditos e matriz de gates (seções 15–17).
6. Só depois: propor correções das specs e evolução da skill rv-analyze-spec, em
   patches separados.

## Cuidados operacionais

- Gerar monitores sempre em diretório scratch, nunca dentro da árvore de specs
  (a ferramenta escreve arquivos ao lado da fonte). Comandos de geração: ver
  `modules/rv-monitor-generator/src/rv_monitor_generator/runtime_verification_generator.py`
  (linhas ~211 e ~267). Conferir o stderr (exit 0 não garante sucesso).
- Emulador Android: somente via rv-experiment/rv-platform, nunca manualmente.
- MetaCrySL e o diretório de specs `jca` são somente leitura.
- Working tree tem ~549 arquivos modificados de outros trabalhos: não commitar nada
  sem o usuário pedir.
- Subagentes: prompts autocontidos com caminhos absolutos; cada revisor escreve só
  arquivos com seu prefixo (alfa_/beta_/gama_/juiz_/refutacao_) para preservar a
  independência entre pareceres.
- Caminhos, hashes e versões da toolchain: `fase0/toolchain_ambiente.md`.
- pytest do repo: sempre `--import-mode=importlib -o "addopts="`.

Comece pelo passo 1.
