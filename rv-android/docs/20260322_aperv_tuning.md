# APE-RV Fine-Tuning: Pre-Plano Exploratório

**Data**: 2026-03-22
**Status**: Brainstorming / Exploratório
**Contexto**: Investigar viabilidade e estratégias de fine-tuning de Qwen3-VL para o APE-RV

---

## 1. Motivação

O APE-RV usa Qwen3-VL-4B-Instruct para seleção de ações durante exploração de aplicativos Android. O modelo recebe um screenshot + lista estruturada de widgets (da hierarquia UIAutomator) e deve retornar uma tool call (`android_click`, `android_type_text`, etc.) com coordenadas precisas.

**Problemas atuais:**

1. **37.3% no-match rate** — o LLM prediz coordenadas que não correspondem a nenhum widget (3.554/9.525 chamadas no exp3)
2. **Formato inconsistente de tool call** — SGLang retorna ~50% nativo OpenAI, ~50% XML/JSON, exigindo parser complexo com fallback multi-nível
3. **Sem consciência de histórico** — o LLM não entende bem o estado de exploração (quais ações já foram tomadas, quais screens já foram visitados)
4. **Coverage pior que baseline** — variante LLM: 27.60% method coverage vs 28.35% sem LLM (p=0.014)

**Por que fine-tuning?** O gh43 está validando se prompt engineering resolve. Se não resolver, fine-tuning é o próximo passo lógico. Mesmo que prompts melhorem, fine-tuning pode amplificar esses ganhos.

**Abordagem única na literatura**: A survey SOTA (21 ferramentas) revelou que **nenhuma ferramenta madura usa predição de coordenadas cruas**. Todas usam Set-of-Marks (SoM) ou seleção de lista numerada. APE-RV é um caso sem precedentes — fine-tuning pode ser essencial para viabilizar esta abordagem.

---

## 2. Objetivos do Fine-Tuning (por prioridade)

1. **Action selection** — Dado screenshot + hierarquia + histórico, selecionar a ação mais promissora para exploração
2. **Formato consistente** — Modelo sempre retorna tool calls no formato OpenAI nativo (elimina necessidade do parser de fallback)
3. **Consciência de histórico** — Compreender trajetória de exploração, evitar revisitar ações/telas já exploradas
4. **Grounding de coordenadas** — Melhorar precisão espacial (coordenada predita → centro do widget correto)

---

## 3. Panorama da Literatura: Como Outros Treinam GUI Agents

### 3.1 Trabalhos Relevantes

| Trabalho | Modelo Base | Dados Treinamento | Estratégia | Resultado |
|----------|-------------|-------------------|------------|-----------|
| **ZonUI-3B** | Qwen2.5-VL-3B | ~24K exemplos (AMEX + ShowUI + UGround) | LoRA 2-stage: (1) cross-platform semantics (2) resolution adaptation | 91.3% mobile grounding (ScreenSpot-v2) |
| **OS-Atlas** | InternVL2-4B / Qwen2-VL-7B | 13M+ GUI elements, multi-platform | 2-phase: (1) grounding pre-training (2) action fine-tuning | SOTA cross-platform |
| **GUI-Actor** | VLM backbone | SFT only | Attention-based `<ACTOR>` token, coordinate-free | 88.3% avg (ScreenSpot) |
| **GUI-Actor-LiteTrain** | VLM frozen | ~19-103M params treinados | Congela backbone, treina apenas head | Melhoria substancial preservando capabilities gerais |
| **AgentCPM-GUI** | CPM backbone | 12M grounding + 55K trajetórias | 3-stage: grounding → SFT → GRPO (RL) | SOTA em apps chineses |
| **UI-E2I-Synth** | VLM | Dados sintéticos larga escala | Síntese automatizada de grounding data | Melhora generalização |

### 3.2 Insights Chave

1. **Volume não é tudo**: ZonUI-3B atingiu 91.3% com apenas ~24K exemplos. Diversidade de fontes importa mais que quantidade bruta. Treinamento com ~16K exemplos (1/7 do dataset) atingiu accuracy comparável ao dataset completo.

2. **Two-stage é o padrão**: Praticamente todos os trabalhos bem-sucedidos usam pelo menos 2 estágios: (1) grounding/compreensão visual e (2) ação/tarefa.

3. **LoRA é suficiente**: ZonUI-3B treinou numa única RTX 4090 (24GB). Não é necessário full fine-tuning.

4. **Coordinate-free é alternativa**: GUI-Actor elimina predição de coordenadas com token de atenção — relevante como plano B se coordinate grounding não funcionar.

5. **Qwen-VL tem grounding nativo**: A família Qwen2.5-VL/Qwen3-VL já tem suporte nativo a coordenadas absolutas [0, 1000). Fine-tuning refina esta capability, não a cria do zero.

6. **Congelar backbone é viável**: GUI-Actor-LiteTrain mostra que treinar apenas componentes novos (~19M params) já dá resultados — opção ultra-conservadora que preserva as capabilities gerais do modelo.

---

## 4. Datasets Disponíveis: Análise de Viabilidade

### 4.1 Tier 1 — Com Ações + Screenshots + Hierarquia (Mais Valiosos)

#### AITW (Android In The Wild)
- **Volume**: 715K episódios, 30K instruções únicas
- **Formato**: Screenshots + accessibility tree + ações como dual-point (y,x) coordinates
- **Ações**: Touch/lift coordinates em pixels, representando clicks e scrolls
- **Apps**: Multi-domínio (General, WebShopping, Install, GoogleApps)
- **Devices**: Pixel 2 XL a Pixel 6, Android 10-13, resoluções variadas
- **Conversão para APE-RV**: Média complexidade
  - Coordinates: converter (y,x) pixels → [0, 1000) normalizado
  - Hierarquia: tem accessibility tree, converter para formato widget list do APE-RV
  - Actions: mapear dual-point para `android_click`, `android_swipe`, etc.
- **Download**: [GitHub](https://github.com/google-research/google-research/tree/master/android_in_the_wild)
- **Licença**: Apache 2.0
- **Valor**: ★★★★ — Maior dataset de ações Android, diversidade máxima. Porém é **instruction-following** (task completion), não exploração. ~33% das ações não correspondem a elementos UI detectáveis (label noise). Usar como fonte secundária, com filtragem rigorosa.

#### AndroidControl
- **Volume**: 15.283 demos, 833 apps
- **Formato**: Screenshots + accessibility trees (TFRecord + GZIP) + instruções high/low level
- **Ações**: Coordenadas de toque + tipo de ação
- **Conversão**: Alta complexidade — formato TFRecord requer `android_env` SDK
- **Download**: Via `android_env` toolkit
- **Licença**: Pesquisa
- **Valor**: ★★★★ — Instruções multi-nível, bom para ensinar raciocínio
- **Nota**: AndroidControl-Curated corrigiu ruído na avaliação — modelos 3B performam melhor que reportado originalmente

#### AMEX (Android Multi-annotation Expo)
- **Volume**: 104K screenshots, 711K functionalities, ~3K instruções com cadeias de ação (avg 13 passos)
- **Formato**: Screenshots alta resolução + bounding boxes verificadas humanamente + descrições GPT-4o
- **Apps**: 110 apps populares
- **Conversão**: Média complexidade
  - Bounding boxes verificadas → coordenadas centro → [0, 1000)
  - Descrições funcionais → element_description do tool call
  - Cadeias de ação → sequências de treinamento multi-turn
- **Download**: [HuggingFace](https://huggingface.co/datasets/Yuxiang007/AMEX)
- **Licença**: Pesquisa
- **Valor**: ★★★★★ — Grounding verificado humanamente = máxima confiabilidade. Usado pelo ZonUI-3B.

#### Mobile3M
- **Volume**: 3M páginas UI, 49 apps populares
- **Formato**: XML hierarquias + grafos de transição dirigidos (Parquet)
- **Coleta**: Appium com random walk + threshold de similaridade
- **Conversão**: Alta complexidade — XML + grafos dirigidos
- **Download**: [HuggingFace](https://huggingface.co/datasets/xwk123/Mobile3M)
- **Licença**: CC BY-NC-SA 4.0
- **Valor**: ★★★★ — Grafos de transição são únicos (ensina "topologia de apps"), apps majoritariamente chineses
- **Potencial especial**: Treinar consciência de histórico/trajetória usando grafos de transição

#### MoTIF
- **Volume**: 6.1K comandos com anotações de viabilidade
- **Formato**: Screenshots + coordenadas + feedback iterativo
- **Diferencial**: Anotações de quando uma instrução é impossível
- **Valor**: ★★★ — Nicho mas único (ensina "quando NÃO agir")

#### OS-Atlas Data
- **Volume**: 13M+ elementos GUI, multi-plataforma
- **Formato**: Screenshots + bounding boxes + grounding labels
- **Download**: [HuggingFace](https://huggingface.co/datasets/OS-Copilot/OS-Atlas-data)
- **Valor**: ★★★★★ — Maior corpus de grounding aberto, inclui Android. Usado para treinar OS-Atlas que atingiu SOTA.

#### MobileViews (RECLASSIFICADO: Tier 1)
- **Volume**: 1.2M pares screenshot + view hierarchy + **traces completas de exploração** de 20K+ apps
- **Formato**: DroidBot JSON + ADB XML dual format, deduplicado por hash
- **Apps**: 30K+ apps modernos
- **Coleta**: DroidBot como crawler automatizado — identifica elementos interativos (clickable, editable, focusable) e executa ações sequencialmente (clicks, scrolls, text inputs), até 1.000 ações por app
- **Traces**: O dataset inclui `MobileViews_Apps_CompleteTraces` com sequências completas de interação (estados, ações, transições)
- **Download**: [HuggingFace](https://huggingface.co/datasets/mllmTeam/MobileViews)
- **Licença**: Pesquisa
- **Valor**: ★★★★★ — **Este dataset é o mais alinhado com o APE-RV**: exploração automatizada sem instrução específica, maximizando cobertura de UI. As ações são exatamente as mesmas que o APE-RV faz (clicks, scrolls, text inputs). Resolve o domain gap "exploration vs task completion" que os datasets de instruction-following (AITW, AndroidControl) têm. Maior diversidade de apps (30K+ vs 110 do AMEX).
- **Tarefas de treinamento**:
  1. Action selection a partir de traces de exploração (principal)
  2. Compreensão visual de UIs Android
  3. Coordinate grounding (prever posição de elementos)
  4. Consciência de histórico usando sequências de trace

#### Aguvis Dataset (NOVO)
- **Volume**: 4.2M samples de grounding (Stage 1) + 1.3M trajetórias de GUI agent (Stage 2)
- **Formato**: Treinado em Qwen2-VL — formato diretamente compatível com Qwen3-VL
- **Multi-plataforma**: Mobile + Desktop + Web
- **Download**: [aguvis-project.github.io](https://aguvis-project.github.io/)
- **Licença**: Open-source (ICML 2025)
- **Valor**: ★★★★★ — Enorme corpus de grounding com trajetórias de agent, formato compatível

### 4.2 Tier 2 — Screenshots + Hierarquia (Sem Traces de Ação)

#### RICO (Original)
- **Volume**: 72K UIs, 9.7K apps
- **Formato**: JSON hierarquias + screenshots + 214GB de animações GIF
- **Valor**: ★★ — Fundacional mas datado (2017), apps desatualizados. Melhor usar derivados.

#### RICO-Screen2Words
- **Formato**: Screenshots → captions descritivas
- **Valor**: ★★ — Útil para ensinar compreensão semântica de telas

#### RICO-ScreenAnnotation / RICO-SCA
- **Formato**: Anotações semânticas de componentes
- **Valor**: ★★ — Útil para classificação de elementos, menos para ação

#### ncoop57/rico_captions
- **Formato**: Captions derivadas do RICO
- **Valor**: ★ — Redundante com Screen2Words

### 4.3 Resumo: Seleção Recomendada de Datasets

| Estágio | Datasets | Volume Estimado | Objetivo |
|---------|----------|-----------------|----------|
| Stage 1: Format + Grounding | AMEX + OS-Atlas Data (Android subset) + dados próprios | ~10-20K exemplos | Tool call format + coordinate grounding |
| Stage 2: Action Selection (Exploração) | **MobileViews traces** + Aguvis trajetórias | ~20-100K exemplos (incremental) | Seleção de ação para exploração maximal |
| Stage 3: APE-RV Specific | Dados próprios (synthetic + exp logs) | ~1-5K exemplos | MOP awareness, formato APE-RV exato |
| Stage 4 (Opcional): GRPO | Dados próprios com reward verifiable | ~3-5K exemplos | Reward: coordenada dentro da bbox = 1, fora = 0 |

**Mudanças vs versão anterior**: MobileViews promovido para Tier 1 (tem traces de exploração); AITW rebaixado (instruction-following + label noise); Aguvis adicionado; GRPO adicionado como Stage 4.

**Abordagem de escala**: Começar com volumes mínimos (~10K Stage 1, ~20K Stage 2) e avaliar incrementalmente. Escalar até milhões se os resultados justificarem (MobileViews tem 1.2M, Aguvis tem 4.2M).

---

## 5. Abordagens de Fine-Tuning

### 5.1 Abordagem A: Minimal SFT com LoRA (Recomendada)

**Filosofia**: Começar com a menor intervenção possível. Focar nos ganhos mais mensuráveis e seguros.

**Estágios:**

#### Stage 1: Format Alignment + Grounding (~500-1K exemplos)
- **Dados**: Criar a partir dos prompts reais do APE-RV + AMEX (grounding verificado)
  - Pegar screenshots de experimentos anteriores
  - Usar hierarquias reais (UIAutomator dumps)
  - Label manual/semi-automático: qual ação deveria ter sido tomada
  - Resposta: tool call no formato nativo (ver Seção 7 para formato definitivo)
- **Ganho esperado**: Elimina parser de fallback. Mensurável: 50% → ~95%+ format compliance.
- **Risco**: Muito baixo — treinar formato é o caso mais seguro de fine-tuning.

#### Stage 2: Action Selection com Traces de Exploração (~10-20K exemplos, incremental até milhões)
- **Dados**: **MobileViews traces** (exploração DroidBot, 20K+ apps) + **Aguvis** trajetórias (formato Qwen-VL compatível)
- **Pipeline de conversão**:
  1. Extrair traces de `actions.csv` agrupando por `from_state` (ver Seção 6.4)
  2. Converter hierarquia DroidBot JSON para formato widget list do APE-RV
  3. Converter ações para tool calls APE-RV: `touch` → `android_click`, `scroll` → `android_scroll`
  4. Normalizar coordenadas para [0, 1000)
  5. Incluir histórico de ações anteriores na mesma tela
- **Ganho esperado**: Modelo aprende a selecionar ações para exploração maximal (mesmo paradigma que APE-RV). Redução do no-match rate.
- **Risco**: Médio — hierarquia DroidBot difere de UIAutomator. Mitigação: mix com dados próprios (Stage 1); escalar incrementalmente.

#### Stage 3: APE-RV Specific (~1-5K exemplos)
- **Dados**: Dados próprios (exp logs + synthetic) com MOP markers, dialog handling
- **Formato**: Prompt APE-RV final (definido pelo gh43) com histórico real
- **Ganho esperado**: Modelo alinhado com o formato e prioridades específicas do APE-RV
- **Risco**: Baixo — volume pequeno, formato controlado

**Configuração de treinamento:**
- **Método**: LoRA bf16 (sem quantização — QLoRA é incompatível com vision training)
- **Framework**: Unsloth (recomendado — 1.7x mais rápido, 60% menos VRAM)
- **Learning rate**: 2e-5 (language), 2e-6 a 4e-6 (vision — 1/5 a 1/10 do language LR)
- **Epochs**: 2-3 (com early stopping baseado em validation loss)
- **Batch size efetivo**: 8-16 (via gradient accumulation)
- **LoRA rank**: r=16, `lora_dropout=0.05`
- **VRAM**: ~16-18GB com LoRA bf16 language+vision (requer Colab Pro A100 ou RunPod)
- **Resolução de imagem**: Definir `max_pixels=544896` (~720×1280) para balancear qualidade e VRAM
- **Tempo estimado**: Stage 1: ~1h, Stage 2: ~2-4h, Stage 3: ~30min (em A100)

**Por que esta abordagem é recomendada:**
1. Mais simples de implementar e debugar
2. Resultados mais previsíveis — cada estágio tem métrica clara
3. Fácil A/B test: modelo base vs com adapter (basta desligar o LoRA)
4. Pode parar após Stage 1 se os ganhos de formato já forem suficientes
5. Progressão incremental: avaliar cada estágio antes de continuar

---

### 5.2 Abordagem B: Multi-Stage Domain Adaptation

**Filosofia**: Pré-treinar compreensão visual de UIs Android antes de ensinar ação. Mais robusto mas mais complexo.

**Estágios:**

#### Stage 0: Screen Understanding Pre-training (~50-100K exemplos)
- **Dados**: MobileViews (screenshot + hierarchy pairs) + OS-Atlas Data
- **Tarefas**:
  - "Descreva os elementos interativos neste screenshot" → lista de widgets
  - "Onde está o botão [X]?" → coordenadas normalizadas
  - "Quantos elementos clicáveis existem?" → contagem
- **Propósito**: Construir representação interna forte de UIs Android
- **Nota**: Esta tarefa NÃO precisa de ações — usa datasets Tier 2

#### Stage 1: Grounding Fine-tuning (~20K exemplos)
- **Dados**: AMEX (bounding boxes verificadas) + OS-Atlas (13M elements)
- **Tarefa**: "Clique no elemento [description]" → coordenadas (x, y)
- **Propósito**: Precision de grounding

#### Stage 2: Action Selection (~50K exemplos)
- **Dados**: AITW + AndroidControl traces
- **Tarefa**: Dado screenshot + hierarquia + instrução, retornar tool call correto
- **Propósito**: Decisão de ação

#### Stage 3: APE-RV Specific (~1-5K exemplos)
- **Dados**: Próprios (synthetic + logs)
- **Tarefa**: Formato APE-RV exato com MOP markers, dialog handling
- **Propósito**: Alinhamento final com o sistema

**Configuração:**
- **Método**: LoRA bf16 (QLoRA incompatível com vision training)
- **VRAM**: ~16-24GB (precisa A100 ou RTX 4090)
- **Tempo**: Stage 0: ~8-12h, Stage 1: ~4-6h, Stage 2: ~10-15h, Stage 3: ~1h (A100)
- **Total**: ~24-34h em A100

**Prós**: Mais robusto, compreensão visual mais profunda, melhor generalização
**Contras**: Mais complexo, mais caro, mais pontos de falha, requer mais dados

---

### 5.3 Abordagem C: SFT + DPO (Preference Learning)

**Filosofia**: Após SFT básico, usar Direct Preference Optimization com pares de preferência derivados de logs reais.

**Estágios:**

#### Stage 1: SFT Base (como Abordagem A, Stages 1-2)

#### Stage 2: DPO com Pares de Preferência
- **Dados**: Derivados dos logs de experimentos APE-RV
  - **Chosen** (preferido): Ações que levaram a novos estados / novas activities / coverage
  - **Rejected** (rejeitado): Ações no-match / ações que revisitaram estados / ações que não geraram cobertura
- **Volume**: ~2-5K pares (cada par = chosen + rejected para mesmo contexto)
- **Propósito**: Ensinar o modelo o que constitui "boa exploração"

**Configuração:**
- Requer SFT primeiro (Stage 1 obrigatório)
- DPO: lr ~5e-7, beta 0.1, 1-2 epochs
- Tempo adicional: ~2-4h em A100

**Prós**: Mais alinhado com o objetivo real (maximizar coverage), aprende de dados negativos
**Contras**: Mais complexo, requer curadoria cuidadosa de pares, risco de overfitting nas preferências

---

### 5.4 Abordagem D: SFT + GRPO (Reinforcement Learning)

**Filosofia**: Após SFT básico, usar Group Relative Policy Optimization com reward verifiable para refinar grounding e exploração.

**Motivação** (da literatura 2025):
- **SE-GUI** (2025): GRPO com apenas 3K samples supera modelos 18x maiores em ScreenSpot-Pro (47.3%)
- **GUI-G1**: Analisa pipeline R1-Zero-like para grounding — rewards densos (distância euclidiana ao centro) superam rewards esparsos (hit/miss)
- GRPO é mais natural que DPO para coordenadas: reward = coordenada dentro da bbox = 1, fora = 0

**Estágios:**

#### Stage 1: SFT Base (como Abordagem A, Stages 1-2)

#### Stage 2: GRPO com Verifiable Reward (~3-5K exemplos)
- **Reward function**: `reward = 1.0 if point_in_bbox(predicted, target_bbox) else 0.0`
- **Variante densa**: `reward = 1.0 - min(euclidean_distance(predicted, target_center) / max_distance, 1.0)`
- **Dados**: Screenshots + hierarquias próprias ou de AMEX/MobileViews
- **Framework**: TRL `GRPOTrainer` (suportado) ou Unsloth (notebooks prontos para Qwen3-VL)

#### Stage 3 (Opcional): GRPO com Coverage Reward
- **Reward derivado de rv-experiment**: ação levou a novo estado/método = reward alto
- **Propósito**: Ensinar política de exploração diretamente do objetivo real

**Prós**: Mais alinhado com grounding, reward function clara e verificável, funciona com poucos dados
**Contras**: Mais complexo que SFT puro, requer infraestrutura de RL, instabilidade de treinamento

**Referências**:
- [SE-GUI: Self-Evolutionary RL for GUI Grounding](https://arxiv.org/html/2505.12370v1)
- [GUI-G1: Understanding R1-Zero-Like Training](https://openreview.net/pdf/f6767d3d1ddd7b12b85d94abd6d7a313406de8a8.pdf)
- [GRPO for GUI Grounding Done Right (HuggingFace Blog)](https://huggingface.co/blog/HelloKKMe/grounding-r1)

---

### 5.5 Comparação das Abordagens (A/B/C/D)

| Aspecto | A: Minimal SFT | B: Multi-Stage | C: SFT + DPO | D: SFT + GRPO |
|---------|----------------|----------------|---------------|----------------|
| Complexidade | ★☆☆ | ★★★ | ★★☆ | ★★☆ |
| Dados necessários | ~10-20K | ~100-150K | ~15-25K | ~13-25K (SFT + 3-5K RL) |
| Tempo de treino | ~4-6h | ~24-34h | ~8-12h | ~8-14h |
| VRAM mínimo | ~12-14GB (LoRA bf16) | ~16-24GB | ~16GB | ~16-24GB |
| Risco de regressão | Baixo | Médio | Médio-Alto | Médio |
| Ganho esperado (formato) | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ |
| Ganho esperado (action) | ★★★ | ★★★★★ | ★★★★ | ★★★★ |
| Ganho esperado (grounding) | ★★ | ★★★★ | ★★★ | ★★★★★ |
| Facilidade de A/B test | ★★★★★ | ★★★ | ★★★★ | ★★★★ |
| Preservação capabilities | ★★★★★ | ★★★ | ★★★★ | ★★★★ |

**Recomendação**: Começar com **Abordagem A** (minimal). Progressão natural:

```
A (Stage 1: format+grounding) → avaliar → A (Stage 2: action com MobileViews) → avaliar →
→ Se grounding insuficiente: D (GRPO com verifiable reward, 3-5K samples)
→ Se action selection insuficiente: escalar dados (MobileViews 1.2M, Aguvis 4.2M)
→ Se tudo falhar: B (pre-training) ou pivotar para coordinate-free (SoM/GUI-Actor)
```

**GRPO (D) é preferível a DPO (C)** para grounding — reward verifiable (coordenada dentro da bbox) é mais limpo que pares chosen/rejected de logs.

---

## 6. Pipeline de Conversão de Dados

### 6.1 Formato Alvo: Qwen3-VL Chat com Tool Calls

O formato de treinamento usa `tool_calls` nativo + coluna `tools` + coluna `images` (ver Seção 7 para detalhes completos da investigação):

```python
training_sample = {
    "messages": [
        {
            "role": "system",
            "content": APERV_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": format_widget_list(hierarchy, visit_counts, mop_data)}
            ]
        },
        {
            "role": "assistant",
            "tool_calls": [{
                "type": "function",
                "function": {
                    "name": "android_click",
                    "arguments": {"x": 185, "y": 117, "element_description": "Encrypt button"}
                }
            }]
        }
    ],
    "tools": APERV_TOOL_SCHEMAS,   # JSON schemas das 7 tools (android_click, etc.)
    "images": [screenshot_pil]      # PIL Image do screenshot
}
```

O chat_template do Qwen3-VL converte `tool_calls` → `<tool_call>{JSON}</tool_call>` e `tools` → `<tools>[schemas]</tools>` automaticamente durante tokenização.

### 6.2 Conversor AITW → APE-RV Format

```python
def convert_aitw_sample(episode_step):
    """Converte um step de episódio AITW para formato APE-RV."""
    screenshot = episode_step['screenshot']  # PIL Image ou path

    # AITW usa (y, x) format — converter para (x, y)
    touch_y, touch_x = episode_step['results/yx_touch']

    # Normalizar para [0, 1000)
    img_h, img_w = screenshot.size[1], screenshot.size[0]
    norm_x = int((touch_x / img_w) * 1000)
    norm_y = int((touch_y / img_h) * 1000)

    # Converter accessibility tree para widget list
    ui_elements = episode_step.get('ui_elements', [])
    widget_list = format_as_aperv_widget_list(ui_elements)

    # Determinar tipo de ação
    lift_y, lift_x = episode_step['results/yx_lift']
    action_type = classify_action(touch_x, touch_y, lift_x, lift_y)

    if action_type == 'click':
        tool_call = {
            "name": "android_click",
            "arguments": {"x": norm_x, "y": norm_y, "element_description": ""}
        }
    elif action_type == 'swipe':
        direction = determine_swipe_direction(touch_x, touch_y, lift_x, lift_y)
        tool_call = {
            "name": "android_swipe",
            "arguments": {"direction": direction, "distance": "medium"}
        }
    # ... etc

    return format_training_sample(screenshot, widget_list, tool_call)
```

### 6.3 Conversor AMEX → APE-RV Format

```python
def convert_amex_sample(annotation, screenshot_path):
    """Converte anotação AMEX para formato APE-RV."""
    screenshot = Image.open(screenshot_path)
    img_w, img_h = screenshot.size

    # AMEX tem bounding boxes verificadas
    for element in annotation['elements']:
        bbox = element['bbox']  # [x1, y1, x2, y2]
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2

        # Normalizar para [0, 1000)
        norm_x = int((center_x / img_w) * 1000)
        norm_y = int((center_y / img_h) * 1000)

        # Descrição funcional (GPT-4o generated)
        description = element['functionality']

        # Criar widget entry
        widget = f'[{idx}] {element["class"]} "{element.get("text", "")}" @({norm_x},{norm_y})'

    # Para cadeias de ação, cada step da cadeia vira um sample
    for step in annotation.get('instruction_chain', []):
        target_element = step['target']
        tool_call = map_action_to_tool(step['action_type'], target_element)
        yield format_training_sample(screenshot, widget_list, tool_call)
```

### 6.4 Conversor MobileViews Traces → APE-RV Format

O MobileViews tem traces completas de exploração em `actions.csv` com a estrutura:

```csv
from_state,to_state,action
0,1,touch <button alt="Login" bounds="100,200,300,250"/>
1,2,touch <p>Settings</p>
2,2,scroll bounds="0,0,1080,1920"
2,3,touch <button alt="Next" bounds="500,800,700,850"/>
```

Cada app tem: `states/screen_{N}.jpg` (screenshots), `states/state_{N}.json` (hierarquia DroidBot), `actions.csv` (trace).

**Lógica de extração de histórico**: Agrupar por `from_state`. Linhas consecutivas com mesmo `from_state` formam o histórico de ações naquela tela. A última ação do grupo (quando `to_state` muda) é a ação de transição que levou a uma nova tela.

```python
def convert_mobileviews_traces(app_dir):
    """Converte traces MobileViews para samples de treinamento com histórico."""
    actions = pd.read_csv(os.path.join(app_dir, 'actions.csv'))

    # Agrupar ações por from_state para construir histórico
    history = []
    current_state = None

    for _, row in actions.iterrows():
        from_state = row['from_state']
        to_state = row['to_state']
        action = row['action']

        if from_state != current_state:
            # Nova tela — reset do histórico
            history = []
            current_state = from_state

        # Carregar screenshot e hierarquia da tela atual
        screenshot_path = f"states/screen_{from_state}.jpg"
        hierarchy_path = f"states/state_{from_state}.json"

        if from_state == to_state:
            # Ação na mesma tela — acumula no histórico
            history.append(action_to_text(action))
        else:
            # Ação que levou a nova tela — sample de treinamento
            widget_list = convert_droidbot_hierarchy(hierarchy_path)
            tool_call = parse_mobileviews_action(action)  # touch → android_click, scroll → android_scroll

            yield {
                "screenshot": os.path.join(app_dir, screenshot_path),
                "widget_list": widget_list,
                "history": history.copy(),  # Ações anteriores nesta tela
                "tool_call": tool_call,      # Ação que causou transição
                "from_state": from_state,
                "to_state": to_state,
            }

            history.append(action_to_text(action))
            current_state = to_state  # Próximo grupo

def parse_mobileviews_action(action_str):
    """Converte ação MobileViews para tool call APE-RV."""
    if action_str.startswith('touch'):
        # Extrair bounds do elemento
        bounds = extract_bounds(action_str)  # [x1, y1, x2, y2]
        center_x = (bounds[0] + bounds[2]) // 2
        center_y = (bounds[1] + bounds[3]) // 2
        # Normalizar para [0, 1000)
        norm_x = int((center_x / screen_width) * 1000)
        norm_y = int((center_y / screen_height) * 1000)
        description = extract_alt_or_text(action_str)
        return {"name": "android_click", "arguments": {"x": norm_x, "y": norm_y, "element_description": description}}
    elif action_str.startswith('scroll'):
        return {"name": "android_scroll", "arguments": {"direction": "down"}}
    # ... etc
```

**Nota importante**: O formato exato do prompt (como o histórico é serializado, quais campos da hierarquia entram) depende do trabalho em andamento no gh43 (prompt variants do APE-RV). O conversor será finalizado quando o formato do prompt estiver definido. O pipeline de dados pode ser construído independentemente — só o template de serialização final precisa ser plugado.

### 6.5 Tarefas Auxiliares de Grounding (sem traces)

Converter screenshots + hierarquias (de qualquer dataset) para tarefas de compreensão visual:

```python
def convert_grounding_sample(screenshot_path, view_hierarchy):
    """Cria sample de grounding a partir de screenshot + hierarquia."""
    elements = parse_view_hierarchy(view_hierarchy)

    # Selecionar elemento aleatório como target
    target = random.choice([e for e in elements if e.get('clickable')])

    # Tarefa: "Onde está o elemento [description]?"
    question = f"Where is the {target['class']} with text '{target.get('text', '')}' on this screen?"
    answer = f"The element is at coordinates ({target['norm_x']}, {target['norm_y']})"

    return {
        "messages": [
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": question}
            ]},
            {"role": "assistant", "content": answer}
        ],
        "images": [Image.open(screenshot_path)]
    }

def convert_grounding_description(screenshot_path, view_hierarchy):
    """Cria sample de screen description a partir de screenshot + hierarquia."""
    elements = parse_view_hierarchy(view_hierarchy)

    # Formatar como widget list APE-RV
    widget_list = format_as_aperv_widget_list(elements)

    return {
        "messages": [
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": "List all interactive elements visible on this Android screen."}
            ]},
            {"role": "assistant", "content": widget_list}
        ],
        "images": [Image.open(screenshot_path)]
    }
```

---

## 7. Tool Call Format no SFT — RESOLVIDO

### Investigação do Chat Template

O `chat_template` do Qwen3-VL-4B-Instruct foi inspecionado. O template Jinja2 converte `tool_calls` automaticamente para o formato:

```xml
<tool_call>
{"name": "android_click", "arguments": {"x": 185, "y": 117, "element_description": "Encrypt"}}
</tool_call>
```

O template inclui:
- **Tools no system prompt**: Quando `tools` são fornecidas, o template injeta `<tools>[schemas]</tools>` + instrução "return JSON within `<tool_call>` tags"
- **Tool calls no assistant**: O campo `tool_calls` na message é convertido automaticamente para `<tool_call>{JSON}</tool_call>` text
- **Tool responses**: Responses de tools são wrappadas em `<tool_response>...</tool_response>`

### Resposta: Usar `tool_calls` Nativo no Dataset

O **TRL SFTTrainer suporta tool calling nativamente** ([docs](https://huggingface.co/docs/trl/en/dataset_formats#tool-calling)). O dataset deve incluir:
1. Campo `tool_calls` nas messages do assistant (formato OpenAI)
2. Coluna `tools` com JSON schemas das tools disponíveis
3. Coluna `images` com PIL Images (para VLM)

O chat template cuida da conversão para tokens. **Não é necessário colocar o XML manualmente** — basta usar o formato estruturado e o template gera os tokens corretos.

### Formato Definitivo do Dataset

```python
from datasets import Dataset, Features, Json, List, Value
from transformers.utils import get_json_schema
from PIL import Image

# 1. Definir tools como JSON schemas
def android_click(x: int, y: int, element_description: str = "") -> str:
    """Click on a UI element at the specified coordinates.
    Args:
        x: Normalized x coordinate [0, 1000).
        y: Normalized y coordinate [0, 1000).
        element_description: Description of the target element.
    """
    ...

def android_type_text(x: int, y: int, text: str, element_description: str = "") -> str:
    """Click on a text field and type text.
    Args:
        x: Normalized x coordinate [0, 1000).
        y: Normalized y coordinate [0, 1000).
        text: The text to type.
        element_description: Description of the target element.
    """
    ...

# ... android_swipe, android_long_click, android_scroll, android_back, android_home

tool_schemas = [
    get_json_schema(android_click),
    get_json_schema(android_type_text),
    # ... etc
]

# 2. Criar sample de treinamento
sample = {
    "messages": [
        {
            "role": "system",
            "content": APERV_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": (
                    'Screen "MainActivity":\n'
                    '[0] Button "Encrypt" @(185,117) [DM] (v:0)\n'
                    '[1] EditText "Password" @(208,169) (v:3)\n'
                    'Recent actions: none'
                )}
            ]
        },
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "type": "function",
                    "function": {
                        "name": "android_click",
                        "arguments": {"x": 185, "y": 117, "element_description": "Encrypt button"}
                    }
                }
            ]
        }
    ],
    "tools": tool_schemas,
    "images": [Image.open("screenshot.jpg")]
}

# 3. Criar Dataset com tipos corretos
data = [sample, ...]
dataset = Dataset.from_list(data, on_mixed_types="use_json")
```

### O Que Acontece Internamente

Quando o SFTTrainer tokeniza este sample:
1. O `chat_template` vê `tools` → injeta schemas no system prompt dentro de `<tools>` tags
2. Vê a image → insere `<|vision_start|><|image_pad|><|vision_end|>` tokens
3. Vê `tool_calls` no assistant → gera `<tool_call>\n{"name": "android_click", "arguments": {"x": 185, ...}}\n</tool_call>`
4. O modelo aprende a gerar EXATAMENTE estes tokens

### Implicação para Serving

Quando o modelo fine-tuned for servido via SGLang/vLLM com `--tool-call-parser hermes`:
- O framework reconhece `<tool_call>` tags na saída do modelo
- Converte automaticamente para o formato `tool_calls` do OpenAI API
- O fallback parser complexo do APE-RV **não será mais necessário**

Isso resolve simultaneamente: (1) consistência de formato e (2) compatibilidade com serving frameworks.

---

## 8. Infraestrutura de Treinamento

### 8.1 Requisitos de VRAM

O Qwen3-VL-4B-Instruct usa **bf16 nativo** (`torch_dtype: bfloat16` no config.json). O modelo ocupa ~8.2GB em bf16 (4B params × 2 bytes).

| Modelo | Full FT | LoRA bf16 (language only) | LoRA bf16 (language + vision) | QLoRA 4-bit (language only) |
|--------|---------|--------------------------|-------------------------------|----------------------------|
| Qwen3-VL-4B | ~32GB | ~12-14GB | ~16-18GB | ~8-10GB |
| Qwen3-VL-8B | ~64GB | ~20-24GB | ~28-32GB | ~12-16GB |

**Notas:**
- Valores para batch_size=1 **com screenshots** (~500-1000 vision tokens por imagem). Gradient checkpointing reduz em ~30%.
- **QLoRA + vision training é INCOMPATÍVEL** — o repo [2U1/Qwen-VL-Series-Finetune](https://github.com/2U1/Qwen-VL-Series-Finetune) alerta explicitamente: "Do NOT combine quantization (`--bits 4`) with vision training". Se treinar vision layers, usar LoRA bf16 (sem quantização).
- Se treinar vision layers, usar **vision LR = 1/5 a 1/10 do language LR** (best practice do 2U1).
- Screenshots Android (1080×1920) geram centenas de vision tokens. Definir `max_pixels` no processador para limitar resolução durante treino (~720×1280).

### 8.1.1 Serving do Modelo Fine-Tuned

| Método | Suporta Vision LoRA? | Throughput | Rollback |
|--------|---------------------|------------|----------|
| **HuggingFace transformers (PEFT)** | **SIM** — `PeftModel.from_pretrained()` carrega adapters em TODAS as layers | Baixo (sem batching) | Fácil (ligar/desligar adapter) |
| **SGLang** | **NÃO** — LoRA em vision layers é feature request aberto | Alto | N/A |
| **vLLM** | **NÃO** — vision layer adapters silenciosamente ignorados | Alto | N/A |
| **Merge + qualquer framework** | N/A — adapter fundido no modelo base (~8GB) | Alto | Trabalhoso (manter 2 modelos) |

**Decisão para APE-RV**: Como o APE-RV faz chamadas sequenciais (não batch), **serving via transformers nativo com PEFT** é viável. A latência será ligeiramente maior que SGLang mas funcional. Alternativamente, fazer **merge antes de deploy** para usar SGLang/vLLM com throughput otimizado.

### 8.1.2 Automação via Colab MCP Server

O [Google Colab MCP Server](https://github.com/googlecolab/colab-mcp) permite que Claude Code controle notebooks Colab diretamente, eliminando a necessidade de interação manual com o browser.

**Capacidades:**
- Criar notebooks `.ipynb` e adicionar células (code + markdown)
- Executar código Python em tempo real no runtime Colab (com GPU T4/L4/A100)
- Instalar dependências (`pip install`)
- Capturar outputs e resultados de execução
- Gerenciar o ciclo completo: setup → treino → avaliação → publicação no HF Hub

**Configuração (Claude Code):**
```json
{
  "mcpServers": {
    "colab-mcp": {
      "command": "uvx",
      "args": ["git+https://github.com/googlecolab/colab-mcp"],
      "timeout": 30000
    }
  }
}
```

**Pré-requisitos:** Python, git, uv (`pip install uv`), sessão Colab ativa no browser.

**Impacto no workflow de fine-tuning:**

| Sem Colab MCP | Com Colab MCP |
|---------------|---------------|
| Abrir Colab no browser manualmente | Claude Code cria e executa notebooks remotamente |
| Copiar/colar código entre terminal e Colab | Claude Code escreve e roda células diretamente |
| Monitorar training loss manualmente | Claude Code captura métricas e decide próximos passos |
| Checkpoint download/upload manual | Claude Code automatiza push_to_hub e resume |
| Cada iteração requer intervenção humana | **Ciclo completo automatizável**: smoke test → treino → avaliação → publicação |

**Fluxo automatizado proposto:**

```
Claude Code (local) ──MCP──> Colab (cloud GPU)
     │                           │
     ├── Criar notebook          │
     ├── Instalar Unsloth/TRL    │
     ├── Upload dataset (HF Hub) │
     ├── Configurar LoRA         │
     ├── Treinar ──────────────> │ GPU A100/T4
     ├── Capturar métricas <──── │
     ├── Avaliar offline         │
     ├── Push adapter ao HF Hub  │
     └── Reportar resultados     │
```

Isso permite **iterações rápidas**: se Stage 1 não atingir 90% format compliance, Claude Code pode ajustar hyperparameters e re-treinar sem intervenção manual. O smoke test (Fase 1.6) pode ser executado inteiramente por Claude Code via MCP.

### 8.2 Comparação de Plataformas

| Plataforma | GPU | VRAM | Custo | Limite Sessão | Setup | Melhor Para |
|------------|-----|------|-------|---------------|-------|-------------|
| **Google Colab Free** | T4 | 16GB | Grátis | ~12h, instável | Mínimo | Smoke test (1 sample). Stage 1 marginal — LoRA bf16 com vision ~16-18GB |
| **Google Colab Pro** | A100 40GB | 40GB | ~$10/mês | 24h | Mínimo | Stages 1-2 (até 20K exemplos) |
| **Google Colab Pro+** | A100 40GB | 40GB | ~$50/mês | Prioridade | Mínimo | Treinamento completo |
| **Kaggle** | P100/T4 | 16GB | Grátis | 30h/semana | Mínimo | Similar Colab free, limites diferentes |
| **RunPod** | A100 80GB | 80GB | ~$2-3/h | Sem limite | Médio (Docker) | Treinamento intensivo, datasets grandes |
| **Vast.ai** | A100/4090 | 24-80GB | ~$1-2/h | Sem limite | Médio | Custo-benefício, flexível |
| **Lambda Cloud** | A100 | 40-80GB | ~$1.50/h | Sem limite | Full VM | Setup permanente, reprodutível |
| **HuggingFace Spaces (GPU)** | A10G | 24GB | ~$1-5/h | Sem limite | Mínimo | Integrado com HF Hub |

### 8.3 Recomendação de Infraestrutura

**Para Abordagem A (Recomendada) — com vision training (LoRA bf16, ~16-18GB VRAM):**

1. **Smoke test** (1 sample, 10 steps): **Google Colab Free** com T4 (16GB, marginal)
   - Verificar se VLM + tool_calls funciona no SFTTrainer
   - Se OOM: usar Kaggle (T4 P100) ou Colab Pro
   - Custo: $0

2. **Protótipo + Stage 1** (~500-1K exemplos): **Google Colab Pro** com A100
   - LoRA bf16 com vision layers cabe folgado em 40GB
   - Tempo: ~1-2h
   - Custo: ~$10/mês

3. **Treinamento completo** (Stages 1-3, ~20K+ exemplos): **Google Colab Pro** ou **RunPod**
   - Tempo: ~4-6h em A100
   - Custo: ~$10-30 por run

4. **Escala e iterações** (100K+ exemplos): **RunPod** ou **Vast.ai** (pay-per-use)
   - Para escalar com MobileViews (1.2M) ou Aguvis (4.2M)
   - Custo: ~$30-100 por run completo

### 8.4 Estratégia de Checkpoints e HuggingFace Hub

```python
from huggingface_hub import HfApi

# Durante treinamento: salvar checkpoints a cada N steps
training_args = TrainingArguments(
    save_steps=500,                    # Checkpoint a cada 500 steps
    save_total_limit=3,                # Manter apenas últimos 3 checkpoints
    push_to_hub=True,                  # Enviar para HF Hub automaticamente
    hub_model_id="pamunb/aperv-qwen3vl-4b-lora",  # Repo no HF
    hub_strategy="checkpoint",         # Push a cada checkpoint
)

# Se sessão morrer, retomar de último checkpoint:
# trainer.train(resume_from_checkpoint="checkpoint-1500")
```

**Estrutura no HuggingFace Hub:**
```
pamunb/aperv-qwen3vl-4b-lora/
├── adapter_config.json     # Configuração LoRA
├── adapter_model.safetensors  # Pesos do adapter
├── tokenizer/              # Se modificado
├── README.md               # Model card com métricas
└── training_args.json      # Hiperparâmetros
```

**Vantagem**: O adapter LoRA é pequeno (~50-200MB vs 8GB do modelo base). Upload/download rápido. Para usar:
```python
from peft import PeftModel
model = PeftModel.from_pretrained(base_model, "pamunb/aperv-qwen3vl-4b-lora")
```

---

## 9. Framework de Treinamento Recomendado

### 9.1 Opções

| Framework | Prós | Contras |
|-----------|------|---------|
| **Unsloth** | 1.7x mais rápido, 60% menos VRAM, Colab notebooks prontos, suporta Qwen3-VL | API proprietária, menos flexível |
| **LLaMA-Factory** | GUI web (LLaMA Board), configs YAML, templates Qwen-VL prontos | Mais complexo, overhead de config |
| **TRL (HuggingFace)** | Oficial HF, SFTTrainer + DPOTrainer, máxima flexibilidade | Mais código manual, sem otimizações especiais |
| **Axolotl** | Config-driven, multi-GPU, bom para reprodutibilidade | Curva de aprendizado |

### 9.2 Recomendação: Unsloth

**Por que Unsloth:**
1. **Notebooks prontos** para Qwen3-VL — reduz barreira para quem nunca fez fine-tuning
2. **VRAM eficiente** — 60% menos memória, viabiliza T4/4090
3. **Velocidade** — 1.7x mais rápido = menos custo de cloud
4. **Suporte ativo** para vision fine-tuning com Qwen3-VL
5. **Colab integration** — notebooks gratuitos para começar

**Exemplo minimal com Unsloth:**

```python
from unsloth import FastVisionModel
import torch

# 1. Carregar modelo com Unsloth (otimizado)
# IMPORTANTE: NÃO usar load_in_4bit=True com finetune_vision_layers=True
# QLoRA + vision training é incompatível (repo 2U1 alerta explicitamente)
model, tokenizer = FastVisionModel.from_pretrained(
    "unsloth/Qwen3-VL-4B-Instruct",
    load_in_4bit=False,  # LoRA bf16 (necessário para treinar vision)
    dtype=torch.bfloat16,
)

# 2. Configurar LoRA
model = FastVisionModel.get_peft_model(
    model,
    r=16,                              # LoRA rank
    lora_alpha=16,
    target_modules=[                    # Quais layers treinar
        "q_proj", "k_proj", "v_proj",  # Attention
        "o_proj",
        "gate_proj", "up_proj", "down_proj",  # MLP
    ],
    finetune_vision_layers=True,        # Treinar vision encoder
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    lora_dropout=0.05,                  # Anti-overfitting para 4B
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# 3. Preparar dataset
from datasets import load_dataset
dataset = load_dataset("json", data_files="aperv_training_data.jsonl")

# 4. Configurar trainer
from trl import SFTTrainer, SFTConfig

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    args=SFTConfig(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        warmup_steps=50,
        num_train_epochs=3,
        learning_rate=2e-5,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        save_steps=500,
        output_dir="outputs",
        push_to_hub=True,
        hub_model_id="pamunb/aperv-qwen3vl-4b-lora",
    ),
    data_collator=UnslothVisionDataCollator(model, tokenizer),
)

# 5. Treinar
trainer.train()

# 6. Salvar adapter
model.save_pretrained("aperv-adapter")
model.push_to_hub("pamunb/aperv-qwen3vl-4b-lora")
```

---

## 10. Avaliação: Garantindo Melhoria

### 10.1 Offline Benchmark (Gate obrigatório antes de deploy)

**Composição do Test Set:**
- **Hold-out**: 10-20% dos dados de treinamento (não usados no treino)
- **Out-of-distribution**: Screenshots de apps NÃO presentes no treino (garantir generalização)
- **APE-RV specific**: Screenshots reais de experimentos anteriores

**Métricas:**

| Métrica | Descrição | Target |
|---------|-----------|--------|
| **Format Compliance Rate** | % respostas em formato tool call válido | >95% (vs ~50% base) |
| **Action Match Accuracy** | % ações onde coordenada cai dentro de bounding box do widget correto | >70% (vs ~63% base) |
| **Coordinate MAE** | Distância média entre coordenada predita e centro do widget mais próximo | <50px (vs ~100px+ base) |
| **Action Type Accuracy** | % de tool calls com tipo correto (click vs swipe vs type) | >90% |
| **No-Match Rate** | % coordenadas que não caem em NENHUM widget | <20% (vs 37.3% base) |

**Protocolo de avaliação:**
```python
def evaluate_model(model, test_set):
    results = {
        "format_compliance": 0,
        "action_match": 0,
        "coordinate_errors": [],
        "no_match_count": 0,
    }

    for sample in test_set:
        response = model.generate(sample['input'])

        # 1. Format compliance
        tool_call = parse_tool_call(response)
        if tool_call is not None:
            results["format_compliance"] += 1

        # 2. Action match
        predicted_coords = (tool_call['x'], tool_call['y'])
        target_coords = sample['target_coords']
        target_bbox = sample['target_bbox']

        if point_in_bbox(predicted_coords, target_bbox):
            results["action_match"] += 1

        # 3. Coordinate error
        error = euclidean_distance(predicted_coords, target_coords)
        results["coordinate_errors"].append(error)

        # 4. No-match
        if not any(point_in_bbox(predicted_coords, w['bbox']) for w in sample['all_widgets']):
            results["no_match_count"] += 1

    return compute_metrics(results, len(test_set))
```

### 10.2 Online Validation (via rv-experiment)

**Só executar se offline benchmark passar o gate.**

**Protocolo:**
1. Deploy modelo fine-tuned via **PEFT** (`PeftModel.from_pretrained()`) ou **merge + SGLang/vLLM** (ver Seção 8.1.1)
2. Rodar rv-experiment com 10+ APKs × 3 reps × 2 configurações (base vs fine-tuned)
3. Total: 60+ runs (~10-15h)

**Métricas:**
- Method coverage (% métodos executados)
- Activity coverage (% activities visitadas)
- MOP coverage (% operações monitoradas atingidas)
- No-match rate (% chamadas LLM sem match)

**Teste estatístico:**
- **Wilcoxon signed-rank test** por APK (mais poder com dados contínuos de coverage que McNemar binário)
- **Bootstrap confidence intervals** para as métricas de coverage
- Bonferroni correction se testar múltiplas variantes
- Definir effect size mínimo a priori (e.g., +2% method coverage) e calcular power da amostra

### 10.3 Proteção Contra Regressão

1. **Checkpoint comparison**: Avaliar CADA checkpoint (não só o final) no test set
2. **Early stopping**: Parar se validation loss aumentar por N steps consecutivos
3. **LoRA merge opcional**: Testar tanto com merge quanto sem merge
4. **Rollback**: Se online validation não melhorar, simplesmente remover o adapter (LoRA não modifica o modelo base)
5. **Mix de dados**: Incluir ~10% de exemplos genéricos (VQA, OCR) no training mix para prevenir catastrophic forgetting
6. **Avaliação de catastrophic forgetting**: Testar antes e depois do fine-tuning em tarefas genéricas:
   - OCR: "What text is visible in the search bar?" em 20 screenshots diversos
   - VQA: "What app is this?" / "How many buttons are visible?" em 20 screenshots
   - Se accuracy cair >5% em qualquer métrica genérica, reduzir LoRA rank (r=8) ou aumentar dropout

---

## 11. Qwen3-VL-4B vs 8B: Análise para Fine-Tuning

### 11.1 Trade-offs

| Aspecto | 4B | 8B |
|---------|-----|-----|
| Inferência (16GB GPU) | Cabe nativo (bf16, ~8.2GB) | Requer quantização (4-bit/8-bit) |
| Fine-tuning VRAM (LoRA bf16, language+vision) | ~16-18GB | ~28-32GB |
| Fine-tuning VRAM (QLoRA 4-bit, language only) | ~8-10GB | ~12-16GB |
| Capacidade base | Boa | Melhor (mais parâmetros = mais capacidade de aprender) |
| Velocidade inferência | ~2x mais rápido | Mais lento |
| Latência por call | ~1-2s | ~2-4s |
| Fine-tuning ganho potencial | Bom | Potencialmente melhor (mais headroom) |

### 11.2 Recomendação

**Começar com 4B**, porque:
1. Já está em uso no APE-RV — baseline comparável
2. Cabe em 16GB para inferência sem quantização
3. Fine-tuning mais rápido e barato
4. Se os resultados forem bons no 4B, provavelmente serão melhores no 8B

**Considerar 8B** se:
1. O 4B fine-tuned ainda tiver no-match rate alto (>25%)
2. O ganho de action selection não for suficiente
3. A latência de 2-4s/call for aceitável (depende do budget de LLM calls do APE-RV)

### 11.3 Nota sobre SGLang Compatibility

O gh43 descobriu que o Qwen3-VL-4B-Instruct está broken no SGLang v0.5.9 (vision encoder recebe pixel data corrompido). **Para fine-tuning, isso NÃO é problema** — o fine-tuning usa transformers/Unsloth diretamente, não SGLang. O modelo fine-tuned pode ser servido em qualquer framework (SGLang, vLLM, etc.) e a versão do framework pode ser diferente da usada no treinamento.

Se SGLang estiver fixo quando o adapter estiver pronto, usar SGLang. Se não, usar vLLM como alternativa.

---

## 12. Dados Próprios: Como Gerar Training Data do APE-RV

### 12.1 Semi-Automático a partir de Logs

Os logs de experimentos APE-RV contêm:
- Screenshots capturados
- UIAutomator dumps (hierarquia XML)
- Ações tomadas (com coordenadas e resultados)
- Cobertura atingida

**Pipeline:**

```
Logs APE-RV (exp1-3)
    ↓
Filtrar ações com match (63% dos logs)
    ↓
Parejar: screenshot + hierarquia + ação (matched)
    ↓
Converter para formato APE-RV training
    ↓
Revisar manualmente subset (~100-200 exemplos)
    ↓
Dataset Stage 1 (~500-1K exemplos)
```

### 12.2 Synthetic Data via LLM Forte

Usar modelo mais capaz (GPT-4o, Claude) para gerar ações corretas:

1. Dar screenshot + hierarquia a GPT-4o
2. Pedir: "Qual ação um testador deveria tomar para maximizar exploração?"
3. Validar que a ação corresponde a um widget real
4. Usar como training data para o Qwen3-VL-4B

**Custo**: ~$0.01-0.05 por exemplo com GPT-4o → $50-250 para 5K exemplos

### 12.3 Dados de Histórico (para consciência de trajetória)

```python
def create_history_aware_sample(trace, step_idx):
    """Cria sample com contexto de histórico a partir de trace."""
    current_step = trace[step_idx]

    # Últimas 3-5 ações como histórico
    history = trace[max(0, step_idx-5):step_idx]
    history_text = "\n".join([
        f"Step {i}: {action_to_text(h)}"
        for i, h in enumerate(history)
    ])

    # Ações já visitadas nesta tela
    current_screen = current_step['activity']
    visited_actions = [
        a for a in trace[:step_idx]
        if a['activity'] == current_screen
    ]

    user_message = (
        f"Screen \"{current_screen}\":\n"
        f"{format_widgets(current_step['hierarchy'])}\n\n"
        f"Recent actions:\n{history_text}\n\n"
        f"Previously visited on this screen: {len(visited_actions)} actions"
    )

    return format_training_sample(
        screenshot=current_step['screenshot'],
        user_message=user_message,
        tool_call=current_step['action']  # Ação que levou a novo estado
    )
```

---

## 13. Plano de Execução (Roadmap)

**Nota**: As Fases 1-3 podem ser amplamente automatizadas via **Colab MCP Server** (Seção 8.1.2). Claude Code pode criar notebooks, executar treino, capturar métricas e iterar sem intervenção manual — reduzindo significativamente o tempo de cada fase.

### Fase 0: Pré-requisitos (1-2 semanas)

1. **Aguardar/avaliar resultado do gh43** — se prompt engineering resolver, fine-tuning pode ser desnecessário
2. **Root cause analysis do no-match rate** — classificar ~100 no-matches em: (a) parsing/format, (b) denormalização de coordenadas, (c) grounding visual, (d) policy ruim. Se >50% forem (a)/(b), fine-tuning é prematuro
3. **Baseline de snapping determinístico** — medir quanto o no-match cai apenas mapeando coordenada → widget mais próximo (custo zero de treino)
4. **Go/No-Go**: Se snapping + gh43 reduzem no-match a <20%, reavaliar necessidade de fine-tuning

### Fase 1: Setup e Protótipo (1-2 semanas)

5. ~~**Inspecionar chat_template**~~ — FEITO: usa `<tool_call>{JSON}</tool_call>` (ver Seção 7)
6. **Configurar Colab MCP Server** — `claude mcp add colab-mcp -- uvx git+https://github.com/googlecolab/colab-mcp` (ver Seção 8.1.2). Permite Claude Code controlar notebooks Colab remotamente.
7. **Smoke test VLM + tool_calls** no SFTTrainer via Colab MCP (1 sample com imagem + tool_calls + tools, verificar tokenização)
8. **Smoke test serving** — verificar que adapter LoRA funciona com `PeftModel.from_pretrained()` e produz `<tool_call>` na saída
8. **Criar dataset Stage 1** (~500 exemplos) a partir de logs do APE-RV
9. **Setup Colab Pro notebook** com Unsloth + LoRA bf16 (NÃO QLoRA — vision training requer bf16)
10. **Treinar Stage 1** (format + grounding)
11. **Avaliar offline**: format compliance rate + benchmark genérico (OCR/VQA) antes/depois (detectar catastrophic forgetting)
12. **Publicar adapter** no HuggingFace Hub

### Fase 2: Dataset Pipeline (2-3 semanas)

13. **Baixar e explorar** MobileViews traces + AMEX
14. **Implementar conversores** MobileViews → APE-RV (Seção 6.4) e AMEX → APE-RV (Seção 6.3)
15. **Criar dataset Stage 2** (~10-20K exemplos, incremental)
16. **Validar amostras** manualmente (~100-200 exemplos)
17. **Criar test set** (hold-out + OOD com apps não presentes no treino, split por package_name)

### Fase 3: Treinamento Principal (1 semana)

18. **Treinar Stage 2** (action selection com MobileViews traces) em Colab Pro ou RunPod
19. **Avaliar offline** com test set completo + benchmark genérico (CF check)
20. **Comparar checkpoints** e selecionar melhor
21. **Publicar modelo** no HuggingFace Hub

### Fase 4: Validação Online (1-2 semanas)

22. **Deploy** via `PeftModel.from_pretrained()` (PEFT nativo) ou merge + SGLang/vLLM
23. **Rodar rv-experiment** com 10+ APKs × 3 reps
24. **Análise estatística** (Wilcoxon signed-rank test por APK, bootstrap confidence intervals)
25. **Decisão**: deploy em produção OU iterar (Fase 5)

### Fase 5 (Opcional): Refinamento

20. **Se grounding insuficiente**: GRPO com verifiable reward (coordenada dentro da bbox) — 3-5K samples (ver Abordagem D)
21. **Se action selection insuficiente**: Escalar dados com MobileViews (1.2M traces de exploração) e Aguvis (4.2M grounding)
22. **Se 4B insuficiente**: Testar fine-tuning do 8B (requer quantização para inferência em 16GB)
23. **Se coordinate prediction fundamentalmente limitado**: Pivotar para coordinate-free (Set-of-Marks ou seleção por índice de widget)

---

## 14. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Catastrophic forgetting** — modelo perde capabilities gerais após fine-tuning | Média (SMoLoRA/ICCV 2025 mostra que LoRA NÃO previne CF completamente) | Alto | LoRA preserva base model; `lora_dropout=0.05`; avaliar em benchmarks gerais (OCR, VQA) antes/depois; incluir ~10% exemplos genéricos; considerar LoRA rank menor (r=8) se CF detectado |
| **Domain shift** — datasets públicos têm UIs diferentes dos apps alvo | Média (mitigado com MobileViews) | Médio | MobileViews usa exploração automatizada (mesmo paradigma do APE-RV); mix com dados próprios; validar em holdout de apps não presentes no treino |
| **QLoRA + vision training incompatível** | Alta | Alto | Repo 2U1 alerta explicitamente. Usar LoRA bf16 (sem quantização) se treinar vision layers. QLoRA só com vision congelado |
| **Vision LoRA não servível em SGLang/vLLM** | Alta | Médio | Servir via HuggingFace transformers (PEFT) ou fazer merge antes de deploy. APE-RV usa chamadas sequenciais, não precisa de batching |
| **AITW label noise (~33%)** | Alta | Médio | ~33% das ações não correspondem a elementos UI. Filtrar rigorosamente; priorizar AMEX/MobileViews; validar amostras manualmente |
| **Coordinate system mismatch** — diferentes datasets usam sistemas de coordenadas incompatíveis | Média | Alto | Pipeline de normalização rigoroso para [0, 1000); validar amostras manualmente |
| **SGLang incompatibility** — modelo fine-tuned pode ter problemas com SGLang | Baixa | Alto | Testar serving com SGLang ANTES de treinamento extenso; ter vLLM como fallback |
| **Overfitting** — poucos dados próprios (~500-1K) levam a memorização | Média | Médio | Mix com dados públicos; early stopping; validation split |
| **Custo de cloud** — treinamento iterativo fica caro | Baixa | Baixo | Começar com Colab Pro (~$10/mês); usar checkpoints + push_to_hub para resumir sessões |
| **Regressão no no-match rate** — fine-tuning piora a situação | Baixa | Alto | Gate obrigatório (offline benchmark); LoRA permite rollback instantâneo |
| **Formato tool call incompatível** — o formato treinado não é reconhecido pelo SGLang | Baixa (mitigado) | Alto | Chat template inspecionado — usa `<tool_call>` format. SGLang/vLLM reconhecem com `--tool-call-parser hermes`. Smoke test obrigatório antes de criar dataset grande |

### Gates de Decisão (Go/No-Go)

```
Fase 0 → Snapping + gh43 reduzem no-match a <20%?
  ├─ SIM → Reavaliar necessidade de fine-tuning (pode ser suficiente)
  └─ NÃO → Continuar para Fase 1

Fase 1 → Smoke test VLM + tool_calls funciona?
  ├─ SIM → Continuar
  └─ NÃO → Plano B: usar text manual <tool_call> no content (sem coluna tool_calls)

Stage 1 → Format compliance ≥90%? + Benchmark genérico não caiu >5%?
  ├─ SIM → Continuar para Stage 2
  └─ NÃO → Debug (dados? template? hyperparams?) → Retry (max 3x) → Abortar

Stage 2 → No-match rate ≤25%?
  ├─ SIM → Continuar para Stage 3
  └─ NÃO → Escalar dados (MobileViews 1.2M) OU GRPO (Abordagem D) OU pivotar para coordinate-free

Stage 3 → Coverage online ≥ baseline (28.35%)?
  ├─ SIM → Deploy em produção
  └─ NÃO → GRPO com coverage reward OU pivotar
```

---

## 15. Questões Resolvidas e Remanescentes

### Resolvidas

1. **Modelo**: ~~Qwen3-VL-4B vs Qwen3.5-4B~~ → **Qwen3-VL-4B-Instruct**. Decisão firme desde o início do projeto. Qwen3.5 não será cogitado.

2. **Tool call format no SFT**: ~~Nativo ou text?~~ → **Nativo (`tool_calls` no dataset)**. Investigação confirmou que o TRL SFTTrainer suporta tool calling nativamente. O chat_template do Qwen3-VL converte `tool_calls` → `<tool_call>{JSON}</tool_call>` automaticamente. Dataset deve incluir colunas `tools` (JSON schemas) e `images` (PIL Images). Ver Seção 7 para detalhes completos.

3. **Vision layers**: ~~Treinar ou congelar?~~ → **Treinar ambos (vision + language)**. O objetivo é action selection, que requer tanto compreensão visual da tela quanto decisão sobre qual ação tomar.

4. **Escala de dados**: ~~Sweet spot?~~ → **Avaliar incrementalmente, podendo chegar a milhões**. Começar com ~500 (Stage 1), expandir para ~20K (Stage 2), e se os resultados justificarem, escalar com MobileViews (1.2M traces de exploração), Aguvis (4.2M grounding), OS-Atlas (13M). ZonUI-3B mostra que diversidade importa mais que volume bruto, mas não há limite superior predefinido.

5. **Avaliação Stage 1**: Gerar ~100 respostas com modelo base vs fine-tuned e comparar format compliance rate. Completamente offline, sem pipeline.

6. **Multi-GPU**: Não necessário. LoRA bf16 do Qwen3-VL-4B com vision training requer ~16-18GB — cabe numa A100 (40GB). Gradient accumulation substitui batch size grande.

### Remanescentes

1. **Serving framework pós fine-tuning**: Três opções investigadas: (a) **HuggingFace transformers com PEFT** — funciona garantido com vision LoRA, sem batching (aceitável para APE-RV), (b) **merge + SGLang/vLLM** — throughput otimizado mas perde rollback dinâmico, (c) testar versão mais recente do SGLang com fix. Decisão depende de latência aceitável no APE-RV.

2. **Combinação VLM + tool calling no SFTTrainer**: Ambas features suportadas individualmente. Combinação (imagem + tool_calls + tools no mesmo sample) precisa de **smoke test** — é o blocker #1, deve ser a primeira tarefa antes de qualquer dataset.

3. **Licenciamento dos datasets**: AITW (Apache 2.0), AMEX (pesquisa), Mobile3M (CC BY-NC-SA 4.0), MobileViews (pesquisa), Aguvis (open-source). Para publicar o modelo fine-tuned no HuggingFace Hub, verificar compatibilidade das licenças.

4. **LoRA rank ideal**: Testar r=16 primeiro. Se insuficiente, escalar para r=32 ou r=64. `lora_dropout=0.05` (anti-overfitting para 4B). Vision encoder LR = 1/5 a 1/10 do language LR.

5. **Root cause do no-match rate**: Antes de investir pesado em fine-tuning, isolar quantos no-matches são por: (a) parsing/format failure, (b) denormalização de coordenadas, (c) grounding visual, (d) policy ruim. Se >50% forem (a)/(b), fine-tuning pode ser premature — o gh43 pode resolver.

---

## 16. Referências

### Infraestrutura e Automação
- [Google Colab MCP Server](https://github.com/googlecolab/colab-mcp) — Controle de Colab via MCP (Claude Code → GPU cloud)
- [Anúncio Colab MCP](https://developers.googleblog.com/announcing-the-colab-mcp-server-connect-any-ai-agent-to-google-colab/)

### Modelos e Frameworks
- [Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct)
- [Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct)
- [Unsloth — Qwen3-VL Fine-tuning](https://unsloth.ai/docs/models/qwen3-vl-how-to-run-and-fine-tune)
- [Unsloth — Vision Fine-tuning Guide](https://unsloth.ai/docs/basics/vision-fine-tuning)
- [LLaMA-Factory — Qwen VL](https://qwen.readthedocs.io/en/latest/training/llama_factory.html)
- [2U1/Qwen-VL-Series-Finetune](https://github.com/2U1/Qwen-VL-Series-Finetune)
- [Fine-Tuning Qwen3-VL 8B (DataCamp)](https://www.datacamp.com/tutorial/fine-tuning-qwen3-vl-8b)
- [Qwen3-VL-8B VRAM + Unsloth (Kaitchup)](https://kaitchup.substack.com/p/qwen3-vl-fine-tuning-on-your-computer)

### Trabalhos de GUI Grounding e Agentes
- [ZonUI-3B: GUI Grounding with 3B VLM](https://arxiv.org/html/2506.23491)
- [GUI-Actor: Coordinate-Free Visual Grounding](https://microsoft.github.io/GUI-Actor/)
- [OS-Atlas: Foundation Action Model](https://arxiv.org/abs/2410.23218) — [Data](https://huggingface.co/datasets/OS-Copilot/OS-Atlas-data)
- [AgentCPM-GUI: Reinforcement Fine-Tuning](https://aclanthology.org/2025.emnlp-demos.12.pdf)
- [UI-E2I-Synth: Advancing GUI Grounding](https://aclanthology.org/2025.findings-acl.809.pdf)
- [Fine-Tuning VLM for Grounding (HF Cookbook)](https://huggingface.co/learn/cookbook/en/fine_tuning_vlm_object_detection_grounding)

### Datasets
- [AITW — Android In The Wild](https://github.com/google-research/google-research/tree/master/android_in_the_wild) — [Paper](https://arxiv.org/abs/2307.10088)
- [AndroidControl](https://arxiv.org/abs/2406.08264)
- [AMEX — Android Multi-annotation Expo](https://huggingface.co/datasets/Yuxiang007/AMEX) — [Paper](https://arxiv.org/abs/2407.17490)
- [MobileViews](https://huggingface.co/datasets/mllmTeam/MobileViews) — [Paper](https://arxiv.org/html/2409.14337)
- [Mobile3M](https://huggingface.co/datasets/xwk123/Mobile3M)
- [RICO](https://interactionmining.org/rico)
- [RICO-Screen2Words](https://huggingface.co/datasets/rootsautomation/RICO-Screen2Words)
- [RICO-SCA](https://huggingface.co/datasets/rootsautomation/RICO-SCA)
- [MoTIF](https://arxiv.org/abs/2202.02312)

### RL para GUI Grounding (Abordagem D)
- [SE-GUI: Self-Evolutionary RL for GUI Grounding](https://arxiv.org/html/2505.12370v1)
- [GUI-G1: Understanding R1-Zero-Like Training](https://openreview.net/pdf/f6767d3d1ddd7b12b85d94abd6d7a313406de8a8.pdf)
- [GRPO for GUI Grounding Done Right (HF Blog)](https://huggingface.co/blog/HelloKKMe/grounding-r1)
- [TRL GRPOTrainer](https://huggingface.co/docs/trl/en/grpo_trainer)

### Catastrophic Forgetting e Mitigação
- [SMoLoRA: Dual Catastrophic Forgetting in Continual Visual (ICCV 2025)](https://openaccess.thecvf.com/content/ICCV2025/papers/Wang_SMoLoRA_Exploring_and_Defying_Dual_Catastrophic_Forgetting_in_Continual_Visual_ICCV_2025_paper.pdf)
- [VLM2VLA: Fine-tuning Without Catastrophic Forgetting](https://arxiv.org/html/2509.22195v1)

### Datasets Adicionais
- [Aguvis: 4.2M Grounding + 1.3M Trajectories (ICML 2025)](https://aguvis-project.github.io/)
- [SeeClick: GUI Grounding Web Corpus](https://github.com/njucckevin/SeeClick)

### Alternativas a Fine-Tuning
- [GUIPivot: Query Inference sem Fine-Tuning](https://arxiv.org/pdf/2503.00401)

### Tutoriais e Guias Práticos
- [Fine-Tuning Qwen2.5-VL (Roboflow)](https://blog.roboflow.com/fine-tune-qwen-2-5/)
- [Fine-Tuning VLM with TRL (HF Cookbook)](https://huggingface.co/learn/cookbook/en/fine_tuning_vlm_trl)
- [AWS — Fine-tune Qwen2-VL with LLaMA-Factory](https://github.com/aws-samples/fine-tune-qwen2-vl-with-llama-factory)
- [Creating Custom VL Dataset for LLaMA-Factory](https://ashokpoudel.medium.com/a-step-by-step-guide-to-creating-a-custom-vision-language-dataset-for-fine-tuning-qwen-2-vl-with-c2c996fb67b8)
- [Practical Guide: Fine-tuning Qwen3 with LoRA (DPO)](https://blog.ivan.digital/finetuning-qwen3-with-lora-done-right-94d6343e1814)
