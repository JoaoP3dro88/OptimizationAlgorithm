"""Testes unitarios para os modelos de dominio (arquitetura generica)."""

import pytest

from src.models import (
    ClasseDimensional,
    CombinacaoMontagem,
    EstoqueMercado,
    Modelo,
    ProdutoFinal,
    _gerar_nomes_classes,
    _range_com_step,
)


# ---------------------------------------------------------------------------
# ClasseDimensional
# ---------------------------------------------------------------------------

class TestClasseDimensional:
    def test_nome_e_valor(self):
        c = ClasseDimensional(nome="A", valor=3.005)
        assert c.nome == "A"
        assert c.valor == pytest.approx(3.005)

    def test_frozen(self):
        c = ClasseDimensional(nome="B", valor=3.015)
        with pytest.raises(Exception):
            c.nome = "X"  # type: ignore[misc]

    def test_repr(self):
        c = ClasseDimensional(nome="C", valor=3.025)
        assert "C" in repr(c)


# ---------------------------------------------------------------------------
# _range_com_step
# ---------------------------------------------------------------------------

class TestRangeComStep:
    def test_valores_simples(self):
        vals = _range_com_step(1.0, 1.02, 0.01)
        assert vals == pytest.approx([1.0, 1.01, 1.02])

    def test_inclui_extremos(self):
        vals = _range_com_step(0.0, 0.05, 0.01)
        assert len(vals) == 6
        assert vals[0] == pytest.approx(0.0)
        assert vals[-1] == pytest.approx(0.05)

    def test_step_invalido_levanta_erro(self):
        with pytest.raises(ValueError):
            _range_com_step(0.0, 1.0, 0.0)

    def test_step_negativo_levanta_erro(self):
        with pytest.raises(ValueError):
            _range_com_step(0.0, 1.0, -0.01)


# ---------------------------------------------------------------------------
# _gerar_nomes_classes
# ---------------------------------------------------------------------------

class TestGerarNomesClasses:
    def test_primeiras_26_letras(self):
        nomes = _gerar_nomes_classes(26)
        assert nomes[0] == "A"
        assert nomes[25] == "Z"

    def test_27a_classe_eh_AA(self):
        nomes = _gerar_nomes_classes(27)
        assert nomes[26] == "AA"

    def test_quantidade_correta(self):
        assert len(_gerar_nomes_classes(13)) == 13


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------

class TestModelo:
    def _op(self) -> Modelo:
        return Modelo(nome="OP", nominal=3.025, tolerancia=0.020, step=0.010)

    def test_gera_5_classes(self):
        classes = self._op().gerar_classes()
        assert len(classes) == 5

    def test_primeira_classe_eh_nominal_menos_tol(self):
        classes = self._op().gerar_classes()
        assert classes[0].valor == pytest.approx(3.005, abs=1e-9)

    def test_ultima_classe_eh_nominal_mais_tol(self):
        classes = self._op().gerar_classes()
        assert classes[-1].valor == pytest.approx(3.045, abs=1e-9)

    def test_nomes_sequenciais(self):
        classes = self._op().gerar_classes()
        assert [c.nome for c in classes] == ["A", "B", "C", "D", "E"]

    def test_agulha_tem_13_classes(self):
        agulha = Modelo(nome="AGULHA", nominal=72.750, tolerancia=0.060, step=0.010)
        classes = agulha.gerar_classes()
        assert len(classes) == 13

    def test_agulha_classes_A_ate_M(self):
        agulha = Modelo(nome="AGULHA", nominal=72.750, tolerancia=0.060, step=0.010)
        nomes = [c.nome for c in agulha.gerar_classes()]
        assert nomes == list("ABCDEFGHIJKLM")

    def test_repr_contem_nome(self):
        assert "OP" in repr(self._op())

    def test_step_incremental(self):
        classes = self._op().gerar_classes()
        for i in range(1, len(classes)):
            delta = round(classes[i].valor - classes[i - 1].valor, 10)
            assert delta == pytest.approx(0.010, abs=1e-9)


# ---------------------------------------------------------------------------
# ProdutoFinal
# ---------------------------------------------------------------------------

class TestProdutoFinal:
    def _pf(self) -> ProdutoFinal:
        # Formula: OP+BICO+SPACER - AGULHA = 0.325 exato
        return ProdutoFinal(nominal=0.325, tolerancia=0.000, step=0.001)

    def test_gera_uma_classe_sem_tolerancia(self):
        classes = self._pf().gerar_classes()
        assert len(classes) == 1

    def test_valor_da_classe_eh_nominal(self):
        classes = self._pf().gerar_classes()
        assert classes[0].valor == pytest.approx(0.325, abs=1e-9)

    def test_pf_com_tolerancia_gera_multiplas_classes(self):
        pf = ProdutoFinal(nominal=72.000, tolerancia=0.005, step=0.001)
        classes = pf.gerar_classes()
        assert len(classes) == 11  # 71.995 a 72.005 com step 0.001

    def test_pf_extremos(self):
        pf = ProdutoFinal(nominal=72.000, tolerancia=0.005, step=0.001)
        classes = pf.gerar_classes()
        assert classes[0].valor == pytest.approx(71.995, abs=1e-9)
        assert classes[-1].valor == pytest.approx(72.005, abs=1e-9)

    def test_classe_para_valor_encontra_classe(self):
        pf = ProdutoFinal(nominal=0.325, tolerancia=0.000, step=0.001)
        classes = pf.gerar_classes()
        c = pf.classe_para_valor(0.325, classes)
        assert c is not None
        assert c.valor == pytest.approx(0.325, abs=1e-9)

    def test_classe_para_valor_fora_do_range(self):
        pf = ProdutoFinal(nominal=0.325, tolerancia=0.000, step=0.001)
        classes = pf.gerar_classes()
        c = pf.classe_para_valor(1.000, classes)
        assert c is None


# ---------------------------------------------------------------------------
# EstoqueMercado
# ---------------------------------------------------------------------------

class TestEstoqueMercado:
    def _estoque(self) -> EstoqueMercado:
        # Chaves sao valores dimensionais (float), nao rotulos de classe
        return EstoqueMercado(
            niveis={
                "OP":     {3.005: 100, 3.015: 200},
                "BICO":   {30.005: 50, 30.025: 150},
                "SPACER": {40.035: 300},
            }
        )

    def test_qtd_existente(self):
        e = self._estoque()
        assert e.qtd("OP", 3.005) == 100

    def test_qtd_inexistente_retorna_zero(self):
        e = self._estoque()
        assert e.qtd("OP", 9.999) == 0

    def test_qtd_modelo_inexistente_retorna_zero(self):
        e = self._estoque()
        assert e.qtd("AGULHA", 72.69) == 0

    def test_total_modelo(self):
        e = self._estoque()
        assert e.total("OP") == 300
        assert e.total("BICO") == 200
        assert e.total("SPACER") == 300

    def test_definir_nova_entrada(self):
        e = self._estoque()
        e.definir("OP", 3.025, 99)
        assert e.qtd("OP", 3.025) == 99

    def test_definir_novo_modelo(self):
        e = self._estoque()
        e.definir("AGULHA", 72.69, 50)
        assert e.qtd("AGULHA", 72.69) == 50

    def test_resumo_contem_modelos(self):
        r = self._estoque().resumo()
        assert "OP" in r
        assert "BICO" in r
        assert "SPACER" in r
