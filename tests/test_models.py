"""Testes unitarios para os modelos de dominio."""

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


class TestClasseDimensional:
    def test_nome_e_valor(self):
        c = ClasseDimensional(nome="A", valor=3.005)
        assert c.nome == "A"
        assert c.valor == pytest.approx(3.005)

    def test_frozen(self):
        c = ClasseDimensional(nome="B", valor=3.015)
        with pytest.raises(Exception):
            c.nome = "X"  # type: ignore[misc]


class TestGerarClasses:
    def test_quantidade(self):
        classes = gerar_classes(valor_inicial=10.0, passo=0.01, nomes=["A", "B", "C"])
        assert len(classes) == 3

    def test_valores_incrementais(self):
        classes = gerar_classes(valor_inicial=3.005, passo=0.010, nomes=["A", "B", "C", "D", "E"])
        for i, c in enumerate(classes):
            assert c.valor == pytest.approx(3.005 + i * 0.010, abs=1e-6)

    def test_nomes_corretos(self):
        classes = gerar_classes(valor_inicial=1.0, passo=0.1, nomes=["X", "Y", "Z"])
        assert [c.nome for c in classes] == ["X", "Y", "Z"]


class TestClassesPadrao:
    def test_op_tem_5_classes(self):
        assert len(CLASSES_OP) == 5

    def test_bico_tem_5_classes(self):
        assert len(CLASSES_BICO) == 5

    def test_spacer_tem_5_classes(self):
        assert len(CLASSES_SPACER) == 5

    def test_agulha_tem_13_classes(self):
        assert len(CLASSES_AGULHA) == 13

    def test_agulha_classes_A_ate_M(self):
        nomes = [c.nome for c in CLASSES_AGULHA]
        assert nomes == list("ABCDEFGHIJKLM")


class TestEstoqueComponentes:
    def _estoque(self):
        return EstoqueComponentes(
            op={"A": 100, "B": 200},
            bico={"A": 50, "C": 150},
            spacer={"D": 300},
        )

    def test_qtd_op_existente(self):
        e = self._estoque()
        assert e.qtd_op("A") == 100

    def test_qtd_op_inexistente(self):
        e = self._estoque()
        assert e.qtd_op("Z") == 0

    def test_total_op(self):
        e = self._estoque()
        assert e.total_op() == 300

    def test_total_bico(self):
        e = self._estoque()
        assert e.total_bico() == 200

    def test_total_spacer(self):
        e = self._estoque()
        assert e.total_spacer() == 300

    def test_resumo_contem_componentes(self):
        e = self._estoque()
        r = e.resumo()
        assert "OP" in r
        assert "BICO" in r
        assert "SPACER" in r
