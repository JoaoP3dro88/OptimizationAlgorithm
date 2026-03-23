"""
Exemplo de uso do otimizador de sequenciamento de montagem.

Como usar
---------
1. Defina cada Modelo com seu nominal, tolerancia e step.
   Isso gera as classes automaticamente (A, B, C, ...).

2. Informe o estoque de CADA MODELO FIXO por VALOR DIMENSIONAL real.
   Ex.: se o OP tem nominal=3.025 e tol=0.020, as classes possiveis sao:
        A=3.005  B=3.015  C=3.025  D=3.035  E=3.045
   O estoque e informado assim:
        "OP": {3.005: 410, 3.015: 391, 3.025: 383, 3.035: 409, 3.045: 407}

3. Defina o Produto Final (nominal, tolerancia, step da soma resultante).

4. Escolha qual Modelo quer otimizar (calcular producao necessaria).
   Os demais modelos sao os "fixos" (estoque de mercado disponivel).

5. Execute o Otimizador.
"""

from src.models import EstoqueMercado, Modelo, ProdutoFinal
from src.optimizer import Otimizador

# ---------------------------------------------------------------------------
# 1. Definicao dos Modelos (nominal, tolerancia, step)
#    O algoritmo gera as classes automaticamente a partir desses parametros.
# ---------------------------------------------------------------------------

op     = Modelo(nome="OP",     nominal=3.025,  tolerancia=0.020, step=0.010)
bico   = Modelo(nome="BICO",   nominal=30.025, tolerancia=0.020, step=0.010)
spacer = Modelo(nome="SPACER", nominal=40.025, tolerancia=0.020, step=0.010)
agulha = Modelo(nome="AGULHA", nominal=72.750, tolerancia=0.060, step=0.010)

# Classes geradas automaticamente — so para visualizacao:
print("=== Classes geradas por Modelo ===")
for m in [op, bico, spacer, agulha]:
    cls = m.gerar_classes()
    nomes_vals = "  ".join(f"{c.nome}={c.valor:.3f}" for c in cls)
    print(f"  {m.nome:8s}: {nomes_vals}")
print()

# ---------------------------------------------------------------------------
# 2. Estoque de mercado — informado por VALOR DIMENSIONAL real de cada classe
#    (apenas para os modelos fixos, ou seja, todos exceto o otimizado)
# ---------------------------------------------------------------------------
#
#  OP:     A=3.005  B=3.015  C=3.025  D=3.035  E=3.045
#  BICO:   A=30.005 B=30.015 C=30.025 D=30.035 E=30.045
#  SPACER: A=40.005 B=40.015 C=40.025 D=40.035 E=40.045

estoque = EstoqueMercado(
    niveis={
        "OP": {
            3.005: 410,
            3.015: 391,
            3.025: 383,
            3.035: 409,
            3.045: 407,
        },
        "BICO": {
            30.005: 396,
            30.015: 384,
            30.025: 389,
            30.035: 427,
            30.045: 404,
        },
        "SPACER": {
            40.005: 374,
            40.015: 390,
            40.025: 417,
            40.035: 397,
            40.045: 422,
        },
    }
)

# ---------------------------------------------------------------------------
# 3. Produto Final
#    Formula: OP + BICO + SPACER - AGULHA = 0.325 mm (exato)
# ---------------------------------------------------------------------------

produto_final = ProdutoFinal(nominal=0.325, tolerancia=0.000, step=0.001)

# ---------------------------------------------------------------------------
# 4. Execucao — otimizar producao de AGULHA
# ---------------------------------------------------------------------------

otimizador = Otimizador(
    modelos_fixos=[op, bico, spacer],   # modelos com estoque disponivel
    modelo_otimizado=agulha,             # modelo a ser produzido/otimizado
    produto_final=produto_final,
    estoque=estoque,
)

print(estoque.resumo())
print()

combinacoes = otimizador.enumerar_combinacoes()
print(f"Combinacoes validas encontradas: {len(combinacoes)}")
print()

resultado = otimizador.otimizar()
print(resultado.resumo())
