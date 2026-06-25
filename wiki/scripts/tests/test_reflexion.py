#!/usr/bin/env python3
"""
Testes para Reflexion Engine - Projeto Atena
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.reflexion_standalone import (
    ReflexionMemory,
    ReflectionEntry,
    ConfidenceRouter,
    DistoniaDetector,
)

def test_reflexion_memory():
    """Teste de memória de reflexão"""
    memory = ReflexionMemory(max_entries=100)
    
    entry = ReflectionEntry(
        state={"test": "value"},
        action="test_action",
        result="test_result",
        reflection="test_reflection",
        score=0.9
    )
    
    entry_id = memory.add(entry)
    
    # Verificar se foi armazenado
    assert entry_id is not None
    assert len(memory.buffer) == 1
    print("✅ test_reflexion_memory PASSED")

def test_confidence_router():
    """Teste do roteador de confiança"""
    memory = ReflexionMemory()
    router = ConfidenceRouter(memory)
    
    confidence = router.calculate_confidence(
        "resultado teste",
        {"query": "teste"},
        ["tool"]
    )
    
    assert 0.0 <= confidence <= 1.0
    print(f"✅ test_confidence_router PASSED (confidence: {confidence:.2f})")

def test_distonia_detector():
    """Teste do detector de distonia"""
    detector = DistoniaDetector()
    
    outputs = [
        "Temperatura em Diadema é 18°C",
        "Em Diadema, SP está fazendo 18 graus",
        "Diadema-SP: 18°C no momento"
    ]
    
    divergence = detector.calculate_divergence(outputs)
    
    assert 0.0 <= divergence <= 1.0
    print(f"✅ test_distonia_detector PASSED (divergence: {divergence:.2f})")

def test_similarity_search():
    """Teste de busca por similaridade"""
    memory = ReflexionMemory()
    
    # Adicionar algumas entradas
    for i in range(5):
        entry = ReflectionEntry(
            state={"query": f"test{i}"},
            action="test",
            result=f"result{i}",
            reflection="test",
            score=0.5 + i * 0.1
        )
        memory.add(entry)
    
    # Buscar similares
    results = memory.retrieve_similar({"query": "test3"}, top_k=2)
    
    assert len(results) <= 2
    print(f"✅ test_similarity_search PASSED ({len(results)} results)")

if __name__ == "__main__":
    test_reflexion_memory()
    test_confidence_router()
    test_distonia_detector()
    test_similarity_search()
    print("\n🎉 Todos os testes do Reflexion Engine PASSED!")