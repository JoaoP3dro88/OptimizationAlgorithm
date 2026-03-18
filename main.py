from src.models import (
    CLASSES_OP,
    CLASSES_BICO,
    CLASSES_SPACER,
    CLASSES_AGULHA,
    EstoqueComponentes,
)
from src.optimizer import OtimizadorAgulha


def montar_estoque_exemplo() -> EstoqueComponentes:
    """
    Cria um exemplo de estoque com distribuicao realista de classes.
    Valores inspirados nos dados da aba 'Geral' do SequenciamentoInteligente.xlsm.
    """
    return EstoqueComponentes(
        op={"A": 410, "B": 391, "C": 383, "D": 409, "E": 407},
        bico={"A": 396, "B": 384, "C": 389, "D": 427, "E": 404},
        spacer={"A": 374, "B": 390, "C": 417, "D": 397, "E": 422},
    )


def main() -> None:
    estoque = montar_estoque_exemplo()

    print(estoque.resumo())
    print()

    print("Classes de OP     :", [f"{c.nome}={c.valor:.4f}" for c in CLASSES_OP])
    print("Classes de BICO   :", [f"{c.nome}={c.valor:.4f}" for c in CLASSES_BICO])
    print("Classes de SPACER :", [f"{c.nome}={c.valor:.4f}" for c in CLASSES_SPACER])
    print("Classes de AGULHA :", [f"{c.nome}={c.valor:.4f}" for c in CLASSES_AGULHA])
    print()

    otimizador = OtimizadorAgulha(estoque=estoque)

    combinacoes = otimizador.enumerar_combinacoes()
    print(f"Total de combinacoes validas (OP x BICO x SPACER -> AGULHA): {len(combinacoes)}")
    print()

    resultado = otimizador.otimizar()
    print(resultado.resumo())


if __name__ == "__main__":
    main()
