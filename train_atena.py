#!/usr/bin/env python3
"""
train_atena.py — Fine-tuning do Qwen com os contos do Senhor Robério

Usa QLoRA para treinar o modelo localmente.
Sem custo de API. Funciona em CPU com 15.7GB RAM.

Requisitos:
    pip install transformers peft datasets accelerate bitsandbytes trl
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AtenaTraining")


# ══════════════════════════════════════════════════════════════════════
# 1. COLETA DOS CONTOS
# ══════════════════════════════════════════════════════════════════════

CONTO_PATHS = [
    r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\temp_docs\O Gotejar do Tempo.txt",
    r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\temp_docs\Renascer.txt",
    r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\temp_docs\Selene.txt",
    r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\temp_docs\Sussurros Prateados.txt",
]

LITERARY_VAULT = r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\literary_vault"


def collect_contos() -> List[Dict[str, str]]:
    """Coleta todos os contos disponíveis."""
    contos = []
    
    # Contos conhecidos
    for path in CONTO_PATHS:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
                title = os.path.basename(path).replace('.txt', '')
                contos.append({
                    "title": title,
                    "text": text,
                    "source": path,
                })
                logger.info(f"Conto coletado: {title} ({len(text)} chars)")
    
    # Literary vault
    if os.path.exists(LITERARY_VAULT):
        for f in os.listdir(LITERARY_VAULT):
            if f.endswith('.txt'):
                path = os.path.join(LITERARY_VAULT, f)
                with open(path, 'r', encoding='utf-8') as fh:
                    text = fh.read()
                    title = f.replace('.txt', '')
                    contos.append({
                        "title": title,
                        "text": text,
                        "source": path,
                    })
                    logger.info(f"Conto vault: {title} ({len(text)} chars)")
    
    logger.info(f"Total: {len(contos)} contos coletados")
    return contos


# ══════════════════════════════════════════════════════════════════════
# 2. PREPARAÇÃO DO DATASET
# ══════════════════════════════════════════════════════════════════════

def create_training_dataset(contos: List[Dict[str, str]], output_path: str = "atena_training.jsonl"):
    """
    Cria dataset de treinamento no formato JSONL.
    
    Formato:
    {"instruction": "Escreva um conto no estilo do Senhor Robério", "input": "Tema: memória e tempo", "output": "..."}
    """
    dataset = []
    
    for conto in contos:
        # Criar exemplos de treinamento a partir de cada conto
        text = conto["text"]
        title = conto["title"]
        
        # Exemplo 1: Continuação de texto
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 50]
        
        for i in range(0, len(paragraphs) - 1, 2):
            if i + 1 < len(paragraphs):
                context = paragraphs[i]
                continuation = paragraphs[i + 1]
                
                dataset.append({
                    "instruction": f"Continue o conto '{title}' no estilo literário do Senhor Robério, mantendo a narrativa em primeira pessoa, temas de memória/tempo/transcendência, e prosa poética.",
                    "input": context[:500],
                    "output": continuation[:500],
                })
        
        # Exemplo 2: Análise de estilo
        dataset.append({
            "instruction": "Analise o estilo literário deste trecho, identificando: narrativa (1a/3a pessoa), temas principais, figuras de linguagem, e tom emocional.",
            "input": text[:1000],
            "output": f"Conto: {title}\nNarrativa: Primeira pessoa\nTemas: Memória, tempo, transcendência, solidão\nEstilo: Prosa poética, fluxo de consciência, metáforas naturais\nTom: Melancólico, reflexivo, filosófico",
        })
        
        # Exemplo 3: Criação no estilo
        dataset.append({
            "instruction": f"Escreva um trecho literário no estilo do conto '{title}', usando narrativa em primeira pessoa, temas de memória e tempo, e prosa poética.",
            "input": "O cenário é uma casa antiga durante uma chuva.",
            "output": text[:800],
        })
    
    # Salvar dataset
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    logger.info(f"Dataset criado: {len(dataset)} exemplos → {output_path}")
    return dataset


# ══════════════════════════════════════════════════════════════════════
# 3. FINE-TUNING COM QLORA
# ══════════════════════════════════════════════════════════════════════

def train_qlora(
    model_name: str = "qwen3:8b",
    dataset_path: str = "atena_training.jsonl",
    output_dir: str = "atena_lora_adapter",
    epochs: int = 3,
    lr: float = 2e-4,
    batch_size: int = 1,
):
    """
    Fine-tuning com QLoRA.
    
    QLoRA = Quantized Low-Rank Adaptation
    - Quantiza o modelo base para 4-bit
    - Treina apenas adaptadores LoRA (poucos parâmetros)
    - Funciona em CPU com 15GB RAM
    
    Args:
        model_name: Nome do modelo no Ollama
        dataset_path: Caminho do dataset JSONL
        output_dir: Diretório de saída do adapter LoRA
        epochs: Número de épocas
        lr: Learning rate
        batch_size: Batch size (1 para economizar RAM)
    """
    
    try:
        from transformers import (
            AutoModelForCausalLM, AutoTokenizer, 
            TrainingArguments, BitsAndBytesConfig
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import SFTTrainer
        from datasets import load_dataset
        import torch
        
        logger.info(f"Iniciando QLoRA training: {model_name}")
        
        # Configuração de quantização 4-bit
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        
        # Carregar modelo
        logger.info("Carregando modelo...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
        )
        tokenizer.pad_token = tokenizer.eos_token
        
        # Preparar para treinamento
        model = prepare_model_for_kbit_training(model)
        
        # Configuração LoRA
        lora_config = LoraConfig(
            r=16,                    # Rank do LoRA
            lora_alpha=32,           # Alpha scaling
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )
        
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
        
        # Carregar dataset
        logger.info(f"Carregando dataset: {dataset_path}")
        dataset = load_dataset("json", data_files=dataset_path, split="train")
        
        # Tokenização
        def tokenize_function(examples):
            texts = []
            for inst, inp, out in zip(examples["instruction"], examples["input"], examples["output"]):
                text = f"### Instrução:\n{inst}\n\n### Entrada:\n{inp}\n\n### Resposta:\n{out}"
                texts.append(text)
            
            return tokenizer(
                texts,
                truncation=True,
                max_length=512,
                padding="max_length",
            )
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        
        # Argumentos de treinamento
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=lr,
            fp16=True,
            logging_steps=10,
            save_strategy="epoch",
            warmup_ratio=0.1,
            optim="paged_adamw_8bit",
            report_to="none",
        )
        
        # Trainer
        trainer = SFTTrainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            tokenizer=tokenizer,
            max_seq_length=512,
        )
        
        # Treinar
        logger.info("Iniciando treinamento...")
        trainer.train()
        
        # Salvar adapter
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        
        logger.info(f"Treinamento completo! Adapter salvo em: {output_dir}")
        return True
        
    except ImportError as e:
        logger.error(f"Dependência não instalada: {e}")
        logger.info("Instale com: pip install transformers peft datasets accelerate bitsandbytes trl torch")
        return False
    except Exception as e:
        logger.error(f"Erro no treinamento: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════
# 4. GERAÇÃO COM O MODELO TREINADO
# ══════════════════════════════════════════════════════════════════════

class AtenaGenerator:
    """
    Gerador de texto usando o Qwen treinado com os contos.
    """
    
    def __init__(self, model_name: str = "qwen3:8b", adapter_path: str = None):
        self.model_name = model_name
        self.adapter_path = adapter_path
        self.model = None
        self.tokenizer = None
    
    def load(self):
        """Carrega o modelo (com adapter se disponível)."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            logger.info(f"Carregando modelo: {self.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
            )
            
            # Carregar adapter LoRA se disponível
            if self.adapter_path and os.path.exists(self.adapter_path):
                from peft import PeftModel
                self.model = PeftModel.from_pretrained(self.model, self.adapter_path)
                logger.info(f"Adapter LoRA carregado: {self.adapter_path}")
            
            logger.info("Modelo carregado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            return False
    
    def generate(
        self,
        instruction: str,
        input_text: str = "",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Gera texto no estilo dos contos."""
        if not self.model:
            if not self.load():
                return "Erro: modelo não carregado"
        
        prompt = f"### Instrução:\n{instruction}\n\n### Entrada:\n{input_text}\n\n### Resposta:\n"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        import torch
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extrair apenas a resposta
        if "### Resposta:" in response:
            response = response.split("### Resposta:")[-1].strip()
        
        return response


# ══════════════════════════════════════════════════════════════════════
# 5. PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

def main():
    """Pipeline completo de treinamento."""
    logger.info("=" * 60)
    logger.info("ATENA EVOLUÇÃO — Treinamento com Contos")
    logger.info("=" * 60)
    
    # 1. Coletar contos
    contos = collect_contos()
    if not contos:
        logger.error("Nenhum conto encontrado!")
        return
    
    # 2. Criar dataset
    dataset = create_training_dataset(contos)
    
    # 3. Treinar (opcional — requer GPU ou muita RAM)
    logger.info("\nPara treinar o modelo, execute:")
    logger.info("  python train_atena.py --train")
    logger.info("\nOu use o Ollama diretamente com o modelo base:")
    logger.info("  ollama run qwen3:8b")
    
    # 4. Testar geração
    logger.info("\nTestando geração com Qwen...")
    generator = AtenaGenerator(model_name="qwen3:8b")
    
    if generator.load():
        result = generator.generate(
            instruction="Escreva um trecho literário no estilo dos contos do Senhor Robério, sobre memória e tempo.",
            input_text="Uma casa antiga durante uma chuva.",
            max_tokens=200,
        )
        logger.info(f"Geração:\n{result[:300]}...")
    else:
        logger.info("Modelo não carregado. Use o Ollama diretamente.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Treinamento Atena Evolução")
    parser.add_argument("--train", action="store_true", help="Iniciar treinamento QLoRA")
    parser.add_argument("--generate", type=str, help="Gerar texto com instrução")
    parser.add_argument("--model", default="qwen3:8b", help="Modelo base")
    
    args = parser.parse_args()
    
    if args.train:
        contos = collect_contos()
        dataset = create_training_dataset(contos)
        train_qlora(model_name=args.model)
    elif args.generate:
        gen = AtenaGenerator(model_name=args.model)
        if gen.load():
            result = gen.generate(args.generate)
            print(result)
    else:
        main()
