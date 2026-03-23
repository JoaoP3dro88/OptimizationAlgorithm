"""
Otimizador generico de sequenciamento de montagem.

Objetivo
--------
Dado um conjunto de Modelos, um Produto Final e o Modelo a ser otimizado,
o algoritmo:
  1. Cruza as classes de cada Modelo com o estoque informado por valor
     dimensional, descobrindo quais classes possuem estoque disponivel.
  2. Enumera todas as combinacoes validas dos Modelos fixos cujas somas
     dimensionais, combinadas a alguma classe do Modelo otimizado, caem
     dentro das classes do Produto Final.
  3. Para cada combinacao valida, calcula o potencial de producao com base
     no estoque disponivel dos Modelos fixos.
  4. Aloca producao de forma gananciosa (greedy) — priorizando as combinacoes
     com maior potencial — consumindo o estoque e calculando a producao
     necessaria do Modelo otimizado por classe.

Estoque
-------
O estoque e informado por VALOR DIMENSIONAL (float), nao por rotulo de classe.
O Otimizador faz o vinculo automaticamente: para cada classe gerada pelo Modelo
(ex.: OP classe C = 25.02), busca no estoque a quantidade em 25.02.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .models import (
    ClasseDimensional,
    CombinacaoMontagem,
    EstoqueMercado,
    Modelo,
    ProdutoFinal,
)


# ---------------------------------------------------------------------------
# Resultado da otimizacao
# ---------------------------------------------------------------------------

@dataclass
class ResultadoOtimizacao:
    """
    Resultado da execucao do otimizador.

    Attributes
    ----------
    producao_otimizado          : Producao necessaria do Modelo otimizado por
                                  ClasseDimensional (valor dimensional -> qtd).
    montagens_por_combinacao    : Lista de (combinacao, quantidade produzida).
    estoque_inicial             : Snapshot do estoque antes da otimizacao.
    modelos_fixos               : Nomes dos Modelos fixos.
    nome_otimizado              : Nome do Modelo que foi otimizado.
    """

    producao_otimizado: Dict[ClasseDimensional, int]
    montagens_por_combinacao: List[Tuple[CombinacaoMontagem, int]]
    estoque_inicial: EstoqueMercado
    modelos_fixos: List[str]
    nome_otimizado: str

    def total_montagens(self) -> int:
        return sum(q for _, q in self.montagens_por_combinacao)

    def aproveitamento(self, modelo: str) -> float:
        """Retorna o aproveitamento (0.0 a 1.0) do estoque do Modelo informado."""
        total_inicial = self.estoque_inicial.total(modelo)
        if total_inicial == 0:
            return 0.0
        consumido = sum(
            q
            for combo, q in self.montagens_por_combinacao
            if modelo in combo.classes_fixos
        )
        return consumido / total_inicial

    def resumo(self) -> str:
        linhas = ["=" * 60, "RESULTADO DA OTIMIZACAO", "=" * 60]

        linhas.append(f"Total de montagens    : {self.total_montagens()}")

        linhas.append(f"\nProducao necessaria de {self.nome_otimizado} por classe:")
        for cls, qtd in sorted(self.producao_otimizado.items(), key=lambda x: x[0].valor):
            if qtd > 0:
                linhas.append(f"  Classe {cls.nome} ({cls.valor:.4f} mm): {qtd} pecas")

        linhas.append("\nAproveitamento do estoque dos Modelos fixos:")
        for m in self.modelos_fixos:
            pct = self.aproveitamento(m) * 100
            linhas.append(f"  {m:10s}: {pct:.1f}%")

        linhas.append("\nMontagens por combinacao (top 20):")
        ordenadas = sorted(self.montagens_por_combinacao, key=lambda x: -x[1])
        for combo, qtd in ordenadas[:20]:
            if qtd > 0:
                linhas.append(f"  {combo} x{qtd}")

        linhas.append("=" * 60)
        return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Otimizador
# ---------------------------------------------------------------------------

class Otimizador:
    """
    Otimizador generico de sequenciamento de montagem.

    Parameters
    ----------
    modelos_fixos    : Modelos cujo estoque de mercado sera consumido.
    modelo_otimizado : Modelo cuja producao necessaria sera calculada.
                       Seus parametros (nominal, tolerancia, step) definem
                       quais classes podem ser produzidas.
    produto_final    : Especificacao dimensional do produto final.
    estoque          : Quantidades disponiveis por valor dimensional de cada Modelo.
                       Ex.: {"OP": {25.00: 150, 25.01: 200}, "BICO": {30.00: 100}}
    """

    def __init__(
        self,
        modelos_fixos: List[Modelo],
        modelo_otimizado: Modelo,
        produto_final: ProdutoFinal,
        estoque: EstoqueMercado,
    ) -> None:
        self.modelos_fixos = modelos_fixos
        self.modelo_otimizado = modelo_otimizado
        self.produto_final = produto_final
        self.estoque = estoque

        # Todas as classes possiveis de cada modelo fixo (geradas por nominal/tol/step)
        self._classes_fixos: Dict[str, List[ClasseDimensional]] = {
            m.nome: m.gerar_classes() for m in modelos_fixos
        }
        # Todas as classes possiveis do modelo otimizado
        self._classes_otimizado: List[ClasseDimensional] = modelo_otimizado.gerar_classes()

        # Classes do produto final e mapa de lookup por valor (arredondado em 6 dec.)
        self._classes_pf: List[ClasseDimensional] = produto_final.gerar_classes()
        self._mapa_pf: Dict[float, ClasseDimensional] = {
            round(c.valor, 6): c for c in self._classes_pf
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _estoque_para_classe(self, modelo: str, classe: ClasseDimensional) -> int:
        """Retorna o estoque disponivel para uma classe de um modelo fixo."""
        return self.estoque.qtd(modelo, classe.valor)

    # ------------------------------------------------------------------
    # Enumeracao de combinacoes validas
    # ------------------------------------------------------------------

    def enumerar_combinacoes(self) -> List[CombinacaoMontagem]:
        """
        Retorna todas as combinacoes validas entre classes dos Modelos fixos
        e classes do Modelo otimizado, dentro do range do Produto Final.

        Para cada combinacao dos Modelos fixos, testa:
            soma_fixos - dim_otimizado = valor_pf   (modelo otimizado eh subtraido)
            soma_fixos + dim_otimizado = valor_pf   (modelo otimizado eh somado)
        """
        combinacoes: List[CombinacaoMontagem] = []

        nomes_fixos = [m.nome for m in self.modelos_fixos]
        lista_classes_fixos = [self._classes_fixos[n] for n in nomes_fixos]

        for combo in itertools.product(*lista_classes_fixos):
            soma = round(sum(c.valor for c in combo), 6)
            classes_dict = {nome: c for nome, c in zip(nomes_fixos, combo)}

            for classe_ot in self._classes_otimizado:
                # Relacao 1: soma_fixos - dim_otimizado = valor_pf
                chave1 = round(soma - classe_ot.valor, 6)
                if chave1 in self._mapa_pf:
                    combinacoes.append(CombinacaoMontagem(
                        classes_fixos=classes_dict,
                        classe_otimizado=classe_ot,
                        classe_produto_final=self._mapa_pf[chave1],
                        soma_fixos=soma,
                    ))
                    break

                # Relacao 2: soma_fixos + dim_otimizado = valor_pf
                chave2 = round(soma + classe_ot.valor, 6)
                if chave2 in self._mapa_pf:
                    combinacoes.append(CombinacaoMontagem(
                        classes_fixos=classes_dict,
                        classe_otimizado=classe_ot,
                        classe_produto_final=self._mapa_pf[chave2],
                        soma_fixos=soma,
                    ))
                    break

        return combinacoes

    # ------------------------------------------------------------------
    # Otimizacao gananciosa (greedy)
    # ------------------------------------------------------------------

    def otimizar(self) -> ResultadoOtimizacao:
        """
        Executa a otimizacao greedy.

        Estrategia
        ----------
        1. Enumera combinacoes validas.
        2. Calcula potencial de cada combo:
               min(estoque[modelo][valor_classe]) para cada modelo fixo.
        3. Ordena por potencial decrescente.
        4. Aloca greedily, consumindo o saldo do estoque.
        5. Acumula producao necessaria do Modelo otimizado por classe.
        """
        estoque_inicial = EstoqueMercado(
            niveis={m: dict(banco) for m, banco in self.estoque.niveis.items()}
        )

        combinacoes = self.enumerar_combinacoes()
        if not combinacoes:
            return ResultadoOtimizacao(
                producao_otimizado={},
                montagens_por_combinacao=[],
                estoque_inicial=estoque_inicial,
                modelos_fixos=[m.nome for m in self.modelos_fixos],
                nome_otimizado=self.modelo_otimizado.nome,
            )

        # Saldo mutavel: { nome_modelo -> { valor_dimensional -> quantidade } }
        nomes_fixos = [m.nome for m in self.modelos_fixos]
        saldo: Dict[str, Dict[float, int]] = {
            m: {round(v, 6): q for v, q in self.estoque.niveis.get(m, {}).items()}
            for m in nomes_fixos
        }

        def potencial(combo: CombinacaoMontagem) -> int:
            return min(
                saldo[m].get(round(cls.valor, 6), 0)
                for m, cls in combo.classes_fixos.items()
            )

        combinacoes_ordenadas = sorted(combinacoes, key=potencial, reverse=True)

        montagens: List[Tuple[CombinacaoMontagem, int]] = []
        producao_ot: Dict[ClasseDimensional, int] = {}

        for combo in combinacoes_ordenadas:
            qtd = potencial(combo)
            if qtd <= 0:
                continue

            # Consome saldo
            for m, cls in combo.classes_fixos.items():
                chave = round(cls.valor, 6)
                saldo[m][chave] = saldo[m].get(chave, 0) - qtd

            # Acumula producao do otimizado
            cls_ot = combo.classe_otimizado
            producao_ot[cls_ot] = producao_ot.get(cls_ot, 0) + qtd

            montagens.append((combo, qtd))

        return ResultadoOtimizacao(
            producao_otimizado=producao_ot,
            montagens_por_combinacao=montagens,
            estoque_inicial=estoque_inicial,
            modelos_fixos=nomes_fixos,
            nome_otimizado=self.modelo_otimizado.nome,
        )
