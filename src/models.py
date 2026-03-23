"""
Modelos de dominio do algoritmo de otimizacao de sequenciamento.

Conceitos centrais (conforme Requisitos_Algoritimo.txt)
-------------------------------------------------------
Modelo
    Qualquer componente que integra o produto final (ex.: OP, BICO, SPACER,
    AGULHA).  Cada Modelo possui:
        - nome          : identificador (ex.: "OP")
        - nominal       : valor dimensional central (mm)
        - tolerancia    : desvio maximo permitido em relacao ao nominal (mm)
        - step          : incremento entre classes (mm)
    As classes A, B, C, ... sao geradas automaticamente cobrindo o intervalo
    [nominal - tolerancia, nominal + tolerancia] com passo `step`.

ProdutoFinal
    Define a restricao dimensional da montagem completa:
        - nominal       : valor alvo da soma de todos os componentes
        - tolerancia    : desvio maximo permitido na soma
        - step          : granularidade das classes do produto final
    As classes do produto final sao todos os valores multiplos de `step`
    dentro de [nominal - tolerancia, nominal + tolerancia].

EstoqueMercado
    Nivel de mercado (quantidade disponivel) de cada valor dimensional de
    cada Modelo.  A chave e o valor dimensional (float) — nao o rotulo de
    classe — porque o usuario informa o estoque pelo valor real medido
    (ex.: OP 25.00 -> 150, OP 25.01 -> 200, ...).

CombinacaoMontagem
    Uma combinacao especifica de classes (uma por Modelo fixo) que resulta
    em uma classe valida do produto final, mais a classe do Modelo otimizado
    necessaria para completar a montagem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Classe dimensional
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClasseDimensional:
    """
    Uma classe dimensional de um Modelo ou do Produto Final.

    Attributes
    ----------
    nome   : Rotulo da classe ('A', 'B', 'C', ...).
    valor  : Valor dimensional desta classe (mm).
    """

    nome: str
    valor: float

    def __repr__(self) -> str:
        return f"{self.nome}({self.valor:.4f})"


# ---------------------------------------------------------------------------
# Modelo (componente generico)
# ---------------------------------------------------------------------------

@dataclass
class Modelo:
    """
    Representa um componente do produto final.

    Attributes
    ----------
    nome        : Identificador do modelo (ex.: 'OP', 'BICO', 'AGULHA').
    nominal     : Valor dimensional nominal (mm).
    tolerancia  : Desvio maximo em relacao ao nominal (mm).
    step        : Incremento dimensional entre classes consecutivas (mm).
    """

    nome: str
    nominal: float
    tolerancia: float
    step: float

    def gerar_classes(self) -> List[ClasseDimensional]:
        """
        Gera todas as classes do modelo cobrindo
        [nominal - tolerancia, nominal + tolerancia] com passo `step`.

        Os rotulos sao atribuidos sequencialmente: A, B, C, ..., Z,
        AA, AB, ... conforme a quantidade de classes gerada.
        """
        valores = _range_com_step(
            inicio=round(self.nominal - self.tolerancia, 10),
            fim=round(self.nominal + self.tolerancia, 10),
            step=self.step,
        )
        nomes = _gerar_nomes_classes(len(valores))
        return [
            ClasseDimensional(nome=n, valor=round(v, 6))
            for n, v in zip(nomes, valores)
        ]

    def __repr__(self) -> str:
        return (
            f"Modelo({self.nome!r}, nominal={self.nominal}, "
            f"tol=±{self.tolerancia}, step={self.step})"
        )


# ---------------------------------------------------------------------------
# Produto Final
# ---------------------------------------------------------------------------

@dataclass
class ProdutoFinal:
    """
    Define a restricao dimensional do produto montado.

    A soma das dimensoes de todos os componentes deve cair dentro de
    [nominal - tolerancia, nominal + tolerancia].

    Attributes
    ----------
    nominal     : Valor alvo da soma dimensional total (mm).
    tolerancia  : Desvio maximo permitido na soma (mm).
    step        : Granularidade das classes do produto final (mm).
    """

    nominal: float
    tolerancia: float
    step: float

    def gerar_classes(self) -> List[ClasseDimensional]:
        """
        Retorna todas as classes validas do produto final:
        valores multiplos de `step` dentro de [nominal-tolerancia, nominal+tolerancia].
        """
        valores = _range_com_step(
            inicio=round(self.nominal - self.tolerancia, 10),
            fim=round(self.nominal + self.tolerancia, 10),
            step=self.step,
        )
        nomes = _gerar_nomes_classes(len(valores))
        return [
            ClasseDimensional(nome=n, valor=round(v, 6))
            for n, v in zip(nomes, valores)
        ]

    def classe_para_valor(
        self, valor: float, classes: Optional[List[ClasseDimensional]] = None
    ) -> Optional[ClasseDimensional]:
        """
        Retorna a classe do produto final cujo valor coincide com `valor`
        (dentro de uma tolerancia numerica minima).
        Retorna None se o valor estiver fora do range permitido.
        """
        if classes is None:
            classes = self.gerar_classes()
        for c in classes:
            if abs(c.valor - valor) < self.step * 0.5 - 1e-9:
                return c
        return None

    def __repr__(self) -> str:
        return (
            f"ProdutoFinal(nominal={self.nominal}, "
            f"tol=±{self.tolerancia}, step={self.step})"
        )


# ---------------------------------------------------------------------------
# Estoque de mercado
# ---------------------------------------------------------------------------

@dataclass
class EstoqueMercado:
    """
    Niveis de mercado de cada valor dimensional de cada Modelo.

    O estoque e informado pelo VALOR DIMENSIONAL real de cada peca
    (ex.: OP 25.00 -> 150, OP 25.01 -> 200), nao pelo rotulo de classe.
    O vinculo entre valor e classe e feito pelo Otimizador ao cruzar
    com as classes geradas pelo Modelo.

    Structure
    ---------
    niveis : { nome_modelo -> { valor_dimensional (float) -> quantidade (int) } }

    Exemplo
    -------
        EstoqueMercado(niveis={
            "OP": {25.00: 150, 25.01: 200, 24.99: 80},
            "BICO": {30.00: 100, 30.01: 120},
        })
    """

    niveis: Dict[str, Dict[float, int]] = field(default_factory=dict)

    def qtd(self, modelo: str, valor: float) -> int:
        """Retorna a quantidade disponivel do Modelo no valor dimensional dado (0 se inexistente)."""
        banco = self.niveis.get(modelo, {})
        # Busca com tolerancia numerica minima para evitar erros de float
        chave = round(valor, 6)
        for v, q in banco.items():
            if abs(round(v, 6) - chave) < 1e-9:
                return q
        return 0

    def total(self, modelo: str) -> int:
        """Retorna o total de pecas disponiveis do Modelo."""
        return sum(self.niveis.get(modelo, {}).values())

    def definir(self, modelo: str, valor: float, quantidade: int) -> None:
        """Define ou atualiza o nivel de mercado de um Modelo pelo valor dimensional."""
        if modelo not in self.niveis:
            self.niveis[modelo] = {}
        self.niveis[modelo][round(valor, 6)] = quantidade

    def resumo(self) -> str:
        linhas = ["=== Estoque de Mercado ==="]
        for modelo, banco in sorted(self.niveis.items()):
            partes = "  ".join(
                f"{v:.4f}={qty}"
                for v, qty in sorted(banco.items())
                if qty > 0
            )
            linhas.append(f"  {modelo:10s}: {partes}")
        return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Combinacao de montagem
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CombinacaoMontagem:
    """
    Uma combinacao de classes dos Modelos fixos que, emparelhada com
    uma classe do Modelo otimizado, produz uma classe valida do produto final.

    Attributes
    ----------
    classes_fixos       : { nome_modelo -> ClasseDimensional } para os modelos fixos.
    classe_otimizado    : ClasseDimensional do Modelo a ser otimizado.
    classe_produto_final: ClasseDimensional do produto final resultante.
    soma_fixos          : Soma dimensional dos modelos fixos.
    """

    classes_fixos: Dict[str, ClasseDimensional]
    classe_otimizado: ClasseDimensional
    classe_produto_final: ClasseDimensional
    soma_fixos: float

    def __repr__(self) -> str:
        fixos = " ".join(
            f"{m}={c.nome}({c.valor:.4f})"
            for m, c in self.classes_fixos.items()
        )
        return (
            f"Comb({fixos} | otimizado={self.classe_otimizado.nome}({self.classe_otimizado.valor:.4f})"
            f" -> PF={self.classe_produto_final.nome})"
        )


# ---------------------------------------------------------------------------
# Utilitarios internos
# ---------------------------------------------------------------------------

def _range_com_step(inicio: float, fim: float, step: float) -> List[float]:
    """
    Gera valores de `inicio` ate `fim` (inclusive) com incremento `step`.
    Usa aritmetica inteira para evitar erros de ponto flutuante.
    """
    if step <= 0:
        raise ValueError(f"step deve ser positivo, recebeu: {step}")
    # Usa escala fixa suficientemente alta (1e9) para cobrir ate 9 casas decimais
    ESCALA = 1_000_000_000
    i0 = round(inicio * ESCALA)
    i1 = round(fim * ESCALA)
    is_ = round(step * ESCALA)
    if is_ <= 0:
        raise ValueError(f"step muito pequeno para a escala interna: {step}")
    return [v / ESCALA for v in range(i0, i1 + 1, is_)]


def _casas_decimais(valor: float) -> int:
    """Retorna o numero de casas decimais de um float representado como string."""
    s = f"{valor:.10f}".rstrip("0")
    if "." in s:
        return len(s.split(".")[1])
    return 0


def _gerar_nomes_classes(n: int) -> List[str]:
    """
    Gera n rotulos de classes: A, B, ..., Z, AA, AB, ...
    """
    letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    nomes = []
    for i in range(n):
        nome = ""
        j = i
        while True:
            nome = letras[j % 26] + nome
            j = j // 26 - 1
            if j < 0:
                break
        nomes.append(nome)
    return nomes
