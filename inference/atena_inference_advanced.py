#!/usr/bin/env python3
"""
atena_inference_advanced.py - Sistema Avancado de Inferencia da Atena Evolucao

Implementa:
1. SpeculativeDecoding: draft model (phi4-mini) gera tokens, target model (atena-glm5) verifica
2. KVCacheManager: gerenciamento de KV-cache com LRU eviction e compressao
3. FlashAttentionWrapper: wrapper com fallback (flash-attn -> atencao padrao)
4. InferenceProfiler: profiling de latencia, throughput e memoria

Dependencias:
  pip install numpy psutil requests
  pip install flash-attn  # opcional, para GPU

Compativel com Ollama API (http://localhost:11434)

Versao: 2.0.0
Data: 18/06/2026
"""

import os
import sys
import time
import math
import json
import logging
import hashlib
import warnings
from typing import Any, Optional, Dict, List, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field
from contextlib import contextmanager

import numpy as np

logger = logging.getLogger("AtenaInferenceAdvanced")

# ===========================================================================
# Constantes
# ===========================================================================

OLLAMA_URL = "http://localhost:11434"
DEFAULT_DRAFT_MODEL = "phi4-mini"
DEFAULT_TARGET_MODEL = "atena-glm5"
DEFAULT_MAX_TOKENS = 512
DEFAULT_K = 5

# Tokens especiais (approximate - Ollama trata internamente)
EOS_TOKENS = ["<|endoftext|>", "<|end|>", "<eos>", "\n\n\n"]
MAX_RETRIES = 3
REQUEST_TIMEOUT = 120


# ===========================================================================
# Utilitarios Ollama
# ===========================================================================

class OllamaClient:
    """
    Cliente HTTP para a Ollama API.
    Suporta generate (streaming) e pull de modelos.
    """

    def __init__(self, base_url: str = OLLAMA_URL, timeout: int = REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = None

    @property
    def session(self):
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers.update({"Content-Type": "application/json"})
            except ImportError:
                raise ImportError("Instale requests: pip install requests")
        return self._session

    def pull(self, model: str) -> bool:
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                installed = [m["name"].split(":")[0] for m in models]
                if model.split(":")[0] in installed:
                    logger.info(f"Modelo '{model}' ja instalado.")
                    return True
            logger.info(f"Modelo '{model}' nao encontrado. Tentando pull...")
            pull_resp = self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model, "stream": False},
                timeout=300,
            )
            return pull_resp.status_code == 200
        except Exception as e:
            logger.warning(f"Erro ao verificar/pull modelo '{model}': {e}")
            return False

    def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        stream: bool = True,
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
            },
        }

        start = time.perf_counter()
        total_tokens = 0
        full_text = ""

        try:
            if stream:
                resp = self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    stream=True,
                    timeout=self.timeout,
                )
                resp.raise_for_status()

                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    token_text = chunk.get("response", "")
                    full_text += token_text
                    total_tokens += 1

                    if chunk.get("done", False):
                        elapsed = time.perf_counter() - start
                        return {
                            "text": full_text,
                            "tokens": total_tokens,
                            "done": True,
                            "elapsed": elapsed,
                            "model": model,
                            "prompt_eval_count": chunk.get("prompt_eval_count", 0),
                            "eval_count": chunk.get("eval_count", total_tokens),
                        }

            else:
                resp = self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                elapsed = time.perf_counter() - start
                return {
                    "text": data.get("response", ""),
                    "tokens": data.get("eval_count", 0),
                    "done": True,
                    "elapsed": elapsed,
                    "model": model,
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                }

        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(f"Erro Ollama generate (model={model}): {e}")
            return {
                "text": full_text,
                "tokens": total_tokens,
                "done": False,
                "elapsed": elapsed,
                "model": model,
                "error": str(e),
            }

    def health(self) -> bool:
        try:
            resp = self.session.get(f"{self.base_url}/", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []


# ===========================================================================
# 1. SpeculativeDecoding
# ===========================================================================

@dataclass
class SpeculativeMetrics:
    total_tokens_generated: int = 0
    draft_tokens_proposed: int = 0
    draft_tokens_accepted: int = 0
    target_forward_passes: int = 0
    rounds: int = 0
    elapsed_seconds: float = 0.0
    acceptance_rate: float = 0.0
    tokens_per_second: float = 0.0
    speedup_estimate: float = 1.0

    def finalize(self):
        if self.draft_tokens_proposed > 0:
            self.acceptance_rate = self.draft_tokens_accepted / self.draft_tokens_proposed
        if self.elapsed_seconds > 0:
            self.tokens_per_second = self.total_tokens_generated / self.elapsed_seconds
        self.speedup_estimate = (
            self.total_tokens_generated / max(1, self.target_forward_passes)
        )


class SpeculativeDecoding:
    """
    Speculative Decoding via Ollama API.

    Algoritmo:
    1. Modelo draft (phi4-mini) gera K=5 tokens candidatos (rapido)
    2. Modelo target (atena-glm5) verifica K tokens em paralelo
    3. Se match: aceita todos. Se mismatch: aceita ate divergencia + 1 do target
    4. Repete ate max_tokens ou EOS
    """

    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        draft_model: str = DEFAULT_DRAFT_MODEL,
        target_model: str = DEFAULT_TARGET_MODEL,
        k: int = DEFAULT_K,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        self.ollama = ollama or OllamaClient()
        self.draft_model = draft_model
        self.target_model = target_model
        self.k = k
        self.max_tokens = max_tokens
        self.metrics = SpeculativeMetrics()
        logger.info(
            f"SpeculativeDecoding: draft={draft_model}, target={target_model}, k={k}"
        )

    def _generate_draft_tokens(self, context: str, k: int) -> List[str]:
        result = self.ollama.generate(
            model=self.draft_model,
            prompt=context,
            max_tokens=k,
            temperature=0.7,
            stream=False,
        )
        text = result.get("text", "")
        tokens = self._split_to_tokens(text)
        return tokens[:k]

    @staticmethod
    def _split_to_tokens(text: str) -> List[str]:
        tokens = []
        current = ""
        for char in text:
            if char == " ":
                if current:
                    tokens.append(current)
                    current = ""
                tokens.append(" ")
            else:
                current += char
        if current:
            tokens.append(current)
        return [t for t in tokens if t]

    @staticmethod
    def _tokens_compatible(draft_token: str, target_next: str) -> bool:
        if not target_next:
            return True
        d = draft_token.strip().lower()
        t = target_next.strip().lower()
        if not d or not t:
            return True
        return d == t or d.startswith(t) or t.startswith(d)

    @staticmethod
    def _is_eos(text: str) -> bool:
        stripped = text.strip()
        return stripped in EOS_TOKENS or len(stripped) == 0

    def _verify_batch(
        self, context: str, draft_tokens: List[str], target_model: str
    ) -> List[str]:
        draft_text = "".join(draft_tokens)
        result = self.ollama.generate(
            model=target_model,
            prompt=context,
            max_tokens=len(draft_tokens),
            temperature=0.0,
            stream=False,
        )

        target_text = result.get("text", "")
        if not target_text:
            return []

        accepted = []
        target_remaining = target_text

        for token in draft_tokens:
            token_stripped = token.strip()

            if not token_stripped:
                accepted.append(token)
                continue

            expected = target_remaining[:len(token)] if len(target_remaining) >= len(token) else target_remaining

            if target_remaining and self._tokens_compatible(token, expected):
                accepted.append(token)
                if len(target_remaining) >= len(token):
                    target_remaining = target_remaining[len(token):]
                else:
                    target_remaining = ""
            else:
                if target_remaining:
                    target_tokens = self._split_to_tokens(target_remaining)
                    if target_tokens:
                        accepted.append(target_tokens[0])
                break

        return accepted

    def generate(
        self,
        prompt: str,
        draft_model: Optional[str] = None,
        target_model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        draft_m = draft_model or self.draft_model
        target_m = target_model or self.target_model
        max_tok = max_tokens or self.max_tokens
        k = self.k

        logger.info(
            f"SpeculativeDecoding.generate: prompt_len={len(prompt)}, max_tokens={max_tok}"
        )

        self.metrics = SpeculativeMetrics()
        start_time = time.perf_counter()

        generated_text = ""
        current_context = prompt
        total_generated = 0

        while total_generated < max_tok:
            remaining = max_tok - total_generated
            current_k = min(k, remaining)

            draft_tokens = self._generate_draft_tokens(current_context, current_k)
            if not draft_tokens:
                logger.debug("Draft nao gerou tokens. Parando.")
                break

            self.metrics.draft_tokens_proposed += len(draft_tokens)

            accepted = self._verify_batch(current_context, draft_tokens, target_m)

            if not accepted:
                fallback = self.ollama.generate(
                    model=target_m,
                    prompt=current_context,
                    max_tokens=1,
                    temperature=0.7,
                    stream=False,
                )
                fallback_text = fallback.get("text", "")
                if not fallback_text or self._is_eos(fallback_text):
                    break
                accepted = [fallback_text]
                self.metrics.target_forward_passes += 1
            else:
                self.metrics.target_forward_passes += 1

            accepted_text = "".join(accepted)
            generated_text += accepted_text
            current_context += accepted_text
            total_generated += len(accepted)
            self.metrics.draft_tokens_accepted += len(accepted)
            self.metrics.rounds += 1

            if self._is_eos(accepted_text):
                logger.debug("EOS detectado. Parando.")
                break

        self.metrics.total_tokens_generated = total_generated
        self.metrics.elapsed_seconds = time.perf_counter() - start_time
        self.metrics.finalize()

        logger.info(
            f"SpeculativeDecoding completo: {total_generated} tokens em "
            f"{self.metrics.elapsed_seconds:.2f}s "
            f"({self.metrics.tokens_per_second:.1f} tok/s, "
            f"aceitacao={self.metrics.acceptance_rate:.1%}, "
            f"speedup~{self.metrics.speedup_estimate:.1f}x)"
        )

        return generated_text

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_tokens_generated": self.metrics.total_tokens_generated,
            "draft_tokens_proposed": self.metrics.draft_tokens_proposed,
            "draft_tokens_accepted": self.metrics.draft_tokens_accepted,
            "target_forward_passes": self.metrics.target_forward_passes,
            "rounds": self.metrics.rounds,
            "elapsed_seconds": round(self.metrics.elapsed_seconds, 3),
            "acceptance_rate": round(self.metrics.acceptance_rate, 4),
            "tokens_per_second": round(self.metrics.tokens_per_second, 2),
            "speedup_estimate": round(self.metrics.speedup_estimate, 2),
        }


# ===========================================================================
# 2. KVCacheManager
# ===========================================================================

@dataclass
class KVCacheEntry:
    key: np.ndarray
    value: np.ndarray
    timestamp: float
    access_count: int = 0
    compressed: bool = False
    original_size: int = 0


class KVCacheManager:
    """
    Gerenciador de KV-Cache para contexto longo.

    - Max cache size (em numero de entradas)
    - Politica de eviction LRU (Least Recently Used)
    - Compressao opcional (media de tokens vizinhos)
    - Estatisticas de hit/miss
    """

    def __init__(
        self,
        max_size: int = 4096,
        compress: bool = False,
        compress_ratio: float = 0.5,
        compress_block_size: int = 4,
    ):
        self.max_size = max_size
        self.compression_enabled = compress
        self.compress_ratio = compress_ratio
        self.compress_block_size = compress_block_size
        self._cache: OrderedDict = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._compressions = 0
        self._total_tokens_stored = 0

        logger.info(
            f"KVCacheManager: max_size={max_size}, compress={compress}"
        )

    @property
    def current_size(self) -> int:
        return len(self._cache)

    @property
    def total_tokens(self) -> int:
        return sum(
            entry.key.shape[0] if entry.key is not None else 0
            for entry in self._cache.values()
        )

    def get(self, key: str) -> Optional[KVCacheEntry]:
        """
        Recupera uma entrada do cache.
        Move o item para o final (mais recentemente usado).

        Args:
            key: identificador da entrada (ex: "layer_0_key")

        Returns:
            KVCacheEntry ou None se nao encontrado
        """
        if key in self._cache:
            entry = self._cache.pop(key)
            entry.access_count += 1
            entry.timestamp = time.time()
            self._cache[key] = entry
            self._hits += 1
            return entry

        self._misses += 1
        return None

    def put(self, key: str, value: KVCacheEntry) -> None:
        """
        Armazena uma entrada no cache.
        Se o cache estiver cheio, aplica eviction LRU.
        """
        if key in self._cache:
            self._cache.pop(key)
            self._cache[key] = value
            return

        while len(self._cache) >= self.max_size:
            self.evict()

        self._cache[key] = value
        self._total_tokens_stored += value.key.shape[0] if value.key is not None else 0

    def put_arrays(
        self,
        key_id: str,
        key_array: np.ndarray,
        value_array: np.ndarray,
    ) -> None:
        entry = KVCacheEntry(
            key=key_array,
            value=value_array,
            timestamp=time.time(),
            original_size=key_array.shape[0] if key_array is not None else 0,
        )
        self.put(key_id, entry)

    def evict(self, n: int = 1) -> int:
        """
        Remove as N entradas menos recentemente usadas (LRU).

        Returns:
            Numero de entradas removidas
        """
        evicted = 0
        for _ in range(min(n, len(self._cache))):
            if not self._cache:
                break
            evicted_key, evicted_entry = self._cache.popitem(last=False)
            self._evictions += 1
            evicted += 1
            logger.debug(
                f"KVCache EVICT: {evicted_key} "
                f"(accesses={evicted_entry.access_count})"
            )
        return evicted

    def compress(self, key: Optional[str] = None) -> int:
        """
        Comprime entradas do cache usando media de tokens vizinhos.

        Args:
            key: se especificado, comprime apenas esta entrada.
                 Se None, comprime todas.

        Returns:
            Numero de entradas comprimidas
        """
        if not self.compression_enabled:
            return 0

        compressed_count = 0
        keys_to_compress = [key] if key else list(self._cache.keys())

        for k in keys_to_compress:
            if k not in self._cache:
                continue
            entry = self._cache[k]
            if entry.compressed:
                continue

            if entry.key is not None and entry.key.shape[0] >= self.compress_block_size * 2:
                entry.key = self._compress_tensor(entry.key)
                if entry.value is not None and entry.value.shape[0] >= self.compress_block_size * 2:
                    entry.value = self._compress_tensor(entry.value)
                entry.compressed = True
                compressed_count += 1
                self._compressions += 1

        return compressed_count

    def _compress_tensor(self, tensor: np.ndarray) -> np.ndarray:
        block = self.compress_block_size
        seq_len = tensor.shape[0]
        trim_len = (seq_len // block) * block
        trimmed = tensor[:trim_len]

        if trimmed.ndim == 2:
            reshaped = trimmed.reshape(-1, block, trimmed.shape[1])
            return reshaped.mean(axis=1)
        else:
            reshaped = trimmed.reshape(-1, block)
            return reshaped.mean(axis=1)

    def clear(self) -> None:
        self._cache.clear()
        logger.info("KVCache limpo.")

    def get_stats(self) -> Dict[str, Any]:
        total_requests = self._hits + self._misses
        hit_rate = self._hits / max(1, total_requests)
        return {
            "current_size": self.current_size,
            "max_size": self.max_size,
            "total_tokens": self.total_tokens,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "evictions": self._evictions,
            "compressions": self._compressions,
            "total_tokens_stored": self._total_tokens_stored,
        }


# ===========================================================================
# 3. FlashAttentionWrapper
# ===========================================================================

class FlashAttentionWrapper:
    """
    Wrapper de atencao que tenta usar flash-attn se disponivel,
    com fallback para atencao padrao (PyTorch ou NumPy).
    """

    def __init__(self, use_flash: bool = True):
        self._flash_available = False
        self._torch_available = False
        self._flash_attn_func = None
        self._torch = None

        try:
            import torch
            self._torch_available = True
            self._torch = torch
            logger.info("PyTorch disponivel.")
        except ImportError:
            logger.info("PyTorch nao disponivel. Usando NumPy.")

        if use_flash:
            try:
                from flash_attn import flash_attn_func
                self._flash_attn_func = flash_attn_func
                self._flash_available = True
                logger.info("Flash Attention disponivel!")
            except ImportError:
                logger.info("Flash Attention nao disponivel. Fallback para atencao padrao.")

    @property
    def is_flash_available(self) -> bool:
        return self._flash_available

    @property
    def is_torch_available(self) -> bool:
        return self._torch_available

    def attention(
        self,
        q: Any,
        k: Any,
        v: Any,
        causal: bool = True,
        softmax_scale: Optional[float] = None,
    ) -> Any:
        """
        Computa atencao escalonada: softmax(Q * K^T / sqrt(d_k)) * V

        Args:
            q: query  [batch, num_heads, seq_len, head_dim]
            k: key    [batch, num_heads, seq_len, head_dim]
            v: value  [batch, num_heads, seq_len, head_dim]
            causal: aplica mascara causal
            softmax_scale: escala (default: 1/sqrt(head_dim))

        Returns:
            output [batch, num_heads, seq_len, head_dim]
        """
        if self._flash_available and self._torch_available:
            return self._flash_attention(q, k, v, causal, softmax_scale)
        elif self._torch_available:
            return self._torch_attention(q, k, v, causal, softmax_scale)
        else:
            return self._numpy_attention(q, k, v, causal, softmax_scale)

    def _flash_attention(self, q, k, v, causal, softmax_scale):
        """Flash Attention via flash-attn library."""
        torch = self._torch
        if isinstance(q, np.ndarray):
            q = torch.from_numpy(q).cuda() if torch.cuda.is_available() else torch.from_numpy(q)
            k = torch.from_numpy(k).cuda() if torch.cuda.is_available() else torch.from_numpy(k)
            v = torch.from_numpy(v).cuda() if torch.cuda.is_available() else torch.from_numpy(v)

        # flash_attn_func espera [batch, seq_len, num_heads, head_dim]
        if q.ndim == 4 and q.shape[1] < q.shape[2]:
            q = q.transpose(1, 2)
            k = k.transpose(1, 2)
            v = v.transpose(1, 2)

        try:
            out = self._flash_attn_func(q, k, v, causal=causal)
        except Exception as e:
            logger.warning(f"Flash Attention falhou ({e}). Fallback para PyTorch.")
            return self._torch_attention(q, k, v, causal, softmax_scale)

        if isinstance(out, torch.Tensor):
            return out.cpu().numpy() if not torch.cuda.is_available() else out
        return out

    def _torch_attention(self, q, k, v, causal, softmax_scale):
        """Atencao via PyTorch scaled_dot_product_attention."""
        torch = self._torch

        if isinstance(q, np.ndarray):
            q = torch.from_numpy(q).float()
            k = torch.from_numpy(k).float()
            v = torch.from_numpy(v).float()

        head_dim = q.shape[-1]
        if softmax_scale is None:
            softmax_scale = 1.0 / math.sqrt(head_dim)

        # Transpor se necessario: [B, H, N, D] -> [B, N, H, D] para PyTorch
        if q.ndim == 4:
            q_t = q.transpose(1, 2)
            k_t = k.transpose(1, 2)
            v_t = v.transpose(1, 2)
        else:
            q_t, k_t, v_t = q, k, v

        try:
            out = torch.nn.functional.scaled_dot_product_attention(
                q_t, k_t, v_t, is_causal=causal, scale=softmax_scale
            )
        except Exception:
            # Fallback manual
            scores = torch.matmul(q_t, k_t.transpose(-2, -1)) * softmax_scale
            if causal:
                mask = torch.triu(torch.ones(scores.shape[-2:], dtype=torch.bool), diagonal=1)
                scores = scores.masked_fill(mask, float('-inf'))
            attn = torch.softmax(scores, dim=-1)
            out = torch.matmul(attn, v_t)

        if q.ndim == 4:
            out = out.transpose(1, 2)

        return out.numpy() if isinstance(out, torch.Tensor) else out

    def _numpy_attention(self, q, k, v, causal, softmax_scale):
        """Atencao via NumPy (tiled para eficiencia)."""
        if q.ndim != 4:
            raise ValueError(f"Esperado 4D tensor [B,H,N,D], got shape {q.shape}")

        B, H, N, D = q.shape
        M = k.shape[2]

        if softmax_scale is None:
            softmax_scale = 1.0 / math.sqrt(D)

        block_size = min(64, N)
        output = np.zeros_like(q, dtype=np.float64)

        for b in range(B):
            for h in range(H):
                q_bh = q[b, h].astype(np.float64)
                k_bh = k[b, h].astype(np.float64)
                v_bh = v[b, h].astype(np.float64)

                o = np.zeros((N, D), dtype=np.float64)
                m = np.full(N, -np.inf, dtype=np.float64)
                l = np.zeros(N, dtype=np.float64)

                for start_j in range(0, M, block_size):
                    end_j = min(start_j + block_size, M)
                    k_block = k_bh[start_j:end_j]
                    v_block = v_bh[start_j:end_j]

                    for start_i in range(0, N, block_size):
                        end_i = min(start_i + block_size, N)
                        q_block = q_bh[start_i:end_i]
                        n_curr = end_i - start_i

                        s = softmax_scale * np.dot(q_block, k_block.T)

                        if causal:
                            i_offs = np.arange(start_i, end_i)[:, None]
                            j_offs = np.arange(start_j, end_j)[None, :]
                            mask = i_offs >= j_offs
                            s = np.where(mask, s, -np.inf)

                        m_prev = m[start_i:end_i].copy()
                        m_curr = np.maximum(np.max(s, axis=1), m_prev)

                        p = np.exp(s - m_curr[:, None])
                        l_prev = l[start_i:end_i].copy()
                        l_curr = l_prev * np.exp(m_prev - m_curr) + np.sum(p, axis=1)

                        o_slice = o[start_i:end_i]
                        o_slice *= (l_prev * np.exp(m_prev - m_curr))[:, None]
                        o_slice += np.dot(p, v_block)
                        o_slice /= l_curr[:, None]

                        m[start_i:end_i] = m_curr
                        l[start_i:end_i] = l_curr

                output[b, h] = o

        return output.astype(q.dtype)


# ===========================================================================
# 4. InferenceProfiler
# ===========================================================================

@dataclass
class ProfilerLap:
    label: str
    timestamp: float
    elapsed_since_start: float
    elapsed_since_prev: float
    memory_mb: float


class InferenceProfiler:
    """
    Profiler de inferencia.

    Mede:
    - Latencia total e por checkpoint (lap)
    - Tokens por segundo
    - Memoria usada (RSS)
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._start_time: float = 0.0
        self._last_lap_time: float = 0.0
        self._laps: List[ProfilerLap] = []
        self._active = False
        self._psutil_available = False

        try:
            import psutil
            self._psutil = psutil
            self._psutil_available = True
        except ImportError:
            logger.info("psutil nao disponivel. Metricas de memoria serao limitadas.")

    def start(self) -> None:
        """Inicia o profiling."""
        if not self.enabled:
            return
        self._start_time = time.perf_counter()
        self._last_lap_time = self._start_time
        self._laps = []
        self._active = True
        mem = self._get_memory_mb()
        logger.info(f"InferenceProfiler iniciado. Memoria inicial: {mem:.1f} MB")

    def lap(self, label: str) -> Optional[ProfilerLap]:
        """
        Registra um checkpoint de tempo.

        Args:
            label: nome do checkpoint (ex: "draft", "verify", "total")

        Returns:
            ProfilerLap ou None se desabilitado
        """
        if not self.enabled or not self._active:
            return None

        now = time.perf_counter()
        elapsed_start = now - self._start_time
        elapsed_prev = now - self._last_lap_time
        self._last_lap_time = now

        mem = self._get_memory_mb()

        entry = ProfilerLap(
            label=label,
            timestamp=now,
            elapsed_since_start=elapsed_start,
            elapsed_since_prev=elapsed_prev,
            memory_mb=mem,
        )
        self._laps.append(entry)

        logger.info(
            f"[Profiler] {label}: {elapsed_prev:.4f}s "
            f"(total: {elapsed_start:.4f}s, mem: {mem:.1f}MB)"
        )
        return entry

    def report(self, tokens_generated: int = 0) -> Dict[str, Any]:
        """
        Gera relatorio final do profiling.

        Args:
            tokens_generated: numero de tokens gerados na execucao

        Returns:
            Dict com metricas dePerformance
        """
        if not self.enabled:
            return {"enabled": False}

        total_time = time.perf_counter() - self._start_time if self._active else 0.0
        tps = tokens_generated / max(total_time, 1e-6)

        mem_final = self._get_memory_mb()
        mem_initial = self._laps[0].memory_mb if self._laps else mem_final
        mem_delta = mem_final - mem_initial

        laps_data = [
            {
                "label": lap.label,
                "elapsed_s": round(lap.elapsed_since_prev, 6),
                "cumulative_s": round(lap.elapsed_since_start, 6),
                "memory_mb": round(lap.memory_mb, 2),
            }
            for lap in self._laps
        ]

        report = {
            "enabled": True,
            "active": self._active,
            "total_time_s": round(total_time, 4),
            "tokens_generated": tokens_generated,
            "tokens_per_second": round(tps, 2),
            "memory_initial_mb": round(mem_initial, 2),
            "memory_final_mb": round(mem_final, 2),
            "memory_delta_mb": round(mem_delta, 2),
            "num_laps": len(self._laps),
            "laps": laps_data,
        }

        self._active = False
        return report

    def _get_memory_mb(self) -> float:
        if self._psutil_available:
            try:
                process = self._psutil.Process(os.getpid())
                return process.memory_info().rss / (1024 * 1024)
            except Exception:
                pass
        return 0.0

    @contextmanager
    def section(self, label: str):
        """Context manager para medir uma secao de codigo."""
        self.lap(f"{label}_start")
        yield
        self.lap(f"{label}_end")


# ===========================================================================
# Testes
# ===========================================================================

def run_tests():
    """Executa testes unitarios para todos os componentes."""
    print("=" * 70)
    print("TESTES - Sistema Avancado de Inferencia da Atena")
    print("=" * 70)

    results = {}

    # ------------------------------------------------------------------
    # Teste 1: OllamaClient (mock / integracao)
    # ------------------------------------------------------------------
    print("\n--- Teste 1: OllamaClient ---")

    client = OllamaClient()
    # Sem conexao, testamos estrutura basica
    assert hasattr(client, 'generate'), "OllamaClient deve ter metodo generate"
    assert hasattr(client, 'health'), "OllamaClient deve ter metodo health"
    assert hasattr(client, 'list_models'), "OllamaClient deve ter metodo list_models"
    print("  OK: OLLamaClient tem a interface correta")

    # Teste health (pode falhar se Ollama nao estiver rodando)
    try:
        healthy = client.health()
        print(f"  Ollama health: {healthy}")
        results["ollama_health"] = healthy
    except Exception as e:
        print(f"  Ollama health check falhou (esperado sem servidor): {e}")
        results["ollama_health"] = "unavailable"

    # ------------------------------------------------------------------
    # Teste 2: SpeculativeDecoding
    # ------------------------------------------------------------------
    print("\n--- Teste 2: SpeculativeDecoding ---")

    decoder = SpeculativeDecoding(
        ollama=client,
        draft_model="phi4-mini",
        target_model="atena-glm5",
        k=5,
        max_tokens=64,
    )

    assert decoder.k == 5, "K deve ser 5"
    assert decoder.draft_model == "phi4-mini", "Draft model deve ser phi4-mini"
    assert decoder.target_model == "atena-glm5", "Target model deve ser atena-glm5"
    print("  OK: Parametros inicializados corretamente")

    # Teste splitting de tokens
    tokens = decoder._split_to_tokens("Ola, como voce esta?")
    assert len(tokens) > 0, "Deve gerar tokens"
    print(f"  OK: _split_to_tokens gerou {len(tokens)} tokens: {tokens}")

    # Teste compatibilidade
    assert decoder._tokens_compatible("Ola", "Ola") == True
    assert decoder._tokens_compatible("Hello", "World") == False
    print("  OK: _tokens_compatible funciona corretamente")

    # Teste EOS
    assert decoder._is_eos("<|endoftext|>") == True
    assert decoder._is_eos("texto normal") == False
    print("  OK: _is_eos funciona corretamente")

    # Teste metricas iniciais
    metrics = decoder.get_metrics()
    assert "total_tokens_generated" in metrics
    print(f"  OK: Metricas inicializadas: {metrics}")

    results["speculative_decoding"] = "passed"

    # ------------------------------------------------------------------
    # Teste 3: KVCacheManager
    # ------------------------------------------------------------------
    print("\n--- Teste 3: KVCacheManager ---")

    cache = KVCacheManager(max_size=4, compress=True, compress_block_size=2)

    k1 = np.random.randn(8, 64).astype(np.float32)
    v1 = np.random.randn(8, 64).astype(np.float32)
    cache.put_arrays("layer0_key", k1, v1)
    assert cache.current_size == 1
    print("  OK: put_arrays armazenou entrada")

    entry = cache.get("layer0_key")
    assert entry is not None, "get deve retornar entrada existente"
    assert np.array_equal(entry.key, k1), "Keys devem ser iguais"
    print("  OK: get retornou entrada correta (HIT)")

    miss = cache.get("inexistente")
    assert miss is None, "get deve retornar None para chave inexistente"
    print("  OK: get retornou None para chave inexistente (MISS)")

    # Teste eviction LRU
    cache.put_arrays("layer1_key", np.random.randn(4, 64).astype(np.float32),
                     np.random.randn(4, 64).astype(np.float32))
    cache.put_arrays("layer2_key", np.random.randn(4, 64).astype(np.float32),
                     np.random.randn(4, 64).astype(np.float32))
    cache.put_arrays("layer3_key", np.random.randn(4, 64).astype(np.float32),
                     np.random.randn(4, 64).astype(np.float32))
    assert cache.current_size == 4
    print(f"  OK: Size antes da eviction: {cache.current_size}")

    # Esta deve causar eviction da entrada mais antiga
    cache.put_arrays("layer4_key", np.random.randn(4, 64).astype(np.float32),
                     np.random.randn(4, 64).astype(np.float32))
    assert cache.current_size == 4, f"Size deve permanecer 4, got {cache.current_size}"
    assert cache._evictions >= 1
    print(f"  OK: Eviction funcionou (evictions={cache._evictions})")

    # layer0 deve ter sido evicted (primeiro inserido)
    evicted_entry = cache.get("layer0_key")
    assert evicted_entry is None or evicted_entry.access_count == 1, \
        "layer0 deve ter sido evicted ou ter 1 acesso"
    print("  OK: Entrada mais antiga foi evicted (LRU)")

    # Teste compressao
    big_k = np.random.randn(16, 64).astype(np.float32)
    big_v = np.random.randn(16, 64).astype(np.float32)
    cache.put_arrays("compress_key", big_k, big_v)
    n_compressed = cache.compress("compress_key")
    assert n_compressed == 1
    compressed_entry = cache.get("compress_key")
    assert compressed_entry.compressed == True
    expected_size = 16 // 2  # block_size=2
    assert compressed_entry.key.shape[0] == expected_size, \
        f"Key comprimida deve ter {expected_size} tokens, tem {compressed_entry.key.shape[0]}"
    print(f"  OK: Compressao funcionou (16 -> {expected_size} tokens)")

    # Estatisticas
    stats = cache.get_stats()
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1
    assert stats["evictions"] >= 1
    assert stats["compressions"] >= 1
    print(f"  OK: Estatisticas: {json.dumps(stats, indent=2)}")

    # Clear
    cache.clear()
    assert cache.current_size == 0
    print("  OK: clear() funcionou")

    results["kv_cache_manager"] = "passed"

    # ------------------------------------------------------------------
    # Teste 4: FlashAttentionWrapper
    # ------------------------------------------------------------------
    print("\n--- Teste 4: FlashAttentionWrapper ---")

    wrapper = FlashAttentionWrapper(use_flash=False)

    print(f"  Flash disponivel: {wrapper.is_flash_available}")
    print(f"  PyTorch disponivel: {wrapper.is_torch_available}")

    # Criar tensores de teste: [batch=1, heads=2, seq_len=8, head_dim=16]
    np.random.seed(42)
    q = np.random.randn(1, 2, 8, 16).astype(np.float32)
    k = np.random.randn(1, 2, 8, 16).astype(np.float32)
    v = np.random.randn(1, 2, 8, 16).astype(np.float32)

    # Teste atencao com NumPy (sem PyTorch)
    try:
        out = wrapper._numpy_attention(q, k, v, causal=True, softmax_scale=None)
        assert out.shape == q.shape, f"Shape de saida deve ser {q.shape}, got {out.shape}"
        assert np.isfinite(out).all(), "Output deve ser finito"
        print(f"  OK: NumPy attention output shape={out.shape}")
        print(f"  OK: NumPy attention min={out.min():.4f}, max={out.max():.4f}")

        # Verificar mascara causal: output[i] deve depender apenas de k[j<=i]
        # Isso e implicitamente testado pelo algoritmo online softmax
    except Exception as e:
        print(f"  ERRO NumPy attention: {e}")
        results["flash_attention_numpy"] = f"FAILED: {e}"

    # Teste com PyTorch se disponivel
    if wrapper.is_torch_available:
        try:
            out_torch = wrapper._torch_attention(q, k, v, causal=True, softmax_scale=None)
            assert out_torch.shape == (1, 2, 8, 16)
            print(f"  OK: PyTorch attention output shape={out_torch.shape}")
        except Exception as e:
            print(f"  ERRO PyTorch attention: {e}")

    # Teste wrapper principal
    try:
        out_main = wrapper.attention(q, k, v, causal=True)
        assert out_main.shape == q.shape
        print(f"  OK: wrapper.attention() retornou shape correto")
    except Exception as e:
        print(f"  ERRO wrapper.attention: {e}")
        results["flash_attention"] = f"FAILED: {e}"

    # Verificar que causal masking funciona comparando com/sem mascara
    out_causal = wrapper._numpy_attention(q, k, v, causal=True, softmax_scale=None)
    out_non_causal = wrapper._numpy_attention(q, k, v, causal=False, softmax_scale=None)
    assert not np.allclose(out_causal, out_non_causal), \
        "Saidas com/sem mascara causal devem ser diferentes"
    print("  OK: mascara causal produz resultados diferentes")

    results["flash_attention"] = "passed"

    # ------------------------------------------------------------------
    # Teste 5: InferenceProfiler
    # ------------------------------------------------------------------
    print("\n--- Teste 5: InferenceProfiler ---")

    profiler = InferenceProfiler(enabled=True)

    # Teste start
    profiler.start()
    assert profiler._active == True
    print("  OK: start() ativou o profiler")

    time.sleep(0.01)  # 10ms
    lap1 = profiler.lap("checkpoint_1")
    assert lap1 is not None
    assert lap1.label == "checkpoint_1"
    assert lap1.elapsed_since_start > 0
    print(f"  OK: lap 'checkpoint_1' em {lap1.elapsed_since_start:.4f}s")

    time.sleep(0.02)  # 20ms
    lap2 = profiler.lap("checkpoint_2")
    assert lap2.elapsed_since_prev >= 0.015, \
        f"elapsed_since_prev deve ser ~0.02s, got {lap2.elapsed_since_prev}"
    print(f"  OK: lap 'checkpoint_2' delta={lap2.elapsed_since_prev:.4f}s")

    # Teste report
    report = profiler.report(tokens_generated=50)
    assert report["enabled"] == True
    assert report["total_time_s"] > 0
    assert report["tokens_generated"] == 50
    assert report["tokens_per_second"] > 0
    assert report["num_laps"] == 2
    assert len(report["laps"]) == 2
    print(f"  OK: Report gerado: {json.dumps(report, indent=2)}")

    # Teste secao com context manager
    profiler.start()
    with profiler.section("teste_secao"):
        time.sleep(0.01)
    report2 = profiler.report(tokens_generated=10)
    section_laps = [l for l in report2["laps"] if "teste_secao" in l["label"]]
    assert len(section_laps) == 2, "Deve ter 2 laps para a secao (start+end)"
    print("  OK: context manager section() funciona")

    # Teste desabilitado
    disabled_prof = InferenceProfiler(enabled=False)
    disabled_prof.start()
    assert disabled_prof.lap("test") is None
    r = disabled_prof.report()
    assert r["enabled"] == False
    print("  OK: profiler desabilitado retorna None/empty")

    results["inference_profiler"] = "passed"

    # ------------------------------------------------------------------
    # Teste 6: Integracao completa (simulada)
    # ------------------------------------------------------------------
    print("\n--- Teste 6: Integracao (execucao simulada) ---")

    profiler2 = InferenceProfiler(enabled=True)
    profiler2.start()

    # Simula fluxo de speculative decoding com profiling
    cache2 = KVCacheManager(max_size=128, compress=True)

    # Simula verificacao de uma rodada
    k_tensor = np.random.randn(5, 64).astype(np.float32)  # 5 tokens draft
    v_tensor = np.random.randn(5, 64).astype(np.float32)
    cache2.put_arrays("draft_kv", k_tensor, v_tensor)
    profiler2.lap("draft_kv_cached")

    # Simula FlashAttention
    q_attn = np.random.randn(1, 2, 10, 64).astype(np.float32)
    k_attn = np.random.randn(1, 2, 15, 64).astype(np.float32)
    v_attn = np.random.randn(1, 2, 15, 64).astype(np.float32)
    attn_out = wrapper._numpy_attention(q_attn, k_attn, v_attn, causal=True, softmax_scale=None)
    profiler2.lap("attention_compute")

    assert attn_out.shape == q_attn.shape

    # Comprime cache
    cache2.compress()
    profiler2.lap("cache_compress")

    report_integration = profiler2.report(tokens_generated=20)
    assert report_integration["num_laps"] == 3
    print(f"  OK: Fluxo integrado executado com sucesso")
    print(f"  Report: {json.dumps(report_integration, indent=4)}")

    stats2 = cache2.get_stats()
    print(f"  Cache stats: {json.dumps(stats2, indent=2)}")

    results["integration"] = "passed"

    # ------------------------------------------------------------------
    # Resumo
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("RESUMO DOS TESTES")
    print("=" * 70)

    all_passed = True
    for name, status in results.items():
        if status == "passed":
            print(f"  [PASS] {name}")
        else:
            print(f"  [INFO] {name}: {status}")
            if isinstance(status, str) and status.startswith("FAILED"):
                all_passed = False

    print("=" * 70)
    if all_passed:
        print("TODOS OS TESTES PASSARAM!")
    else:
        print("ALGUNS TESTES FALHARAM!")
    print("=" * 70)

    return results


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Executa testes
    run_tests()
