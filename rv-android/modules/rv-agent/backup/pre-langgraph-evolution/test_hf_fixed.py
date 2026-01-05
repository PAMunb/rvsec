#!/usr/bin/env python3
"""
HuggingFace Test Corrigido - Baseado no teste do usuário
Corrige o problema de device placement
"""

import os
import torch
from dotenv import load_dotenv
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig
)

# Load environment
load_dotenv()

def setup_model_quantized():
    """
    Configura e carrega o modelo com quantização de 4 bits - CORRIGIDO
    """
    # Lê o token do HuggingFace do .env
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    print(f"Token encontrado: {bool(hf_token)}")

    # Define o modelo pequeno
    model_name = "gpt2"
    print(f"Carregando modelo: {model_name}")

    # Configuração de quantização 4-bit
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,  # Mudança: bfloat16 é mais estável
        bnb_4bit_quant_type="nf4"
    )

    # Carrega o tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        token=hf_token
    )

    # Define pad_token se não existir
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Carrega o modelo com quantização
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quantization_config,
        device_map="auto",
        token=hf_token,
        torch_dtype=torch.bfloat16  # Consistency com quantization
    )

    print(f"✅ Modelo carregado! Device: {next(model.parameters()).device}")
    return model, tokenizer

def generate_text(model, tokenizer, prompt, max_length=50):
    """
    Gera texto - CORRIGIDO device placement
    """
    # Tokeniza o input
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        padding=True,
        truncation=True
    )

    # CORREÇÃO: Move inputs para mesmo device do modelo
    device = next(model.parameters()).device
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)

    print(f"  Input device: {input_ids.device}, Model device: {device}")

    # Gera o texto
    with torch.no_grad():
        outputs = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_length,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )

    # Decodifica a saída
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    response = generated_text[len(prompt):].strip()

    return response

def main():
    """
    Test HuggingFace corrigido
    """
    try:
        print("🔍 Test HuggingFace Quantização Corrigida")
        print("=" * 50)

        # Setup modelo
        model, tokenizer = setup_model_quantized()

        # Test prompts
        prompts = [
            "Hello, how are you?",
            "The future of AI is"
        ]

        # Generate para cada prompt
        for prompt in prompts:
            print(f"\n📝 Prompt: {prompt}")
            print("-" * 40)

            response = generate_text(model, tokenizer, prompt, max_length=30)
            print(f"🤖 Response: {response}")

        # GPU Memory check
        if torch.cuda.is_available():
            memory_used = torch.cuda.memory_allocated() / 1024**3
            print(f"\n📊 GPU Memory used: {memory_used:.2f} GB")

        print("\n✅ HuggingFace quantization test SUCCESSFUL!")

        # Cleanup
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()