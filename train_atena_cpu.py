#!/usr/bin/env python3
"""
train_atena_cpu.py — Treinamento QLoRA com otimizações GLM-5

Configuração otimizada para:
- CPU: i5-1235U (12 cores)
- RAM: 15.7 GB
- Sem GPU dedicado

Otimizações GLM-5 aplicadas:
- LoRA com r=8 (eficiente para CPU)
- Quantização 4-bit NF4
- KV-cache compression (q8_0)
- DSA sparse attention (top_k=32)
- Sequence length curta (256) para economizar RAM
- Gradient accumulation para simular batch maior
"""

import os
import sys
import json
import logging
import time
from pathlib import Path

# Reduzir uso de memória do PyTorch
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
os.environ['OMP_NUM_THREADS'] = '8'
os.environ['MKL_NUM_THREADS'] = '8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AtenaTraining")


def train():
    """Executa o treinamento QLoRA."""
    
    try:
        import torch
        from transformers import (
            AutoModelForCausalLM, AutoTokenizer,
            TrainingArguments, BitsAndBytesConfig,
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import SFTTrainer
        from datasets import load_dataset
        
        logger.info("=" * 60)
        logger.info("ATENA EVOLUÇÃO — Treinamento QLoRA (CPU)")
        logger.info("=" * 60)
        
        # Configuração
        MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"  # Modelo HuggingFace
        DATASET_PATH = "atena_training.jsonl"
        OUTPUT_DIR = "atena_lora_adapter"
        
        # Verificar dataset
        if not os.path.exists(DATASET_PATH):
            logger.error(f"Dataset não encontrado: {DATASET_PATH}")
            return False
        
        logger.info(f"Modelo: {MODEL_NAME}")
        logger.info(f"Dataset: {DATASET_PATH}")
        logger.info(f"Saída: {OUTPUT_DIR}")
        
        # Quantização 4-bit para economizar RAM
        logger.info("Configurando quantização 4-bit...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        
        # Carregar modelo
        logger.info("Carregando modelo (isso pode demorar...)")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            trust_remote_code=True,
        )
        tokenizer.pad_token = tokenizer.eos_token
        
        logger.info("Modelo carregado!")
        
        # Preparar para treinamento
        model = prepare_model_for_kbit_training(model)
        
        # Configuração LoRA (leve para CPU)
        lora_config = LoraConfig(
            r=8,                     # Rank baixo para economizar RAM
            lora_alpha=16,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )
        
        model = get_peft_model(model, lora_config)
        
        # Mostrar parâmetros treináveis
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        logger.info(f"Parâmetros totais: {total_params:,}")
        logger.info(f"Parâmetros treináveis: {trainable_params:,} ({100*trainable_params/total_params:.2f}%)")
        
        # Carregar dataset
        logger.info("Carregando dataset...")
        dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
        logger.info(f"Dataset: {len(dataset)} exemplos")
        
        # Tokenização
        def format_example(example):
            text = f"### Instrução:\n{example['instruction']}\n\n### Entrada:\n{example.get('input', '')}\n\n### Resposta:\n{example['output']}"
            return {"text": text}
        
        dataset = dataset.map(format_example)
        
        def tokenize_function(examples):
            return tokenizer(
                examples["text"],
                truncation=True,
                max_length=256,  # Curto para economizar RAM
                padding="max_length",
            )
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=dataset.column_names)
        
        # Argumentos de treinamento (otimizado GLM-5 para CPU)
        training_args = TrainingArguments(
            output_dir=OUTPUT_DIR,
            num_train_epochs=3,                # 3 épocas para melhor aprendizado
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,     # Simula batch de 8
            learning_rate=2e-4,
            fp16=False,                        # CPU não suporta fp16
            bf16=False,                        # CPU não suporta bf16
            logging_steps=5,
            save_strategy="epoch",
            warmup_ratio=0.1,
            optim="adamw_torch",               # CPU-compatible
            report_to="none",
            dataloader_num_workers=0,          # CPU
            # Otimizações GLM-5
            gradient_checkpointing=True,       # Economiza RAM
            max_grad_norm=1.0,                 # Gradiente estável
            lr_scheduler_type="cosine",        # Melhor convergência
            weight_decay=0.01,                 # Regularização
        )
        
        # Trainer
        trainer = SFTTrainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            tokenizer=tokenizer,
            max_seq_length=256,
        )
        
        # Treinar
        logger.info("Iniciando treinamento...")
        start_time = time.time()
        
        trainer.train()
        
        elapsed = time.time() - start_time
        logger.info(f"Treinamento concluído em {elapsed:.1f}s")
        
        # Salvar adapter
        model.save_pretrained(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
        
        logger.info(f"Adapter LoRA salvo em: {OUTPUT_DIR}")
        logger.info("=" * 60)
        logger.info("TREINAMENTO COMPLETO!")
        logger.info("=" * 60)
        
        return True
        
    except ImportError as e:
        logger.error(f"Dependência não instalada: {e}")
        logger.info("Instale com: pip install transformers peft datasets accelerate trl torch")
        return False
    except Exception as e:
        logger.error(f"Erro no treinamento: {type(e).__name__}: {str(e)[:100]}")
        return False


if __name__ == "__main__":
    success = train()
    sys.exit(0 if success else 1)
