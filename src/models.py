"""
Modelos de domínio do algoritmo de sequenciamento inteligente de AGULHA.

Cenário:
    O produto final é montado com 4 componentes: OP, BICO, SPACER e AGULHA.
    Cada componente possui um valor dimensional nominal dividido em classes (A, B, C, ...).
    A restrição de qualidade é:

        dim(OP) + dim(BICO) + dim(SPACER) + dim(AGULHA) == ALVO ± TOLERANCIA

    Dado o estoque de classes de OP, BICO e SPACER, o otimizador determina
    quais classes de AGULHA devem ser produzidas e em que quantidade para
    maximizar o aproveitamento do estoque existente dos outros três componentes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Constantes do produto
# ---------------------------------------------------------------------------

#: Diferenca fixa entre a soma (OP + BICO + SPACER) e a AGULHA necessaria.
#: Condicao de OK: ROUND(OP + BICO + SPACER - AGULHA, 3) == DIFERENCA_MONTAGEM
DIFERENCA_MONTAGEM: float = 0.325

#: Passo dimensional entre classes de OP, BICO e SPACER
PASSO_OP_BICO_SPACER: float = 0.010

#: Passo dimensional entre classes de AGULHA
PASSO_AGULHA: float = 0.010

# Manter por compatibilidade (valor de referencia apenas)
ALVO_MONTAGEM: float = 73.015
TOLERANCIA_MONTAGEM: float = DIFERENCA_MONTAGEM


# ---------------------------------------------------------------------------
# Definição das classes dimensionais
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClasseDimensional:
    """
    Representa uma classe dimensional de um componente.

    Attributes
    ----------
    nome   : Rótulo da classe (ex.: 'A', 'B', 'C', ...).
    valor  : Valor dimensional nominal desta classe (mm).
    """

    nome: str
    valor: float

    def __repr__(self) -> str:
        return f"Classe({self.nome}, {self.valor:.4f})"


def gerar_classes(
    valor_inicial: float,
    passo: float,
    nomes: List[str],
) -> List[ClasseDimensional]:
    """
    Gera uma lista de :class:`ClasseDimensional` com valores espaçados por ``passo``.

    Parameters
    ----------
    valor_inicial : Valor nominal da primeira classe.
    passo         : Incremento dimensional entre classes consecutivas.
    nomes         : Rótulos das classes, em ordem.
    """
    return [
        ClasseDimensional(nome=n, valor=round(valor_inicial + i * passo, 6))
        for i, n in enumerate(nomes)
    ]


# ---------------------------------------------------------------------------
# Classes padrão de cada componente (extraídas do Excel)
# ---------------------------------------------------------------------------

#: OP  – 5 classes (A..E), valor base 3.005 mm, passo 0.010 mm
CLASSES_OP: List[ClasseDimensional] = gerar_classes(
    valor_inicial=3.005,
    passo=PASSO_OP_BICO_SPACER,
    nomes=["A", "B", "C", "D", "E"],
)

#: BICO – 5 classes (A..E), valor base 30.005 mm, passo 0.010 mm
CLASSES_BICO: List[ClasseDimensional] = gerar_classes(
    valor_inicial=30.005,
    passo=PASSO_OP_BICO_SPACER,
    nomes=["A", "B", "C", "D", "E"],
)

#: SPACER – 5 classes (A..E), valor base 40.005 mm, passo 0.010 mm
CLASSES_SPACER: List[ClasseDimensional] = gerar_classes(
    valor_inicial=40.005,
    passo=PASSO_OP_BICO_SPACER,
    nomes=["A", "B", "C", "D", "E"],
)

#: AGULHA – 13 classes (A..M), valor base 72.690 mm, passo 0.010 mm
CLASSES_AGULHA: List[ClasseDimensional] = gerar_classes(
    valor_inicial=72.690,
    passo=PASSO_AGULHA,
    nomes=["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"],
)


# ---------------------------------------------------------------------------
# Estoque
# ---------------------------------------------------------------------------

@dataclass
class EstoqueComponentes:
    """
    Mantém o nível de estoque de cada classe de OP, BICO e SPACER.

    Attributes
    ----------
    op     : Mapeamento {nome_classe → quantidade}.
    bico   : Mapeamento {nome_classe → quantidade}.
    spacer : Mapeamento {nome_classe → quantidade}.
    """

    op: Dict[str, int] = field(default_factory=dict)
    bico: Dict[str, int] = field(default_factory=dict)
    spacer: Dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers de acesso
    # ------------------------------------------------------------------

    def qtd_op(self, classe: str) -> int:
        """Retorna o estoque de OP da classe informada (0 se não existir)."""
        return self.op.get(classe, 0)

    def qtd_bico(self, classe: str) -> int:
        """Retorna o estoque de BICO da classe informada."""
        return self.bico.get(classe, 0)

    def qtd_spacer(self, classe: str) -> int:
        """Retorna o estoque de SPACER da classe informada."""
        return self.spacer.get(classe, 0)

    def total_op(self) -> int:
        return sum(self.op.values())

    def total_bico(self) -> int:
        return sum(self.bico.values())

    def total_spacer(self) -> int:
        return sum(self.spacer.values())

    def resumo(self) -> str:
        linhas = ["=== Estoque de Componentes ==="]
        for comp, dados in [("OP", self.op), ("BICO", self.bico), ("SPACER", self.spacer)]:
            linha = f"  {comp:6s}: " + "  ".join(
                f"{cls}={qty}" for cls, qty in sorted(dados.items()) if qty > 0
            )
            linhas.append(linha)
        return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Combinação de montagem
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CombinacaoMontagem:
    """
    Uma combinação válida de classes de OP + BICO + SPACER que,
    emparelhada com a classe de AGULHA correspondente, produz uma
    montagem dentro da tolerância.

    Attributes
    ----------
    classe_op     : Classe do componente OP.
    classe_bico   : Classe do componente BICO.
    classe_spacer : Classe do componente SPACER.
    classe_agulha : Classe da AGULHA necessária para completar a montagem.
    soma_op_bico_spacer : Soma dimensional OP + BICO + SPACER.
    dim_agulha_necessaria : Valor dimensional que a AGULHA deve ter.
    """

    classe_op: str
    classe_bico: str
    classe_spacer: str
    classe_agulha: str
    soma_op_bico_spacer: float
    dim_agulha_necessaria: float

    def __repr__(self) -> str:
        return (
            f"Comb(OP={self.classe_op}, BICO={self.classe_bico}, "
            f"SPACER={self.classe_spacer} → AGULHA={self.classe_agulha})"
        )
