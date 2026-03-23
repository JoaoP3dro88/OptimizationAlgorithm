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

op     = Modelo(nome="OP",     nominal=3.025,  tolerancia=0.020, step=0.001)
bico   = Modelo(nome="BICO",   nominal=30.025, tolerancia=0.020, step=0.001)
spacer = Modelo(nome="SPACER", nominal=40.025, tolerancia=0.020, step=0.001)
agulha = Modelo(nome="AGULHA", nominal=72.750, tolerancia=0.060, step=0.001)

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
#  OP:     A=3.005 ... AO=3.045  (41 classes, step=0.001)
#  BICO:   A=30.005 ... AO=30.045 (41 classes, step=0.001)
#  SPACER: A=40.005 ... AO=40.045 (41 classes, step=0.001)

estoque = EstoqueMercado(
    niveis={
        "OP": {
            3.005: 120,  # A
            3.006: 95,   # B
            3.007: 0,    # C  (zerado)
            3.008: 84,   # D
            3.009: 110,  # E
            3.010: 73,   # F
            3.011: 89,   # G
            3.012: 0,    # H  (zerado)
            3.013: 102,  # I
            3.014: 67,   # J
            3.015: 115,  # K
            3.016: 88,   # L
            3.017: 94,   # M
            3.018: 77,   # N
            3.019: 0,    # O  (zerado)
            3.020: 131,  # P
            3.021: 58,   # Q
            3.022: 143,  # R
            3.023: 99,   # S
            3.024: 86,   # T
            3.025: 107,  # U
            3.026: 72,   # V
            3.027: 118,  # W
            3.028: 0,    # X  (zerado)
            3.029: 91,   # Y
            3.030: 104,  # Z
            3.031: 66,   # AA
            3.032: 138,  # AB
            3.033: 79,   # AC
            3.034: 93,   # AD
            3.035: 112,  # AE
            3.036: 0,    # AF  (zerado)
            3.037: 85,   # AG
            3.038: 97,   # AH
            3.039: 123,  # AI
            3.040: 61,   # AJ
            3.041: 108,  # AK
            3.042: 76,   # AL
            3.043: 0,    # AM  (zerado)
            3.044: 114,  # AN
            3.045: 90,   # AO
        },
        "BICO": {
            30.005: 105,  # A
            30.006: 88,   # B
            30.007: 116,  # C
            30.008: 0,    # D  (zerado)
            30.009: 74,   # E
            30.010: 129,  # F
            30.011: 93,   # G
            30.012: 81,   # H
            30.013: 0,    # I  (zerado)
            30.014: 107,  # J
            30.015: 62,   # K
            30.016: 134,  # L
            30.017: 98,   # M
            30.018: 77,   # N
            30.019: 112,  # O
            30.020: 0,    # P  (zerado)
            30.021: 86,   # Q
            30.022: 121,  # R
            30.023: 70,   # S
            30.024: 103,  # T
            30.025: 95,   # U
            30.026: 0,    # V  (zerado)
            30.027: 118,  # W
            30.028: 84,   # X
            30.029: 91,   # Y
            30.030: 109,  # Z
            30.031: 73,   # AA
            30.032: 127,  # AB
            30.033: 0,    # AC  (zerado)
            30.034: 88,   # AD
            30.035: 96,   # AE
            30.036: 115,  # AF
            30.037: 69,   # AG
            30.038: 0,    # AH  (zerado)
            30.039: 102,  # AI
            30.040: 83,   # AJ
            30.041: 117,  # AK
            30.042: 78,   # AL
            30.043: 94,   # AM
            30.044: 0,    # AN  (zerado)
            30.045: 111,  # AO
        },
        "SPACER": {
            40.005: 98,   # A
            40.006: 0,    # B  (zerado)
            40.007: 113,  # C
            40.008: 87,   # D
            40.009: 124,  # E
            40.010: 71,   # F
            40.011: 0,    # G  (zerado)
            40.012: 106,  # H
            40.013: 89,   # I
            40.014: 118,  # J
            40.015: 75,   # K
            40.016: 132,  # L
            40.017: 0,    # M  (zerado)
            40.018: 92,   # N
            40.019: 104,  # O
            40.020: 68,   # P
            40.021: 115,  # Q
            40.022: 83,   # R
            40.023: 0,    # S  (zerado)
            40.024: 127,  # T
            40.025: 96,   # U
            40.026: 109,  # V
            40.027: 74,   # W
            40.028: 121,  # X
            40.029: 0,    # Y  (zerado)
            40.030: 88,   # Z
            40.031: 103,  # AA
            40.032: 77,   # AB
            40.033: 136,  # AC
            40.034: 91,   # AD
            40.035: 0,    # AE  (zerado)
            40.036: 114,  # AF
            40.037: 86,   # AG
            40.038: 99,   # AH
            40.039: 72,   # AI
            40.040: 0,    # AJ  (zerado)
            40.041: 125,  # AK
            40.042: 80,   # AL
            40.043: 117,  # AM
            40.044: 93,   # AN
            40.045: 108,  # AO
        },
    }
)

# ---------------------------------------------------------------------------
# 3. Produto Final
#    Formula: OP + BICO + SPACER - AGULHA = 0.325 mm
# ---------------------------------------------------------------------------

produto_final = ProdutoFinal(nominal=0.325, tolerancia=0.005, step=0.001)

# ---------------------------------------------------------------------------
# 4. Execucao — otimizar producao de AGULHA
# ---------------------------------------------------------------------------

otimizador = Otimizador(
    modelos_fixos=[op, bico, spacer],   # modelos com estoque disponivel
    modelo_otimizado=agulha,             # modelo a ser produzido/otimizado
    produto_final=produto_final,
    estoque=estoque,
)

combinacoes = otimizador.enumerar_combinacoes()
resultado = otimizador.otimizar()

# ---------------------------------------------------------------------------
# 5. Saida — imprime no terminal E salva em resultado.txt
# ---------------------------------------------------------------------------

def _montar_saida(modelos, combinacoes, resultado) -> str:
    linhas = []

    # --- Classes de cada modelo ---
    linhas.append("=" * 60)
    linhas.append("CLASSES GERADAS POR MODELO")
    linhas.append("=" * 60)
    for m in modelos:
        cls = m.gerar_classes()
        linhas.append(f"\n  {m.nome}  ({len(cls)} classes | "
                      f"nominal={m.nominal}  tol=±{m.tolerancia}  step={m.step})")
        for c in cls:
            linhas.append(f"    {c.nome:3s}  =  {c.valor:.4f} mm")

    # --- Estoque ---
    linhas.append("")
    linhas.append(estoque.resumo())

    # --- Resultado ---
    linhas.append("")
    linhas.append(resultado.resumo())

    return "\n".join(linhas)


saida = _montar_saida([op, bico, spacer, agulha], combinacoes, resultado)

# Imprime no terminal
print(saida)

# Salva em arquivo
ARQUIVO_SAIDA = "resultado.txt"
with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
    f.write(saida)
    f.write("\n")

print(f"\nResultado salvo em: {ARQUIVO_SAIDA}")
