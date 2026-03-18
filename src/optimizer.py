"""
Otimizador de producao de AGULHA.

Problema
--------
Dados os estoques de classes de OP, BICO e SPACER, determinar:

    1. Todas as combinacoes validas (OP_classe, BICO_classe, SPACER_classe)
       que satisfazem a restricao dimensional do produto:

           ROUND(OP + BICO + SPACER - AGULHA, 3) == 0.325

    2. Quantas unidades de cada classe de AGULHA devem ser produzidas para
       maximizar o aproveitamento dos estoques de OP, BICO e SPACER.

Estrategia
----------
Para cada combinacao (op_i, bico_j, spacer_k) o numero de montagens possiveis
e limitado pelo menor estoque disponivel entre os tres componentes:

    disponivel(comb) = min(estoque_op[i], estoque_bico[j], estoque_spacer[k])

O otimizador:
    1. Enumera todas as combinacoes validas.
    2. Agrupa por classe de AGULHA necessaria.
    3. Resolve um problema de alocacao para maximizar montagens totais
       sem ultrapassar os estoques de nenhuma classe de OP, BICO e SPACER.
    4. Retorna a demanda de producao de AGULHA por classe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .models import (
    DIFERENCA_MONTAGEM,
    CLASSES_AGULHA,
    CLASSES_BICO,
    CLASSES_OP,
    CLASSES_SPACER,
    ALVO_MONTAGEM,
    TOLERANCIA_MONTAGEM,
    ClasseDimensional,
    CombinacaoMontagem,
    EstoqueComponentes,
)


# ---------------------------------------------------------------------------
# Resultado da otimização
# ---------------------------------------------------------------------------

@dataclass
class ResultadoOtimizacao:
    """
    Contém o plano de produção de AGULHA e as estatísticas de aproveitamento.

    Attributes
    ----------
    producao_agulha : Mapeamento {classe_agulha → quantidade a produzir}.
    montagens_por_combinacao : Lista de (combinação, quantidade alocada).
    estoque_inicial : Estoque de entrada (cópia de referência).
    """

    producao_agulha: Dict[str, int] = field(default_factory=dict)
    montagens_por_combinacao: List[Tuple[CombinacaoMontagem, int]] = field(
        default_factory=list
    )
    estoque_inicial: EstoqueComponentes = field(
        default_factory=EstoqueComponentes
    )

    # ------------------------------------------------------------------

    def total_montagens(self) -> int:
        return sum(q for _, q in self.montagens_por_combinacao)

    def aproveitamento_op(self) -> float:
        """Percentual do estoque total de OP utilizado."""
        total = self.estoque_inicial.total_op()
        if total == 0:
            return 0.0
        usado = sum(q for comb, q in self.montagens_por_combinacao)
        return round(usado / total * 100, 1)

    def aproveitamento_bico(self) -> float:
        total = self.estoque_inicial.total_bico()
        if total == 0:
            return 0.0
        usado = sum(q for comb, q in self.montagens_por_combinacao)
        return round(usado / total * 100, 1)

    def aproveitamento_spacer(self) -> float:
        total = self.estoque_inicial.total_spacer()
        if total == 0:
            return 0.0
        usado = sum(q for comb, q in self.montagens_por_combinacao)
        return round(usado / total * 100, 1)

    def resumo(self) -> str:
        linhas = [
            "=" * 55,
            "  RESULTADO DA OTIMIZAÇÃO",
            "=" * 55,
            f"  Total de montagens planejadas : {self.total_montagens()}",
            "",
            "  Produção de AGULHA necessária:",
        ]
        for classe in sorted(self.producao_agulha):
            qty = self.producao_agulha[classe]
            if qty > 0:
                linhas.append(f"    Classe {classe:2s} → {qty:>6d} unidades")

        linhas += [
            "",
            "  Aproveitamento de estoque:",
            f"    OP     : {self.aproveitamento_op():5.1f}%",
            f"    BICO   : {self.aproveitamento_bico():5.1f}%",
            f"    SPACER : {self.aproveitamento_spacer():5.1f}%",
            "",
            "  Detalhamento por combinação (top 20):",
        ]
        top = sorted(self.montagens_por_combinacao, key=lambda x: -x[1])[:20]
        for comb, qty in top:
            linhas.append(
                f"    OP={comb.classe_op} BICO={comb.classe_bico} "
                f"SPACER={comb.classe_spacer} → AGULHA {comb.classe_agulha}"
                f"  ×{qty}"
            )
        if len(self.montagens_por_combinacao) > 20:
            linhas.append(
                f"    ... e mais {len(self.montagens_por_combinacao) - 20} combinações."
            )
        linhas.append("=" * 55)
        return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Motor de otimização
# ---------------------------------------------------------------------------

class OtimizadorAgulha:
    """
    Determina a demanda de produção de AGULHA para melhor aproveitar os
    estoques de OP, BICO e SPACER.

    Parameters
    ----------
    estoque           : Estoque atual de classes de OP, BICO e SPACER.
    classes_op        : Lista de classes dimensionais de OP.
    classes_bico      : Lista de classes dimensionais de BICO.
    classes_spacer    : Lista de classes dimensionais de SPACER.
    classes_agulha    : Lista de classes dimensionais de AGULHA.
    diferenca         : Valor fixo tal que ROUND(OP+BICO+SPACER-AGULHA,3) == diferenca.
    """

    def __init__(
        self,
        estoque: EstoqueComponentes,
        classes_op: List[ClasseDimensional] = None,
        classes_bico: List[ClasseDimensional] = None,
        classes_spacer: List[ClasseDimensional] = None,
        classes_agulha: List[ClasseDimensional] = None,
        diferenca: float = DIFERENCA_MONTAGEM,
    ) -> None:
        self.estoque = estoque
        self.classes_op = classes_op or CLASSES_OP
        self.classes_bico = classes_bico or CLASSES_BICO
        self.classes_spacer = classes_spacer or CLASSES_SPACER
        self.classes_agulha = classes_agulha or CLASSES_AGULHA
        self.diferenca = diferenca

        # Índice rápido: nome → ClasseDimensional de AGULHA
        self._idx_agulha: Dict[str, ClasseDimensional] = {
            c.nome: c for c in self.classes_agulha
        }

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def enumerar_combinacoes(self) -> List[CombinacaoMontagem]:
        """
        Retorna todas as combinações (OP, BICO, SPACER) que, somadas a
        alguma classe de AGULHA, resultam em montagem válida.
        """
        combinacoes: List[CombinacaoMontagem] = []
        for op in self.classes_op:
            for bico in self.classes_bico:
                for spacer in self.classes_spacer:
                    soma = round(op.valor + bico.valor + spacer.valor, 6)
                    agulha = self._classe_agulha_para(soma)
                    if agulha is not None:
                        combinacoes.append(
                            CombinacaoMontagem(
                                classe_op=op.nome,
                                classe_bico=bico.nome,
                                classe_spacer=spacer.nome,
                                classe_agulha=agulha.nome,
                                soma_op_bico_spacer=soma,
                                dim_agulha_necessaria=agulha.valor,
                            )
                        )
        return combinacoes

    def otimizar(self) -> ResultadoOtimizacao:
        """
        Executa a otimização e retorna o :class:`ResultadoOtimizacao`.

        Algoritmo (greedy com equilíbrio de estoque):
        1. Enumera todas as combinações válidas.
        2. Para cada combinação, calcula o volume aproveitável =
           min(estoque_op[classe], estoque_bico[classe], estoque_spacer[classe]).
        3. Ordena pelo volume aproveitável (decrescente) para priorizar as
           combinações mais vantajosas.
        4. Aloca de forma gulosa respeitando os estoques remanescentes.
        5. Acumula a produção de AGULHA necessária por classe.
        """
        combinacoes = self.enumerar_combinacoes()

        # Cópias mutáveis dos estoques para simulação
        saldo_op = dict(self.estoque.op)
        saldo_bico = dict(self.estoque.bico)
        saldo_spacer = dict(self.estoque.spacer)

        # Potencial inicial de cada combinação
        def _potencial(comb: CombinacaoMontagem) -> int:
            return min(
                saldo_op.get(comb.classe_op, 0),
                saldo_bico.get(comb.classe_bico, 0),
                saldo_spacer.get(comb.classe_spacer, 0),
            )

        # Ordena por potencial decrescente
        combinacoes.sort(key=_potencial, reverse=True)

        alocacoes: List[Tuple[CombinacaoMontagem, int]] = []
        producao_agulha: Dict[str, int] = {c.nome: 0 for c in self.classes_agulha}

        for comb in combinacoes:
            qty = min(
                saldo_op.get(comb.classe_op, 0),
                saldo_bico.get(comb.classe_bico, 0),
                saldo_spacer.get(comb.classe_spacer, 0),
            )
            if qty <= 0:
                continue

            # Consome os saldos
            saldo_op[comb.classe_op] = saldo_op.get(comb.classe_op, 0) - qty
            saldo_bico[comb.classe_bico] = saldo_bico.get(comb.classe_bico, 0) - qty
            saldo_spacer[comb.classe_spacer] = saldo_spacer.get(comb.classe_spacer, 0) - qty

            alocacoes.append((comb, qty))
            producao_agulha[comb.classe_agulha] = producao_agulha.get(comb.classe_agulha, 0) + qty

        return ResultadoOtimizacao(
            producao_agulha={k: v for k, v in producao_agulha.items() if v > 0},
            montagens_por_combinacao=alocacoes,
            estoque_inicial=self.estoque,
        )

    # ------------------------------------------------------------------
    # Métodos auxiliares
    # ------------------------------------------------------------------

    def _classe_agulha_para(self, soma_op_bico_spacer: float) -> ClasseDimensional | None:
        """
        Dada a soma dimensional de OP + BICO + SPACER, retorna a
        :class:`ClasseDimensional` de AGULHA tal que:

            ROUND(soma - dim_agulha, 3) == diferenca

        Ou seja: dim_agulha = soma - diferenca (exato, com arredondamento a 3 casas).

        Retorna ``None`` se nenhuma classe de AGULHA satisfizer a restricao.
        """
        dim_agulha_necessaria = round(soma_op_bico_spacer - self.diferenca, 6)
        for classe in self.classes_agulha:
            # Verifica usando a regra do Excel: ROUND(soma - ag, 3) == diferenca
            if round(abs(classe.valor - dim_agulha_necessaria), 6) < 1e-6:
                return classe
        return None
