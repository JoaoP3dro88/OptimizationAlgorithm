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
    estoque_final               : Saldo remanescente apos todas as montagens.
    modelos_fixos               : Nomes dos Modelos fixos.
    nome_otimizado              : Nome do Modelo que foi otimizado.
    """

    producao_otimizado: Dict[ClasseDimensional, int]
    montagens_por_combinacao: List[Tuple[CombinacaoMontagem, int]]
    estoque_inicial: EstoqueMercado
    estoque_final: Dict[str, Dict[float, int]]
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

        linhas.append("\nEstoque final (saldo remanescente):")
        for modelo, banco in self.estoque_final.items():
            linhas.append(f"\n  {modelo}:")
            total_restante = sum(q for q in banco.values() if q > 0)
            for val, qtd in sorted(banco.items()):
                if qtd > 0:
                    linhas.append(f"    {val:.4f} mm : {qtd} pecas")
            linhas.append(f"    Total restante: {total_restante} pecas")

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

        # Mapa de lookup do modelo otimizado: valor -> ClasseDimensional
        self._mapa_otimizado: Dict[float, ClasseDimensional] = {
            round(c.valor, 6): c for c in self._classes_otimizado
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

        Estrategia O(N^k) puro com lookup O(1):
        Para cada combo dos fixos, calcula soma_int (inteiro escalado).
        Para cada classe do PF, o valor necessario do otimizado e:
            dim_ot = soma - pf   (relacao 1: soma - ot = pf)
            dim_ot = pf - soma   (relacao 2: soma + ot = pf)
        Ambos sao testados via dict lookup — sem nenhum loop sobre otimizado.
        Como queremos no maximo UMA combinacao por combo fixo, paramos no
        primeiro PF que casar (preferindo relacao 1).
        """
        combinacoes: List[CombinacaoMontagem] = []

        nomes_fixos = [m.nome for m in self.modelos_fixos]
        listas: List[List[ClasseDimensional]] = [
            self._classes_fixos[n] for n in nomes_fixos
        ]
        n = len(listas)

        # Trabalha em inteiros (escala 1e6) para evitar erros de float
        ESCALA = 1_000_000
        ot_int: Dict[int, ClasseDimensional] = {
            round(c.valor * ESCALA): c for c in self._classes_otimizado
        }
        # Lista de (pf_int, ClasseDimensional) para iterar no loop
        pf_list = [(round(c.valor * ESCALA), c) for c in self._classes_pf]

        # Odometro manual sobre indices
        indices = [0] * n
        tamanhos = [len(l) for l in listas]

        while True:
            soma_int = sum(
                round(listas[i][indices[i]].valor * ESCALA)
                for i in range(n)
            )

            for pf_int, cpf in pf_list:
                # Relacao 1: ot = soma - pf
                cand = soma_int - pf_int
                cls_ot = ot_int.get(cand)
                if cls_ot is None:
                    # Relacao 2: ot = pf - soma
                    cls_ot = ot_int.get(pf_int - soma_int)

                if cls_ot is not None:
                    classes_dict = {
                        nomes_fixos[i]: listas[i][indices[i]]
                        for i in range(n)
                    }
                    combinacoes.append(CombinacaoMontagem(
                        classes_fixos=classes_dict,
                        classe_otimizado=cls_ot,
                        classe_produto_final=cpf,
                        soma_fixos=soma_int / ESCALA,
                    ))
                    break  # uma combinacao por combo fixo

            # Avanca odometro
            pos = n - 1
            while pos >= 0:
                indices[pos] += 1
                if indices[pos] < tamanhos[pos]:
                    break
                indices[pos] = 0
                pos -= 1
            if pos < 0:
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
        2. Ordena pelos combos mais PERIFERICOS primeiro:
               criterio primario  : desvio da soma dos fixos em relacao
                                    a soma dos nominais (maior desvio = mais
                                    dificil de combinar = prioridade maior).
               criterio secundario: menor potencial de estoque disponivel
                                    (classes raras antes das abundantes).
           Isso garante que as classes nos extremos da tolerancia sejam
           consumidas enquanto ainda ha parceiros, deixando as nominais
           (faceis de combinar) para fechar o saldo restante.
        3. Aloca greedily, consumindo o saldo do estoque.
        4. Acumula producao necessaria do Modelo otimizado por classe.
        """
        estoque_inicial = EstoqueMercado(
            niveis={m: dict(banco) for m, banco in self.estoque.niveis.items()}
        )

        combinacoes = self.enumerar_combinacoes()
        if not combinacoes:
            estoque_final_vazio = {
                m.nome: {round(v, 6): q for v, q in self.estoque.niveis.get(m.nome, {}).items()}
                for m in self.modelos_fixos
            }
            return ResultadoOtimizacao(
                producao_otimizado={},
                montagens_por_combinacao=[],
                estoque_inicial=estoque_inicial,
                estoque_final=estoque_final_vazio,
                modelos_fixos=[m.nome for m in self.modelos_fixos],
                nome_otimizado=self.modelo_otimizado.nome,
            )

        # Saldo mutavel: { nome_modelo -> { valor_dimensional -> quantidade } }
        nomes_fixos = [m.nome for m in self.modelos_fixos]
        saldo: Dict[str, Dict[float, int]] = {
            m: {round(v, 6): q for v, q in self.estoque.niveis.get(m, {}).items()}
            for m in nomes_fixos
        }

        # Soma dos nominais dos modelos fixos — referencia do centro
        soma_nominais = sum(m.nominal for m in self.modelos_fixos)

        def desvio_do_centro(combo: CombinacaoMontagem) -> float:
            """Distancia da soma dos fixos em relacao ao centro nominal.
            Quanto maior, mais periferica e a combinacao."""
            return abs(combo.soma_fixos - soma_nominais)

        def potencial(combo: CombinacaoMontagem) -> int:
            return min(
                saldo[m].get(round(cls.valor, 6), 0)
                for m, cls in combo.classes_fixos.items()
            )

        # Prioridade: 1) maior desvio do centro (perifericas primeiro)
        #             2) menor potencial (classes mais raras primeiro)
        combinacoes_ordenadas = sorted(
            combinacoes,
            key=lambda c: (-desvio_do_centro(c), potencial(c)),
        )

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
            estoque_final=saldo,
            modelos_fixos=nomes_fixos,
            nome_otimizado=self.modelo_otimizado.nome,
        )
