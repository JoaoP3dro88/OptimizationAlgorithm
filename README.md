# Otimizador de Sequenciamento Inteligente de AGULHA

Algoritmo de otimizacao para producao do componente **AGULHA**, com base nos estoques disponiveis de **OP**, **BICO** e **SPACER**.

---

## Cenario do Problema

O produto final e montado com **4 componentes**:

| Componente | Classes | Valor base (mm) | Passo (mm) |
|------------|---------|-----------------|------------|
| OP         | A..E    | 3.005           | 0.010      |
| BICO       | A..E    | 30.005          | 0.010      |
| SPACER     | A..E    | 40.005          | 0.010      |
| AGULHA     | A..M    | 72.690          | 0.010      |

**Restricao de qualidade:**

```
dim(OP) + dim(BICO) + dim(SPACER) + dim(AGULHA) = 73.015 +/- 0.325
```

---

## Logica do Algoritmo

**Input:**
- Estoque atual de cada classe de OP, BICO e SPACER.

**Output:**
- Quantidade de AGULHA a produzir por classe para maximizar o aproveitamento dos estoques dos outros tres componentes.

**Passos:**
1. **Enumerar combinacoes validas** - Para cada trinca (OP_i, BICO_j, SPACER_k), calcula a soma dimensional e verifica qual classe de AGULHA satisfaz a restricao de qualidade.
2. **Calcular potencial** - Para cada combinacao, o maximo de montagens possiveis e `min(estoque_OP, estoque_BICO, estoque_SPACER)`.
3. **Alocar (greedy)** - Ordena as combinacoes pelo potencial (decrescente) e aloca os estoques de forma gulosa.
4. **Agregar producao de AGULHA** - Soma as quantidades necessarias por classe de AGULHA.

---

## Estrutura do Projeto

```
OptimizationAlgorithm/
+-- main.py                # Ponto de entrada - cenario de exemplo
+-- requirements.txt
+-- src/
|   +-- __init__.py
|   +-- models.py          # ClasseDimensional, EstoqueComponentes, CombinacaoMontagem
|   +-- optimizer.py       # OtimizadorAgulha, ResultadoOtimizacao
+-- tests/
    +-- test_models.py
    +-- test_optimizer.py
```

---

## Execucao Rapida

```bash
pip install -r requirements.txt
python main.py
```

### Saida esperada

```
=== Estoque de Componentes ===
  OP    : A=396  B=384  C=389  D=427  E=404
  BICO  : A=50   B=396  C=384  D=389  E=427
  SPACER: A=374  B=390  C=417  D=397  E=422

Total de combinacoes validas (OP x BICO x SPACER -> AGULHA): 125

=======================================================
  RESULTADO DA OTIMIZACAO
=======================================================
  Total de montagens planejadas : XXXX

  Producao de AGULHA necessaria:
    Classe C  ->   XXX unidades
    Classe D  ->   XXX unidades
    ...
```

---

## Testes

```bash
python -m pytest tests/ -v
```

---

## Conceitos-chave

| Classe | Descricao |
|--------|-----------|
| `ClasseDimensional` | Valor nominal de uma classe de um componente. |
| `EstoqueComponentes` | Estoque de classes de OP, BICO e SPACER. |
| `CombinacaoMontagem` | Trinca valida (OP, BICO, SPACER) com a classe de AGULHA correspondente. |
| `OtimizadorAgulha` | Motor de otimizacao greedy. |
| `ResultadoOtimizacao` | Plano de producao de AGULHA e estatisticas de aproveitamento. |
