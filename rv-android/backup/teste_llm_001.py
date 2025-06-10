import json
import logging
import os
import sys
import time
from typing import Dict, Any

import torch
from transformers import AutoProcessor, Gemma3ForConditionalGeneration
from transformers import BitsAndBytesConfig

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.llm.constants import PromptStrategyType, ScreenParserType, VisitorType, StateEntry
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.parser.static import static_analysis_parser

"""
Implementação otimizada do cliente HuggingFace para melhorar o desempenho
de inferência, aproximando o tempo do Ollama.

Este módulo contém otimizações específicas para a geração de texto
com modelos Hugging Face, focando em reduzir o tempo de inferência.
"""

import time
import logging
import os
from typing import List, Dict, Optional, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import BitsAndBytesConfig, TextIteratorStreamer
from threading import Thread

from rvandroid.llm.language_model import LanguageModel
from rvandroid.llm.data_structures import LLMMessage, LLMResponse
from rvandroid.llm.llm_config import LLMConfiguration


class OptimizedHuggingFaceLLM(LanguageModel):
    """
    Uma implementação otimizada do HuggingFaceLLM para melhor desempenho.
    """
    NAME = "optimized_huggingface"

    # Definições de modelos disponíveis
    LLAMA = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    DEEPSEEK = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
    GEMMA = "google/gemma-3-4b-it"
    QWEN = "Qwen/Qwen2.5-3B-Instruct"
    PHI = "microsoft/Phi-3.5-mini-instruct"
    GRANITE = "ibm-granite/granite-3.1-8b-instruct"
    FALCON = "tiiuae/Falcon3-3B-Instruct"
    MISTRAL = "mistralai/Mistral-7B-Instruct-v0.3"

    # Conjunto padrão de modelos para usar
    MODELS = [LLAMA, GEMMA, QWEN]

    def __init__(self, model_name: str, device: str = "cuda", **kwargs):
        """
        Inicializa o OptimizedHuggingFaceLLM.

        Args:
            model_name: Nome do modelo Hugging Face
            device: Dispositivo para inferência ('cuda' ou 'cpu')
            **kwargs: Parâmetros adicionais para geração
        """
        # Inicializa a classe base do modelo de linguagem
        super().__init__(model_name, **kwargs)

        # Configuração do logger
        self.logger = logging.getLogger("llm.optimized_huggingface")

        # Propriedades do modelo
        self._model = None
        self._tokenizer = None
        self._device = device

        # Armazena o dispositivo em kwargs para consistência
        self.kwargs["device"] = device

        # Configurações de geração otimizadas
        self.generation_config = {
            "max_new_tokens": kwargs.get("max_new_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.2),
            "top_p": kwargs.get("top_p", 0.95),
            "top_k": kwargs.get("top_k", 40),
            "repetition_penalty": kwargs.get("repetition_penalty", 1.1),
            "do_sample": kwargs.get("temperature", 0.2) > 0.001,
            "pad_token_id": kwargs.get("pad_token_id", None),
            "eos_token_id": kwargs.get("eos_token_id", None),
        }

        # Carrega o modelo e tokenizador se pre_load estiver habilitado
        if kwargs.get("pre_load", True):
            self.logger.info(f"Pré-carregando modelo {model_name}")
            _ = self.model
            _ = self.tokenizer

    @property
    def model(self):
        """
        Carrega e retorna o modelo de linguagem (lazy-loaded).

        Returns:
            Instância AutoModelForCausalLM
        """
        if self._model is None:
            self.logger.info(f"Carregando modelo {self.model_name} em {self._device}...")
            try:
                # Determina o dtype apropriado com base no dispositivo
                torch_dtype = torch.bfloat16 if self._device == "cuda" else torch.float32

                # Configuração de quantização para carregamento mais eficiente
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch_dtype,
                    bnb_4bit_quant_type="nf4"
                )

                # Opções de carregamento otimizadas
                model_kwargs = {
                    "device_map": self._device,
                    "torch_dtype": torch_dtype,
                    "low_cpu_mem_usage": True,
                }

                # Adiciona quantização se estiver em CUDA
                if self._device == "cuda":
                    model_kwargs["quantization_config"] = quantization_config

                # Carrega o modelo com configurações otimizadas
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    **model_kwargs
                )

                # Ativa o modo de avaliação para melhor desempenho de inferência
                model.eval()

                # Tenta compilar o modelo se a versão do PyTorch suportar
                if hasattr(torch, 'compile') and self._device == 'cuda':
                    try:
                        self.logger.info("Compilando modelo para melhor desempenho...")
                        model = torch.compile(model, mode="reduce-overhead")
                        self.logger.info("Compilação do modelo bem-sucedida")
                    except Exception as e:
                        self.logger.warning(f"Não foi possível compilar o modelo: {str(e)}")

                self._model = model
                self.logger.info(f"Modelo {self.model_name} carregado com sucesso")

            except Exception as e:
                error_msg = f"Erro ao carregar modelo: {str(e)}"
                self.logger.error(error_msg)
                raise

        return self._model

    @property
    def tokenizer(self):
        """
        Carrega e retorna o tokenizador (lazy-loaded).

        Returns:
            Instância AutoTokenizer
        """
        if self._tokenizer is None:
            self.logger.info(f"Carregando tokenizador para {self.model_name}...")
            try:
                # Carrega o tokenizador com opções otimizadas
                tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    use_fast=True,
                    padding_side="left"
                )

                # Se não tiver um pad_token, define um
                if tokenizer.pad_token is None:
                    # Tenta usar um token de padding comum se existir no vocabulário
                    if '<pad>' in tokenizer.get_vocab():
                        tokenizer.pad_token = '<pad>'
                    # Caso contrário, usa o token EOS
                    else:
                        tokenizer.pad_token = tokenizer.eos_token

                self._tokenizer = tokenizer
                self.logger.info(f"Tokenizador para {self.model_name} carregado com sucesso")

            except Exception as e:
                error_msg = f"Erro ao carregar tokenizador: {str(e)}"
                self.logger.error(error_msg)
                raise

        return self._tokenizer

    def generate(self, messages: List[LLMMessage], config: Optional[LLMConfiguration] = None) -> LLMResponse:
        """
        Gera texto com base nas mensagens de entrada, com otimizações para desempenho.

        Args:
            messages: Lista de objetos LLMMessage
            config: Objeto LLMConfiguration opcional

        Returns:
            LLMResponse contendo o texto gerado e métricas de desempenho
        """
        # Usa a configuração fornecida ou a padrão
        _config = config or self.default_config

        try:
            # Rastreia métricas de desempenho
            start_time = time.time()
            load_start_time = start_time

            # Formata mensagens para HuggingFace
            hf_messages = []
            for message in messages:
                content = message.get_text_content()
                hf_messages.append({
                    "role": message.role.value,
                    "content": content
                })

            # Extrai parâmetros de geração da configuração
            max_new_tokens = _config.max_tokens if _config and _config.max_tokens is not None else \
            self.generation_config["max_new_tokens"]
            temperature = _config.temperature if _config and _config.temperature is not None else \
            self.generation_config["temperature"]
            top_p = _config.kwargs.get("top_p", self.generation_config["top_p"])
            top_k = _config.kwargs.get("top_k", self.generation_config["top_k"])
            repetition_penalty = _config.kwargs.get("repetition_penalty", self.generation_config["repetition_penalty"])

            # Garante que modelo e tokenizador estejam carregados
            _ = self.model  # Isso aciona o lazy loading
            _ = self.tokenizer

            # Registra o tempo de carregamento do modelo
            load_end_time = time.time()
            load_duration = (load_end_time - load_start_time) * 1000  # Converte para ms

            # Inicia o timer de tokenização
            tokenization_start = time.time()

            # Usa o mecanismo de processamento otimizado para diferentes tipos de modelos
            # Alguns modelos têm templates de chat específicos
            try:
                # Primeiro, tenta com apply_chat_template, que é mais rápido para modelos de chat
                encoded_input = self.tokenizer.apply_chat_template(
                    hf_messages,
                    return_tensors="pt",
                    add_generation_prompt=True
                )
            except (AttributeError, NotImplementedError):
                # Fallback para modelos sem template de chat
                combined_text = "\n\n".join([m.get("content", "") for m in hf_messages])
                encoded_input = self.tokenizer(
                    combined_text,
                    return_tensors="pt",
                    padding="max_length",
                    truncation=True,
                    max_length=2048
                ).input_ids

            # Tamanho da entrada para identificar apenas novos tokens depois
            input_length = encoded_input.shape[1]
            input_tokens = input_length

            # Move tensores para o dispositivo correto
            inputs = encoded_input.to(self._device)

            # Fim do timer de tokenização
            tokenization_end = time.time()
            input_tokens_duration = (tokenization_end - tokenization_start) * 1000  # Converte para ms

            # Configurar parâmetros de geração otimizados
            generation_params = {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "repetition_penalty": repetition_penalty,
                "do_sample": temperature > 0.001,  # Só usa amostragem se a temperatura não for zero
                "use_cache": True,  # Habilita o caching de KV para melhor desempenho
            }

            # Se o token de pad ou eos não estiverem definidos no tokenizador, adiciona-os à configuração
            if self.tokenizer.pad_token_id is not None:
                generation_params["pad_token_id"] = self.tokenizer.pad_token_id
            if self.tokenizer.eos_token_id is not None:
                generation_params["eos_token_id"] = self.tokenizer.eos_token_id

            # Inicia o timer de geração
            generation_start = time.time()

            # Configurar streamer para processamento assíncrono
            streamer = TextIteratorStreamer(self.tokenizer, skip_special_tokens=True, timeout=10.0)
            generation_params["streamer"] = streamer

            # Inicia a geração em uma thread separada para permitir processamento paralelo
            generation_thread = Thread(target=self._generate_text, args=(inputs, generation_params))
            generation_thread.start()

            # Coleta o texto gerado do streamer
            generated_text = ""
            for text_chunk in streamer:
                generated_text += text_chunk

            # Espera a thread de geração terminar
            generation_thread.join()

            # Fim do timer de geração
            generation_end = time.time()
            output_tokens_duration = (generation_end - generation_start) * 1000  # Converte para ms

            # Estima o número de tokens de saída com base no texto gerado
            output_tokens = len(generated_text.split())  # Estimativa aproximada

            # Libera memória
            del inputs
            if self._device == "cuda":
                torch.cuda.empty_cache()

            # Calcula a duração total
            end_time = time.time()
            total_duration = (end_time - start_time) * 1000  # Converte para ms

            # Cria e retorna a resposta com métricas de desempenho
            response = LLMResponse(
                content=generated_text,
            )

            # Adiciona métricas de desempenho
            response.done_reason = "stop"
            response.total_duration = total_duration
            response.load_duration = load_duration
            response.input_tokens = input_tokens
            response.input_tokens_duration = input_tokens_duration
            response.output_tokens = output_tokens
            response.output_tokens_duration = output_tokens_duration

            return response

        except Exception as e:
            error_msg = f"Erro ao gerar texto: {str(e)}"
            self.logger.error(error_msg)
            raise

    def _generate_text(self, inputs, generation_params):
        """
        Método interno para geração de texto em uma thread separada.

        Args:
            inputs: Tensores de entrada tokenizados
            generation_params: Parâmetros de geração
        """
        # Remove o streamer dos parâmetros para evitar confusão de tipos
        streamer = generation_params.pop("streamer")
        generation_params["streamer"] = streamer

        # Gera texto (o resultado será enviado ao streamer)
        with torch.no_grad():
            _ = self.model.generate(
                inputs,
                **generation_params
            )

    def cleanup(self):
        """
        Descarrega o modelo e tokenizador da memória para liberar recursos.
        """
        if hasattr(self, '_model') and self._model is not None:
            del self._model
            self._model = None

        if hasattr(self, '_tokenizer') and self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        if self._device == "cuda":
            torch.cuda.empty_cache()

        self.logger.info("Modelo e tokenizador descarregados, recursos liberados")

    @staticmethod
    def models() -> List[str]:
        """
        Retorna uma lista de modelos disponíveis.

        Returns:
            Lista de identificadores de modelo
        """
        return OptimizedHuggingFaceLLM.MODELS

    @property
    def default_config(self) -> LLMConfiguration:
        """
        Retorna a configuração padrão para este modelo.

        Returns:
            LLMConfiguration com configurações padrão
        """
        return LLMConfiguration(
            model_type=self.NAME,
            model_name=self.model_name,
            max_tokens=1000,
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            repetition_penalty=1.1
        )


# Registra o modelo
def register():
    """Registra o modelo HuggingFace otimizado com o configurador."""
    from rvandroid.config.component_configurator import ComponentConfigurator

    # Verifica se este LLM já está registrado
    if "optimized_huggingface" in ComponentConfigurator._registries.get('llm', {}).get_names():
        # Já registrado, pula o registro
        return

    # Registra o LLM
    ComponentConfigurator.register_llm("optimized_huggingface", OptimizedHuggingFaceLLM)


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Lê o arquivo de estado do DroidBot."""
    with open(filename, 'r') as file:
        return json.load(file)


def create_state_from_droidbot_state(droidbot_state_file: str, screenshot_path: str, package: str,
                                     static_data: StaticAnalysisData):
    """Cria um estado a partir do arquivo de estado do DroidBot."""
    screen_info = read_droidbot_state(droidbot_state_file)
    parser = ParserFactory.create(ParserType.DROIDBOT, BasicTextVisitor)
    screen_description: ScreenDescription = parser.parse(screen_info, static_data)
    state = {
        StateEntry.PACKAGE_NAME: package,
        StateEntry.ACTIVITY: screen_description.activity,
        StateEntry.VIEW_TREE: screen_info[StateEntry.VIEW_TREE],
        StateEntry.SCREENSHOT_PATH: screenshot_path,
        StateEntry.STRUCTURED_SCREEN: screen_description
    }
    return state


def create_ollama_config(model_name: str, static_data: StaticAnalysisData,
                         strategy=PromptStrategyType.BATCH_ACTION,
                         visitor=VisitorType.DEFAULT,
                         temperature=0.2, max_tokens=1200):
    """Cria configuração para o modelo Ollama."""
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,
        model=model_name,
        base_url="http://127.0.0.1:11434",
        temperature=temperature,
        max_tokens=max_tokens
    )
    configurator.set_strategy(strategy)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(visitor)
    return configurator


def create_huggingface_config(model_name: str, static_data: StaticAnalysisData,
                              strategy=PromptStrategyType.BATCH_ACTION,
                              visitor=VisitorType.DEFAULT,
                              temperature=0.2, max_tokens=500):
    """Cria configuração para o modelo HuggingFace padrão."""
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=HuggingFaceLLM.NAME,
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens
    )
    configurator.set_strategy(strategy)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(visitor)
    return configurator


def create_optimized_huggingface_config(model_name: str, static_data: StaticAnalysisData,
                                        strategy=PromptStrategyType.BATCH_ACTION,
                                        visitor=VisitorType.DEFAULT,
                                        temperature=0.2, max_tokens=500):
    """Cria configuração para o modelo HuggingFace otimizado."""
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=OptimizedHuggingFaceLLM.NAME,
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        # Parâmetros adicionais de otimização
        pre_load=True,
        top_p=0.95,
        top_k=40,
        repetition_penalty=1.1
    )
    configurator.set_strategy(strategy)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(visitor)
    return configurator


def benchmark_service(service, state, num_iterations=5, description=""):
    """Executa benchmark do serviço."""
    print(f"\n{'-' * 40}")
    print(f"BENCHMARK: {description}")
    print(f"{'-' * 40}")

    times = []
    for i in range(num_iterations):
        print(f"\nIteração {i + 1}/{num_iterations}")
        start_time = time.time()
        actions = service.process_state(state)
        end_time = time.time()
        duration = end_time - start_time
        times.append(duration)
        print(f"Tempo da iteração {i + 1}: {duration:.2f} segundos")
        print(f"Ações geradas: {len(actions)}")

    # Cálculo de estatísticas
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"\nResultados para {description}:")
    print(f"Tempo médio: {avg_time:.2f} segundos")
    print(f"Tempo mínimo: {min_time:.2f} segundos")
    print(f"Tempo máximo: {max_time:.2f} segundos")
    return avg_time


def main():
    """Função principal para executar os testes de benchmark."""
    # Configuração de logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)

    # Regisitra o LLM otimizado
    register()

    # Caminhos para dados do app
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "009"
    app_folder = screenshots_folder + "/" + apk
    droidbot_state_file = os.path.join(app_folder, f"{prefix}.state")
    srceenshot_file = os.path.join(app_folder, f"{prefix}.png")

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    # Cria estado de teste
    state = create_state_from_droidbot_state(droidbot_state_file, srceenshot_file, package, static_data)

    # Define modelos consistentes para comparação
    deepseek_model = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
    ollama_model = OllamaLLM.DEEPSEEK

    # Parâmetros comuns
    max_tokens = 800
    temperature = 0.2

    # Comparação de desempenho
    results = {}

    # 1. Teste HuggingFace padrão
    try:
        print("\n\n=== TESTE HUGGINGFACE PADRÃO ===")
        configurator = create_huggingface_config(
            model_name=deepseek_model,
            static_data=static_data,
            max_tokens=max_tokens,
            temperature=temperature
        )
        service = LLMActionService(static_data, configurator, package)
        results["HuggingFace Padrão"] = benchmark_service(
            service, state, num_iterations=3, description="HuggingFace Padrão"
        )
        service.llm_manager.cleanup()
        # Limpeza explícita
        torch.cuda.empty_cache()
        import gc
        gc.collect()
    except Exception as e:
        print(f"Erro no teste HuggingFace padrão: {e}")
        results["HuggingFace Padrão"] = "ERRO"

    # 2. Teste HuggingFace Otimizado
    try:
        print("\n\n=== TESTE HUGGINGFACE OTIMIZADO ===")
        configurator = create_optimized_huggingface_config(
            model_name=deepseek_model,
            static_data=static_data,
            max_tokens=max_tokens,
            temperature=temperature
        )
        service = LLMActionService(static_data, configurator, package)
        results["HuggingFace Otimizado"] = benchmark_service(
            service, state, num_iterations=3, description="HuggingFace Otimizado"
        )
        service.llm_manager.cleanup()
        # Limpeza explícita
        torch.cuda.empty_cache()
        import gc
        gc.collect()
    except Exception as e:
        print(f"Erro no teste HuggingFace otimizado: {e}")
        results["HuggingFace Otimizado"] = "ERRO"

    # 3. Teste Ollama
    try:
        print("\n\n=== TESTE OLLAMA ===")
        configurator = create_ollama_config(
            model_name=ollama_model,
            static_data=static_data,
            max_tokens=max_tokens,
            temperature=temperature
        )
        service = LLMActionService(static_data, configurator, package)
        results["Ollama"] = benchmark_service(
            service, state, num_iterations=3, description="Ollama"
        )
        service.llm_manager.cleanup()
    except Exception as e:
        print(f"Erro no teste Ollama: {e}")
        results["Ollama"] = "ERRO"

    # Resultados finais
    print("\n\n" + "=" * 50)
    print("RESULTADOS COMPARATIVOS DE DESEMPENHO")
    print("=" * 50)
    for name, value in results.items():
        if isinstance(value, float):
            print(f"{name}: {value:.2f} segundos")
        else:
            print(f"{name}: {value}")
    print("=" * 50)

    # Cálculo da diferença percentual (se possível)
    if isinstance(results.get("HuggingFace Padrão"), float) and isinstance(results.get("HuggingFace Otimizado"), float):
        improvement = (results["HuggingFace Padrão"] - results["HuggingFace Otimizado"]) / results[
            "HuggingFace Padrão"] * 100
        print(f"Melhoria de desempenho HF Otimizado vs. HF Padrão: {improvement:.1f}%")

    if isinstance(results.get("HuggingFace Otimizado"), float) and isinstance(results.get("Ollama"), float):
        difference = (results["HuggingFace Otimizado"] - results["Ollama"]) / results["Ollama"] * 100
        print(f"Diferença entre HF Otimizado e Ollama: {difference:.1f}% ({'-' if difference > 0 else '+'}lento)")


if __name__ == "__main__":
    main()