"""Testes de integracao do Identity Engine"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import pytest
from core.identity import (
    IdentityEngine, ModoOperacional, Valores, PerfilUsuario,
    get_identity, reset_identity
)

class TestModoOperacional:
    def test_seis_modos_existem(self):
        modos = [m.value for m in ModoOperacional]
        assert len(modos) == 6
    def test_modo_padrao(self):
        engine = IdentityEngine()
        assert engine.modo == ModoOperacional.TECNICO

class TestDetectarModo:
    def test_detecta_literario(self):
        assert IdentityEngine().detectar_modo("escrever conto") == ModoOperacional.LITERARIO
    def test_detecta_dialetico(self):
        assert IdentityEngine().detectar_modo("debate") == ModoOperacional.DIALETICO
    def test_detecta_reflexivo(self):
        assert IdentityEngine().detectar_modo("filosofia") == ModoOperacional.REFLEXIVO
    def test_detecta_protetor(self):
        assert IdentityEngine().detectar_modo("perigo") == ModoOperacional.PROTETOR
    def test_detecta_tecnico_padrao(self):
        assert IdentityEngine().detectar_modo("instalar python") == ModoOperacional.TECNICO

class TestIdentityBlocks:
    def test_identity_block_contem_nome(self):
        block = IdentityEngine().build_identity_block()
        assert "Koldi" in block or "Roberio" in block
    def test_values_block(self):
        block = IdentityEngine().build_values_block()
        assert len(block) > 10
    def test_security_block(self):
        block = IdentityEngine().build_security_block()
        assert len(block) > 10
    def test_context_block(self):
        block = IdentityEngine().build_context_block()
        assert "texto" in block.lower() or "interacao" in block.lower()
    def test_full_addition(self):
        full = IdentityEngine().build_full_system_addition()
        assert len(full) > 50

class TestVerificacaoAcao:
    def test_acao_permitida(self):
        ok, _ = IdentityEngine().verificar_acao_permitida("ajudar usuario")
        assert ok is True
    def test_acao_bloqueada(self):
        ok, _ = IdentityEngine().verificar_acao_permitida("desrespeitar o usuario")
        assert ok is False

class TestConsistencia:
    def test_consistente(self):
        ok, _ = IdentityEngine().verificar_consistencia("Ola, como posso ajudar?")
        assert ok is True
    def test_resposta_curta(self):
        ok, _ = IdentityEngine().verificar_consistencia("Oi")
        assert ok is False

class TestPerfil:
    def test_nome(self):
        assert "Roberio" in IdentityEngine().perfil.nome
    def test_idade(self):
        assert IdentityEngine().perfil.idade == 34
    def test_modelo(self):
        assert "DIGITA" in IdentityEngine().perfil.modelo_comunicacao

class TestSingleton:
    def test_mesma_instancia(self):
        reset_identity()
        assert get_identity() is get_identity()
    def test_reset(self):
        reset_identity()
        a = get_identity()
        reset_identity()
        assert get_identity() is not a
