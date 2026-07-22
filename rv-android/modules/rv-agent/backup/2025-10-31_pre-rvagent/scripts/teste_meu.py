"""
Exemplo simples de uso do HuggingFace com quantização de 4 bits
Requerimentos:
pip install transformers torch bitsandbytes accelerate python-dotenv
"""

import os
import torch
from dotenv import load_dotenv
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    BitsAndBytesConfig
)

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

def setup_model_quantized():
    """
    Configura e carrega o modelo com quantização de 4 bits
    """
    # Lê o token do HuggingFace do .env (opcional para modelos públicos)
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    
    # Define o modelo pequeno (GPT-2 é público e não precisa de token)
    model_name = "gpt2"  # Modelo pequeno e eficiente
    # Alternativas pequenas: "microsoft/DialoGPT-small", "distilgpt2"
    
    print(f"Carregando modelo: {model_name}")
    
    # Configuração de quantização 4-bit
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,                    # Carrega em 4 bits
        bnb_4bit_use_double_quant=True,       # Quantização dupla para mais compressão
        bnb_4bit_compute_dtype=torch.float16, # Tipo de dado para computação
        bnb_4bit_quant_type="nf4"            # Tipo de quantização (nf4 = NormalFloat4)
    )
    
    # Carrega o tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        token=hf_token  # Use o token se necessário
    )
    
    # Define pad_token se não existir
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Carrega o modelo com quantização
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quantization_config,
        device_map="auto",  # Distribui automaticamente entre CPU/GPU
        token=hf_token,     # Use o token se necessário
        torch_dtype=torch.float16
    )
    
    print("Modelo carregado com sucesso!")
    return model, tokenizer


def generate_text(model, tokenizer, prompt, max_length=100):
    """
    Gera texto a partir de um prompt
    """
    # Tokeniza o input
    inputs = tokenizer(
        prompt, 
        return_tensors="pt",
        padding=True,
        truncation=True
    )
    
    # Move para o mesmo dispositivo do modelo
    input_ids = inputs["input_ids"]
    attention_mask = inputs["attention_mask"]
    
    # Gera o texto
    with torch.no_grad():
        outputs = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_length,
            temperature=0.7,          # Controla a criatividade
            top_p=0.9,               # Nucleus sampling
            do_sample=True,          # Ativa sampling
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # Decodifica a saída
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Remove o prompt da resposta
    response = generated_text[len(prompt):].strip()
    
    return response


def main():
    """
    Exemplo de uso
    """
    try:
        # Configura o modelo
        model, tokenizer = setup_model_quantized()
        
        # Exemplos de prompts
        prompts = [
            "Once upon a time, in a distant galaxy,",
            "The secret to happiness is",
            "In the year 2050, technology will"
        ]
        
        # Gera texto para cada prompt
        for prompt in prompts:
            print(f"\n📝 Prompt: {prompt}")
            print("-" * 50)
            
            response = generate_text(
                model, 
                tokenizer, 
                prompt,
                max_length=50  # Limita o tamanho da resposta
            )
            
            print(f"🤖 Resposta: {response}")
        
        # Limpa memória (importante com quantização)
        del model
        torch.cuda.empty_cache()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("\nDicas de resolução:")
        print("1. Certifique-se de ter instalado: pip install transformers torch bitsandbytes accelerate")
        print("2. Se não tiver GPU, remova a quantização_config do from_pretrained")
        print("3. Para modelos privados, adicione HUGGINGFACE_TOKEN no arquivo .env")


if __name__ == "__main__":
    main()
