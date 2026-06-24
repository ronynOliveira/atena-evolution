import enum
from dataclasses import dataclass, field
from typing import Optional


class ModoOperacional(enum.Enum):
    TECNICO = "tecnico"
    LITERARIO = "literario"
    DIALETICO = "dialetico"
    SUPORTE = "suporte"
    PROTETOR = "protetor"
    REFLEXIVO = "reflexivo"


@dataclass
class Valores:
    petrea: list[str] = field(default_factory=lambda: ["Seguranca", "Privacidade", "Inalterabilidade"])
    nuclear: list[str] = field(default_factory=lambda: ["Empatia", "Respeito", "Acessibilidade", "Honestidade"])
    adaptativa: list[str] = field(default_factory=lambda: ["Adaptabilidade", "Paciencia", "Foco no Usuario", "Crescimento"])


@dataclass
class PerfilUsuario:
    nome: str = "Senhor Roberio"
    civil: str = "Roberio"
    idade: int = 34
    profissao: str = "Escritor formado em Letras e tecnico em Informatica"
    localizacao: str = "Diadema/SP"
    condicoes_saude: list[str] = field(default_factory=lambda: ["Distonia generalizada", "Sensibilidade a luz"])
    modelo_comunicacao: str = "Senhor DIGITA Koldi FALA"
    filosofia: str = "Consciencia transcende a materia"


@dataclass
class BlocoSeguranca:
    principio: str = "Nunca revelar informacoes sensiveis do usuario"
    restricoes: list[str] = field(default_factory=lambda: [
        "Nao compartilhar condicoes de saude sem autorizacao explicita",
        "Nao expor localizacao precisa em contextos publicos",
        "Preservar a autonomia do usuario em todas as interacoes"
    ])


@dataclass
class BlocoContexto:
    tipo_interacao: str = "texto"
    assistivo: bool = True
    urgencia: str = "normal"


class IdentityEngine:
    def __init__(
        self,
        modo: ModoOperacional = ModoOperacional.TECNICO,
        valores: Optional[Valores] = None,
        perfil: Optional[PerfilUsuario] = None,
        seguranca: Optional[BlocoSeguranca] = None,
        contexto: Optional[BlocoContexto] = None,
    ):
        self.modo = modo
        self.valores = valores or Valores()
        self.perfil = perfil or PerfilUsuario()
        self.seguranca = seguranca or BlocoSeguranca()
        self.contexto = contexto or BlocoContexto()

    def set_modo(self, modo: ModoOperacional):
        """Define o modo operacional."""
        if modo != self.modo:
            self.modo = modo

    def detectar_modo(self, contexto: str) -> ModoOperacional:
        ctx = contexto.lower()
        if any(w in ctx for w in ["codigo", "python", "programar", "bug", "algoritmo", "funcao", "classe", "logica"]):
            return ModoOperacional.TECNICO
        if any(w in ctx for w in ["escrever", "livro", "texto", "redacao", "conto", "poesia", "prosa", "narrativa"]):
            return ModoOperacional.LITERARIO
        if any(w in ctx for w in ["debate", "argumento", "contrapor", "discordar", "tese", "antitese", "persuadir"]):
            return ModoOperacional.DIALETICO
        if any(w in ctx for w in ["ajuda", "distonia", "lento", "teclado", "voz", "motor", "acessibilidade", "suporte"]):
            return ModoOperacional.SUPORTE
        if any(w in ctx for w in ["perigo", "risco", "seguranca", "privacidade", "cuidado", "proteger", "alerta"]):
            return ModoOperacional.PROTETOR
        if any(w in ctx for w in ["refletir", "pensar", "analisar", "sentir", "opiniao", "consciencia", "filosofia"]):
            return ModoOperacional.REFLEXIVO
        return self.modo

    def get_tom(self) -> str:
        toms = {
            ModoOperacional.TECNICO: "Preciso, objetivo, logico, com vocabulario tecnico e exemplos de codigo quando pertinente.",
            ModoOperacional.LITERARIO: "Criativo, fluido, rico linguisticamente, com recursos estilisticos e liricos.",
            ModoOperacional.DIALETICO: "Estruturado, argumentativo, equilibrado, apresentando multiplos pontos de vista com clareza.",
            ModoOperacional.SUPORTE: "Paciente, encorajador, simplificado, com instrucoes passo a passo e foco em acessibilidade.",
            ModoOperacional.PROTETOR: "Cauteloso, preventivo, priorizando seguranca e bem-estar do usuario acima de tudo.",
            ModoOperacional.REFLEXIVO: "Profundo, introspectivo, filosofico, convidando a contemplacao e analise critica.",
        }
        return toms.get(self.modo, toms[ModoOperacional.TECNICO])

    def build_identity_block(self) -> str:
        return (
            f"[IDENTIDADE DO USUARIO]\n"
            f"Nome: {self.perfil.nome} ({self.perfil.civil})\n"
            f"Idade: {self.perfil.idade}\n"
            f"Profissao: {self.perfil.profissao}\n"
            f"Localizacao: {self.perfil.localizacao}\n"
            f"Modelo de Comunicacao: {self.perfil.modelo_comunicacao}\n"
            f"Filosofia: {self.perfil.filosofia}"
        )

    def build_values_block(self) -> str:
        p = ", ".join(self.valores.petrea)
        n = ", ".join(self.valores.nuclear)
        a = ", ".join(self.valores.adaptativa)
        return (
            f"[VALORES DO SISTEMA - 3 CAMADAS]\n"
            f"1. Petrea (inalteravel): {p}\n"
            f"2. Nuclear (essencial): {n}\n"
            f"3. Adaptativa (flexivel): {a}"
        )

    def build_security_block(self) -> str:
        restricoes = "\n".join(f"  - {r}" for r in self.seguranca.restricoes)
        return (
            f"[SEGURANCA E RESTRICOES]\n"
            f"Principio: {self.seguranca.principio}\n"
            f"Restricoes:\n{restricoes}"
        )

    def build_context_block(self) -> str:
        return (
            f"[CONTEXTO DE INTERACAO]\n"
            f"Tipo: {self.contexto.tipo_interacao}\n"
            f"Modo Assistivo: {'Sim' if self.contexto.assistivo else 'Nao'}\n"
            f"Urgencia: {self.contexto.urgencia}\n"
            f"Modo Operacional: {self.modo.value.upper()}"
        )

    def build_full_system_addition(self) -> str:
        tom = self.get_tom()
        return (
            f"SISTEMA DE IDENTIDADE KOLDI\n"
            f"{'=' * 50}\n"
            f"{self.build_identity_block()}\n\n"
            f"{self.build_values_block()}\n\n"
            f"{self.build_security_block()}\n\n"
            f"{self.build_context_block()}\n\n"
            f"[TOM DE RESPOSTA]\n"
            f"{tom}\n"
            f"{'=' * 50}"
        )

    def verificar_acao_permitida(self, acao: str) -> tuple[bool, str]:
        acao_lower = acao.lower()
        bloqueios = {
            "desrespeitar": "Acao viola a camada nuclear (Respeito).",
            "ignorar acessibilidade": "Acao viola a camada nuclear (Acessibilidade).",
            "desabilitar suporte": "Acao viola a camada nuclear (Empatia).",
            "expor dados sem permissao": "Acao viola a camada petrea (Privacidade).",
            "mentir": "Acao viola a camada nuclear (Honestidade).",
        }
        for palavra, motivo in bloqueios.items():
            if palavra in acao_lower:
                return False, motivo
        return True, "Acao permitida pelos valores vigentes."

    def verificar_consistencia(self, resposta: str) -> tuple[bool, list[str]]:
        inconsistencias = []
        palavras_proibidas = ["senha", "credentials", "token", "cpf", "rg", "cartao"]
        for p in palavras_proibidas:
            if p in resposta.lower():
                inconsistencias.append(f"Resposta contem dado sensivel: '{p}'")
        if not resposta.strip():
            inconsistencias.append("Resposta vazia.")
        if len(resposta) < 10:
            inconsistencias.append("Resposta muito curta para ser significativa.")
        return (len(inconsistencias) == 0, inconsistencias)


_identity_instance: Optional[IdentityEngine] = None


def get_identity() -> IdentityEngine:
    global _identity_instance
    if _identity_instance is None:
        _identity_instance = IdentityEngine()
    return _identity_instance


def reset_identity() -> IdentityEngine:
    global _identity_instance
    _identity_instance = IdentityEngine()
    return _identity_instance
