# Plan: Parse components{} section in StaticAnalysisParser

**Change**: gh46-parse-components
**Date**: 2026-03-31
**Track**: Quick Path
**Priority**: P1
**GitHub Issue**: #46
**Affected Domains**: Analysis (rv-static-analysis, rv-android-core)

## Context

O GATOR Java client produz uma seção `components{}` no JSON de análise estática desde gh45/rvsec#45. Esta seção contém dados de triggering para os 4 tipos de componentes Android (activities, services, receivers, providers) com intent-filters, authorities, exported status e MOP reachability. O parser Python (`StaticAnalysisParser`) ignora esta seção — os dados existem no JSON mas são descartados. A spec `openspec/specs/analysis/spec.md` foi parcialmente atualizada no gh45 — o requirement text e os cenários de JSON output mencionam `components{}`, mas a seção Data Models e os cenários de parsing Python NÃO foram atualizados. Esta change corrige esses gaps no spec além de implementar o código.

## Scope

Mudança puramente aditiva — sem breaking changes. O campo `components` em `StaticAnalysisData` tem `default_factory`, então todos os callers existentes continuam funcionando.

### JSON structure (produzida pelo GATOR)

```json
"components": {
  "activities": [{
    "className": "...", "isMain": true,
    "intentFilters": [{"actions": [...], "categories": [...]}],
    "exported": true, "reachesMop": false, "mopMethods": []
  }],
  "receivers": [{ mesma shape que activities }],
  "services": [{ mesma shape que activities }],
  "providers": [{
    "className": "...", "isMain": false,
    "authorities": "com.example.provider",
    "exported": false, "reachesMop": false, "mopMethods": []
  }]
}
```

Diferença: providers usam `authorities` (string) em vez de `intentFilters` (array).

## File Inventory

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `modules/rv-android-core/src/rv_android_core/domain/components.py` | CRIAR | IntentFilter, ComponentInfo, Components |
| `modules/rv-android-core/src/rv_android_core/domain/static.py` | MODIFICAR | Add components field |
| `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py` | MODIFICAR | Add _parse_components() |
| `modules/rv-android-core/tests/domain/test_components.py` | CRIAR | Domain model tests |
| `modules/rv-static-analysis/tests/parser/static/test_static_analysis_parser.py` | MODIFICAR | Add TestComponentsParsing |
| `openspec/specs/analysis/spec.md` | MODIFICAR | Add Components/ComponentInfo/IntentFilter to Data Models, add parser scenario, update StaticAnalysisData description |

## Execution Order

- Group 1 (domain models): independente
- Group 2 (parser): depende de Group 1
- Group 3 (tests): depende de Groups 1+2

## Acceptance Criteria

1. `StaticAnalysisData` tem campo `components` com `Components` container
2. `Components` fornece listas tipadas: `activities`, `receivers`, `services`, `providers`
3. `ComponentInfo` contém: `class_name`, `component_type`, `is_main`, `intent_filters`, `authorities`, `exported`, `reaches_mop`, `mop_methods`
4. Parser lida com `components{}` ausente gracefully (retorna Components vazio)
5. Callers existentes de `StaticAnalysisData(Classes(), Windows(), WTG())` continuam funcionando
6. Todos os testes existentes passam + testes novos para components
7. Smoke test: parse JSON real do GATOR e verificar contagens
