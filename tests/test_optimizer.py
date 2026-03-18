"""Testes unitarios para o otimizador de producao de AGULHA."""

import pytest

from src.models import (
    DIFERENCA_MONTAGEM,
    ALVO_MONTAGEM,
    CLASSES_AGULHA,
    CLASSES_BICO,
    CLASSES_OP,
    CLASSES_SPACER,
    TOLERANCIA_MONTAGEM,
    ClasseDimensional,
    EstoqueComponentes,
    gerar_classes,
)
from src.optimizer import OtimizadorAgulha, ResultadoOtimizacao


# ---------------------------------------------------------------------------
# Fixtures auxiliares
# ---------------------------------------------------------------------------

@pytest.fixture()
def estoque_balanceado():
    """Estoque com quantidades iguais em todas as classes."""
    return EstoqueComponentes(
        op={c.nome: 100 for c in CLASSES_OP},
        bico={c.nome: 100 for c in CLASSES_BICO},
        spacer={c.nome: 100 for c in CLASSES_SPACER},
    )


@pytest.fixture()
def estoque_simples():
    """Estoque minimo: apenas classe A de cada componente."""
    return EstoqueComponentes(
        op={"A": 10},
        bico={"A": 10},
        spacer={"A": 10},
    )


@pytest.fixture()
def otimizador_balanceado(estoque_balanceado):
    return OtimizadorAgulha(estoque=estoque_balanceado)


# ---------------------------------------------------------------------------
# Testes de enumeracao de combinacoes
# ---------------------------------------------------------------------------

class TestEnumeracaoCombinacoes:
    def test_retorna_lista(self, otimizador_balanceado):
        combs = otimizador_balanceado.enumerar_combinacoes()
        assert isinstance(combs, list)

    def test_combinacoes_nao_vazias(self, otimizador_balanceado):
        combs = otimizador_balanceado.enumerar_combinacoes()
        assert len(combs) > 0

    def test_cada_combinacao_tem_agulha_valida(self, otimizador_balanceado):
        combs = otimizador_balanceado.enumerar_combinacoes()
        nomes_agulha = {c.nome for c in CLASSES_AGULHA}
        for comb in combs:
            assert comb.classe_agulha in nomes_agulha

    def test_montagem_dentro_da_tolerancia(self, otimizador_balanceado):
        combs = otimizador_balanceado.enumerar_combinacoes()
        for comb in combs:
            # Regra: ROUND(OP+BICO+SPACER - AGULHA, 3) == DIFERENCA_MONTAGEM
            diferenca = round(comb.soma_op_bico_spacer - comb.dim_agulha_necessaria, 3)
            assert diferenca == pytest.approx(DIFERENCA_MONTAGEM, abs=1e-6), (
                f"Combinacao {comb} invalida: diferenca={diferenca}"
            )

    def test_combinacao_simples_classe_A(self, estoque_simples):
        """
        enumerar_combinacoes retorna todas as combinacoes dimensionalmente validas
        independente do estoque. Com estoque apenas na classe A, o otimizador
        deve alocar somente combinacoes AAA.
        """
        otim = OtimizadorAgulha(estoque=estoque_simples)
        # Deve existir ao menos a combinacao A+A+A -> AGULHA_A
        combs = otim.enumerar_combinacoes()
        assert len(combs) >= 1
        nomes_op = {c.classe_op for c in combs}
        assert "A" in nomes_op

        # O otimizador so deve alocar combinacoes que tem estoque
        res = otim.otimizar()
        for comb, qty in res.montagens_por_combinacao:
            assert comb.classe_op == "A"
            assert comb.classe_bico == "A"
            assert comb.classe_spacer == "A"


# ---------------------------------------------------------------------------
# Testes do otimizador
# ---------------------------------------------------------------------------

class TestOtimizador:
    def test_retorna_resultado(self, otimizador_balanceado):
        res = otimizador_balanceado.otimizar()
        assert isinstance(res, ResultadoOtimizacao)

    def test_total_montagens_positivo(self, otimizador_balanceado):
        res = otimizador_balanceado.otimizar()
        assert res.total_montagens() > 0

    def test_producao_agulha_somente_classes_validas(self, otimizador_balanceado):
        res = otimizador_balanceado.otimizar()
        nomes_agulha = {c.nome for c in CLASSES_AGULHA}
        for classe in res.producao_agulha:
            assert classe in nomes_agulha

    def test_nao_ultrapassa_estoque_op(self, estoque_balanceado):
        """O consumo de cada classe de OP nao pode superar o estoque inicial."""
        otim = OtimizadorAgulha(estoque=estoque_balanceado)
        res = otim.otimizar()
        consumo_op = {}
        for comb, qty in res.montagens_por_combinacao:
            consumo_op[comb.classe_op] = consumo_op.get(comb.classe_op, 0) + qty
        for classe, consumido in consumo_op.items():
            disponivel = estoque_balanceado.qtd_op(classe)
            assert consumido <= disponivel, (
                f"OP classe {classe}: consumido {consumido} > disponivel {disponivel}"
            )

    def test_nao_ultrapassa_estoque_bico(self, estoque_balanceado):
        otim = OtimizadorAgulha(estoque=estoque_balanceado)
        res = otim.otimizar()
        consumo_bico = {}
        for comb, qty in res.montagens_por_combinacao:
            consumo_bico[comb.classe_bico] = consumo_bico.get(comb.classe_bico, 0) + qty
        for classe, consumido in consumo_bico.items():
            disponivel = estoque_balanceado.qtd_bico(classe)
            assert consumido <= disponivel

    def test_nao_ultrapassa_estoque_spacer(self, estoque_balanceado):
        otim = OtimizadorAgulha(estoque=estoque_balanceado)
        res = otim.otimizar()
        consumo_spacer = {}
        for comb, qty in res.montagens_por_combinacao:
            consumo_spacer[comb.classe_spacer] = consumo_spacer.get(comb.classe_spacer, 0) + qty
        for classe, consumido in consumo_spacer.items():
            disponivel = estoque_balanceado.qtd_spacer(classe)
            assert consumido <= disponivel

    def test_estoque_vazio_zero_montagens(self):
        estoque_vazio = EstoqueComponentes(op={}, bico={}, spacer={})
        otim = OtimizadorAgulha(estoque=estoque_vazio)
        res = otim.otimizar()
        assert res.total_montagens() == 0

    def test_resumo_contem_agulha(self, otimizador_balanceado):
        res = otimizador_balanceado.otimizar()
        r = res.resumo()
        assert "AGULHA" in r

    def test_producao_agulha_soma_igual_ao_total_montagens(self, estoque_balanceado):
        otim = OtimizadorAgulha(estoque=estoque_balanceado)
        res = otim.otimizar()
        soma_agulha = sum(res.producao_agulha.values())
        assert soma_agulha == res.total_montagens()


# ---------------------------------------------------------------------------
# Testes de integracao (cenario realista do Excel)
# ---------------------------------------------------------------------------

class TestCenarioRealista:
    def test_cenario_geral_excel(self):
        """
        Reproduz o cenario da aba 'Geral' do SequenciamentoInteligente.xlsm:
            OP:    A=396 B=384 C=389 D=427 E=404
            BICO:  A=396 B=384 C=389 D=427 E=404  (aprox.)
            SPACER:A=374 B=390 C=417 D=397 E=422
        """
        estoque = EstoqueComponentes(
            op={"A": 396, "B": 384, "C": 389, "D": 427, "E": 404},
            bico={"A": 396, "B": 384, "C": 389, "D": 427, "E": 404},
            spacer={"A": 374, "B": 390, "C": 417, "D": 397, "E": 422},
        )
        otim = OtimizadorAgulha(estoque=estoque)
        res = otim.otimizar()

        # Deve produzir montagens
        assert res.total_montagens() > 0

        # A producao de agulha deve cobrir apenas classes reais
        nomes_agulha = {c.nome for c in CLASSES_AGULHA}
        for classe in res.producao_agulha:
            assert classe in nomes_agulha

        # Restricao de estoque respeitada
        consumo_op = {}
        consumo_bico = {}
        consumo_spacer = {}
        for comb, qty in res.montagens_por_combinacao:
            consumo_op[comb.classe_op] = consumo_op.get(comb.classe_op, 0) + qty
            consumo_bico[comb.classe_bico] = consumo_bico.get(comb.classe_bico, 0) + qty
            consumo_spacer[comb.classe_spacer] = consumo_spacer.get(comb.classe_spacer, 0) + qty

        for cls, cons in consumo_op.items():
            assert cons <= estoque.qtd_op(cls)
        for cls, cons in consumo_bico.items():
            assert cons <= estoque.qtd_bico(cls)
        for cls, cons in consumo_spacer.items():
            assert cons <= estoque.qtd_spacer(cls)
