# Algoritmo de Sequenciamento Inteligente de Montagem

Algoritmo de otimização que calcula a **produção necessária de um componente** (o *Modelo otimizado*) com base nos estoques reais disponíveis dos demais componentes (*Modelos fixos*), garantindo que cada montagem resultante esteja dentro da tolerância do Produto Final.

---

## 1. Contexto do Problema

Um produto final é obtido pela montagem de **N componentes**. Cada componente pertence a um *Modelo* com valor nominal e tolerância dimensional. A combinação das dimensões de todos os componentes deve resultar em um valor que caia dentro da faixa do Produto Final.

No cenário padrão implementado em `main.py`:

| Modelo  | Nominal (mm) | Tolerância (mm) | Step (mm) | Nº de classes |
|---------|-------------|-----------------|-----------|---------------|
| OP      | 3,025       | ± 0,020         | 0,001     | 41 (A → AO)   |
| BICO    | 30,025      | ± 0,020         | 0,001     | 41 (A → AO)   |
| SPACER  | 40,025      | ± 0,020         | 0,001     | 41 (A → AO)   |
| AGULHA  | 72,750      | ± 0,060         | 0,001     | 121 (A → DQ)  |

**Restrição dimensional do Produto Final:**

```
OP + BICO + SPACER − AGULHA = 0,325 ± 0,005 mm
```

O estoque de OP, BICO e SPACER é conhecido (medido por valor dimensional real). O objetivo é calcular **quantas peças de cada classe de AGULHA precisam ser produzidas** para aproveitar ao máximo esse estoque.

---

## 2. Conceitos Fundamentais

### 2.1 Classe Dimensional

Cada Modelo é dividido em classes cobrindo o intervalo `[nominal − tolerância, nominal + tolerância]` com incremento `step`. Os rótulos são atribuídos em ordem alfabética: **A, B, C, ..., Z, AA, AB, ...** (mesma lógica das colunas do Excel).

Exemplo para o OP (nominal=3,025  tol=±0,020  step=0,001):
```
A=3,005  B=3,006  C=3,007  ...  U=3,025 (nominal)  ...  AO=3,045
```

### 2.2 Estoque de Mercado

O estoque é informado pelo **valor dimensional real** de cada peça (float), não pelo rótulo de classe. Isso porque o usuário mede as peças fisicamente e informa quantas há de cada valor.

```python
EstoqueMercado(niveis={
    "OP":     {3.005: 120,  3.006: 95,  3.025: 107, ...},
    "BICO":   {30.005: 105, 30.025: 95, ...},
    "SPACER": {40.005: 98,  40.025: 96, ...},
})
```

### 2.3 Produto Final

Define a restrição de qualidade da montagem. Suas classes são todos os valores múltiplos de `step` dentro de `[nominal − tolerância, nominal + tolerância]`.

```
nominal=0,325  tol=±0,005  step=0,001  →  11 classes (A=0,320 ... K=0,330)
```

Qualquer combinação de componentes cujo resultado dimensional caia em **qualquer** uma dessas 11 classes é uma montagem válida.

---

## 3. Arquitetura do Código

```
OptimizationAlgorithm/
├── main.py                  # Ponto de entrada — define modelos, estoque e executa
├── resultado.txt            # Saída gerada automaticamente a cada execução
├── requirements.txt
├── src/
│   ├── models.py            # Todas as estruturas de dados do domínio
│   └── optimizer.py         # Lógica de enumeração e otimização
└── tests/
    ├── test_models.py        # 31 testes unitários de models.py
    └── test_optimizer.py     # 19 testes unitários de optimizer.py
```

### `src/models.py` — Estruturas de Dados

| Classe | Responsabilidade |
|--------|-----------------|
| `ClasseDimensional` | Representa uma classe: `nome` (str) + `valor` (float). Imutável (`frozen=True`). |
| `Modelo` | Define um componente: nominal, tolerância, step. Método `.gerar_classes()` gera todas as classes automaticamente. |
| `ProdutoFinal` | Define a restrição do produto montado. Método `.gerar_classes()` gera as classes válidas de resultado. |
| `EstoqueMercado` | Dicionário `{nome_modelo → {valor_dimensional → quantidade}}`. |
| `CombinacaoMontagem` | Uma combinação válida: classes dos fixos + classe do otimizado + classe do PF resultante. |

Utilitários internos:
- `_range_com_step()` — geração de sequências com aritmética inteira (evita erros de ponto flutuante)
- `_gerar_nomes_classes()` — gera A, B, ..., Z, AA, AB, ...

### `src/optimizer.py` — Lógica de Otimização

| Classe | Responsabilidade |
|--------|-----------------|
| `Otimizador` | Motor principal. Recebe os modelos fixos, o modelo otimizado, o produto final e o estoque. |
| `ResultadoOtimizacao` | Resultado completo: produção por classe, montagens realizadas, estoque inicial, estoque final, aproveitamentos. |

---

## 4. Como o Algoritmo Funciona

### Passo 1 — Enumeração de combinações válidas

**Método:** `Otimizador.enumerar_combinacoes()`

Para cada combinação possível das classes dos Modelos fixos (produto cartesiano), o algoritmo calcula:

```
dim_otimizado = soma_fixos − valor_PF
```

e verifica, via lookup O(1) em dicionário, se esse valor existe entre as classes do Modelo otimizado. Não há nenhum loop sobre as classes do otimizado — a verificação é direta.

**Complexidade:** O(N₁ × N₂ × ... × Nk × P), onde Nᵢ é o número de classes do modelo fixo i e P é o número de classes do Produto Final.

Para o cenário padrão: 41 × 41 × 41 × 11 ≈ 758.000 verificações → **~2 segundos**.

**Precisão numérica:** todos os valores são convertidos para inteiros (escala 1.000.000) antes das comparações, eliminando erros de ponto flutuante.

### Passo 2 — Priorização das combinações

As combinações são ordenadas antes da alocação por dois critérios em cascata:

**Critério 1 — Desvio do centro (primário, decrescente):**

```
desvio = |soma_fixos − soma_nominais_dos_fixos|
```

Combinações com classes nos **extremos da tolerância** são processadas **primeiro**. Classes periféricas têm poucos parceiros possíveis: se não forem consumidas enquanto há estoque compatível, sobrarão sem aproveitamento. As classes nominais são processadas **por último** — por estarem no centro, combinam com o maior número de parceiros e sempre conseguem fechar o saldo residual.

**Critério 2 — Menor estoque disponível (secundário, crescente):**

Em caso de empate no desvio, classes com menos peças em estoque são priorizadas (as mais raras antes das abundantes).

> **Consequência prática:** o saldo remanescente ao final é sempre composto por classes próximas ao nominal — as mais fáceis de aproveitar numa próxima rodada de produção. Nunca sobram classes periféricas.

### Passo 3 — Alocação greedy

**Método:** `Otimizador.otimizar()`

Para cada combinação, na ordem definida no Passo 2:

1. Calcula `qtd = min(saldo disponível de cada modelo fixo naquele combo)`
2. Se `qtd > 0`: consome `qtd` unidades de cada modelo fixo do saldo e acumula `qtd` na produção do modelo otimizado para a classe correspondente
3. Continua para a próxima combinação até esgotar todas

### Passo 4 — Geração da saída

O resultado é salvo em `resultado.txt` com quatro seções:

1. **Classes geradas** por modelo (nome, valor, contagem)
2. **Estoque inicial** por modelo
3. **Produção necessária** do modelo otimizado por classe
4. **Aproveitamento percentual** de cada modelo fixo + **estoque final** (saldo por valor dimensional)

---

## 5. Execução

### Pré-requisitos

```bash
pip install -r requirements.txt
```

### Executar

```bash
python main.py
```

O resultado é impresso no terminal e salvo automaticamente em `resultado.txt`.

### Testes

```bash
python -m pytest tests/ -v
```

50 testes unitários cobrindo todas as estruturas de dados e o comportamento completo do otimizador.

---

## 6. Como Configurar um Novo Cenário

Edite `main.py` alterando as quatro seções de configuração:

**1. Modelos** — defina nominal, tolerância e step de cada componente:
```python
op     = Modelo(nome="OP",     nominal=3.025,  tolerancia=0.020, step=0.001)
bico   = Modelo(nome="BICO",   nominal=30.025, tolerancia=0.020, step=0.001)
spacer = Modelo(nome="SPACER", nominal=40.025, tolerancia=0.020, step=0.001)
agulha = Modelo(nome="AGULHA", nominal=72.750, tolerancia=0.060, step=0.001)
```

**2. Estoque** — informe por valor dimensional real (float), não por rótulo de classe:
```python
estoque = EstoqueMercado(niveis={
    "OP":     {3.005: 120, 3.006: 95, 3.025: 107, ...},
    "BICO":   {30.005: 105, ...},
    "SPACER": {40.005: 98, ...},
})
```

**3. Produto Final** — defina o alvo e a tolerância da montagem:
```python
produto_final = ProdutoFinal(nominal=0.325, tolerancia=0.005, step=0.001)
```

**4. Escolha qual modelo otimizar:**
```python
otimizador = Otimizador(
    modelos_fixos=[op, bico, spacer],   # modelos com estoque disponível
    modelo_otimizado=agulha,             # modelo cuja produção será calculada
    produto_final=produto_final,
    estoque=estoque,
)
```

O algoritmo é **genérico** — qualquer um dos modelos pode ser o otimizado, basta movê-lo entre as listas.

---

## 7. Exemplo de Saída (`resultado.txt`)

```
============================================================
RESULTADO DA OTIMIZACAO
============================================================
Total de montagens    : 3306

Producao necessaria de AGULHA por classe:
  Classe F  (72.6950 mm):  98 pecas
  Classe J  (72.6990 mm):  73 pecas
  ...
  Classe DQ (72.8100 mm): 204 pecas

Aproveitamento do estoque dos Modelos fixos:
  OP        :  98.2%
  BICO      : 100.0%
  SPACER    :  97.5%

Estoque final (saldo remanescente):

  OP:
    3.0250 mm : 59 pecas
    Total restante: 59 pecas

  BICO:
    Total restante: 0 pecas

  SPACER:
    40.0250 mm : 42 pecas
    40.0260 mm : 43 pecas
    Total restante: 85 pecas
============================================================
```

> **Nota:** O saldo remanescente é sempre composto por classes próximas ao nominal — as mais fáceis de aproveitar em uma próxima rodada —, nunca pelas classes periféricas, que são consumidas primeiro pelo algoritmo.
