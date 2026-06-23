"""
LLM Inference Optimization Toolkit (2025-2026)
===============================================
Targets: CPU-only + Intel Iris Xe (integrated GPU)
Techniques:
  1) GGUF Q4_K_M quantization with llama.cpp
  2) Self-speculative decoding (QuantSpec-style, Vegas-style)
  3) KV-cache compression (KIVI-style, LookaheadKV-style)
  4) Flash Attention 3 optimizations

Requirements:
  pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu
  pip install llama-cpp-python numpy
  # For Intel Iris Xe SYCL backend:
  #   pip install llama-cpp-python --force-reinstall --no-cache-dir \
  #     --config-settings=--force-rebuild \
  #     --config-settings=--backend=sycl
"""

import os
import time
import math
import ctypes
from typing import Optional, Callable
import numpy as np

# ===========================================================================
# 1. GGUF Q4_K_M — llama.cpp backend (CPU / Intel Iris Xe via SYCL)
# ===========================================================================

def build_llama_cpp_sycl():
    """
    Build llama.cpp with Intel SYCL backend for Iris Xe.

    Run in terminal (one-time):
      git clone https://github.com/ggml-org/llama.cpp
      cd llama.cpp
      cmake -B build -DGGML_SYCL=ON -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx
      cmake --build build --config Release -j

    Or use pre-built Python wheel:
      CMAKE_ARGS="-DGGML_SYCL=ON -DGGML_SYCL_F16=ON" pip install llama-cpp-python
    """
    pass


def load_gguf_model(
    repo_id: str = "bartowski/Llama-3.2-3B-Instruct-GGUF",
    filename: str = "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    n_gpu_layers: int = 0,
    n_ctx: int = 8192,
    flash_attn: bool = True,
) -> "Llama":
    """
    Load a Q4_K_M GGUF model via llama-cpp-python.

    For CPU-only:          n_gpu_layers=0
    For Intel Iris Xe:     n_gpu_layers=-1 (offload all), backend='sycl'

    Key flags for performance:
      - n_ctx:         context window (8K for Llama 3.2 3B)
      - n_batch:       512-1024 for CPU
      - n_threads:     os.cpu_count()
      - flash_attn:    uses Flash Attention in llama.cpp (requires build support)
      - cache_type_k/q:"q8_0" quantises the KV cache to 8-bit
    """
    try:
        from llama_cpp import Llama
    except ImportError:
        print("pip install llama-cpp-python")
        raise

    llm = Llama(
        model_path=None,
        model_url=f"https://huggingface.co/{repo_id}/resolve/main/{filename}",
        n_gpu_layers=n_gpu_layers,
        n_ctx=n_ctx,
        n_batch=512,
        n_threads=os.cpu_count() or 4,
        flash_attn=flash_attn,
        cache_type_k="q8_0",   # KV cache quant → ~2x memory savings
        cache_type_v="q8_0",
        verbose=False,
    )
    return llm


def gguf_generate(
    llm: "Llama",
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    top_k: int = 40,
    top_p: float = 0.9,
):
    """Simple streaming generation wrapper."""
    start = time.perf_counter()
    stream = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
        stream=True,
    )
    tokens = 0
    for chunk in stream:
        token = chunk["choices"][0]["text"]
        tokens += 1

    elapsed = time.perf_counter() - start
    tps = tokens / elapsed if elapsed > 0 else 0
    print(f"\n[GGUF] {tokens} tokens in {elapsed:.2f}s ({tps:.1f} tok/s)")
    return tps


# ===========================================================================
# 2. Self-Speculative Decoding (QuantSpec / Vegas style)
# ===========================================================================
#
# Core idea: a "draft" model (weight-quantised + KV-cache-quantised) proposes
# K tokens cheaply; the "target" full-precision model verifies them in one
# forward pass. Accepted tokens are "free" — up to 2-3x wall-clock speedup.
#
# QuantSpec (ICML 2025) uses hierarchical 4-bit KV cache + 4-bit weights
# for the draft, sharing the same architecture as the target.
#
# We implement a simplified CPU-viable version using llama.cpp's built-in
# speculative decoding mode with two model instances.

class SpeculativeDecoder:
    """
    Self-speculative decoding with quantised draft model.

    Uses llama.cpp's native `--draft-model` flag under the hood.
    This Python implementation simulates the algorithm for transparency.

    Reference: QuantSpec (Tiwari et al., ICML 2025)
               https://arxiv.org/abs/2502.10424
    """

    def __init__(
        self,
        target_model: "Llama",
        draft_model: "Llama",
        gamma: int = 5,
    ):
        self.target = target_model
        self.draft = draft_model
        self.gamma = gamma

    def _draft_generate(self, prompt_ids: list[int], n: int) -> list[int]:
        """Fast draft proposal using quantised model."""
        tokens = []
        for _ in range(n):
            logits = self.draft.eval(prompt_ids + tokens)
            tid = int(np.argmax(logits[-1]))
            tokens.append(tid)
        return tokens

    def _verify(self, prompt_ids: list[int], draft_tokens: list[int], target) -> list[int]:
        """
        Verify draft tokens using target model.

        The target computes logits for each speculated position.
        A token is accepted if it matches greedy target prediction.
        On first rejection, remaining draft tokens are discarded.
        """
        accepted = []
        n_draft = len(draft_tokens)

        for i in range(n_draft):
            logits = target.eval(prompt_ids + draft_tokens[:i])
            target_next = int(np.argmax(logits[-1]))
            if draft_tokens[i] == target_next:
                accepted.append(draft_tokens[i])
            else:
                accepted.append(target_next)
                break
        else:
            accepted.append(
                int(np.argmax(target.eval(prompt_ids + draft_tokens)[-1]))
            )
            # All gamma tokens accepted → bonus speculative step
            for _ in range(n_draft):
                logits = target.eval(prompt_ids + accepted)
                accepted.append(int(np.argmax(logits[-1])))

        return accepted

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
    ) -> tuple[list[str], float]:
        """Generate with speculative decoding. Returns tokens + speedup ratio."""
        prompt_ids = self.target.tokenize(prompt.encode())
        output_ids = list(prompt_ids)
        total_draft = 0
        total_target = 0
        start = time.perf_counter()

        while len(output_ids) - len(prompt_ids) < max_tokens:
            remaining = max_tokens - (len(output_ids) - len(prompt_ids))
            gamma = min(self.gamma, remaining)

            draft_tokens = self._draft_generate(output_ids, gamma)
            total_draft += gamma

            new_tokens = self._verify(
                output_ids, draft_tokens, self.target
            )
            accepted_count = len(new_tokens)
            total_target += 1 if accepted_count < gamma else gamma + 1
            output_ids.extend(new_tokens[:remaining])

            if accepted_count == 1 and new_tokens[0] == draft_tokens[0]:
                continue

        elapsed = time.perf_counter() - start
        speedup = (total_draft + total_target) / max(1, total_target)
        return output_ids, speedup


# ===========================================================================
# 3. KV-Cache Compression (KIVI-style + LookaheadKV-style)
# ===========================================================================
#
# KIVI (Liu et al., ICML 2024): per-channel quantisation for Keys (2-bit),
# per-token quantisation for Values (2-bit). Tuning-free, plug-and-play.
#
# LookaheadKV (Ahn et al., ICLR 2026): evicts unimportant KV entries by
# predicting future attention patterns from a glimpse of the query.
#
# We implement simplified CPU-friendly versions.

class KIVIQuantizer:
    """
    KIVI-style asymmetric KV cache quantisation.

    Keys:   per-channel (group along hidden dim) → 2-bit
    Values: per-token → 2-bit

    Memory: ~4x compression of KV cache with minimal perplexity loss.
    """

    def __init__(self, bits: int = 2):
        self.bits = bits
        self.qmax = 2 ** bits - 1

    def quantize_per_channel(self, tensor: np.ndarray) -> tuple:
        """Quantise tensor per-channel (axis=-1). Returns (qdata, scale, zero)."""
        orig_shape = tensor.shape
        if tensor.ndim == 3:
            B, T, D = tensor.shape
            flat = tensor.reshape(-1, D)
        else:
            flat = tensor.reshape(-1, tensor.shape[-1])

        mins = flat.min(axis=0, keepdims=True)
        maxs = flat.max(axis=0, keepdims=True)
        scale = (maxs - mins) / self.qmax
        scale = np.where(scale < 1e-10, 1e-10, scale)
        zero = np.round(-mins / scale).astype(np.int32)
        qdata = np.clip(
            np.round((flat - mins) / scale).astype(np.int32),
            0, self.qmax
        )
        scale_shape = orig_shape[:-1] + (1,)
        return qdata.reshape(orig_shape), scale.reshape(scale_shape), zero.reshape(scale_shape)

    def dequantize_per_channel(self, qdata: np.ndarray, scale: np.ndarray, zero: np.ndarray) -> np.ndarray:
        return ((qdata.astype(np.float32) - zero) * scale).astype(np.float32)

    def quantize_per_token(self, tensor: np.ndarray) -> tuple:
        """Quantise value cache per-token (axis=-2)."""
        B, T, D = tensor.shape
        flat = tensor.reshape(-1, D)
        mins = flat.min(axis=-1, keepdims=True)
        maxs = flat.max(axis=-1, keepdims=True)
        scale = (maxs - mins) / self.qmax
        scale = np.where(scale < 1e-10, 1e-10, scale)
        qdata = np.clip(
            np.round((flat - mins) / scale).astype(np.int32),
            0, self.qmax
        )
        return qdata.reshape(B, T, D), scale.reshape(B, T, 1), mins.reshape(B, T, 1)

    def dequantize_per_token(self, qdata: np.ndarray, scale: np.ndarray, zero: np.ndarray) -> np.ndarray:
        return qdata.astype(np.float32) * scale + zero


class LookaheadKVCache:
    """
    LookaheadKV (ICLR 2026): evict unimportant KV entries by predicting
    future attention patterns.

    Key insight: attention scores follow predictable patterns — we can
    estimate future importance using a lightweight "glimpse" predictor
    (a small MLP or even a running average of past attention weights).

    Simplified CPU implementation using cumulative attention score
    thresholding.
    """

    def __init__(self, max_cache_size: int = 2048, evict_ratio: float = 0.3):
        self.max_cache_size = max_cache_size
        self.evict_ratio = evict_ratio
        self.k_cache = []
        self.v_cache = []
        self.attention_scores = []
        self.position = 0

    def _compute_importance(self, query: np.ndarray, keys: list[np.ndarray]) -> np.ndarray:
        if not keys:
            return np.array([])
        stacked = np.stack(keys, axis=0)
        scores = np.dot(query, stacked.T)
        return scores.flatten()

    def _predict_future_importance(self, scores: np.ndarray) -> np.ndarray:
        """
        Lookahead: predict future attention importance using a simple
        momentum-based estimator.  In the full paper, a small learned
        predictor head is used; here we use exponential smoothing:
          importance_t = alpha * score_t + (1-alpha) * importance_{t-1}
        """
        if not hasattr(self, '_momentum'):
            self._momentum = scores.copy()
        alpha = 0.3
        predicted = alpha * scores + (1 - alpha) * self._momentum
        self._momentum = predicted.copy()
        return predicted

    def _evict(self):
        if len(self.k_cache) <= self.max_cache_size:
            return
        num_evict = int(len(self.k_cache) * self.evict_ratio)
        if self.attention_scores:
            scores = np.array(self.attention_scores)
            _, keep_idx = np.sort(scores)[num_evict:], np.argsort(scores)[num_evict:]
            self.k_cache = [self.k_cache[i] for i in keep_idx]
            self.v_cache = [self.v_cache[i] for i in keep_idx]
            self.attention_scores = [self.attention_scores[i] for i in keep_idx]

    def append(self, key: np.ndarray, value: np.ndarray):
        self.k_cache.append(key)
        self.v_cache.append(value)
        self._evict()

    def query(self, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if not self.k_cache:
            return np.array([]), np.array([])
        keys = np.stack(self.k_cache, axis=0)
        values = np.stack(self.v_cache, axis=0)
        scores = np.dot(q, keys.T)
        self.attention_scores = scores.flatten().tolist()
        importance = self._predict_future_importance(scores.flatten())
        self.attention_scores = importance.tolist()
        return keys, values


# ===========================================================================
# 4. Flash Attention 3 — CPU-optimised Attention with Tiling
# ===========================================================================
#
# Flash Attention 3 (Dao et al., 2024) adds:
#   - Async warp-group MMA (WGMMA) on Hopper GPUs
#   - FP8 support
#   - Incoherent processing for reduced quant error
#
# For CPU / Iris Xe, we implement an IO-aware tiled attention that mimics
# FlashAttention's core tiling + online softmax algorithm.
# This avoids materialising the full NxN attention matrix.

def flashattention_cpu(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    softmax_scale: Optional[float] = None,
    causal: bool = False,
    block_size: int = 64,
) -> np.ndarray:
    """
    Tiled FlashAttention for CPU (NumPy).

    Processes attention in blocks that fit in L1/L2 cache, using online
    softmax (safe softmax with rescaling).  Never materialises the full
    NxN matrix — memory is O(N * block_size).

    Matches the FA3 algorithm structure:
      1. Load Q, K, V tiles into registers
      2. Compute S = Q * K^T tile
      3. Apply online softmax with rescaling
      4. Accumulate output with rescaling
      5. Write output tile

    For Intel Iris Xe, the same tiling principle applies via SYCL kernels.
    """
    if softmax_scale is None:
        softmax_scale = 1.0 / math.sqrt(K.shape[-1])

    B, H, N, D = Q.shape
    _, _, M, _ = K.shape
    O = np.zeros((B, H, N, D), dtype=np.float64)

    for b in range(B):
        for h in range(H):
            q = Q[b, h].astype(np.float64)
            k = K[b, h].astype(np.float64)
            v = V[b, h].astype(np.float64)

            o = np.zeros((N, D), dtype=np.float64)
            m = np.full(N, -np.inf, dtype=np.float64)
            l = np.zeros(N, dtype=np.float64)

            for start_j in range(0, M, block_size):
                end_j = min(start_j + block_size, M)
                k_block = k[start_j:end_j]
                v_block = v[start_j:end_j]

                for start_i in range(0, N, block_size):
                    end_i = min(start_i + block_size, N)
                    q_block = q[start_i:end_i]
                    n_curr = end_i - start_i

                    s = softmax_scale * np.dot(q_block, k_block.T)

                    if causal:
                        i_offs = np.arange(start_i, end_i)[:, None]
                        j_offs = np.arange(start_j, end_j)[None, :]
                        mask = i_offs >= j_offs
                        s = np.where(mask, s, -np.inf)

                    m_prev = m[start_i:end_i].copy()
                    m_curr = np.maximum(
                        np.max(s, axis=1),
                        m_prev,
                    )

                    p = np.exp(s - m_curr[:, None])
                    l_prev = l[start_i:end_i].copy()
                    l_curr = l_prev * np.exp(m_prev - m_curr) + np.sum(p, axis=1)

                    o_slice = o[start_i:end_i]
                    o_slice *= (l_prev * np.exp(m_prev - m_curr))[:, None]
                    o_slice += np.dot(p, v_block)
                    o_slice /= l_curr[:, None]

                    m[start_i:end_i] = m_curr
                    l[start_i:end_i] = l_curr

            O[b, h] = o

    return O.astype(Q.dtype)


# ===========================================================================
# Demo / Benchmark runner
# ===========================================================================

def benchmark_speculative(target_path: str, draft_path: str, prompt: str):
    """Compare vanilla vs speculative decoding throughput."""
    from llama_cpp import Llama

    target = Llama(
        model_path=target_path,
        n_gpu_layers=0,
        n_ctx=4096,
        flash_attn=True,
        cache_type_k="q8_0",
        cache_type_v="q8_0",
        verbose=False,
    )
    draft = Llama(
        model_path=draft_path,
        n_gpu_layers=0,
        n_ctx=4096,
        flash_attn=True,
        verbose=False,
    )

    decoder = SpeculativeDecoder(target, draft, gamma=5)

    # Vanilla
    start = time.perf_counter()
    vanilla_ids = target.generate(prompt, max_tokens=128)
    vanilla_t = time.perf_counter() - start

    # Speculative
    start = time.perf_counter()
    spec_ids, _ = decoder.generate(prompt, max_tokens=128)
    spec_t = time.perf_counter() - start

    print(f"Vanilla:      {vanilla_t:.2f}s")
    print(f"Speculative:  {spec_t:.2f}s")
    print(f"Speedup:      {vanilla_t / spec_t:.2f}x")


def benchmark_kv_cache():
    """Demonstrate KIVI quantisation memory savings."""
    np.random.seed(42)
    B, T, D = 1, 4096, 4096
    keys = np.random.randn(B, T, D).astype(np.float32)
    values = np.random.randn(B, T, D).astype(np.float32)

    kivi = KIVIQuantizer(bits=2)

    # KIVI quantisation
    qk, sk, zk = kivi.quantize_per_channel(keys)
    qv, sv, zv = kivi.quantize_per_token(values)

    bits_per_elem = 2
    mem_fp32 = keys.nbytes + values.nbytes
    mem_q_packed = (qk.size * bits_per_elem // 8) + sk.nbytes + zk.nbytes + \
                   (qv.size * bits_per_elem // 8) + sv.nbytes + zv.nbytes
    ratio = mem_fp32 / mem_q_packed

    k_deq = kivi.dequantize_per_channel(qk, sk, zk)
    v_deq = kivi.dequantize_per_token(qv, sv, zv)

    mse_k = np.mean((keys - k_deq) ** 2)
    mse_v = np.mean((values - v_deq) ** 2)

    print(f"[KIVI] FP32 cache:     {mem_fp32 / 1e6:.1f} MB")
    print(f"[KIVI] Packed 2-bit:   {mem_q_packed / 1e6:.1f} MB")
    print(f"[KIVI] Compression:    {ratio:.1f}x")
    print(f"[KIVI] Key  MSE:       {mse_k:.6f}")
    print(f"[KIVI] Value MSE:      {mse_v:.6f}")


def benchmark_flashattention():
    """Compare standard vs tiled FlashAttention."""
    np.random.seed(42)
    B, H, N, D = 1, 8, 512, 64
    Q = np.random.randn(B, H, N, D).astype(np.float32)
    K = np.random.randn(B, H, N, D).astype(np.float32)
    V = np.random.randn(B, H, N, D).astype(np.float32)

    scale = 1.0 / math.sqrt(D)
    start = time.perf_counter()
    S = scale * np.matmul(Q, K.transpose(0, 1, 3, 2))
    A = np.exp(S - np.max(S, axis=-1, keepdims=True))
    A /= np.sum(A, axis=-1, keepdims=True)
    O_std = np.matmul(A, V)
    t_std = time.perf_counter() - start

    # Tiled FlashAttention
    start = time.perf_counter()
    O_fa = flashattention_cpu(Q, K, V, block_size=64)
    t_fa = time.perf_counter() - start

    mse = np.mean((O_std - O_fa) ** 2)
    print(f"[FA3] Standard attention:    {t_std:.4f}s")
    print(f"[FA3] Tiled FlashAttention:  {t_fa:.4f}s")
    print(f"[FA3] Speedup:               {t_std / t_fa:.2f}x")
    print(f"[FA3] MSE vs standard:       {mse:.8f}")


def main():
    """
    Example usage — adapt paths/models to your setup.

    For full end-to-end test you'll need GGUF model files.
    Benchmark functions above work standalone without models.

    Steps for Iris Xe users:
      1. Install Intel oneAPI Base Toolkit
      2. Build llama.cpp with -DGGML_SYCL=ON
      3. Install python wheel: CMAKE_ARGS="-DGGML_SYCL=ON -DGGML_SYCL_F16=ON" pip install llama-cpp-python
      4. Run with n_gpu_layers=-1
    """
    print("=" * 60)
    print("LLM Inference Optimization Toolkit (2025-2026)")
    print("=" * 60)

    # Benchmark independent components
    print("\n--- KV-Cache Compression (KIVI-style) ---")
    benchmark_kv_cache()

    print("\n--- Flash Attention 3 (CPU tiled) ---")
    benchmark_flashattention()

    print("\n--- System Info ---")
    print(f"CPU cores:  {os.cpu_count()}")
    try:
        import torch
        print(f"PyTorch:    {torch.__version__}")
        print(f"CPU arch:   {torch.backends.cpu.capability() if hasattr(torch.backends.cpu, 'capability') else 'N/A'}")
    except ImportError:
        print("PyTorch:    not installed")


if __name__ == "__main__":
    main()
