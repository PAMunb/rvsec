# APE-RV LLM: Integração rv-android (aperv-tool)

**Data**: 2026-03-17
**Status**: Ideação (Phase 0 — entrada para Quick Path)
**Escopo**: Apenas aperv-tool (variantes + properties + testes). Não inclui calibração nem experimento final.

---

## 1. Contexto e Escopo

### 1.1 Relação com gh6 (APE side)

A change [phtcosta/ape#6](https://github.com/phtcosta/ape/issues/6) (`gh6-aperv-llm-integration`) implementa a integração LLM no loop de exploração do APE-RV (Java side):

- 7 classes de infraestrutura LLM copiadas do rvsmart (com conversão Gson→org.json)
- `ApePromptBuilder` — prompt multimodal adaptado ao GUITree do APE
- `LlmRouter` com 2 modos de routing (new-state + stagnation)
- 9 config keys com prefixo `ape.` em `Config.java`
- Pesos MOP revertidos para v1 (500/300/100)

O JAR `ape-rv.jar` buildado a partir do gh6 é o artefato de entrada para o rv-android.

### 1.2 Escopo rv-android

Esta change cobre exclusivamente o **aperv-tool** — o plugin Python que registra variantes e gera `ape.properties`:

- Registrar 2 novas variantes LLM (`sata_llm`, `sata_mop_llm`)
- Gerar `ape.properties` com as 9 config keys LLM quando a variante usa LLM
- Env var override para LLM URL (`APERV_LLM_BASE_URL`)
- Testes unitários para as novas variantes

**Fora de escopo** (changes futuras separadas):
- Calibração de parâmetros LLM (Phase F/G do ideation original `docs/20260316_aperv_llm.md`)
- Experimento final comparativo (Phase H do ideation original)

### 1.3 Diferenças entre ideation original e gh6 final

| Aspecto | Ideation original (`20260316`) | gh6 final |
|---------|-------------------------------|-----------|
| Modos LLM | 3 (new-state, epsilon-LLM, stuck) | **2** (new-state, stagnation) — epsilon-LLM removido (LLMDroid FSE 2025 mostrou que coverage-triggered > probabilístico) |
| Config keys | 5 keys genéricas | **9 keys** com prefixo `ape.` e defaults refinados |
| Pesos MOP | Mencionava revert v2→v1 | Revert **confirmado e implementado** no gh6 |
| Coordinate mapping | Euclidean distance simples | **Bounds containment first** + Euclidean fallback com tolerância proporcional |
| Raw clicks | Não mencionado | Suportado — quando LLM aponta elemento dinâmico sem UIAutomator node |

---

## 2. Mapeamento gh6 Config → ape.properties

As 9 config keys do gh6 e seus valores para cada variante LLM:

| Config Key | Tipo | Default | `sata_llm` | `sata_mop_llm` |
|-----------|------|---------|------------|----------------|
| `ape.llmUrl` | String | null | `http://10.0.2.2:30000/v1` | `http://10.0.2.2:30000/v1` |
| `ape.llmOnNewState` | boolean | true | true | true |
| `ape.llmOnStagnation` | boolean | true | true | true |
| `ape.llmModel` | String | "default" | "default" | "default" |
| `ape.llmTemperature` | double | 0.3 | 0.3 | 0.3 |
| `ape.llmTopP` | double | 0.6 | 0.6 | 0.6 |
| `ape.llmTopK` | int | 50 | 50 | 50 |
| `ape.llmTimeoutMs` | int | 15000 | 15000 | 15000 |
| `ape.llmMaxCalls` | int | 200 | 200 | 200 |

Nota: `ape.llmUrl=null` (default) desabilita completamente a LLM no Java side. As variantes sem LLM (`sata`, `sata_mop`, etc.) não escrevem nenhuma key `ape.llm*` no properties.

---

## 3. Novas Variantes

Adição de 2 variantes ao `get_variants()` existente (que já tem `default`, `sata`, `sata_mop`, `bfs`, `random`):

| Variante | `strategy` | `mop_data` | `llm_url` | Uso |
|----------|-----------|-----------|-----------|-----|
| `sata_llm` | sata | — | `http://10.0.2.2:30000/v1` | LLM guidance pura (sem MOP scoring) |
| `sata_mop_llm` | sata | static_analysis | `http://10.0.2.2:30000/v1` | Híbrido completo (MOP + LLM) |

Ambas usam os defaults da tabela acima para os demais parâmetros LLM. A calibração futura ajustará esses valores via parameter overrides.

---

## 4. Padrão de Implementação

Seguir o padrão estabelecido pelo rvsmart-tool (`rvsmart_tool/tools/rvsmart/tool.py`):

### 4.1 Variantes com `llm_url`

```python
# Em get_variants():
"sata_llm": {
    "strategy": "sata",
    "throttle_ms": 200,
    "llm_url": "http://10.0.2.2:30000/v1",
},
"sata_mop_llm": {
    "strategy": "sata",
    "throttle_ms": 200,
    "mop_data": "static_analysis",
    "llm_url": "http://10.0.2.2:30000/v1",
},
```

### 4.2 Env var override

No `configure()`, análogo ao `RVSMART_LLM_BASE_URL` do rvsmart-tool:

```python
# Allow env var override for LLM URL
llm_url_override = os.environ.get("APERV_LLM_BASE_URL")
if llm_url_override and "llm_url" in self._tool_config:
    self._tool_config["llm_url"] = llm_url_override
```

Em Docker, o `docker-compose` define `APERV_LLM_BASE_URL=http://host.docker.internal:30000/v1`.

### 4.3 Properties generation

No `_push_properties()`, quando `llm_url` está presente no config, escrever todas as 9 keys LLM:

```python
# Existing: throttle + mop
properties_content = f"ape.defaultGUIThrottle={throttle_ms}\n"
if mop_json_pushed:
    properties_content += "ape.mopDataPath=/data/local/tmp/static_analysis.json\n"

# LLM keys (quando llm_url presente)
if self._tool_config.get("llm_url"):
    properties_content += f"ape.llmUrl={self._tool_config['llm_url']}\n"
    properties_content += f"ape.llmOnNewState={str(self._tool_config.get('llm_on_new_state', True)).lower()}\n"
    properties_content += f"ape.llmOnStagnation={str(self._tool_config.get('llm_on_stagnation', True)).lower()}\n"
    properties_content += f"ape.llmModel={self._tool_config.get('llm_model', 'default')}\n"
    properties_content += f"ape.llmTemperature={self._tool_config.get('llm_temperature', 0.3)}\n"
    properties_content += f"ape.llmTopP={self._tool_config.get('llm_top_p', 0.6)}\n"
    properties_content += f"ape.llmTopK={self._tool_config.get('llm_top_k', 50)}\n"
    properties_content += f"ape.llmTimeoutMs={self._tool_config.get('llm_timeout_ms', 15000)}\n"
    properties_content += f"ape.llmMaxCalls={self._tool_config.get('llm_max_calls', 200)}\n"
```

Os defaults nas chamadas `.get()` espelham exatamente os defaults do `Config.java` do gh6.

---

## 5. Arquivos Impactados

| Arquivo | Mudança | LOC estimado |
|---------|---------|--------------|
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | `get_variants()` (+2 variantes), `configure()` (env var override), `_push_properties()` (LLM keys) | ~50-80 |
| `modules/aperv-tool/tests/test_aperv_tool.py` | `TestVariants` (7 variantes), `TestConfigure` (env var override), novos testes para properties LLM | ~40-60 |

**Dependência externa**: JAR `ape-rv.jar` buildado a partir do gh6 merged. Copiar para `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` (padrão JarResolver).

---

## 6. Dependências

| Dependência | Status | Bloqueante? |
|------------|--------|-------------|
| gh6 merged no repo APE | Em andamento | Sim — JAR precisa ser buildado |
| SGLang server | Disponível quando GPU ligada | Não para implementação, sim para validação manual |

---

## 7. Track Selection

**Quick Path** — não há decisões de design pendentes:

- Arquitetura LLM decidida no gh6 (APE side)
- Padrão de variantes/properties já estabelecido pelo rvsmart-tool
- Implementação é wiring mecânico: config dict Python → `ape.properties` Java
- Escopo pequeno: ~90-140 LOC total (tool.py + testes)

---

## 8. Próximos Passos

1. Aguardar gh6 merge + build do JAR `ape-rv.jar`
2. Criar GitHub issue em PAMunb/rvsec para a change rv-android
3. Iniciar Quick Path: `plan.md` → `tasks.md` → implementar → verificar
4. Validação manual: rodar `aperv:sata_mop_llm` no cryptoapp com SGLang ativo
5. **Futuro** (changes separadas):
   - Calibração de parâmetros LLM via Optuna (Phase F/G do ideation original)
   - Experimento final comparativo (Phase H do ideation original)
