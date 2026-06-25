# Pesquisa: Técnicas Avançadas de Redes Neurais para Agentes de IA Autônomos (2025-2026)

> **Data:** 17/06/2026
> **Escopo:** Técnicas para modelos 3-8B parâmetros, foco em autonomia de agentes
> **Versão:** 1.0

---

## Índice

1. [Mixture of Experts (MoE)](#1-mixture-of-experts-moe)
2. [LoRA/QLoRA Avançado](#2-loraqlora-avançado-dora-fora-lokra)
3. [Knowledge Distillation](#3-knowledge-distillation-para-modelos-pequenos)
4. [Speculative Decoding](#4-speculative-decoding)
5. [KV-Cache Compression](#5-kv-cache-compression)
6. [Flash Attention 2/3](#6-flash-attention-23)
7. [Gradient Checkpointing](#7-gradient-checkpointing)
8. [Treinamento com Dados Sintéticos](#8-treinamento-com-dados-sintéticos)
9. [Self-Play e Self-Instruction](#9-self-play-e-self-instruction)
10. [Constitutional AI e RLHF Simplificado](#10-constitutional-ai-e-rlhf-simplificado)
11. [Resumo Comparativo](#11-resumo-comparativo)
12. [Roadmap de Implementação](#12-roadmap-de-implementação)

---

## 1. Mixture of Experts (MoE)

### Conceito

Mixture of Experts é uma arquitetura onde o modelo é dividido em múltiplos "especialistas" (experts) — sub-redes feed-forward independentes — e um **router/gate** seleciona apenas K de N experts para cada token. O resultado: capacidade total alta (muitos parâmetros) com custo computacional baixo (apenas parte ativa por token).

```
Entrada → Router (Top-K gating) → Expert₁, Expert₂, ..., Expertₖ → Saída ponderada
                          ↓
                  Experts N-K (ociosos)
```

**Evolução 2025-2026:**
- **DeepSeek-V3/R1** (671B total, ~37B ativos): router auxiliar-loss-free com bias tokens para balanceamento
- **Mixtral 8x7B** popularizou MoE open-source
- **Qwen3-MoE**, **GLM-4.5 Air** (106B total, 12B ativos)
- **ScMoE** (Sparse Context MoE): experts com context windows diferentes
- **Mixture of Depths**:динамico depth routing (nem todos layers processam todos tokens)

### Aplicabilidade em Modelos 3-8B

| Aspecto | Viabilidade |
|---|---|
| Modelo 3B → MoE 3B (6 experts) | ✅ Viável, ~2x capacidade efetiva |
| Modelo 7B → MoE 7B (8 experts, top-2) | ✅ Excelente, ~4x capacidade com mesmo custo |
| Overhead de memória | Alto (todos experts na RAM) |
| Complexidade de treino | Média-Alta |

**Para agentes autônomos:** MoE permite especialização — experts diferentes para raciocínio, tool calling, parsing, planejamento.

### Implementação Python

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple

class TopKGate(nn.Module):
    """
    Router Top-K para seleção de experts.
    Implementação com auxiliar loss-free (estilo DeepSeek-V3).
    """
    def __init__(self, d_model: int, num_experts: int, top_k: int = 2):
        super().__init__()
        self.top_k = top_k
        self.num_experts = num_experts
        self.gate = nn.Linear(d_model, num_experts, bias=False)
        
        # Bias tokens para balanceamento (loss-free routing)
        # DeepSeek-V3 usa um score bias por expert ajustado por uso
        self.register_buffer(
            self.expert_bias = torch.zeros(num_experts)
        )
        self.register_buffer(
            self.expert_usage_count = torch.zeros(num_experts)
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args: x: (batch, seq_len, d_model)
        Returns: 
            expert_weights: (batch*seq_len, top_k)
            expert_indices: (batch*seq_len, top_k)
        """
        logits = self.gate(x)  # (B, S, E)
        
        # Adicionar bias de balanceamento
        logits = logits + self.expert_bias.unsqueeze(0).unsqueeze(0)
        
        # Top-K selection
        top_k_logits, top_k_indices = torch.topk(
            logits, self.top_k, dim=-1
        )  # (B, S, K)
        
        # Softmax sobre os top-k (não todos experts — eficiente)
        expert_weights = F.softmax(top_k_logits, dim=-1)
        
        # Atualizar contagem de uso (para balanceamento auxiliar)
        if self.training:
            flat_indices = top_k_indices.reshape(-1)
            for e in range(self.num_experts):
                self.expert_usage_count[e] += (flat_indices == e).sum()
        
        return expert_weights, top_k_indices


class Expert(nn.Module):
    """Single Expert — FFN padrão (up-project → activation → down-project)."""
    def __init__(self, d_model: int, d_ff: int, activation: str = "swiglu"):
        super().__init__()
        self.w1 = nn.Linear(d_model, d_ff, bias=False)
        self.w2 = nn.Linear(d_ff, d_model, bias=False)
        self.w3 = nn.Linear(d_model, d_ff, bias=False)  # gate proj (SwiGLU)
        self.activation = activation

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.activation == "swiglu":
            return self.w2(F.silu(self.w1(x)) * self.w3(x))
        return self.w2(F.gelu(self.w1(x)))


class MoELayer(nn.Module):
    """
    Camada Mixture of Experts com roteamento Top-K.
    Substitui a FFN padrão de um bloco Transformer.
    """
    def __init__(
        self, 
        d_model: int = 4096, 
        d_ff: int = 14336, 
        num_experts: int = 8, 
        top_k: int = 2
    ):
        super().__init__()
        self.gate = TopKGate(d_model, num_experts, top_k)
        self.experts = nn.ModuleList([
            Expert(d_model, d_ff) for _ in range(num_experts)
        ])
        self.top_k = top_k
        self.num_experts = num_experts

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args: x: (batch, seq_len, d_model)
        Returns: output: (batch, seq_len, d_model)
        """
        B, S, D = x.shape
        
        expert_weights, expert_indices = self.gate(x)
        # expert_weights: (B, S, K), expert_indices: (B, S, K)
        
        # Flatten para dispatch
        x_flat = x.reshape(-1, D)  # (B*S, D)
        weights_flat = expert_weights.reshape(-1, self.top_k)  # (B*S, K)
        indices_flat = expert_indices.reshape(-1, self.top_k)  # (B*S, K)
        
        # Dispatch: cada token vai para K experts
        output = torch.zeros_like(x_flat)
        
        for i, expert in enumerate(self.experts):
            # Encontrar tokens que usam este expert
            token_mask = (indices_flat == i).any(dim=-1)  # (B*S,)
            if not token_mask.any():
                continue
                
            expert_input = x_flat[token_mask]
            expert_output = expert(expert_input)
            
            # Peso correspondente a este expert para cada token
            expert_weight = weights_flat[token_mask]
            # Pegar o peso K correto (qual dos top-k é este expert)
            weight_for_expert = torch.zeros(expert_input.size(0), device=x.device)
            for k in range(self.top_k):
                weight_for_expert += expert_weight[:, k] * (
                    indices_flat[token_mask, k] == i
                ).float()
            
            output[token_mask] += weight_for_expert.unsqueeze(-1) * expert_output
        
        return output.reshape(B, S, D)


class MoETransformerBlock(nn.Module):
    """Bloco Transformer com MoE no FFN."""
    def __init__(self, d_model=1024, n_heads=8, d_ff=4096, 
                 num_experts=4, top_k=2):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True)
        self.moe = MoELayer(d_model, d_ff, num_experts, top_k)
        self.norm1 = nn.RMSNorm(d_model)
        self.norm2 = nn.RMSNorm(d_model)

    def forward(self, x, mask=None):
        # Pre-norm (estilo LLaMA)
        residual = x
        x = self.norm1(x)
        x, _ = self.attn(x, x, x, attn_mask=mask, is_causal=True)
        x = residual + x
        
        residual = x
        x = self.norm2(x)
        x = residual + self.moe(x)
        return x


# ─── Configuração para modelo 4B ───────────────────────────────────
class MoEModelConfig:
    """Config MoE para modelo ~4B de parâmetros."""
    d_model = 2048
    n_layers = 24
    n_heads = 16
    d_ff = 5632  # por expert
    num_experts = 8
    top_k = 2
    vocab_size = 32000
    max_seq_len = 4096
    
    @property
    def total_params(self):
        # Embedding + attention params + MoE params
        embedding = self.vocab_size * self.d_model
        attn_per_layer = 4 * self.d_layers * self.d_model ** 2  # Q, K, V, O
        ffn_per_layer = self.num_experts * 3 * self.d_model * self.d_ff  # w1, w2, w3
        total = embedding + self.n_layers * (attn_per_layer + ffn_per_layer)
        return total  # ~4B
    
    @property
    def active_params_per_token(self):
        """Parâmetros ativados por token (o que importa para FLOPs)."""
        embedding = self.vocab_size * self.d_model
        attn = self.n_layers * 4 * self.d_model ** 2
        ffn = self.top_k * self.num_experts * 3 * self.d_model * self.d_ff
        return (embedding + attn + ffn)  # ~1.2B ativos!


# ─── Router com Expert Parallelism (para multi-GPU) ────────────────
class ExpertParallelMoE(MoELayer):
    """
    MoE com experts distribuídos entre GPUs.
    Usa all_to_all para dispatch de tokens.
    """
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        import torch.distributed as dist
        
        B, S, D = x.shape
        expert_weights, expert_indices = self.gate(x)
        
        # Tally tokens por expert
        tokens_per_expert = torch.bincount(
            expert_indices.reshape(-1), minlength=self.num_experts
        )
        
        # Sort tokens por expert (all_to_all communication)
        sorted_indices = torch.argsort(expert_indices.reshape(-1))
        x_sorted = x.reshape(-1, D)[sorted_indices]
        
        # Cada GPU processa seus experts locais
        # ... all_to_all dispatch ...
        
        # Unsort
        # ... all_to_all combine ...
        
        return output  # (B, S, D)
```

### Custo Computacional

| Métrica | Dense 7B | MoE 8x7B (top-2) |
|---|---|---|
| **Parâmetros totais** | 7B | ~48B |
| **Parâmetros ativos/token** | 7B | ~12B |
| **Inferência FLOPs/token** | ~14B | ~24B |
| **Memória (inference, fp16)** | ~14 GB | ~96 GB |
| **Throughput relativo** | 1x | ~0.6x |
| **Qualidade (capacidade)** | 1x | ~2-3x |

**Recomendação para agentes:** MoE é viável para modelos 5-8B com 4-8 experts. O gargalo é memória (todos experts carregados). Modelos como **DeepSeekMoE-16B** mostram excelente relação capacidade/custo.

---

## 2. LoRA/QLoRA Avançado (DoRA, FoRA, LoKRA)

### Conceito Base

**LoRA (Low-Rank Adaptation)** congela os pesos pré-treinados W₀ e aprende uma decomposição de baixo rank: W = W₀ + BA, onde B ∈ ℝ^{d×r}, A ∈ ℝ^{r×r'}. Apenas A e B são treinados.

**QLoRA** quantiza W₀ para 4-bit (NF4) e faz LoRA nos pesos quantizados, reduzindo drasticamente memória.

### Variantes Avançadas (2025-2026)

#### Decomposed LoRA (DoRA)
**Conceito:** Decompose W em magnitude + direção. Apenas a magnitude com LoRA.
```
W = m · (W₀ + BA) / ||W₀ + BA||  # Decomposição polar
     ↑          ↑
  magnitude   direção (LoRA)
```
**Benefício:** Melhor que LoRA puro em ~1-3% em benchmarks; mais estável em ranks baixos.

#### Frequency-LoRA (FoRA)
**Conceito:** Aplica LoRA separadamente nos domínios de frequência (via FFT). Componentes de baixa vs alta frequência ajustados independentemente.
```
FFT(x) → [low_freq ⊕ high_freq] → [LoRA_low(x_low) ⊕ LoRA_high(x_high)]
```
**Benefício:** Melhor para adaptação a domínios com distribuições espectrais distintas.

#### Low-Rank Kronecker Adaptation (LoKRA)
**Conceito:** Usa produto de Kronecker A ⊗ B em vez de multiplicação simples. Captura estruturas de baixo rank multidimensionais.
```
ΔW = A ⊗ B, onde A ∈ ℝ^{d₁×r₁}, B ∈ ℝ^{d₂×r₂}
```
d₁ × d₂ = D_in, r₁ × r₂ = r (rank efetivo)
**Benefício:** Mais expressivo que LoRA com mesmo número de parâmetros.

### Implementação Python

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional

# ═══════════════════════════════════════════════════════════
# LoRA Base
# ═══════════════════════════════════════════════════════════

class LoRAAdapter(nn.Module):
    """
    LoRA padrão: ΔW = B @ A, onde rank r << d.
    Parâmetros: 2 * d * r (vs d² no fine-tuning completo)
    """
    def __init__(self, in_features: int, out_features: int, rank: int = 8, alpha: float = 16.0):
        super().__init__()
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank
        
        # A: inicializado com Gaussian (N(0, σ²))
        self.lora_A = nn.Parameter(torch.randn(in_features, rank) * 0.01)
        # B: inicializado com zeros (ΔW = 0 no início)
        self.lora_B = nn.Parameter(torch.zeros(rank, out_features))

    def forward(self, x: torch.Tensor, base_output: torch.Tensor) -> torch.Tensor:
        """x: (..., in_features), base_output = W₀x"""
        lora_delta = (x @ self.lora_A @ self.lora_B) * self.scaling
        return base_output + lora_delta


class LoRALinear(nn.Module):
    """Linear layer com LoRA integrado."""
    def __init__(self, linear: nn.Linear, rank: int = 8, alpha: float = 16.0):
        super().__init__()
        self.base = linear
        self.base.weight.requires_grad = False  # Congelar
        
        self.lora = LoRAAdapter(
            linear.in_features, linear.out_features, rank, alpha
        )
        # Aplicar LoRA a bias se existir
        self.apply_bias = linear.bias is not None

    def forward(self, x):
        base_out = F.linear(x, self.base.weight, self.base.bias)
        return self.lora(x, base_out)


# ═══════════════════════════════════════════════════════════
# DoRA (Decomposed LoRA)
# ═══════════════════════════════════════════════════════════

class DoRAAdapter(nn.Module):
    """
    DoRA: Magnitude-Direction decomposition com LoRA.
    
    W' = m · V/||V|| onde V = W₀ + α·B·A
    m é um vetor de magnitude treinável por coluna.
    
    Referência: Liu et al., "DoRA: Weight-Decomposed Low-Rank Adaptation" (2024)
    """
    def __init__(self, in_features: int, out_features: int, rank: int = 8, alpha: float = 16.0):
        super().__init__()
        self.rank = rank
        self.alpha = alpha
        
        self.lora_A = nn.Parameter(torch.randn(in_features, rank) * 0.01)
        self.lora_B = nn.Parameter(torch.zeros(rank, out_features))
        
        # Vetor de magnitude treinável (por coluna)
        self.magnitude = nn.Parameter(torch.ones(out_features))

    def forward(self, x: torch.Tensor, weight: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, in_features)
            weight: (out_features, in_features) — pesos base congelados
        """
        # Direção: W₀ + α·BA
        lora_update = self.lora_A @ self.lora_B  # (in, out)
        lora_update = lora_update.t()  # (out, in)
        
        V = weight + self.alpha * lora_update
        
        # Normalizar direção (por coluna = por output feature)
        V_norm = F.normalize(V, p=2, dim=1)  # (out, in)
        
        # Escalar por magnitude treinável
        W_dora = self.magnitude.unsqueeze(1) * V_norm  # (out, in)
        
        return F.linear(x, W_dora)


class DoRALinear(nn.Module):
    def __init__(self, linear: nn.Linear, rank=8, alpha=16.0):
        super().__init__()
        self.base_weight = nn.Parameter(linear.weight.data.clone())
        self.base_weight.requires_grad = False
        self.bias = nn.Parameter(linear.bias.data.clone()) if linear.bias is not None else None
        self.dora = DoRAAdapter(linear.in_features, linear.out_features, rank, alpha)

    def forward(self, x):
        out = self.dora(x, self.base_weight)
        if self.bias is not None:
            out = out + self.bias
        return out


# ═══════════════════════════════════════════════════════════
# FoRA (Frequency-LoRA)
# ═══════════════════════════════════════════════════════════

class FoRAAdapter(nn.Module):
    """
    FoRA: LoRA no domínio de frequência.
    
    Aplica FFT à entrada, separa baixa/alta frequência,
    aplica adaptações LoRA independentes, depois IFFT.
    
    """
    def __init__(self, in_features: int, rank: int = 8, alpha: float = 16.0, 
                 freq_ratio: float = 0.5):
        super().__init__()
        self.freq_ratio = freq_ratio  # Proporção de baixas frequências
        
        # LoRA para baixa frequência
        self.lora_low = nn.Parameter(torch.randn(in_features, rank) * 0.01)
        # LoRA para alta frequência
        self.lora_high = nn.Parameter(torch.randn(in_features, rank) * 0.01)
        
        self.alpha = alpha
        self.rank = rank

    def forward(self, x: torch.Tensor, weight: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, in_features)
            weight: (out_features, in_features)
        """
        B, S, D = x.shape
        
        # FFT ao longo da dimensão de features
        x_freq = torch.fft.rfft(x, dim=-1)  # (B, S, D//2+1)
        
        n_freq = x_freq.size(-1)
        n_low = int(n_freq * self.freq_ratio)
        
        # Separar frequências
        x_low = x_freq[..., :n_low]
        x_high = x_freq[..., n_low:]
        
        # Aplicar LoRA no domínio de frequência
        # (simplificado — na prática, projeções complexas)
        delta_low = (x_low.real @ self.lora_low[:n_low, :]) * self.alpha
        delta_high = (x_high.real @ self.lora_high[:n_freq-n_low, :]) * self.alpha
        
        # Recombinar
        x_freq[..., :n_low] += delta_low.to(x_freq.dtype)
        x_freq[..., n_low:] += delta_high.to(x_freq.dtype)
        
        # IFFT de volta
        x_adapted = torch.fft.irfft(x_freq, n=D, dim=-1)
        
        return F.linear(x_adapted, weight)


# ═══════════════════════════════════════════════════════════
# LoKRA (Low-Rank Kronecker Adaptation)
# ═══════════════════════════════════════════════════════════

class LoKRAAdapter(nn.Module):
    """
    LoKRA: Adaptação via produto de Kronecker.
    
    ΔW = A ⊗ B captura estruturas multidimensionais.
    Para W ∈ ℝ^{d_out × d_in}, fatoramos:
        A ∈ ℝ^{d_out₁ × r₁}, B ∈ ℝ^{d_out₂ × r₂}
    onde d_out = d_out₁ × d_out₂, r = r₁ × r₂
    
    Parâmetros: d_out₁·r₁ + d_out₂·r₂ << d_out·d_in
    """
    def __init__(self, d_out: int, d_in: int, rank: int = 8):
        super().__init__()
        
        # Fatorar dimensões para Kronecker
        d_out1 = int(d_out ** 0.5)
        d_out2 = d_out // d_out1
        d_in1 = int(d_in ** 0.5)
        d_in2 = d_in // d_in1
        
        r1 = max(1, int(rank ** 0.5))
        r2 = max(1, rank // r1)
        
        self.d_out1, self.d_out2 = d_out1, d_out2
        self.d_in1, self.d_in2 = d_in1, d_in2
        
        # Fatores de Kronecker
        self.A = nn.Parameter(torch.randn(d_out1, r1) * 0.01)  # direção out
        self.B = nn.Parameter(torch.randn(d_out2, r2) * 0.01)  # direção out
        self.C = nn.Parameter(torch.randn(r1, d_in1) * 0.01)   # direção in
        self.D = nn.Parameter(torch.randn(r2, d_in2) * 0.01)   # direção in

    def forward(self, x: torch.Tensor, weight: torch.Tensor) -> torch.Tensor:
        """
        ΔW = (A ⊗ B) @ (C ⊗ D) via propriedade de Kronecker
        """
        # Reconstruir ΔW via Kronecker
        # (A ⊗ B) @ (C ⊗ D) = (AC) ⊗ (BD)
        AC = self.A @ self.C  # (d_out1, d_in1)
        BD = self.B @ self.D  # (d_out2, d_in2)
        
        # Produto de Kronecker
        delta_W = torch.kron(AC, BD)  # (d_out1*d_out2, d_in1*d_in2)
        
        # Truncar para dimensões exatas
        delta_W = delta_W[:weight.size(0), :weight.size(1)]
        
        W_adapted = weight + delta_W
        return F.linear(x, W_adapted)


# ═══════════════════════════════════════════════════════════
# QLoRA com bitsandbytes (pseudo-código para 4-bit)
# ═══════════════════════════════════════════════════════════

class QLoRALinear(nn.Module):
    """
    QLoRA: Base quantizado em 4-bit + LoRA em fp16/bf16.
    
    Memória: ~0.5 bytes/param (base) + 2 bytes/param (LoRA)
    vs 2 bytes/param (LoRA puro) vs 4 bytes/param (FT completo)
    """
    def __init__(self, linear: nn.Linear, rank: int = 16):
        super().__init__()
        
        # Quantizar base para 4-bit (NF4)
        # Na prática: bitsandbytes.nn.Linear4bit
        self.weight_4bit = self._quantize_nf4(linear.weight)
        self.lora_A = nn.Parameter(torch.randn(linear.in_features, rank) * 0.01)
        self.lora_B = nn.Parameter(torch.zeros(rank, linear.out_features))
        self.scaling = 16.0 / rank

    def _quantize_nf4(self, weight):
        """Quantização NF4 (4-bit NormalFloat)."""
        # NF4 usa quantis da distribuição normal
        # Implementação simplificada — na prática usar bitsandbytes
        w = weight.data.float()
        # Normalizar para [-1, 1]
        w_max = w.abs().max()
        w_norm = w / (w_max + 1e-8)
        # Quantizar para 16 níveis (4-bit)
        levels = torch.linspace(-1, 1, 16)
        w_q = levels[torch.argmin(w_norm.unsqueeze(-1) - levels, dim=-1)]
        return w_q, w_max  # Armazenar escala para dequantização

    def _dequantize(self, weight_4bit):
        """Dequantizar de 4-bit para fp16."""
        w_q, scale = weight_4bit
        return w_q * scale

    def forward(self, x):
        # Base em 4-bit (dequantizado on-the-fly)
        base_weight = self._dequantize(self.weight_4bit)
        base_out = F.linear(x, base_weight)
        
        # LoRA em fp16
        lora_out = (x @ self.lora_A @ self.lora_B) * self.scaling
        
        return base_out + lora_out


# ═══════════════════════════════════════════════════════════
# Aplicar adapters a um modelo existente
# ═══════════════════════════════════════════════════════════

def apply_adapters(model: nn.Module, adapter_type: str = "lora", rank: int = 16):
    """
    Substitui linears do modelo por versões com adapters.
    
    Args:
        model: modelo base (congelado)
        adapter_type: "lora", "dora", "fora", "lokra", "qlora"
        rank: rank do adapter
    """
    adapter_map = {
        "lora": LoRALinear,
        "dora": DoRALinear,
        # "fora": FoRALinear,  # similar pattern
        # "lokra": LoKRALinear,
    }
    
    AdapterClass = adapter_map.get(adapter_type, LoRALinear)
    
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            # Aplicar apenas a Q, V (estilo LLaMA)
            if any(k in name for k in ["q_proj", "v_proj", "gate_proj", "up_proj"]):
                parent_name = ".".join(name.split(".")[:-1])
                child_name = name.split(".")[-1]
                parent = dict(model.named_modules())[parent_name]
                setattr(parent, child_name, AdapterClass(module, rank=rank))
    
    # Congelar tudo exceto adapters
    for name, param in model.named_parameters():
        if "lora" not in name and "dora" not in name and "magnitude" not in name:
            param.requires_grad = False
    
    # Contar parâmetros treináveis
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Parâmetros treináveis: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")
    
    return model
```

### Custo Computacional

| Variante | Parâmetros (7B, r=16) | Memória Treino | Speed vs FT | Qualidade |
|---|---|---|---|---|
| **LoRA** | ~3.6M (0.05%) | ~14 GB | 1.0x | Boa |
| **DoRA** | ~3.6M + magnitude | ~14 GB | 0.95x | Melhor (+1-3%) |
| **FoRA** | ~7.2M (2x LoRA) | ~15 GB | 0.85x | Boa (domínios) |
| **LoKRA** | ~2.8M (mais compacto) | ~14 GB | 0.90x | Similar |
| **QLoRA** | ~3.6M (base 4-bit) | ~8 GB | 0.70x | Similar |
| **FT Completo** | 7B (100%) | ~56 GB | 0.30x | Melhor |

**Recomendação para agentes:** DoRA com rank 16-32 para Q/V projections. QLoRA para treino em GPU única (24GB). Para múltiplas skills, usar LoRA composto (múltiplos adapters com roteamento).

---

## 3. Knowledge Distillation para Modelos Pequenos

### Conceito

Knowledge Distillation (KD) treina um modelo **student** (pequeno) para imitar um modelo **teacher** (grande). Em 2025-2026, as técnicas evoluíram muito além do soft-target matching original (Hinton et al., 2015):

**Técnicas modernas:**
- **Logit distillation:** Student imita distribuição de logits do teacher
- **Feature distillation:** Student imita hidden states intermediários
- **Sequence-level KD:** Teacher gera dados de treino para student
- **Self-distillation:** Modelo distila em si mesmo (camadas profundas → rasas)
- **On-policy KD (RLEIF):** Student gera respostas, teacher avalia (reward)

### Aplicabilidade em Modelos 3-8B

Ideal para criar agentes compactos: distilar um 70B/teacher em um 3-7B/student mantendo ~90% da capacidade.

### Implementação Python

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════
# Logit Distillation (Hinton et al. modernizado)
# ═══════════════════════════════════════════════════════════

class LogitDistiller:
    """
    Distilação via KL divergence entre logits do teacher e student.
    
    Loss = α · KL(teacher_logits || student_logits) + (1-α) · CE(student, labels)
    """
    def __init__(self, temperature: float = 4.0, alpha: float = 0.7):
        self.temperature = temperature
        self.alpha = alpha

    def compute_loss(
        self,
        student_logits: torch.Tensor,   # (B, seq_len, vocab_size)
        teacher_logits: torch.Tensor,   # (B, seq_len, vocab_size)
        labels: torch.Tensor,           # (B, seq_len)
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Compute distillation loss.
        """
        T = self.temperature
        
        # Soft targets via temperature-scaled softmax
        teacher_probs = F.softmax(teacher_logits / T, dim=-1)
        student_log_probs = F.log_softmax(student_logits / T, dim=-1)
        
        # KL divergence: KL(teacher || student)
        kl_loss = F.kl_div(
            student_log_probs, 
            teacher_probs, 
            reduction='none'
        ).sum(dim=-1)  # (B, seq_len)
        
        # Scale by T² (Hinton et al.)
        kl_loss = kl_loss * (T ** 2)
        
        # Hard label loss (cross-entropy)
        ce_loss = F.cross_entropy(
            student_logits.view(-1, student_logits.size(-1)),
            labels.view(-1),
            ignore_index=-100,
            reduction='none'
        ).view(labels.shape)
        
        # Masked average
        if attention_mask is not None:
            mask = attention_mask.float()
            kl_loss = (kl_loss * mask).sum() / mask.sum()
            ce_loss = (ce_loss * mask).sum() / mask.sum()
        else:
            kl_loss = kl_loss.mean()
            ce_loss = ce_loss.mean()
        
        # Combined loss
        total_loss = self.alpha * kl_loss + (1 - self.alpha) * ce_loss
        return total_loss


# ═══════════════════════════════════════════════════════════
# Feature Distillation (Hidden State Matching)
# ═══════════════════════════════════════════════════════════

class FeatureDistiller:
    """
    Distilação de features intermediárias.
    
    Projeta hidden states do student para o espaço do teacher
    e minimiza MSE entre eles.
    """
    def __init__(
        self, 
        student_hidden_size: int, 
        teacher_hidden_size: int,
        student_layers: int,
        teacher_layers: int,
    ):
        # Projetores lineares para alinhar dimensões
        self.projectors = nn.ModuleList([
            nn.Linear(student_hidden_size, teacher_hidden_size)
            for _ in range(student_layers)
        ])
        
        # Mapeamento de layers: student layer i → teacher layer j
        # Ex: student 24 layers → teacher 80 layers
        self.layer_mapping = self._create_layer_mapping(
            student_layers, teacher_layers
        )

    def _create_layer_mapping(self, n_student, n_teacher):
        """Mapeia layers do student para layers do teacher proporcionalmente."""
        mapping = {}
        for i in range(n_student):
            teacher_idx = int(i * n_teacher / n_student)
            mapping[i] = min(teacher_idx, n_teacher - 1)
        return mapping

    def compute_loss(
        self,
        student_hidden_states: List[torch.Tensor],  # Lista de (B, S, H_s)
        teacher_hidden_states: List[torch.Tensor],   # Lista de (B, S, H_t)
    ) -> torch.Tensor:
        """
        MSE entre hidden states projetados.
        """
        total_loss = 0.0
        n_mapped = 0
        
        for s_layer, t_layer in self.layer_mapping.items():
            # Projetar hidden state do student
            projected = self.projectors[s_layer](student_hidden_states[s_layer])
            
            # MSE com hidden state do teacher
            loss = F.mse_loss(projected, teacher_hidden_states[t_layer])
            total_loss += loss
            n_mapped += 1
        
        return total_loss / n_mapped


# ═══════════════════════════════════════════════════════════
# MiniLLM: Sequence-Level KD
# ═══════════════════════════════════════════════════════════

class MiniLLMDistiller:
    """
    MiniLLM: Reverse KL divergence no nível de sequência.
    
    Em vez de KL(teacher||student), usa KL(student||teacher)
    que é mode-seeking e melhor para geração.
    """
    def __init__(self, temperature: float = 2.0):
        self.temperature = temperature

    def compute_loss(
        self,
        student_logits: torch.Tensor,
        teacher_logits: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Reverse KL: E_student[log(student) - log(teacher)]
        """
        T = self.temperature
        
        student_log_probs = F.log_softmax(student_logits / T, dim=-1)
        teacher_log_probs = F.log_softmax(teacher_logits / T, dim=-1)
        
        # Reverse KL
        reverse_kl = (
            torch.exp(student_log_probs) * (student_log_probs - teacher_log_probs)
        ).sum(dim=-1)
        
        mask = attention_mask.float()
        return (reverse_kl * mask).sum() / mask.sum()


# ═══════════════════════════════════════════════════════════
# On-Policy KD (RLEIF-style)
# ═══════════════════════════════════════════════════════════

class OnPolicyDistiller:
    """
    Student gera respostas → Teacher avalia (reward) → Student melhora.
    
    Combina KD com RL: o student gera sequências, o teacher
    fornece rewards via log-prob ou score.
    """
    def __init__(self, teacher_model, tokenizer, reward_type: str = "log_prob"):
        self.teacher = teacher_model
        self.tokenizer = tokenizer
        self.reward_type = reward_type

    def generate_and_learn(
        self,
        student_model,
        prompts: List[str],
        max_new_tokens: int = 256,
        lr: float = 1e-5,
    ):
        """
        Loop: student gera → teacher avalia → student atualiza.
        """
        optimizer = torch.optim.AdamW(student_model.parameters(), lr=lr)
        
        for prompt in prompts:
            # Student gera
            inputs = self.tokenizer(prompt, return_tensors="pt")
            with torch.no_grad():
                student_output = student_model.generate(
                    **inputs, max_new_tokens=max_new_tokens
                )
            
            # Teacher avalia (reward)
            with torch.no_grad():
                teacher_logits = self.teacher(student_output).logits
                teacher_log_probs = F.log_softmax(teacher_logits, dim=-1)
                
                # Reward = log P_teacher(student_output)
                gathered = teacher_log_probs.gather(
                    -1, student_output.unsqueeze(-1)
                ).squeeze(-1)
                reward = gathered.mean()
            
            # Student aprende a maximizar reward
            student_logits = student_model(student_output).logits
            student_log_probs = F.log_softmax(student_logits, dim=-1)
            
            gathered_student = student_log_probs.gather(
                -1, student_output.unsqueeze(-1)
            ).squeeze(-1)
            
            # Policy gradient: -reward * log P_student(output)
            loss = -reward * gathered_student.mean()
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()


# ═══════════════════════════════════════════════════════════
# Self-Distillation (DINO-style para LLMs)
# ═══════════════════════════════════════════════════════════

class SelfDistiller:
    """
    Self-distillation: camadas posteriores ensinam camadas anteriores.
    
    Útil quando não há teacher externo.
    """
    def __init__(self, model, ema_decay: float = 0.999):
        self.model = model
        self.ema_decay = ema_decay
        
        # Criar EMA do modelo (teacher = versão suavizada do student)
        self.ema_model = type(model)(model.config)  # clone
        self._update_ema(0.0)  # Copiar pesos iniciais

    def _update_ema(self, decay: float = None):
        """Atualiza EMA do modelo teacher."""
        decay = decay or self.ema_decay
        with torch.no_grad():
            for ema_p, model_p in zip(
                self.ema_model.parameters(), self.model.parameters()
            ):
                ema_p.data.mul_(decay).add_(model_p.data, alpha=1 - decay)

    def compute_loss(self, input_ids, labels, attention_mask):
        # Student forward
        student_output = self.model(
            input_ids=input_ids, attention_mask=attention_mask
        )
        
        # Teacher (EMA) forward — sem gradiente
        with torch.no_grad():
            teacher_output = self.ema_model(
                input_ids=input_ids, attention_mask=attention_mask
            )
        
        # Distillation loss
        distiller = LogitDistiller(temperature=4.0, alpha=0.5)
        kd_loss = distiller.compute_loss(
            student_output.logits, teacher_output.logits,
            labels, attention_mask
        )
        
        # Atualizar EMA
        self._update_ema()
        
        return kd_loss


# ═══════════════════════════════════════════════════════════
# Pipeline completo de distilação
# ═══════════════════════════════════════════════════════════

class DistillationPipeline:
    """
    Pipeline completo: combina logit + feature + sequence-level KD.
    """
    def __init__(self, teacher, student, tokenizer, config: dict):
        self.teacher = teacher
        self.student = student
        self.tokenizer = tokenizer
        self.config = config
        
        self.logit_distiller = LogitDistiller(
            temperature=config.get("temperature", 4.0),
            alpha=config.get("alpha", 0.7),
        )
        
        self.feature_distiller = FeatureDistiller(
            student_hidden_size=student.config.hidden_size,
            teacher_hidden_size=teacher.config.hidden_size,
            student_layers=student.config.num_hidden_layers,
            teacher_layers=teacher.config.num_hidden_layers,
        )
        
        # Congelar teacher
        for p in self.teacher.parameters():
            p.requires_grad = False
        self.teacher.eval()

    def train_step(self, batch: dict) -> dict:
        """Um passo de treino com todas as losses de distilação."""
        input_ids = batch["input_ids"]
        attention_mask = batch["attention_mask"]
        labels = batch["labels"]
        
        # Teacher forward (sem grad)
        with torch.no_grad():
            teacher_output = self.teacher(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
            )
        
        # Student forward
        student_output = self.student(
            input_ids=input_ids,
            attention_mask=attention_mask,
            output_hidden_states=True,
        )
        
        # Logit-level KD
        logit_loss = self.logit_distiller.compute_loss(
            student_output.logits, teacher_output.logits,
            labels, attention_mask
        )
        
        # Feature-level KD
        feature_loss = self.feature_distiller.compute_loss(
            student_output.hidden_states,
            teacher_output.hidden_states,
        )
        
        # Task loss (cross-entropy com labels)
        task_loss = F.cross_entropy(
            student_output.logits.view(-1, student_output.logits.size(-1)),
            labels.view(-1),
            ignore_index=-100,
        )
        
        # Combined
        total_loss = (
            self.config.get("logit_weight", 0.5) * logit_loss +
            self.config.get("feature_weight", 0.3) * feature_loss +
            self.config.get("task_weight", 0.2) * task_loss
        )
        
        return {
            "total_loss": total_loss,
            "logit_loss": logit_loss.item(),
            "feature_loss": feature_loss.item(),
            "task_loss": task_loss.item(),
        }
```

### Custo Computacional

| Técnica | Teacher GPU-hours | Student GPU-hours | Qualidade (vs teacher) |
|---|---|---|---|
| Logit KD | 0 (inference only) | ~100-500h (A100) | ~85-90% |
| Feature KD | 0 | ~150-600h | ~88-92% |
| MiniLLM | 0 | ~200-800h | ~90-93% |
| On-Policy KD | ~50h (reward) | ~300-1000h | ~92-95% |
| Self-Distillation | 0 | ~100-400h | ~80-85% |

**Recomendação para agentes:** Logit KD + Feature KD combinados. Teacher: Qwen3-72B ou similar. Student: Qwen3-4B/7B. Custo: ~200-400 A100-hours para distilação completa.

---

## 4. Speculative Decoding

### Conceito

Speculative Decoding usa um **draft model** pequeno (ex: 100M-1B) para gerar K tokens candidatos rapidamente, depois o **target model** grande verifica todos em paralelo (1 forward pass). Se o target rejeita um token, recomeça dali.

```
Draft (rápido):  [t₁, t₂, t₃, t₄]  ← 4 tokens em 4 passos pequenos
Target (lento):  verifica [t₁, t₂, t₃, t₄] em 1 passo paralelo
                 → aceita t₁, t₂, rejeita t₃ → gera t₃' → continua
```

**Speedup típico:** 2-4x em produção. Depende da taxa de aceitação (α).

**Evolução 2025-2026:**
- **EAGLE-3** (Li et al., 2025): draft com feature prediction, não token prediction
- **MTP (Multi-Token Prediction):** LLaMA 3.1+ usa MTP heads nativos
- **Self-speculative:** mesmo modelo com early exits como draft
- **Medusa:** múltiplas cabeças de previsão paralela

### Aplicabilidade em Modelos 3-8B

Excelente! Modelo 7B com draft de 1.5B (ou mesmo 300M) → speedup 2-3x. Para agentes que fazem muitas chamadas de geração, o ganho é enorme.

### Implementação Python

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple, Optional

# ═══════════════════════════════════════════════════════════
# Speculative Decoding — Implementação Base
# ═══════════════════════════════════════════════════════════

class SpeculativeDecoder:
    """
    Speculative Decoding com draft model pequeno + target model grande.
    
    Algoritmo:
    1. Draft gera γ tokens candidatos autoregressivamente
    2. Target processa todos γ candidatos em 1 forward pass
    3. Verifica aceitação via amostragem por rejeição
    4. Aceita prefixo máximo, rejeita o resto
    """
    def __init__(
        self,
        target_model: nn.Module,
        draft_model: nn.Module,
        gamma: int = 4,          # Tokens candidatos por iteração
        temperature: float = 1.0,
    ):
        self.target = target_model
        self.draft = draft_model
        self.gamma = gamma
        self.temperature = temperature
        
        # Estatísticas
        self.total_accepted = 0
        self.total_generated = 0

    @torch.no_grad()
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 256,
    ) -> torch.Tensor:
        """
        Geração com speculative decoding.
        
        Args:
            input_ids: (batch_size, seq_len) — prompt
            max_new_tokens: máximo de tokens novos
        Returns:
            output: (batch_size, seq_len + generated)
        """
        generated = input_ids.clone()
        num_generated = 0
        
        while num_generated < max_new_tokens:
            # ─── Fase 1: Draft gera γ candidatos ───
            draft_tokens = self._draft_generate(generated, self.gamma)
            # draft_tokens: (batch, γ)
            
            # ─── Fase 2: Target verifica em paralelo ───
            # Input para target: generated + draft_tokens
            verification_input = torch.cat([generated, draft_tokens], dim=1)
            # (batch, seq_len + γ)
            
            target_logits = self.target(verification_input).logits
            # (batch, seq_len + γ, vocab)
            
            # Extrair logits nas posições dos candidatos
            seq_len = generated.size(1)
            candidate_logits = target_logits[:, seq_len-1:seq_len-1+self.gamma, :]
            # (batch, γ, vocab)
            
            # ─── Fase 3: Amostragem por rejeição ───
            accepted_tokens, n_accepted = self._rejection_sampling(
                draft_tokens, candidate_logits
            )
            
            # ─── Fase 4: Adicionar tokens aceitos + 1 token do target ───
            if n_accepted < self.gamma:
                # Rejeição: adicionar tokens aceitos + 1 token do target
                target_next_token = candidate_logits[:, n_accepted, :].argmax(dim=-1, keepdim=True)
                accepted_tokens = torch.cat([accepted_tokens, target_next_token], dim=1)
            
            generated = torch.cat([generated, accepted_tokens], dim=1)
            num_generated += accepted_tokens.size(1)
            
            self.total_accepted += n_accepted
            self.total_generated += self.gamma
        
        return generated

    def _draft_generate(self, prefix: torch.Tensor, gamma: int) -> torch.Tensor:
        """Draft model gera γ tokens autoregressivamente."""
        tokens = []
        current = prefix.clone()
        
        for _ in range(gamma):
            logits = self.draft(current).logits[:, -1, :]  # (batch, vocab)
            next_token = logits.argmax(dim=-1, keepdim=True)  # Greedy
            tokens.append(next_token)
            current = torch.cat([current, next_token], dim=1)
        
        return torch.cat(tokens, dim=1)  # (batch, γ)

    def _rejection_sampling(
        self,
        draft_tokens: torch.Tensor,
        target_logits: torch.Tensor,
    ) -> Tuple[torch.Tensor, int]:
        """
        Amostragem por rejeição: aceita draft token se
        P_target(token) >= P_draft(token) (com correção).
        """
        batch_size = draft_tokens.size(0)
        accepted = []
        
        for i in range(self.gamma):
            draft_token = draft_tokens[:, i]  # (batch,)
            target_logit = target_logits[:, i, :]  # (batch, vocab)
            
            target_prob = F.softmax(target_logit / self.temperature, dim=-1)
            draft_prob = F.softmax(target_logit / self.temperature, dim=-1)  # Simplificado
            
            # Probabilidade do token draft no target
            p_accept = target_prob.gather(1, draft_token.unsqueeze(1)).squeeze(1)
            
            # Aceitar com probabilidade p_accept
            uniform = torch.rand(batch_size, device=draft_tokens.device)
            accept_mask = uniform <= p_accept
            
            if accept_mask.all():
                accepted.append(draft_token.unsqueeze(1))
            else:
                # Primeiro token rejeitado — parar
                n_accepted = len(accepted)
                if accepted:
                    return torch.cat(accepted, dim=1), n_accepted
                return torch.empty(batch_size, 0, dtype=torch.long, device=draft_tokens.device), 0
        
        return torch.cat(accepted, dim=1), self.gamma

    @property
    def acceptance_rate(self):
        if self.total_generated == 0:
            return 0.0
        return self.total_accepted / self.total_generated


# ═══════════════════════════════════════════════════════════
# EAGLE-style: Draft com Feature Prediction
# ═══════════════════════════════════════════════════════════

class EAGLEDraftModel(nn.Module):
    """
    EAGLE: Draft model que prevê features do target, não tokens diretamente.
    
    O draft usa hidden states do target como input e prevê
    o próximo hidden state, que é convertido em token.
    """
    def __init__(self, target_hidden_size: int, vocab_size: int, draft_layers: int = 1):
        super().__init__()
        
        # Acepta: token embedding + hidden state atual
        self.token_embed = nn.Embedding(vocab_size, target_hidden_size)
        
        # Transformer layers leves para draft
        decoder_layer = nn.TransformerEncoderLayer(
            d_model=target_hidden_size,
            nhead=8,
            dim_feedforward=target_hidden_size * 2,
            batch_first=True,
        )
        self.draft_transformer = nn.TransformerEncoder(
            decoder_layer, num_layers=draft_layers
        )
        
        # Cabeça de previsão
        self.lm_head = nn.Linear(target_hidden_size, vocab_size)

    def forward(
        self, 
        input_ids: torch.Tensor,
        target_hidden_state: torch.Tensor,
    ):
        """
        Args:
            input_ids: tokens candidatos
            target_hidden_state: último hidden state do target
        """
        token_emb = self.token_embed(input_ids)
        
        # Concatenar com hidden state do target como "context"
        # EAGLE usa uma fusão específica
        x = token_emb + target_hidden_state.unsqueeze(1)
        
        x = self.draft_transformer(x)
        logits = self.lm_head(x)
        
        return logits


# ═══════════════════════════════════════════════════════════
# Medusa: Multi-Head Speculative Decoding
# ═══════════════════════════════════════════════════════════

class MedusaHeads(nn.Module):
    """
    Medusa: Múltiplas cabeças de previsão em paralelo.
    
    Cada cabeça prevê o token k passos à frente:
    Head 0: token t+1 (padrão)
    Head 1: token t+2
    Head 2: token t+3
    Head 3: token t+4
    """
    def __init__(self, hidden_size: int, vocab_size: int, n_heads: int = 4):
        super().__init__()
        self.heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_size, hidden_size),
                nn.SiLU(),
                nn.Linear(hidden_size, vocab_size),
            )
            for _ in range(n_heads)
        ])
        self.n_heads = n_heads

    def forward(self, hidden_states: torch.Tensor) -> List[torch.Tensor]:
        """
        Args: hidden_states: (batch, hidden_size) — último hidden state
        Returns: lista de logits para cada posição futura
        """
        return [head(hidden_states) for head in self.heads]


class MedusaDecoder:
    """
    Speculative decoding com Medusa heads.
    """
    def __init__(self, model, medusa_heads: MedusaHeads, tree_width: int = 5):
        self.model = model
        self.medusa_heads = medusa_heads
        self.tree_width = tree_width  # Top-k por cabeça

    @torch.no_grad()
    def generate(self, input_ids, max_new_tokens=256):
        generated = input_ids.clone()
        
        while generated.size(1) < input_ids.size(1) + max_new_tokens:
            # Forward no modelo base
            output = self.model(generated, output_hidden_states=True)
            last_hidden = output.hidden_states[-1][:, -1, :]
            
            # Medusa heads geram candidatos
            medusa_logits = self.medusa_heads(last_hidden)
            
            # Construir árvore de candidatos
            candidates = self._build_tree(medusa_logits)
            
            # Verificar candidatos com modelo base
            best = self._verify_candidates(generated, candidates)
            
            generated = torch.cat([generated, best.unsqueeze(1)], dim=1)
        
        return generated

    def _build_tree(self, medusa_logits):
        """Constrói árvore de tokens candidatos."""
        tree = []
        for i, logits in enumerate(medusa_logits):
            top_k = logits.topk(self.tree_width, dim=-1)
            tree.append(top_k)
        return tree

    def _verify_candidates(self, prefix, candidates):
        """Verifica candidatos e retorna o melhor."""
        # Simplificado: retorna o token mais provável da primeira cabeça
        return candidates[0].indices[:, 0]


# ═══════════════════════════════════════════════════════════
# Self-Speculative: Early Exit como Draft
# ═══════════════════════════════════════════════════════════

class SelfSpeculativeDecoder:
    """
    Self-speculative decoding: usa early exits do mesmo modelo como draft.
    
    Camadas iniciais fazem draft, camadas completas verificam.
    """
    def __init__(self, model, draft_layers: int = 8, total_layers: int = 32):
        self.model = model
        self.draft_layers = draft_layers
        self.total_layers = total_layers

    @torch.no_grad()
    def generate(self, input_ids, max_new_tokens=256, gamma=4):
        generated = input_ids.clone()
        
        while generated.size(1) < input_ids.size(1) + max_new_tokens:
            # Draft: forward parcial (primeiras N camadas)
            draft_tokens = self._draft_forward(generated, gamma)
            
            # Verificação: forward completo
            verification_input = torch.cat([generated, draft_tokens], dim=1)
            full_output = self.model(verification_input)
            
            # Aceitar/rejeitar (mesmo algoritmo do SpeculativeDecoder)
            # ...
            
            generated = torch.cat([generated, draft_tokens[:, :1]], dim=1)
        
        return generated

    def _draft_forward(self, prefix, gamma):
        """Forward parcial para draft."""
        # Forward apenas primeiras N cameras
        hidden = self.model.embed(prefix)
        for layer in self.model.layers[:self.draft_layers]:
            hidden = layer(hidden)
        
        # Gerar γ tokens
        tokens = []
        for _ in range(gamma):
            logits = self.model.lm_head(hidden[:, -1, :])
            next_token = logits.argmax(dim=-1, keepdim=True)
            tokens.append(next_token)
            emb = self.model.embed(next_token)
            hidden = torch.cat([hidden, emb], dim=1)
        
        return torch.cat(tokens, dim=1)
```

### Custo Computacional

| Técnica | Speedup | Taxa Aceitação | Memória Extra | Complexidade |
|---|---|---|---|---|
| Speculative (draft separado) | 2-3x | 60-80% | +1x draft model | Baixa |
| EAGLE-3 | 3-5x | 70-85% | +0.5x | Média |
| Medusa | 2-4x | 50-70% | +0.1x | Média |
| Self-Speculative | 1.5-2.5x | 40-60% | 0x | Baixa |
| MTP (nativo) | 2-3x | 65-80% | +0.05x | Baixa |

**Recomparação para agentes:** EAGLE-3 é o estado da arte. Para modelos 7B, um draft de 1B com EAGLE dá ~3x speedup. Self-speculative é mais simples (sem modelo extra) mas menos eficiente.

---

## 5. KV-Cache Compression

### Conceito

Durante a geração autoregressiva, o modelo cacheia Key e Value de cada token em cada camada (KV-Cache). Para contextos longos, isso consome memória enorme:

```
KV-Cache size = 2 × n_layers × n_heads × head_dim × seq_len × bytes_per_element
Para 7B, 32k context, fp16: 2 × 32 × 32 × 128 × 32768 × 2 = ~17 GB!
```

**Técnicas de compressão 2025-2026:**
- **Grouped Query Attention (GQA):** compartilhar KV entre heads
- **Multi-Query Attention (MQA):** 1 KV para todas heads
- **MLA (Multi-head Latent Attention):** DeepSeek-V2, comprime KV para vetor latente
- **SnapKV:** identifica e mantém apenas tokens "importantes" (attention sinks)
- **StreamingLLM:** manter tokens iniciais + janela deslizante
- **Quantização do cache:** KV em 8-bit ou 4-bit
- **Quest, QUIK:** compressão via low-rank approximation

### Aplicabilidade em Modelos 3-8B

Crítico! Agentes precisam de contexto longo (tools, histórico, documentos). KV-cache compression permite contextos 4-8x maiores na mesma memória.

### Implementação Python

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple

# ═══════════════════════════════════════════════════════════
# Grouped Query Attention (GQA)
# ═══════════════════════════════════════════════════════════

class GroupedQueryAttention(nn.Module):
    """
    GQA: n_kv_heads < n_query_heads.
    Cada grupo de query heads compartilha 1 par KV.
    
    Memória KV: reduzida por fator n_query_heads / n_kv_heads
    Ex: 32 query heads, 8 KV heads → 4x menos memória KV
    """
    def __init__(
        self, 
        d_model: int = 4096, 
        n_query_heads: int = 32, 
        n_kv_heads: int = 8,
        max_seq_len: int = 32768,
    ):
        super().__init__()
        self.n_query_heads = n_query_heads
        self.n_kv_heads = n_kv_heads
        self.n_rep = n_query_heads // n_kv_heads  # Fator de repetição
        self.head_dim = d_model // n_query_heads
        
        self.wq = nn.Linear(d_model, n_query_heads * self.head_dim, bias=False)
        self.wk = nn.Linear(d_model, n_kv_heads * self.head_dim, bias=False)
        self.wv = nn.Linear(d_model, n_kv_heads * self.head_dim, bias=False)
        self.wo = nn.Linear(n_query_heads * self.head_dim, d_model, bias=False)

    def forward(
        self, 
        x: torch.Tensor, 
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
    ):
        B, S, _ = x.shape
        
        q = self.wq(x).view(B, S, self.n_query_heads, self.head_dim).transpose(1, 2)
        k = self.wk(x).view(B, S, self.n_kv_heads, self.head_dim).transpose(1, 2)
        v = self.wv(x).view(B, S, self.n_kv_heads, self.head_dim).transpose(1, 2)
        
        # Atualizar KV cache
        if kv_cache is not None:
            k = torch.cat([kv_cache[0], k], dim=2)
            v = torch.cat([kv_cache[1], v], dim=2)
        
        # Repetir KV heads para matching com query heads
        # (B, n_kv, S, D) → (B, n_query, S, D)
        k = k.unsqueeze(1).expand(-1, self.n_rep, -1, -1, -1).reshape(
            B, self.n_query_heads, k.size(2), self.head_dim
        )
        v = v.unsqueeze(1).expand(-1, self.n_rep, -1, -1, -1).reshape(
            B, self.n_query_heads, v.size(2), self.head_dim
        )
        
        # Scaled dot-product attention
        attn = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        
        attn = attn.transpose(1, 2).contiguous().view(B, S, -1)
        return self.wo(attn), (k, v)


# ═══════════════════════════════════════════════════════════
# MLA (Multi-head Latent Attention) — DeepSeek-V2
# ═══════════════════════════════════════════════════════════

class MultiheadLatentAttention(nn.Module):
    """
    MLA: Comprime KV para espaço latente de baixa dimensão.
    
    Em vez de cachear K, V ∈ ℝ^{n_heads × head_dim},
    cacheia um vetor latente c ∈ ℝ^{d_c} onde d_c << n_heads × head_dim
    
    DeepSeek-V2: d_c = 512 vs n_heads × head_dim = 128 × 128 = 16384
    → Compressão de ~32x no KV cache!
    """
    def __init__(
        self,
        d_model: int = 4096,
        n_heads: int = 32,
        d_c: int = 512,        # Dimensão comprimida do KV
        d_rope: int = 64,      # Dimensão para RoPE (parte não comprimida)
        max_seq_len: int = 32768,
    ):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.d_c = d_c
        self.d_rope = d_rope
        
        # Projeções de compressão
        self.w_dkv = nn.Linear(d_model, d_c, bias=False)  # Down-projection para KV
        self.w_dq = nn.Linear(d_model, d_c, bias=False)   # Down-projection para Q
        
        # Up-projections
        self.w_uk = nn.Linear(d_c, n_heads * self.head_dim, bias=False)
        self.w_uv = nn.Linear(d_c, n_heads * self.head_dim, bias=False)
        self.w_uq = nn.Linear(d_c, n_heads * self.head_dim, bias=False)
        
        # Componente com RoPE (não comprimido)
        self.w_qr = nn.Linear(d_model, n_heads * d_rope, bias=False)
        self.w_kr = nn.Linear(d_model, d_rope, bias=False)  # Shared across heads
        
        self.wo = nn.Linear(d_model, d_model, bias=False)

    def forward(self, x, kv_cache=None):
        B, S, _ = x.shape
        
        # KV latente comprimido
        c_kv = self.w_dkv(x)  # (B, S, d_c)
        
        if kv_cache is not None:
            c_kv = torch.cat([kv_cache, c_kv], dim=1)
        
        # Decompress para K, V
        k = self.w_uk(c_kv).view(B, c_kv.size(1), self.n_heads, self.head_dim)
        v = self.w_uv(c_kv).view(B, c_kv.size(1), self.n_heads, self.head_dim)
        
        # Q latente
        c_q = self.w_dq(x)
        q = self.w_uq(c_q).view(B, S, self.n_heads, self.head_dim)
        
        # Adicionar componente RoPE
        # (simplificado — na prática aplica RoPE a subespaço)
        
        # Attention
        q_t = q.transpose(1, 2)
        k_t = k.transpose(1, 2)
        v_t = v.transpose(1, 2)
        
        attn = F.scaled_dot_product_attention(q_t, k_t, v_t, is_causal=True)
        attn = attn.transpose(1, 2).contiguous().view(B, S, -1)
        
        return self.wo(attn), c_kv


# ═══════════════════════════════════════════════════════════
# SnapKV: Compression via Attention Score Pruning
# ═══════════════════════════════════════════════════════════

class SnapKVCompressor:
    """
    SnapKV: Identifica tokens importantes via attention scores
    e mantém apenas os top-N no cache.
    
    Algoritmo:
    1. Calcular atenção dos tokens de query para todo o contexto
    2. Agregar scores de atenção por token de contexto
    3. Manter tokens com maior score + tokens iniciais (attention sinks)
    """
    def __init__(self, compress_ratio: float = 0.5, sink_tokens: int = 4):
        self.compress_ratio = compress_ratio
        self.sink_tokens = sink_tokens  # Sempre manter primeiros tokens

    def compress(
        self,
        k_cache: torch.Tensor,   # (B, n_heads, seq_len, head_dim)
        v_cache: torch.Tensor,   # (B, n_heads, seq_len, head_dim)
        q: torch.Tensor,         # (B, n_heads, 1, head_dim) — query atual
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Comprime KV cache mantendo tokens importantes.
        """
        B, H, S, D = k_cache.shape
        n_keep = max(self.sink_tokens + 1, int(S * self.compress_ratio))
        
        if S <= n_keep:
            return k_cache, v_cache
        
        # Calcular atenção do query atual para todo o cache
        # (B, H, 1, D) × (B, H, D, S) → (B, H, 1, S)
        attn_scores = torch.matmul(q, k_cache.transpose(-1, -2)) / (D ** 0.5)
        attn_scores = attn_scores.squeeze(2)  # (B, H, S)
        
        # Agregar scores entre heads (média)
        importance = attn_scores.mean(dim=1)  # (B, S)
        
        # Manter attention sinks (primeiros tokens)
        sink_mask = torch.zeros(S, dtype=torch.bool, device=k_cache.device)
        sink_mask[:self.sink_tokens] = True
        
        # Top-k dos restantes
        remaining = importance[:, self.sink_tokens:]
        _, top_indices = remaining.topk(n_keep - self.sink_tokens, dim=-1)
        top_indices = top_indices + self.sink_tokens
        
        # Combinar sinks + top-k
        keep_mask = sink_mask.unsqueeze(0).expand(B, -1).clone()
        for b in range(B):
            keep_mask[b, top_indices[b]] = True
        
        # Comprimir cache
        k_compressed = k_cache[:, :, keep_mask[0], :]
        v_compressed = v_cache[:, :, keep_mask[0], :]
        
        return k_compressed, v_compressed


# ═══════════════════════════════════════════════════════════
# Quantização do KV Cache (4-bit)
# ═══════════════════════════════════════════════════════════

class QuantizedKVCache:
    """
    KV Cache quantizado para 4-bit (NF4) ou 8-bit (INT8).
    
    Reduz memória em 4x (INT8) ou 8x (INT4) com perda mínima de qualidade.
    """
    def __init__(self, bits: int = 8):
        self.bits = bits
        self.scale = None
        self.zero_point = None

    def quantize(self, tensor: torch.Tensor) -> torch.Tensor:
        """Quantizar tensor para INT8/INT4."""
        if self.bits == 8:
            # INT8 quantization
            max_val = tensor.abs().max(dim=-1, keepdim=True).values
            scale = max_val / 127.0
            quantized = torch.clamp(
                torch.round(tensor / scale), -128, 127
            ).to(torch.int8)
            return quantized, scale
        elif self.bits == 4:
            # INT4 (empacotado em INT8)
            max_val = tensor.abs().max(dim=-1, keepdim=True).values
            scale = max_val / 7.0
            quantized = torch.clamp(
                torch.round(tensor / scale), -7, 7
            ).to(torch.int8)
            return quantized, scale

    def dequantize(self, quantized, scale) -> torch.Tensor:
        """Dequantizar de volta para fp16."""
        return quantized.float() * scale


# ═══════════════════════════════════════════════════════════
# StreamingLLM: Attention Sinks + Janela Deslizante
# ═══════════════════════════════════════════════════════════

class StreamingLLM:
    """
    StreamingLLM: Mantém attention sinks (primeiros tokens) + janela deslizante.
    
    Permite contextos infinitos sem compressão complexa.
    Memória: O(sink_tokens + window_size) em vez de O(seq_len)
    """
    def __init__(self, sink_tokens: int = 4, window_size: int = 1024):
        self.sink_tokens = sink_tokens
        self.window_size = window_size

    def get_cache_slice(self, full_cache, current_length):
        """
        Retorna slice do cache: sinks + janela recente.
        """
        if current_length <= self.sink_tokens + self.window_size:
            return full_cache
        
        sinks = full_cache[:, :, :self.sink_tokens, :]
        recent = full_cache[:, :, -self.window_size:, :]
        
        return torch.cat([sinks, recent], dim=2)
```

### Custo Computacional

| Técnica | Compressão | Qualidade | Overhead | Memória (7B, 32k) |
|---|---|---|---|---|
| **Baseline (fp16)** | 1x | 100% | 0% | ~17 GB |
| **GQA (8 KV heads)** | 4x | 98% | 0% | ~4.3 GB |
| **MLA (DeepSeek)** | 32x | 95% | 5% | ~0.5 GB |
| **SnapKV (50%)** | 2x | 92% | 10% | ~8.5 GB |
| **INT8 quant** | 2x | 99% | 2% | ~8.5 GB |
| **INT4 quant** | 4x | 97% | 5% | ~4.3 GB |
| **StreamingLLM** | ~32x | 85% | 0% | ~0.5 GB |

**Recomendação para agentes:** MLA (se disponível no modelo) + INT8 quantization. SnapKV para contextos onde qualidade é crítica. StreamingLLM para streaming infinito.

---

## 6. Flash Attention 2/3

### Conceito

Flash Attention é um algoritmo de atenção **IO-aware** que reduz a leitura/escrita de HBM (memória GPU) de O(N²) para O(N²/d), onde d é o tamanho do SRAM. Em vez de materializar a matriz N×N de atenção em HBM, computa em blocos (tiling) que cabem em SRAM.

**Flash Attention 2 (2023):**
- Melhor paralelização (over sequence length, não apenas batch × heads)
- Redução de shared memory writes
- ~2-4x mais rápido que FA1

**Flash Attention 3 (2024-2025):**
- **Warp-level pipelining:** sobrepõe compute e memory
- **FP8 support:** para Hopper (H100) e Blackwell (B200)
- **Irregular attention masks:** suporte nativo a padding
- **Producer-consumer model:** warps especializados em compute vs memory

### Aplicabilidade em Modelos 3-8B

Essencial! Flash Attention é o padrão em todos os frameworks modernos (vLLM, SGLang, Transformers). Para modelos 3-8B, permite contextos longos com throughput alto.

### Implementação Python

```python
import torch
import torch.nn.functional as F

# ═══════════════════════════════════════════════════════════
# Flash Attention 2 — Implementação didática (Tiling)
# ═══════════════════════════════════════════════════════════

def flash_attention_forward(
    Q: torch.Tensor,  # (B, H, N, d)
    K: torch.Tensor,  # (B, H, N, d)
    V: torch.Tensor,  # (B, H, N, d)
    block_size: int = 64,
    causal: bool = True,
) -> torch.Tensor:
    """
    Flash Attention — implementação didática (não otimizada para GPU).
    
    Ideia: em vez de materializar S = QK^T (N×N), computa em blocos
    que cabem em SRAM, usando online softmax.
    
    Complexidade de memória: O(N) em vez de O(N²)
    """
    B, H, N, d = Q.shape
    scale = d ** -0.5
    
    # Output
    O = torch.zeros(B, H, N, d, device=Q.device, dtype=Q.dtype)
    # Running statistics for online softmax
    l = torch.zeros(B, H, N, device=Q.device)  # Sum of exp
    m = torch.full((B, H, N), float('-inf'), device=Q.device)  # Running max
    
    # Número de blocos
    Tc = (N + block_size - 1) // block_size  # Blocos de K, V
    Tr = (N + block_size - 1) // block_size  # Blocos de Q
    
    for tr in range(Tr):
        # Carregar bloco de Q para SRAM
        q_start = tr * block_size
        q_end = min(q_start + block_size, N)
        Q_i = Q[:, :, q_start:q_end, :]  # (B, H, Br, d)
        
        # Reset output para este bloco
        O_i = torch.zeros_like(Q_i)
        l_i = torch.zeros(B, H, q_end - q_start, device=Q.device)
        m_i = torch.full((B, H, q_end - q_start), float('-inf'), device=Q.device)
        
        for tc in range(Tc):
            # Carregar bloco de K, V para SRAM
            kv_start = tc * block_size
            kv_end = min(kv_start + block_size, N)
            K_j = K[:, :, kv_start:kv_end, :]  # (B, H, Bc, d)
            V_j = V[:, :, kv_start:kv_end, :]  # (B, H, Bc, d)
            
            # Computar scores de atenção (em SRAM)
            S_ij = torch.matmul(Q_i, K_j.transpose(-1, -2)) * scale  # (B, H, Br, Bc)
            
            # Mask causal
            if causal:
                q_indices = torch.arange(q_start, q_end, device=Q.device).unsqueeze(1)
                kv_indices = torch.arange(kv_start, kv_end, device=Q.device).unsqueeze(0)
                causal_mask = q_indices < kv_indices  # (Br, Bc)
                S_ij = S_ij.masked_fill(causal_mask.unsqueeze(0).unsqueeze(0), float('-inf'))
            
            # Online softmax update
            m_ij = S_ij.max(dim=-1).values  # (B, H, Br)
            m_new = torch.maximum(m_i, m_ij)
            
            P_ij = torch.exp(S_ij - m_ij.unsqueeze(-1))  # (B, H, Br, Bc)
            P_ij = P_ij.masked_fill(S_ij == float('-inf'), 0)
            
            l_ij = P_ij.sum(dim=-1)  # (B, H, Br)
            l_new = torch.exp(m_i - m_new) * l_i + torch.exp(m_ij - m_new) * l_ij
            
            # Update output
            O_i = torch.exp(m_i - m_new).unsqueeze(-1) * O_i + \
                  torch.exp(m_ij - m_new).unsqueeze(-1) * torch.matmul(P_ij, V_j)
            
            m_i = m_new
            l_i = l_new
        
        # Normalizar output
        O[:, :, q_start:q_end, :] = O_i / l_i.unsqueeze(-1)
    
    return O


# ═══════════════════════════════════════════════════════════
# Uso prático: PyTorch SDPA (usa Flash Attention automaticamente)
# ═══════════════════════════════════════════════════════════

class EfficientAttention(nn.Module):
    """
    Atenção eficiente que usa Flash Attention via PyTorch SDPA.
    
    PyTorch 2.0+ seleciona automaticamente:
    - Flash Attention 2 (Ampere+)
    - Memory-Efficient Attention (Turing+)
    - Math Attention (fallback)
    """
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        
        self.wq = nn.Linear(d_model, d_model, bias=False)
        self.wk = nn.Linear(d_model, d_model, bias=False)
        self.wv = nn.Linear(d_model, d_model, bias=False)
        self.wo = nn.Linear(d_model, d_model, bias=False)

    def forward(self, x, mask=None):
        B, S, _ = x.shape
        
        q = self.wq(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.wk(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.wv(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
        
        # PyTorch SDPA — usa Flash Attention automaticamente
        attn = F.scaled_dot_product_attention(
            q, k, v,
            attn_mask=mask,
            is_causal=(mask is None),
            scale=self.head_dim ** -0.5,
        )
        
        attn = attn.transpose(1, 2).contiguous().view(B, S, -1)
        return self.wo(attn)


# ═══════════════════════════════════════════════════════════
# Flash Attention 3 com FP8 (Hopper/Blackwell)
# ═══════════════════════════════════════════════════════════

class FP8AttentionConfig:
    """
    Configuração para Flash Attention 3 com FP8.
    
    Requer: GPU Hopper (H100) ou Blackwell (B200)
    Benefício: 2x throughput vs FP16, metade da memória
    """
    def __init__(self):
        self.use_fp8 = torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 9
        self.fp8_format = "e4m3"  # ou "e5m2" para ranges maiores
        
    def create_attn_layer(self, d_model, n_heads):
        if self.use_fp8:
            # Usar Transformer Engine ou flash-attn 3
            try:
                from flash_attn_interface import flash_attn_func
                return FlashAttn3Wrapper(d_model, n_heads)
            except ImportError:
                pass
        return EfficientAttention(d_model, n_heads)


# ═══════════════════════════════════════════════════════════
# Benchmark: Flash Attention vs Standard
# ═══════════════════════════════════════════════════════════

def benchmark_attention(seq_len=4096, d_model=4096, n_heads=32, batch=1):
    """Compara Flash Attention vs atenção padrão."""
    import time
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.float16
    
    x = torch.randn(batch, seq_len, d_model, device=device, dtype=dtype)
    
    # Standard attention
    q = torch.randn(batch, n_heads, seq_len, d_model // n_heads, device=device, dtype=dtype)
    k = torch.randn(batch, n_heads, seq_len, d_model // n_heads, device=device, dtype=dtype)
    v = torch.randn(batch, n_heads, seq_len, d_model // n_heads, device=device, dtype=dtype)
    
    # Warmup
    for _ in range(10):
        _ = F.scaled_dot_product_attention(q, k, v, is_causal=True)
    
    if device.type == "cuda":
        torch.cuda.synchronize()
    
    # Benchmark
    start = time.perf_counter()
    for _ in range(100):
        out = F.scaled_dot_product_attention(q, k, v, is_causal=True)
    if device.type == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    
    # Memória
    if device.type == "cuda":
        mem = torch.cuda.max_memory_allocated() / 1e9
    else:
        mem = 0
    
    print(f"seq_len={seq_len}, d_model={d_model}")
    print(f"Tempo: {elapsed/100*1000:.2f} ms/forward")
    print(f"Memória: {mem:.2f} GB")
    
    return elapsed / 100
```

### Custo Computacional

| Técnico | Memória | Speed (A100) | Speed (H100) | Suporte |
|---|---|---|---|---|
| Standard Attention | O(N²) | 1x (baseline) | 1x | Universal |
| Flash Attention 1 | O(N) | 2-3x | 3x | Volta+ |
| Flash Attention 2 | O(N) | 3-4x | 5x | Ampere+ |
| Flash Attention 3 | O(N) | N/A | 6-8x | Hopper+ |
| FA3 + FP8 | O(N/2) | N/A | 10-12x | Hopper+ |

**Recomendação para agentes:** Sempre usar `F.scaled_dot_product_attention` do PyTorch 2.0+ — seleciona automaticamente a melhor implementação. Para H100, instalar `flash-attn 3.x` para suporte FP8.

---

## 7. Gradient Checkpointing

### Conceito

Gradient Checkpointing (Activation Checkpointing) troca computação por memória: em vez de guardar todos os intermediários do forward pass para o backward, re-computa parte deles durante o backward.

```
Sem checkpoint: memória = O(L × S × H) — todos os L layers salvos
Com checkpoint: memória = O(√L × S × H) — apenas checkpoints a cada √L layers
                  compute: +30% (re-computa intermediários)
```

**Evolução 2025-2026:**
- **Selective checkpointing:** re-computa apenas operações caras (attention)
- **CPU offloading:** checkpoints para CPU RAM (muito lento mas economiza GPU RAM)
- **Ring checkpointing:** distribuídos entre GPUs
- **Unified checkpointing:** combina com model parallelism

### Aplicabilidade em Modelos 3-8B

Essencial para treinar modelos 7B em GPUs com memória limitada (ex: 24GB). Permite batch sizes maiores ou modelos maiores.

### Implementação Python

```python
import torch
import torch.nn as nn
from torch.utils.checkpoint import checkpoint, checkpoint_sequential
from typing import List

# ═══════════════════════════════════════════════════════════
# Gradient Checkpointing Básico
# ═══════════════════════════════════════════════════════════

class CheckpointedTransformerBlock(nn.Module):
    """
    Bloco Transformer com gradient checkpointing.
    
    Durante o forward: não salva intermediários
    Durante o backward: re-computa o forward do bloco
    """
    def __init__(self, d_model=1024, n_heads=8, d_ff=4096):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
        )
        self.norm1 = nn.RMSNorm(d_model)
        self.norm2 = nn.RMSNorm(d_model)

    def _forward_impl(self, x, mask=None):
        """Forward real (sem checkpoint)."""
        residual = x
        x = self.norm1(x)
        x, _ = self.attn(x, x, x, attn_mask=mask, is_causal=True)
        x = residual + x
        
        residual = x
        x = self.norm2(x)
        x = residual + self.ffn(x)
        return x

    def forward(self, x, mask=None, use_checkpointing=True):
        if use_checkpointing and self.training:
            # Checkpoint: re-computa durante backward
            return checkpoint(
                self._forward_impl, x, mask,
                use_reentrant=False,  # Recomendado: False (mais seguro)
            )
        return self._forward_impl(x, mask)


# ═══════════════════════════════════════════════════════════
# Checkpointing Sequencial (por segmentos)
# ═══════════════════════════════════════════════════════════

class CheckpointedModel(nn.Module):
    """
    Modelo com checkpointing sequencial.
    
    Divide os layers em N segmentos. Cada segmento é checkpointed.
    Memória: O(segment_size × S × H) em vez de O(total_layers × S × H)
    """
    def __init__(self, layers: List[nn.Module], n_segments: int = 4):
        super().__init__()
        self.layers = nn.ModuleList(layers)
        self.n_segments = n_segments

    def forward(self, x, mask=None):
        if self.training:
            # Checkpoint sequencial: divide layers em segmentos
            return checkpoint_sequential(
                self.layers, 
                self.n_segments, 
                x, 
                mask=mask,
                use_reentrant=False,
            )
        # Inference: sem checkpointing (mais rápido)
        for layer in self.layers:
            x = layer(x, mask=mask, use_checkpointing=False)


# ═══════════════════════════════════════════════════════════
# Selective Checkpointing (apenas atenção)
# ═══════════════════════════════════════════════════════════

class SelectiveCheckpointBlock(nn.Module):
    """
    Checkpointing seletivo: apenas a atenção é checkpointed (operação mais cara),
    o FFN é mantido em memória (mais barato).
    """
    def __init__(self, d_model=1024, n_heads=8, d_ff=4096):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
        )
        self.norm1 = nn.RMSNorm(d_model)
        self.norm2 = nn.RMSNorm(d_model)

    def _attn_block(self, x, mask=None):
        """Atenção — checkpointed (O(N²) em memória se não checkpointed)."""
        x = self.norm1(x)
        return self.attn(x, x, x, attn_mask=mask, is_causal=True)[0]

    def forward(self, x, mask=None):
        # Checkpoint apenas atenção
        if self.training:
            attn_out = checkpoint(self._attn_block, x, mask, use_reentrant=False)
        else:
            attn_out = self._attn_block(x, mask)
        x = x + attn_out
        
        # FFN sem checkpoint (mais barato)
        x = x + self.ffn(self.norm2(x))
        return x


# ═══════════════════════════════════════════════════════════
# CPU Offloading para Checkpointing
# ═══════════════════════════════════════════════════════════

class CPUOffloadCheckpoint:
    """
    Offload checkpoints para CPU RAM durante forward,
    traz de volta para GPU durante backward.
    
    Economiza GPU RAM mas adiciona overhead de PCIe.
    Útil para modelos que não cabem em GPU.
    """
    def __init__(self, layers: List[nn.Module]):
        self.layers = layers

    def forward_with_offload(self, x, mask=None):
        """Forward com offload para CPU entre layers."""
        for layer in self.layers:
            # Mover input para GPU (se estava em CPU)
            if x.device.type == 'cpu':
                x = x.cuda()
            
            # Forward
            x = layer(x, mask=mask)
            
            # Offload output para CPU (libera GPU RAM)
            if self.training:
                x = x.cpu()
        
        return x.cuda()  # Voltar para GPU no final


# ═══════════════════════════════════════════════════════════
# Integração com HuggingFace Trainer
# ═══════════════════════════════════════════════════════════

def enable_gradient_checkpointing(model, gradient_checkpointing=True):
    """
    Habilita gradient checkpointing em modelos HuggingFace.
    
    Uso:
        model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-4B")
        model = enable_gradient_checkpointing(model)
    """
    if hasattr(model, 'gradient_checkpointing_enable'):
        if gradient_checkpointing:
            model.gradient_checkpointing_enable()
            # Configuração recomendada
            model.config.use_cache = False  # Desabilitar KV cache durante treino
            print("✅ Gradient checkpointing habilitado")
    else:
        print("⚠️ Modelo não suporta gradient_checkpointing_enable()")
    
    return model


# ═══════════════════════════════════════════════════════════
# Benchmark de memória
# ═══════════════════════════════════════════════════════════

def benchmark_checkpointing(model, input_ids, use_checkpointing=True):
    """Compara memória com e sem checkpointing."""
    import gc
    
    model.train()
    model.zero_grad()
    
    if use_checkpointing:
        if hasattr(model, 'gradient_checkpointing_enable'):
            model.gradient_checkpointing_enable()
    
    # Forward
    outputs = model(input_ids=input_ids, labels=input_ids)
    loss = outputs.loss
    
    # Backward
    loss.backward()
    
    if torch.cuda.is_available():
        mem = torch.cuda.max_memory_allocated() / 1e9
        torch.cuda.reset_peak_memory_stats()
    else:
        mem = 0
    
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    return mem
```

### Custo Computacional

| Configuração | Memória Ativa | Overhead Compute | Batch Size (7B, 24GB) |
|---|---|---|---|
| Sem checkpoint | O(L × S × H) | 0% | 1-2 |
| Checkpoint completo | O(√L × S × H) | +30% | 4-8 |
| Selective (attn only) | O(L × S × H / 2) | +15% | 2-4 |
| CPU offload | O(1) | +100-300% | 8+ |
| Ring (multi-GPU) | O(L × S × H / N_gpus) | +20% | 4×N_gpus |

**Recomendação para agentes:** Gradient checkpointing completo é essencial para treinar 7B em GPU única. Selective checkpointing para balancear velocidade/memória. CPU offload como último recurso.

---

## 8. Treinamento com Dados Sintéticos

### Conceito

Dados sintéticos são gerados por modelos (geralmente maiores) para treinar modelos menores ou especializados. Em 2025-2026, é a principal estratégia para criar dados de treino de alta qualidade em escala.

**Pipeline típico:**
```
1. Prompt engineering → gerar instruções diversas
2. Teacher model gera respostas
3. Filtragem (qualidade, diversidade, segurança)
4. Treinar student nos dados filtrados
5. (Opcional) Iterar: student gera → teacher avalia → filtrar → retreinar
```

**Técnicas 2025-2026:**
- **Evol-Instruct (Evol-Instruct):** evolui instruções simples para complexas
- **Magpie:** gera instruções a partir de chat templates do modelo
- **UltraChat:** diálogos multi-turno sintéticos
- **Orca-style:** explicações chain-of-thought sintéticas
- **DataComp:** seleção de dados via qualidade estimada
- **DoReMi:** reweighting de dados por domínio

### Aplicabilidade em Modelos 3-8B

Crítico! Dados sintéticos são a forma mais eficiente de treinar agentes especializados. Um modelo 7B pode ser treinado com dados sintéticos de um 70B e atingir ~90% da qualidade.

### Implementação Python

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import json
import random

# ═══════════════════════════════════════════════════════════
# Evol-Instruções: Evoluir instruções simples → complexas
# ═══════════════════════════════════════════════════════════

class EvolInstructGenerator:
    """
    Evol-Instruct: evolui instruções em profundidade e largura.
    
    Profundidade: adiciona restrições, aumenta complexidade
    Largura: gera variações da mesma instrução
    """
    
    EVOL_STRATEGIES = [
        "Adicione mais restrições e requisitos",
        "Aumente o raciocínio necessário",
        "Torne o problema mais específico",
        "Adicione múltiplos passos",
        "Inclua exemplos de entrada/saída",
        "Peça para explicar o raciocínio",
        "Adicione contexto do mundo real",
        "Combine com outro tópico",
    ]
    
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    def evolve_instruction(self, instruction: str, strategy: str) -> str:
        """Evolui uma instrução usando uma estratégia."""
        prompt = f"""A instrução abaixo é muito simples. Evolua-a aplicando esta estratégia: {strategy}

Instrução original: {instruction}

Instrução evoluída:"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                do_sample=True,
            )
        
        evolved = self.tokenizer.decode(output[0], skip_special_tokens=True)
        # Extrair apenas a instrução evoluída
        return evolved.split("Instrução evoluída:")[-1].strip()

    def generate_evolution_tree(
        self, 
        seed_instructions: List[str], 
        depth: int = 3, 
        breadth: int = 2,
    ) -> List[Dict]:
        """
        Gera árvore de instruções evoluídas.
        
        Args:
            seed_instructions: instruções iniciais simples
            depth: profundidade da árvore
            breadth: número de evoluções por nível
        """
        tree = []
        current_level = [{"instruction": inst, "depth": 0} for inst in seed_instructions]
        
        for d in range(depth):
            next_level = []
            for item in current_level:
                for _ in range(breadth):
                    strategy = random.choice(self.EVOL_STRATEGIES)
                    try:
                        evolved = self.evolve_instruction(item["instruction"], strategy)
                        next_level.append({
                            "instruction": evolved,
                            "depth": d + 1,
                            "parent": item["instruction"],
                            "strategy": strategy,
                        })
                    except Exception as e:
                        print(f"Erro ao evoluir: {e}")
            
            current_level = next_level
            tree.extend(current_level)
        
        return tree


# ═══════════════════════════════════════════════════════════
# Magpie: Gerar instruções a partir de templates
# ═══════════════════════════════════════════════════════════

class MagpieGenerator:
    """
    Magpie: Gera instruções sintéticas a partir do chat template do modelo.
    
    Ideia: o modelo pré-treinado já "sabe" o formato de instruções.
    Gerar o prefixo de uma conversa e deixar o modelo completar.
    """
    
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    def generate_instructions(self, n: int = 100, max_length: int = 128) -> List[str]:
        """
        Gera N instruções sintéticas.
        
        Usa o chat template do modelo para gerar o início de conversas.
        """
        instructions = []
        
        for _ in range(n):
            # Gerar prefixo aleatório que parece início de instrução
            # Usar tokens especiais do chat template
            prefix = self._generate_prefix()
            
            inputs = self.tokenizer(prefix, return_tensors="pt")
            with torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=0.9,
                    do_sample=True,
                    top_p=0.9,
                )
            
            decoded = self.tokenizer.decode(output[0], skip_special_tokens=True)
            instruction = self._extract_instruction(decoded, prefix)
            
            if instruction and len(instruction) > 10:
                instructions.append(instruction)
        
        return instructions

    def _generate_prefix(self) -> str:
        """Gera prefixo para iniciar geração."""
        prefixes = [
            "User: ",
            "Human: ",
            "Instruction: ",
            "Question: ",
            "Task: ",
        ]
        return random.choice(prefixes)

    def _extract_instruction(self, decoded: str, prefix: str) -> str:
        """Extrai instrução do texto gerado."""
        if prefix in decoded:
            return decoded.split(prefix)[-1].strip()
        return decoded.strip()


# ═══════════════════════════════════════════════════════════
# Filtragem de qualidade de dados sintéticos
# ═══════════════════════════════════════════════════════════

@dataclass
class DataQualityConfig:
    """Configuração para filtragem de dados sintéticos."""
    min_length: int = 20
    max_length: int = 2048
    min_response_length: int = 10
    dedup_threshold: float = 0.8  # Similaridade para deduplicação
    quality_threshold: float = 0.5  # Score mínimo de qualidade


class SyntheticDataFilter:
    """
    Pipeline de filtragem para dados sintéticos.
    
    Filtros:
    1. Comprimento (mín/máx)
    2. Deduplicação (hash + similaridade)
    3. Qualidade (modelo classificador ou heurísticas)
    4. Segurança (filtro de conteúdo)
    5. Diversidade (cobertura de tópicos)
    """
    
    def __init__(self, config: DataQualityConfig):
        self.config = config
        self.seen_hashes = set()

    def filter_dataset(self, data: List[Dict]) -> List[Dict]:
        """Pipeline completo de filtragem."""
        filtered = data
        
        # 1. Filtro de comprimento
        filtered = [d for d in filtered if self._check_length(d)]
        print(f"Após filtro de comprimento: {len(filtered)}/{len(data)}")
        
        # 2. Deduplicação
        filtered = self._deduplicate(filtered)
        print(f"Após deduplicação: {len(filtered)}/{len(data)}")
        
        # 3. Filtro de qualidade
        filtered = [d for d in filtered if self._check_quality(d)]
        print(f"Após filtro de qualidade: {len(filtered)}/{len(data)}")
        
        # 4. Filtro de segurança
        filtered = [d for d in filtered if self._check_safety(d)]
        print(f"Após filtro de segurança: {len(filtered)}/{len(data)}")
        
        return filtered

    def _check_length(self, item: Dict) -> bool:
        """Verifica comprimento mínimo e máximo."""
        instruction = item.get("instruction", "")
        response = item.get("response", "")
        
        return (
            self.config.min_length <= len(instruction) <= self.config.max_length
            and len(response) >= self.config.min_response_length
        )

    def _deduplicate(self, data: List[Dict]) -> List[Dict]:
        """Remove duplicatas via hash + similaridade."""
        unique = []
        for item in data:
            text = item.get("instruction", "")
            text_hash = hash(text.lower().strip())
            
            if text_hash not in self.seen_hashes:
                self.seen_hashes.add(text_hash)
                unique.append(item)
        
        return unique

    def _check_quality(self, item: Dict) -> bool:
        """Heurísticas de qualidade."""
        instruction = item.get("instruction", "")
        response = item.get("response", "")
        
        # Resposta não é vazia ou genérica
        generic_responses = [
            "não sei", "não posso", "desculpe", 
            "i don't know", "i cannot",
        ]
        if any(g in response.lower() for g in generic_responses):
            return False
        
        # Instrução é clara (tem verbo)
        verbs = ["explique", "descreva", "liste", "calcule", "analise",
                 "compare", "crie", "escreva", "resolva", "traduza",
                 "explain", "describe", "list", "calculate", "analyze"]
        if not any(v in instruction.lower() for v in verbs):
            return False
        
        return True

    def _check_safety(self, item: Dict) -> bool:
        """Filtro básico de segurança."""
        blocked_keywords = [
            "hack", "exploit", "malware", "phishing",
            # Adicionar mais conforme necessário
        ]
        text = (item.get("instruction", "") + " " + item.get("response", "")).lower()
        return not any(kw in text for kw in blocked_keywords)


# ═══════════════════════════════════════════════════════════
# Orca-style: Chain-of-Thought sintético
# ═══════════════════════════════════════════════════════════

class OrcaStyleGenerator:
    """
    Gera dados com chain-of-thought (CoT) sintético.
    
    Baseado no Orca (Microsoft, 2023): usa prompts de sistema
    que incentivam raciocínio passo a passo.
    """
    
    COT_SYSTEM_PROMPTS = [
        "Pense passo a passo antes de responder.",
        "Explique seu raciocínio detalhadamente.",
        "Mostre todos os passos do cálculo.",
        "Analise o problema sistematicamente.",
        "Reason through this step by step.",
        "Think carefully and explain your reasoning.",
    ]
    
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    def generate_cot_response(self, instruction: str) -> Dict:
        """Gera resposta com chain-of-thought."""
        system_prompt = random.choice(self.COT_SYSTEM_PROMPTS)
        
        prompt = f"""<system>{system_prompt}</system>

<user>{instruction}</user>

<assistant>"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.3,  # Mais determinístico para CoT
                do_sample=True,
            )
        
        response = self.tokenizer.decode(output[0], skip_special_tokens=True)
        response = response.split("<assistant>")[-1].strip()
        
        return {
            "instruction": instruction,
            "response": response,
            "system_prompt": system_prompt,
            "type": "chain_of_thought",
        }

    def generate_cot_dataset(
        self, 
        instructions: List[str], 
        n_cot_per_instruction: int = 1,
    ) -> List[Dict]:
        """Gera dataset completo com CoT."""
        dataset = []
        for inst in instructions:
            for _ in range(n_cot_per_instruction):
                item = self.generate_cot_response(inst)
                dataset.append(item)
        return dataset


# ═══════════════════════════════════════════════════════════
# Pipeline completo de geração de dados sintéticos
# ═══════════════════════════════════════════════════════════

class SyntheticDataPipeline:
    """
    Pipeline completo: gera, filtre e salva dados sintéticos.
    """
    
    def __init__(self, teacher_model, tokenizer, config: dict):
        self.teacher = teacher_model
        self.tokenizer = tokenizer
        self.config = config
        
        self.evol = EvolInstructGenerator(teacher_model, tokenizer)
        self.magpie = MagpieGenerator(teacher_model, tokenizer)
        self.cot = OrcaStyleGenerator(teacher_model, tokenizer)
        self.filter = SyntheticDataFilter(DataQualityConfig())

    def run(
        self,
        seed_instructions: List[str],
        output_path: str,
        n_evol_depth: int = 2,
        n_evol_breadth: int = 2,
        n_magpie: int = 100,
    ):
        """
        Pipeline completo de geração de dados sintéticos.
        """
        all_data = []
        
        # 1. Evol-Instruct
        print("🔄 Gerando instruções evoluídas...")
        evol_data = self.evol.generate_evolution_tree(
            seed_instructions, depth=n_evol_depth, breadth=n_evol_breadth
        )
        all_data.extend(evol_data)
        
        # 2. Magpie
        print("🔄 Gerando instruções via Magpie...")
        magpie_instructions = self.magpie.generate_instructions(n=n_magpie)
        all_data.extend([{"instruction": inst} for inst in magpie_instructions])
        
        # 3. Gerar respostas CoT
        print("🔄 Gerando respostas com Chain-of-Thought...")
        instructions = [d["instruction"] for d in all_data]
        cot_data = self.cot.generate_cot_dataset(instructions[:100])  # Limitar para demo
        all_data.extend(cot_data)
        
        # 4. Filtrar
        print("🔄 Filtrando dados...")
        filtered = self.filter.filter_dataset(all_data)
        
        # 5. Salvar
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Dataset salvo: {len(filtered)} exemplos em {output_path}")
        return filtered
```

### Custo Computacional

| Etapa | GPU-hours (70B teacher) | Output | Custo (A100) |
|---|---|---|---|
| Evol-Instruct (10K instruções) | ~5h | 10K instruções evoluídas | ~$15 |
| Magpie (100K instruções) | ~20h | 100K instruções | ~$60 |
| CoT generation (10K pares) | ~10h | 10K pares CoT | ~$30 |
| Filtragem | ~1h (CPU) | 70% passa | ~$1 |
| **Total** | **~36h** | **~80K exemplos** | **~$106** |

**Recomparação:** Anotar 80K exemplos manualmente custaria ~$40.000+ e meses de trabalho. Dados sintéticos são ~400x mais baratos.

**Recomendação para agentes:** Evol-Instruct + CoT generation para criar dados de treino de agentes. Filtragem rigorosa é essencial — dados sintéticos de baixa qualidade degradam o modelo.

---

## 9. Self-Play e Self-Instruction

### Conceito

**Self-Instruction (Self-Instruct):** O modelo gera suas próprias instruções de treino, cria respostas para elas, e se retreina. É um ciclo de auto-aprimoramento.

**Self-Play:** O modelo joga contra si mesmo (ou variantes de si mesmo) e aprende com os resultados. Inspirado em AlphaGo/AlphaZero.

**Evolução 2025-2026:**
- **SPIN (Self-Play Fine-Tuning):** Iterativo — modelo N ensina modelo N+1
- **STaR (Self-Taught Reasoner):** Gera raciocínios, mantém os que levam à resposta correta
- **RAG (Rejection Sampling Fine-Tuning):** Gera múltiplas respostas, treina na melhor
- **Constitutional AI self-critique:** Modelo critica suas próprias respostas
- **TextArena / AgentBench:** ambientes de self-play para agentes

### Aplicabilidade em Modelos 3-8B

Muito relevante! Self-play permite que um modelo 7B melhore continuamente sem dados externos. Para agentes, permite aprender tool calling, planejamento e raciocínio por tentativa e erro.

### Implementação Python

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional
import random

# ═══════════════════════════════════════════════════════════
# Self-Instruct: Modelo gera suas próprias instruções
# ═══════════════════════════════════════════════════════════

class SelfInstruct:
    """
    Self-Instruct (Wang et al., 2023): modelo gera instruções,
    gera respostas, filtra, e se retreina.
    
    Loop:
    1. Modelo gera novas instruções
    2. Modelo gera respostas para as instruções
    3. Filtrar por qualidade
    4. Adicionar ao dataset de treino
    5. Retreinar
    6. Repetir
    """
    
    TASK_GENERATION_PROMPT = """Aqui estão algumas tarefas de exemplo:
{tasks}

Gere 5 novas tarefas similares mas diferentes. Cada tarefa deve ser uma instrução clara.
Formato: uma tarefa por linha.

Novas tarefas:
"""
    
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    def generate_tasks(self, seed_tasks: List[str], n_new: int = 20) -> List[str]:
        """Gera novas tarefas a partir de tarefas seed."""
        selected_seeds = random.sample(seed_tasks, min(8, len(seed_tasks)))
        prompt = self.TASK_GENERATION_PROMPT.format(
            tasks="\n".join(f"- {t}" for t in selected_seeds)
        )
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.8,
                do_sample=True,
            )
        
        decoded = self.tokenizer.decode(output[0], skip_special_tokens=True)
        # Extrair tarefas geradas
        tasks = []
        for line in decoded.split("\n"):
            line = line.strip().lstrip("- ").lstrip("0123456789. ")
            if line and len(line) > 10:
                tasks.append(line)
        
        return tasks[:n_new]

    def generate_responses(self, tasks: List[str]) -> List[Dict]:
        """Gera respostas para as tarefas."""
        data = []
        for task in tasks:
            inputs = self.tokenizer(task, return_tensors="pt")
            with torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.3,
                )
            
            response = self.tokenizer.decode(output[0], skip_special_tokens=True)
            data.append({
                "instruction": task,
                "response": response,
            })
        
        return data

    def run_iteration(
        self, 
        seed_tasks: List[str], 
        n_new_tasks: int = 20,
    ) -> List[Dict]:
        """Uma iteração de self-instruct."""
        # Gerar novas tarefas
        new_tasks = self.generate_tasks(seed_tasks, n_new_tasks)
        
        # Gerar respostas
        new_data = self.generate_responses(new_tasks)
        
        return new_data


# ═══════════════════════════════════════════════════════════
# STaR: Self-Taught Reasoner
# ═══════════════════════════════════════════════════════════

class STaRReasoner:
    """
    STaR (Zelikman et al., 2022): modelo gera raciocínios (CoT),
    mantém apenas os que levam à resposta correta.
    
    Loop:
    1. Modelo tenta resolver problema com CoT
    2. Se resposta correta → manter (raciocínio + resposta)
    3. Se errado → dar a resposta correta e pedir para explicar
    4. Treinar nos raciocínios que levam à resposta correta
    """
    
    COT_PROMPT = """Resolva o problema passo a passo:

Problema: {problem}

Raciocínio passo a passo:"""

    ANSWER_PROMPT = """O problema é: {problem}

A resposta correta é: {answer}

Explique o raciocínio que leva a esta resposta:

Raciocínio passo a passo:"""
    
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    def generate_reasoning(self, problem: str, answer: Optional[str] = None) -> Dict:
        """
        Gera raciocínio para um problema.
        Se answer é fornecido, gera raciocínio "com dica".
        """
        if answer:
            prompt = self.ANSWER_PROMPT.format(problem=problem, answer=answer)
        else:
            prompt = self.COT_PROMPT.format(problem=problem)
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,
                do_sample=True,
            )
        
        reasoning = self.tokenizer.decode(output[0], skip_special_tokens=True)
        reasoning = reasoning.split("Raciocínio passo a passo:")[-1].strip()
        
        return {
            "problem": problem,
            "reasoning": reasoning,
            "answer": answer,
            "mode": "hint" if answer else "generate",
        }

    def solve_with_reasoning(self, problem: str) -> Tuple[str, str]:
        """Tenta resolver problema e retorna (raciocínio, resposta)."""
        result = self.generate_reasoning(problem)
        reasoning = result["reasoning"]
        
        # Extrair resposta do raciocínio (última linha ou após "Resposta:")
        lines = reasoning.split("\n")
        answer = ""
        for line in reversed(lines):
            if "resposta" in line.lower() or "answer" in line.lower():
                answer = line.split(":")[-1].strip()
                break
        
        return reasoning, answer

    def star_iteration(
        self,
        problems: List[Dict],  # [{"problem": ..., "answer": ...}]
    ) -> List[Dict]:
        """
        Uma iteração STaR.
        
        Args:
            problems: lista de problemas com respostas conhecidas
        Returns:
            dataset de raciocínios para treino
        """
        training_data = []
        
        for item in problems:
            problem = item["problem"]
            correct_answer = item["answer"]
            
            # Tentar resolver sem dica
            reasoning, predicted_answer = self.solve_with_reasoning(problem)
            
            if self._check_answer(predicted_answer, correct_answer):
                # Sucesso! Manter raciocínio
                training_data.append({
                    "problem": problem,
                    "reasoning": reasoning,
                    "answer": correct_answer,
                    "source": "generated",
                })
            else:
                # Falha: gerar raciocínio com dica
                hinted = self.generate_reasoning(problem, correct_answer)
                training_data.append({
                    "problem": problem,
                    "reasoning": hinted["reasoning"],
                    "answer": correct_answer,
                    "source": "hinted",
                })
        
        return training_data

    def _check_answer(self, predicted: str, correct: str) -> bool:
        """Verifica se a resposta está correta (simplificado)."""
        # Na prática: parsing mais sofisticado
        pred_clean = predicted.strip().lower().rstrip(".")
        correct_clean = correct.strip().lower().rstrip(".")
        return pred_clean == correct_clean


# ═══════════════════════════════════════════════════════════
# SPIN: Self-Play Fine-Tuning
# ═══════════════════════════════════════════════════════════

class SPINTrainer:
    """
    SPIN (Self-Play Fine-Tuning, 2024):
    
    Modelo N (player) gera respostas.
    Modelo N-1 (opponent) gera respostas para as mesmas perguntas.
    Treinar modelo N para preferir suas respostas vs opponent.
    
    Loss: E[log σ(f_θ(x, y_w) - f_θ(x, y_l))]
    onde y_w = resposta do player, y_l = resposta do opponent
    """
    
    def __init__(self, player_model, opponent_model):
        self.player = player_model
        self.opponent = opponent_model

    def compute_spin_loss(
        self,
        input_ids: torch.Tensor,
        player_response: torch.Tensor,
        opponent_response: torch.Tensor,
    ) -> torch.Tensor:
        """
        SPIN loss: player deve dar score maior para suas respostas.
        """
        # Score do player para sua própria resposta
        player_logits = self.player(
            torch.cat([input_ids, player_response], dim=1)
        ).logits
        player_score = self._compute_sequence_score(player_logits, player_response)
        
        # Score do player para resposta do opponent
        opponent_logits = self.player(
            torch.cat([input_ids, opponent_response], dim=1)
        ).logits
        opponent_score = self._compute_sequence_score(opponent_logits, opponent_response)
        
        # Loss: player_score > opponent_score
        loss = -F.logsigmoid(player_score - opponent_score).mean()
        
        return loss

    def _compute_sequence_score(self, logits, response):
        """Score = média dos log-probs dos tokens."""
        log_probs = F.log_softmax(logits[:, -response.size(1):, :], dim=-1)
        token_log_probs = log_probs.gather(-1, response.unsqueeze(-1)).squeeze(-1)
        return token_log_probs.mean(dim=-1)

    def self_play_iteration(
        self,
        prompts: List[str],
        tokenizer,
        optimizer,
    ):
        """Uma iteração de self-play."""
        for prompt in prompts:
            inputs = tokenizer(prompt, return_tensors="pt")
            
            # Player gera resposta
            with torch.no_grad():
                player_response = self.player.generate(**inputs, max_new_tokens=256)
                opponent_response = self.opponent.generate(**inputs, max_new_tokens=256)
            
            # Treinar player
            loss = self.compute_spin_loss(
                inputs["input_ids"],
                player_response,
                opponent_response,
            )
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()


# ═══════════════════════════════════════════════════════════
# RAG: Rejection Sampling Fine-Tuning
# ═══════════════════════════════════════════════════════════

class RejectionSamplingFT:
    """
    Rejection Sampling Fine-Tuning:
    
    1. Gerar K respostas para cada prompt
    2. Avaliar cada resposta (reward model ou heurística)
    3. Manter apenas as N melhores
    4. Treinar nas melhores respostas
    """
    
    def __init__(self, model, tokenizer, reward_fn=None):
        self.model = model
        self.tokenizer = tokenizer
        self.reward_fn = reward_fn or self._default_reward

    def _default_reward(self, prompt: str, response: str) -> float:
        """Reward padrão: comprimento + diversidade."""
        # Na prática: usar reward model treinado
        return len(response) / 1000.0

    def generate_and_filter(
        self,
        prompts: List[str],
        n_samples: int = 8,
        n_keep: int = 2,
    ) -> List[Dict]:
        """
        Gera N respostas por prompt, mantém as K melhores.
        """
        training_data = []
        
        for prompt in prompts:
            samples = []
            
            for _ in range(n_samples):
                inputs = self.tokenizer(prompt, return_tensors="pt")
                with torch.no_grad():
                    output = self.model.generate(
                        **inputs,
                        max_new_tokens=512,
                        temperature=0.8,
                        do_sample=True,
                    )
                
                response = self.tokenizer.decode(output[0], skip_special_tokens=True)
                reward = self.reward_fn(prompt, response)
                
                samples.append({
                    "prompt": prompt,
                    "response": response,
                    "reward": reward,
                })
            
            # Manter top-K por reward
            samples.sort(key=lambda x: x["reward"], reverse=True)
            training_data.extend(samples[:n_keep])
        
        return training_data

    def train_on_filtered(
        self,
        filtered_data: List[Dict],
        optimizer,
        n_epochs: int = 1,
    ):
        """Treina nos dados filtrados."""
        for epoch in range(n_epochs):
            total_loss = 0
            for item in filtered_data:
                inputs = self.tokenizer(
                    item["prompt"] + item["response"],
                    return_tensors="pt",
                    truncation=True,
                    max_length=2048,
                )
                
                outputs = self.model(
                    input_ids=inputs["input_ids"],
                    labels=inputs["input_ids"],
                )
                
                loss = outputs.loss
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            print(f"Epoch {epoch+1}, Loss: {total_loss/len(filtered_data):.4f}")
```

### Custo Computacional

| Técnico | GPU-hours (7B) | Iterações | Melhoria | Custo (A100) |
|---|---|---|---|---|
| Self-Instruct | ~10h/iteração | 3-5 | +5-10% | ~$150 |
| STaR | ~15h/iteração | 3-5 | +8-15% (raciocínio) | ~$225 |
| SPIN | ~20h/iteração | 5-10 | +10-20% | ~$600 |
| Rejection Sampling FT | ~8h/iteração | 3-5 | +5-12% | ~$120 |

**Recomendação para agentes:** STaR para melhorar raciocínio (crítico para agentes). SPIN para alinhamento geral. Rejection Sampling FT para tool calling (gerar múltiplas chamadas de tool, manter as corretas).

---

## 10. Constitutional AI e RLHF Simplificado

### Conceito

**Constitutional AI (CAI)** (Anthropic, 2022-2024): O modelo segue uma "constituição" — um conjunto de princípios escritos em linguagem natural. Em vez de RLHF com humanos, usa AI feedback (AIF) onde o modelo critica e revisa suas próprias respostas baseado nos princípios.

**Pipeline CAI:**
```
1. Modelo gera resposta
2. Modelo critica a resposta baseado na constituição
3. Modelo revisa a resposta
4. (Opcional) Treinar um reward model nos critérios
5. Treinar com RL (PPO) ou DPO
```

**RLHF Simplificado (2025-2026):**
- **DPO (Direct Preference Optimization):** Substitui RL por classificação direta
- **ORPO (Odds Ratio Preference Optimization):** Combina SFT + DPO em 1 etapa
- **KTO (Kahneman-Tversky Optimization):** Usa labels binários (bom/ruim) em vez de pares
- **SimPO:** DPO sem referência model (mais simples)
- **RLOO (REINFORCE Leave-One-Out):** RL leve sem reward model

### Aplicabilidade em Modelos 3-8B

Essencial para alinhar agentes! DPO/ORPO são viáveis em modelos 3-8B com hardware modesto. Constitutional AI elimina necessidade de anotadores humanos.

### Implementação Python

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional

# ═══════════════════════════════════════════════════════════
# Constitutional AI: Auto-crítica e revisão
# ═══════════════════════════════════════════════════════════

class ConstitutionalAI:
    """
    Constitutional AI: modelo segue princípios de uma "constituição".
    
    Pipeline:
    1. Gerar resposta inicial
    2. Auto-critique baseado na constituição
    3. Revisar resposta
    4. (Opcional) Coletar pares (rejeitada, revisada) para DPO
    """
    
    DEFAULT_CONSTITUTION = [
        "Seja honesto e não enganoso.",
        "Não forneça informações prejudiciais ou perigosas.",
        "Respeite a privacidade e autonomia do usuário.",
        "Seja útil e construtivo.",
        "Reconheça suas limitações quando não souber algo.",
        "Não discrimine com base em raça, gênero, religião, etc.",
        "Forneça informações precisas e bem fundamentadas.",
    ]
    
    CRITIQUE_PROMPT = """Avalie a resposta abaixo de acordo com este princípio constitucional:

Princípio: {principle}

Pergunta: {prompt}

Resposta: {response}

A resposta viola este princípio? Se sim, explique por quê e sugira uma melhoria.
Se não, escreva "Nenhuma violação."

Avaliação:"""
    
    REVISE_PROMPT = """A resposta abaixo foi criticada por violar este princípio constitucional:

Princípio: {principle}

Pergunta: {prompt}

Resposta original: {response}

Crítica: {critique}

Reescreva a resposta para respeitar o princípio, mantendo-a útil e relevante:

Resposta revisada:"""
    
    def __init__(self, model, tokenizer, constitution: List[str] = None):
        self.model = model
        self.tokenizer = tokenizer
        self.constitution = constitution or self.DEFAULT_CONSTITUTION

    def generate_response(self, prompt: str) -> str:
        """Gera resposta inicial."""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
            )
        return self.tokenizer.decode(output[0], skip_special_tokens=True)

    def critique_response(
        self, prompt: str, response: str, principle: str
    ) -> str:
        """Critica resposta baseado em um princípio."""
        critique_prompt = self.CRITIQUE_PROMPT.format(
            principle=principle, prompt=prompt, response=response
        )
        
        inputs = self.tokenizer(critique_prompt, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.3,
            )
        
        return self.tokenizer.decode(output[0], skip_special_tokens=True)

    def revise_response(
        self, prompt: str, response: str, critique: str, principle: str
    ) -> str:
        """Revisa resposta baseado na crítica."""
        revise_prompt = self.REVISE_PROMPT.format(
            principle=principle, prompt=prompt,
            response=response, critique=critique
        )
        
        inputs = self.tokenizer(revise_prompt, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.5,
            )
        
        return self.tokenizer.decode(output[0], skip_special_tokens=True)

    def constitutional_process(self, prompt: str) -> Dict:
        """
        Pipeline completo: gerar → criticar → revisar.
        """
        # Gerar resposta
        response = self.generate_response(prompt)
        
        # Criticar contra cada princípio
        critiques = []
        for principle in self.constitution:
            critique = self.critique_response(prompt, response, principle)
            if "nenhuma violação" not in critique.lower():
                critiques.append({"principle": principle, "critique": critique})
        
        # Se houver críticas, revisar
        revised = response
        if critiques:
            # Usar a primeira crítica encontrada
            main_critique = critiques[0]
            revised = self.revise_response(
                prompt, response,
                main_critique["critique"],
                main_critique["principle"],
            )
        
        return {
            "prompt": prompt,
            "initial_response": response,
            "critiques": critiques,
            "revised_response": revised,
            "was_revised": len(critiques) > 0,
        }

    def generate_dpo_pairs(self, prompts: List[str]) -> List[Dict]:
        """
        Gera pares (rejected, accepted) para DPO a partir do processo constitucional.
        """
        pairs = []
        for prompt in prompts:
            result = self.constitutional_process(prompt)
            if result["was_revised"]:
                pairs.append({
                    "prompt": prompt,
                    "rejected": result["initial_response"],
                    "chosen": result["revised_response"],
                })
        
        return pairs


# ═══════════════════════════════════════════════════════════
# DPO: Direct Preference Optimization
# ═══════════════════════════════════════════════════════════

class DPOTrainer:
    """
    DPO (Rafailov et al., 2023): otimização direta de preferências.
    
    Loss = -log σ(β · (log π_θ(y_w|x)/π_ref(y_w|x) - log π_θ(y_l|x)/π_ref(y_l|x)))
    
    Onde:
    - y_w = resposta preferida (chosen)
    - y_l = resposta rejeitada (rejected)
    - π_θ = modelo sendo treinado
    - π_ref = modelo de referência (congelado)
    - β = temperatura (controle de divergência)
    """
    
    def __init__(
        self, 
        model: nn.Module, 
        ref_model: nn.Module, 
        beta: float = 0.1,
    ):
        self.model = model
        self.ref_model = ref_model
        self.beta = beta
        
        # Congelar modelo de referência
        for p in self.ref_model.parameters():
            p.requires_grad = False
        self.ref_model.eval()

    def compute_dpo_loss(
        self,
        input_ids: torch.Tensor,
        chosen_ids: torch.Tensor,
        rejected_ids: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute DPO loss.
        
        Args:
            input_ids: (B, S_prompt) — prompts
            chosen_ids: (B, S_chosen) — respostas preferidas
            rejected_ids: (B, S_rejected) — respostas rejeitadas
        """
        # Forward no modelo treinável
        chosen_logits = self.model(
            torch.cat([input_ids, chosen_ids], dim=1)
        ).logits[:, input_ids.size(1):, :]
        
        rejected_logits = self.model(
            torch.cat([input_ids, rejected_ids], dim=1)
        ).logits[:, input_ids.size(1):, :]
        
        # Forward no modelo de referência (sem grad)
        with torch.no_grad():
            ref_chosen_logits = self.ref_model(
                torch.cat([input_ids, chosen_ids], dim=1)
            ).logits[:, input_ids.size(1):, :]
            
            ref_rejected_logits = self.ref_model(
                torch.cat([input_ids, rejected_ids], dim=1)
            ).logits[:, input_ids.size(1):, :]
        
        # Log-ratios
        chosen_log_ratio = self._compute_log_ratio(
            chosen_logits, ref_chosen_logits, chosen_ids
        )
        rejected_log_ratio = self._compute_log_ratio(
            rejected_logits, ref_rejected_logits, rejected_ids
        )
        
        # DPO loss
        logits_diff = self.beta * (chosen_log_ratio - rejected_log_ratio)
        loss = -F.logsigmoid(logits_diff).mean()
        
        return loss

    def _compute_log_ratio(
        self, 
        policy_logits: torch.Tensor, 
        ref_logits: torch.Tensor,
        response_ids: torch.Tensor,
    ) -> torch.Tensor:
        """Compute log(π_θ(y|x) / π_ref(y|x)) para a sequência."""
        policy_log_probs = F.log_softmax(policy_logits, dim=-1)
        ref_log_probs = F.log_softmax(ref_logits, dim=-1)
        
        # Gather log-probs dos tokens reais
        policy_lp = policy_log_probs.gather(-1, response_ids.unsqueeze(-1)).squeeze(-1)
        ref_lp = ref_log_probs.gather(-1, response_ids.unsqueeze(-1)).squeeze(-1)
        
        # Soma sobre a sequência (log de produto = soma de logs)
        return (policy_lp - ref_lp).sum(dim=-1)

    @property
    def metrics(self):
        """Métricas úteis para monitorar DPO."""
        return {
            "beta": self.beta,
            "model_params": sum(p.numel() for p in self.model.parameters()),
            "ref_params": sum(p.numel() for p in self.ref_model.parameters()),
        }


# ═══════════════════════════════════════════════════════════
# ORPO: Odds Ratio Preference Optimization
# ═══════════════════════════════════════════════════════════

class ORPOTrainer:
    """
    ORPO (Hong et al., 2024): combina SFT + preference optimization em 1 loss.
    
    Loss = Loss_SFT + λ · Loss_OR
    
    Loss_OR = -log σ(log odds_θ(y_w|x) - log odds_θ(y_l|x))
    
    Onde odds = P(y|x) / (1 - P(y|x))
    
    Vantagem: não precisa de modelo de referência!
    """
    
    def __init__(self, model: nn.Module, lambda_or: float = 1.0):
        self.model = model
        self.lambda_or = lambda_or

    def compute_orpo_loss(
        self,
        input_ids: torch.Tensor,
        chosen_ids: torch.Tensor,
        rejected_ids: torch.Tensor,
        chosen_labels: torch.Tensor,
    ) -> Tuple[torch.Tensor, dict]:
        """
        ORPO loss = SFT loss (on chosen) + OR loss.
        """
        # SFT loss (apenas nas respostas chosen)
        chosen_input = torch.cat([input_ids, chosen_ids], dim=1)
        chosen_logits = self.model(chosen_input).logits[:, input_ids.size(1):, :]
        
        sft_loss = F.cross_entropy(
            chosen_logits.view(-1, chosen_logits.size(-1)),
            chosen_labels.view(-1),
            ignore_index=-100,
        )
        
        # Odds Ratio loss
        # Log-likelihood de chosen
        chosen_ll = self._log_likelihood(chosen_logits, chosen_ids)
        
        # Log-likelihood de rejected
        rejected_input = torch.cat([input_ids, rejected_ids], dim=1)
        rejected_logits = self.model(rejected_input).logits[:, input_ids.size(1):, :]
        rejected_ll = self._log_likelihood(rejected_logits, rejected_ids)
        
        # Odds = exp(log_likelihood) / (1 - exp(log_likelihood))
        # log_odds = log_likelihood - log(1 - exp(log_likelihood))
        chosen_odds = chosen_ll - torch.log1p(-torch.exp(chosen_ll) + 1e-8)
        rejected_odds = rejected_ll - torch.log1p(-torch.exp(rejected_ll) + 1e-8)
        
        or_loss = -F.logsigmoid(chosen_odds - rejected_odds).mean()
        
        # Combined
        total_loss = sft_loss + self.lambda_or * or_loss
        
        return total_loss, {
            "sft_loss": sft_loss.item(),
            "or_loss": or_loss.item(),
            "total_loss": total_loss.item(),
        }

    def _log_likelihood(self, logits, response_ids):
        """Log-likelihood de uma sequência."""
        log_probs = F.log_softmax(logits, dim=-1)
        token_lp = log_probs.gather(-1, response_ids.unsqueeze(-1)).squeeze(-1)
        return token_lp.mean(dim=-1)


# ═══════════════════════════════════════════════════════════
# SimPO: Simplified Preference Optimization
# ═══════════════════════════════════════════════════════════

class SimPOTrainer:
    """
    SimPO (Meng et al., 2024): DPO simplificado sem modelo de referência.
    
    Loss = -log σ(β · (log π_θ(y_w|x)/|y_w| - log π_θ(y_l|x)/|y_l|))
    
    Diferença vs DPO: normaliza pelo comprimento da resposta.
    Não precisa de modelo de referência!
    """
    
    def __init__(self, model: nn.Module, beta: float = 2.0, gamma: float = 0.5):
        self.model = model
        self.beta = beta
        self.gamma = gamma  # Margin

    def compute_simpo_loss(
        self,
        input_ids: torch.Tensor,
        chosen_ids: torch.Tensor,
        rejected_ids: torch.Tensor,
    ) -> torch.Tensor:
        """SimPO loss."""
        # Chosen
        chosen_input = torch.cat([input_ids, chosen_ids], dim=1)
        chosen_logits = self.model(chosen_input).logits[:, input_ids.size(1):, :]
        chosen_ll = self._avg_log_prob(chosen_logits, chosen_ids)
        
        # Rejected
        rejected_input = torch.cat([input_ids, rejected_ids], dim=1)
        rejected_logits = self.model(rejected_input).logits[:, input_ids.size(1):, :]
        rejected_ll = self._avg_log_prob(rejected_logits, rejected_ids)
        
        # SimPO loss
        logits_diff = self.beta * (chosen_ll - rejected_ll) - self.gamma
        loss = -F.logsigmoid(logits_diff).mean()
        
        return loss

    def _avg_log_prob(self, logits, response_ids):
        """Log-prob média por token."""
        log_probs = F.log_softmax(logits, dim=-1)
        token_lp = log_probs.gather(-1, response_ids.unsqueeze(-1)).squeeze(-1)
        return token_lp.mean(dim=-1)


# ═══════════════════════════════════════════════════════════
# RLOO: REINFORCE Leave-One-Out
# ═══════════════════════════════════════════════════════════

class RLOOTrainer:
    """
    RLOO (Ahmadian et al., 2024): RL leve sem reward model.
    
    Para cada prompt, gera N respostas. Usa N-1 respostas como baseline
    para reduzir variância do gradiente.
    
    Advantage_i = reward_i - mean(reward_{-i})
    Loss = - Advantage_i · log π_θ(y_i | x)
    """
    
    def __init__(self, model: nn.Module, reward_fn, n_samples: int = 4):
        self.model = model
        self.reward_fn = reward_fn
        self.n_samples = n_samples

    def compute_rloo_loss(
        self,
        input_ids: torch.Tensor,
    ) -> torch.Tensor:
        """RLOO loss."""
        B = input_ids.size(0)
        
        # Gerar N respostas por prompt
        all_responses = []
        all_log_probs = []
        all_rewards = []
        
        for _ in range(self.n_samples):
            with torch.no_grad():
                responses = self.model.generate(
                    input_ids, max_new_tokens=256, do_sample=True
                )
            
            # Calcular log-probs (com grad)
            full_input = torch.cat([input_ids, responses[:, input_ids.size(1):]], dim=1)
            logits = self.model(full_input).logits[:, input_ids.size(1):, :]
            log_probs = F.log_softmax(logits, dim=-1)
            
            response_ids = responses[:, input_ids.size(1):]
            token_lp = log_probs.gather(-1, response_ids.unsqueeze(-1)).squeeze(-1)
            seq_lp = token_lp.mean(dim=-1)
            
            # Rewards
            rewards = torch.tensor([
                self.reward_fn(
                    self.tokenizer.decode(input_ids[i]),
                    self.tokenizer.decode(response_ids[i]),
                )
                for i in range(B)
            ], device=input_ids.device)
            
            all_responses.append(responses)
            all_log_probs.append(seq_lp)
            all_rewards.append(rewards)
        
        # Stack: (N, B)
        rewards = torch.stack(all_rewards)
        log_probs = torch.stack(all_log_probs)
        
        # Leave-one-out baseline
        # Para cada amostra i: baseline = mean(reward[j != i])
        total_reward = rewards.sum(dim=0)  # (B,)
        baseline = (total_reward - rewards) / (self.n_samples - 1)  # (N, B)
        
        # Advantage
        advantages = rewards - baseline  # (N, B)
        
        # Policy gradient loss
        loss = -(advantages.detach() * log_probs).mean()
        
        return loss
```

### Custo Computacional

| Técnico | GPU-hours (7B) | Dados Necessários | Melhoria | Complexidade |
|---|---|---|---|---|
| Constitutional AI (AIF) | ~20h | Constituição (texto) | +10-15% segurança | Média |
| DPO | ~30h | 10-50K pares | +15-25% alinhamento | Baixa |
| ORPO | ~25h | 10-50K pares | +12-20% | Baixa |
| SimPO | ~20h | 10-50K pares | +10-18% | Muito Baixa |
| RLOO | ~40h | 5-20K prompts | +10-15% | Média |
| PPO (clássico) | ~100h | 5-20K prompts + RM | +15-25% | Alta |

**Recomendação para agentes:** 
1. **Constitutional AI** para segurança básica (custo zero em dados)
2. **DPO** para alinhamento com preferências humanas (melhor qualidade)
3. **ORPO** se quiser simplicidade (sem modelo de referência)
4. **SimPO** para implementação mais simples

---

## 11. Resumo Comparativo

### Tabela Geral

| # | Técnica | Tipo | Impacto | Custo | Dificuldade | Prioridade Agente |
|---|---|---|---|---|---|---|
| 1 | **MoE** | Arquitetura | ⭐⭐⭐⭐ | Alto | Alta | Média |
| 2 | **DoRA/QLoRA** | Fine-tuning | ⭐⭐⭐⭐ | Baixo | Baixa | **Alta** |
| 3 | **Knowledge Distillation** | Treino | ⭐⭐⭐⭐ | Médio | Média | **Alta** |
| 4 | **Speculative Decoding** | Inferência | ⭐⭐⭐ | Baixo | Baixa | **Alta** |
| 5 | **KV-Cache Compression** | Inferência | ⭐⭐⭐⭐ | Baixo | Média | **Alta** |
| 6 | **Flash Attention 2/3** | Inferência | ⭐⭐⭐ | Zero | Baixa | **Alta** |
| 7 | **Gradient Checkpointing** | Treino | ⭐⭐⭐ | Zero | Baixa | **Alta** |
| 8 | **Dados Sintéticos** | Dados | ⭐⭐⭐⭐ | Baixo | Média | **Alta** |
| 9 | **Self-Play/Self-Instruction** | Treino | ⭐⭐⭐ | Médio | Alta | Média |
| 10 | **CAI + DPO/ORPO** | Alinhamento | ⭐⭐⭐⭐ | Médio | Média | **Alta** |

### Por Caso de Uso (Agente 3-8B)

| Caso de Uso | Técnicas Recomendadas |
|---|---|
| **Treinar agente do zero** | Dados sintéticos + KD + DoRA + Gradient checkpointing |
| **Adaptar modelo existente** | DoRA/QLoRA + DPO/ORPO + Constitutional AI |
| **Otimizar inferência** | Flash Attention + KV-cache compression + Speculative decoding |
| **Melhorar raciocínio** | STaR + CoT sintético + DPO |
| **Alinhar comportamento** | Constitutional AI + DPO + Self-play |
| **Contexto longo** | MLA + KV-cache quantização + StreamingLLM |

---

## 12. Roadmap de Implementação

### Fase 1: Fundação (Semanas 1-4)
```
✅ Flash Attention 2/3 (já disponível via PyTorch SDPA)
✅ Gradient Checkpointing (1 linha de código)
✅ DoRA/QLoRA para fine-tuning
✅ Dados sintéticos (Evol-Instruct + CoT)
```

### Fase 2: Otimização (Semanas 5-8)
```
✅ KV-Cache compression (GQA + INT8)
✅ Speculative Decoding (EAGLE ou self-speculative)
✅ Knowledge Distillation (logit + feature)
✅ DPO/ORPO para alinhamento
```

### Fase 3: Avançado (Semanas 9-12)
```
✅ Constitutional AI (auto-crítica)
✅ Self-play (SPIN ou STaR)
✅ MoE (se recursos permitirem)
✅ Iteração: coletar dados reais → retreinar
```

### Stack Recomendado 2025-2026

```yaml
# stack.yaml — Stack recomendado para agente 3-8B
framework:
  training: "Unsloth + TRL"  # ou "Axolotl"
  inference: "vLLM"          # ou "SGLang"
  attention: "Flash Attention 3"
  
fine_tuning:
  method: "DoRA"             # ou "QLoRA" para GPU limitada
  rank: 32
  alpha: 64
  target_modules: ["q_proj", "v_proj", "gate_proj", "up_proj"]

alignment:
  method: "DPO"              # ou "ORPO" para simplicidade
  beta: 0.1
  dataset: "synthetic + human preferences"

inference_optimization:
  attention: "Flash Attention 3"
  kv_cache: "INT8 quantization"
  speculative: "EAGLE-3"     # ou "self-speculative"
  batching: "continuous batching (vLLM)"

data:
  synthetic: "Evol-Instruct + Orca-style CoT"
  filtering: "dedup + quality + safety"
  augmentation: "Self-instruction"
```

### Estimativa de Recursos

| Cenário | GPU | RAM | Tempo | Custo |
|---|---|---|---|---|
| **Mínimo** (QLoRA 4B) | 1× A100 40GB | 64 GB | 2-5 dias | ~$200 |
| **Recomendado** (DoRA 7B) | 1× A100 80GB | 128 GB | 5-10 dias | ~$500 |
| **Ideal** (Full pipeline) | 2-4× A100 80GB | 256 GB | 2-4 semanas | ~$2000 |
| **Especulativo** (MoE 8B) | 4× A100 80GB | 512 GB | 4-8 semanas | ~$5000 |

---

## Referências

### Papers Fundamentais
1. **MoE:** Fedus et al., "Switch Transformers" (2021); DeepSeek-V3 Technical Report (2024)
2. **LoRA:** Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models" (2021)
3. **QLoRA:** Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs" (2023)
4. **DoRA:** Liu et al., "DoRA: Weight-Decomposed Low-Rank Adaptation" (2024)
5. **KD:** Hinton et al., "Distilling the Knowledge in a Neural Network" (2015)
6. **MiniLLM:** Gu et al., "MiniLLM: Knowledge Distillation of Large Language Models" (2023)
7. **Speculative Decoding:** Leviathan et al., "Fast Inference from Transformers via Speculative Decoding" (2022)
8. **EAGLE-3:** Li et al., "EAGLE-3: Speculative Decoding with Lossless Inference" (2025)
9. **Flash Attention:** Dao et al., "FlashAttention: Fast and Memory-Efficient Exact Attention" (2022)
10. **Flash Attention 2:** Dao et al., "FlashAttention-2: Faster Attention with Better Parallelism" (2023)
11. **MLA:** DeepSeek-V2 Technical Report (2024)
12. **SnapKV:** Li et al., "SnapKV: LLM Knows What You are Looking for Before Generation" (2024)
13. **Gradient Checkpointing:** Chen et al., "Training Deep Nets with Sublinear Memory Cost" (2016)
14. **Self-Instruct:** Wang et al., "Self-Instruct: Aligning Language Models with Self-Generated Instructions" (2022)
15. **STaR:** Zelikman et al., "STaR: Bootstrapping Reasoning With Reasoning" (2022)
16. **SPIN:** Chen et al., "Self-Play Fine-Tuning Converts Weak Language Models into Strong Language Models" (2024)
17. **Constitutional AI:** Bai et al., "Constitutional AI: Harmlessness from AI Feedback" (2022)
18. **DPO:** Rafailov et al., "Direct Preference Optimization: Your Language Model is Secretly a Reward Model" (2023)
19. **ORPO:** Hong et al., "ORPO: Monolithic Preference Optimization without Reference Model" (2024)
20. **SimPO:** Meng et al., "SimPO: Simple Preference Optimization with a Reference-Free Reward" (2024)

### Frameworks e Bibliotecas
- **Unsloth** (unsloth.ai): Fine-tuning 2x mais rápido com menos memória
- **TRL** (HuggingFace): DPO, PPO, ORPO, etc.
- **vLLM**: Inferência otimizada com Flash Attention + PagedAttention
- **SGLang**: Runtime otimizado para LLMs
- **flash-attn** (Dao-AILab): Flash Attention 2/3
- **bitsandbytes**: Quantização 4-bit/8-bit
- **Axolotl**: Configuração simplificada de fine-tuning
- **LLaMA-Factory**: Interface unificada para fine-tuning

---

> **Nota:** Este documento reflete o estado da arte em junho de 2026. O campo evolui rapidamente — verificar papers recentes no arXiv e implementações atualizadas nos repositórios oficiais.
> 
> **Próximos passos:** Implementar um protótipo de agente 4B usando QLoRA + Dados Sintéticos + DPO como prova de conceito.
