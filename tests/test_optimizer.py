"""Testes unitarios para o otimizador generico de producao."""

import pytest

from src.models import (
    ClasseDimensional,
    EstoqueMercado,
    Modelo,
    ProdutoFinal,
)
from src.optimizer import Otimizador, ResultadoOtimizacao


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _modelos_padrao():
    """Retorna os 4 modelos do cenario OP/BICO/SPACER/AGULHA."""
    op     = Modelo(nome="OP",     nominal=3.025,  tolerancia=0.020, step=0.010)
    bico   = Modelo(nome="BICO",   nominal=30.025, tolerancia=0.020, step=0.010)
    spacer = Modelo(nome="SPACER", nominal=40.025, tolerancia=0.020, step=0.010)
    agulha = Modelo(nome="AGULHA", nominal=72.750, tolerancia=0.060, step=0.010)
    return op, bico, spacer, agulha


def _produto_final_padrao() -> ProdutoFinal:
    """OP + BICO + SPACER - AGULHA = 0.325 exato."""
    return ProdutoFinal(nominal=0.325, tolerancia=0.000, step=0.001)


def _estoque_por_valor(op_qtds, bico_qtds, spacer_qtds) -> EstoqueMercado:
    """
    Cria EstoqueMercado com chaves por valor dimensional (float).
    op_qtds / bico_qtds / spacer_qtds: list de int, uma por classe (A, B, C, D, E).
    """
    op_vals     = [3.005, 3.015, 3.025, 3.035, 3.045]
    bico_vals   = [30.005, 30.015, 30.025, 30.035, 30.045]
    spacer_vals = [40.005, 40.015, 40.025, 40.035, 40.045]
    return EstoqueMercado(niveis={
        "OP":     {v: q for v, q in zip(op_vals,     op_qtds)},
        "BICO":   {v: q for v, q in zip(bico_vals,   bico_qtds)},
        "SPACER": {v: q for v, q in zip(spacer_vals, spacer_qtds)},
    })


@pytest.fixture()
def estoque_balanceado() -> EstoqueMercado:
    return _estoque_por_valor(
        [100, 100, 100, 100, 100],
        [100, 100, 100, 100, 100],
        [100, 100, 100, 100, 100],
    )


@pytest.fixture()
def estoque_simples() -> EstoqueMercado:
    """Estoque minimo: apenas classe A (menor valor) de cada modelo fixo."""
    return _estoque_por_valor([10, 0, 0, 0, 0], [10, 0, 0, 0, 0], [10, 0, 0, 0, 0])


@pytest.fixture()
def otimizador_balanceado(estoque_balanceado) -> Otimizador:
    op, bico, spacer, agulha = _modelos_padrao()
    return Otimizador(
        modelos_fixos=[op, bico, spacer],
        modelo_otimizado=agulha,
        produto_final=_produto_final_padrao(),
        estoque=estoque_balanceado,
    )


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

    def test_quantidade_combinacoes_validas(self, otimizador_balanceado):
        """5x5x5 = 125 combos fixos, cada uma tem exatamente 1 classe AGULHA valida."""
        combs = otimizador_balanceado.enumerar_combinacoes()
        assert len(combs) == 125

    def test_classe_otimizado_eh_ClasseDimensional(self, otimizador_balanceado):
        for comb in otimizador_balanceado.enumerar_combinacoes():
            assert isinstance(comb.classe_otimizado, ClasseDimensional)

    def test_classe_otimizado_valida(self, otimizador_balanceado):
        _, _, _, agulha = _modelos_padrao()
        valores_agulha = {round(c.valor, 6) for c in agulha.gerar_classes()}
        for comb in otimizador_balanceado.enumerar_combinacoes():
            assert round(comb.classe_otimizado.valor, 6) in valores_agulha

    def test_montagem_satisfaz_produto_final(self, otimizador_balanceado):
        """Para cada combo: soma_fixos - dim_otimizado deve estar nas classes do PF."""
        pf = _produto_final_padrao()
        valores_pf = {round(c.valor, 6) for c in pf.gerar_classes()}
        for comb in otimizador_balanceado.enumerar_combinacoes():
            resultado = round(comb.soma_fixos - comb.classe_otimizado.valor, 6)
            assert resultado in valores_pf, (
                f"{comb}: resultado {resultado} nao esta nas classes do PF"
            )

    def test_combinacao_classe_A_op_existe(self, estoque_simples):
        op, bico, spacer, agulha = _modelos_padrao()
        otim = Otimizador(
            modelos_fixos=[op, bico, spacer],
            modelo_otimizado=agulha,
            produto_final=_produto_final_padrao(),
            estoque=estoque_simples,
        )
        combs = otim.enumerar_combinacoes()
        valores_op = {round(c.classes_fixos["OP"].valor, 6) for c in combs}
        assert round(3.005, 6) in valores_op  # classe A do OP


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

    def test_producao_otimizado_somente_classes_validas(self, otimizador_balanceado):
        _, _, _, agulha = _modelos_padrao()
        valores_agulha = {round(c.valor, 6) for c in agulha.gerar_classes()}
        res = otimizador_balanceado.otimizar()
        for cls in res.producao_otimizado:
            assert isinstance(cls, ClasseDimensional)
            assert round(cls.valor, 6) in valores_agulha

    def test_producao_soma_igual_ao_total(self, otimizador_balanceado):
        res = otimizador_balanceado.otimizar()
        assert sum(res.producao_otimizado.values()) == res.total_montagens()

    def test_nao_ultrapassa_estoque_op(self, estoque_balanceado):
        op, bico, spacer, agulha = _modelos_padrao()
        otim = Otimizador(
            modelos_fixos=[op, bico, spacer],
            modelo_otimizado=agulha,
            produto_final=_produto_final_padrao(),
            estoque=estoque_balanceado,
        )
        res = otim.otimizar()
        consumo: dict = {}
        for comb, qty in res.montagens_por_combinacao:
            v = comb.classes_fixos["OP"].valor
            consumo[v] = consumo.get(v, 0) + qty
        for v, cons in consumo.items():
            assert cons <= estoque_balanceado.qtd("OP", v)

    def test_nao_ultrapassa_estoque_bico(self, estoque_balanceado):
        op, bico, spacer, agulha = _modelos_padrao()
        otim = Otimizador(
            modelos_fixos=[op, bico, spacer],
            modelo_otimizado=agulha,
            produto_final=_produto_final_padrao(),
            estoque=estoque_balanceado,
        )
        res = otim.otimizar()
        consumo: dict = {}
        for comb, qty in res.montagens_por_combinacao:
            v = comb.classes_fixos["BICO"].valor
            consumo[v] = consumo.get(v, 0) + qty
        for v, cons in consumo.items():
            assert cons <= estoque_balanceado.qtd("BICO", v)

    def test_nao_ultrapassa_estoque_spacer(self, estoque_balanceado):
        op, bico, spacer, agulha = _modelos_padrao()
        otim = Otimizador(
            modelos_fixos=[op, bico, spacer],
            modelo_otimizado=agulha,
            produto_final=_produto_final_padrao(),
            estoque=estoque_balanceado,
        )
        res = otim.otimizar()
        consumo: dict = {}
        for comb, qty in res.montagens_por_combinacao:
            v = comb.classes_fixos["SPACER"].valor
            consumo[v] = consumo.get(v, 0) + qty
        for v, cons in consumo.items():
            assert cons <= estoque_balanceado.qtd("SPACER", v)

    def test_estoque_vazio_zero_montagens(self):
        op, bico, spacer, agulha = _modelos_padrao()
        estoque_vazio = EstoqueMercado(niveis={"OP": {}, "BICO": {}, "SPACER": {}})
        otim = Otimizador(
            modelos_fixos=[op, bico, spacer],
            modelo_otimizado=agulha,
            produto_final=_produto_final_padrao(),
            estoque=estoque_vazio,
        )
        res = otim.otimizar()
        assert res.total_montagens() == 0

    def test_resumo_contem_nome_otimizado(self, otimizador_balanceado):
        res = otimizador_balanceado.otimizar()
        assert "AGULHA" in res.resumo()

    def test_aproveitamento_entre_0_e_1(self, otimizador_balanceado):
        res = otimizador_balanceado.otimizar()
        for m in ["OP", "BICO", "SPACER"]:
            a = res.aproveitamento(m)
            assert 0.0 <= a <= 1.0


# ---------------------------------------------------------------------------
# Testes de integracao (cenario realista)
# ---------------------------------------------------------------------------

class TestCenarioRealista:
    def test_cenario_estoque_real(self):
        """
        Verifica que o algoritmo produz 2000 montagens com 100% de aproveitamento
        usando o estoque real fornecido pelo usuario (por valor dimensional).
        """
        op, bico, spacer, agulha = _modelos_padrao()
        estoque = _estoque_por_valor(
            [410, 391, 383, 409, 407],  # OP:    3.005..3.045
            [396, 384, 389, 427, 404],  # BICO:  30.005..30.045
            [374, 390, 417, 397, 422],  # SPACER:40.005..40.045
        )
        otim = Otimizador(
            modelos_fixos=[op, bico, spacer],
            modelo_otimizado=agulha,
            produto_final=_produto_final_padrao(),
            estoque=estoque,
        )
        res = otim.otimizar()

        assert res.total_montagens() == 2000

        for m in ["OP", "BICO", "SPACER"]:
            assert res.aproveitamento(m) == pytest.approx(1.0, abs=1e-6), (
                f"Aproveitamento de {m} deve ser 100%"
            )

    def test_classes_produto_final_nas_combinacoes(self):
        """Todas as combinacoes devem referenciar uma ClasseDimensional valida do PF."""
        op, bico, spacer, agulha = _modelos_padrao()
        pf = _produto_final_padrao()
        estoque = _estoque_por_valor(
            [10, 10, 10, 10, 10],
            [10, 10, 10, 10, 10],
            [10, 10, 10, 10, 10],
        )
        otim = Otimizador(
            modelos_fixos=[op, bico, spacer],
            modelo_otimizado=agulha,
            produto_final=pf,
            estoque=estoque,
        )
        valores_pf = {round(c.valor, 6) for c in pf.gerar_classes()}
        for comb in otim.enumerar_combinacoes():
            assert isinstance(comb.classe_produto_final, ClasseDimensional)
            assert round(comb.classe_produto_final.valor, 6) in valores_pf
