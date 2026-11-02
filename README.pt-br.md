# SINCERO — Simulador de custo de apartamento na planta (Brasil)

**Simulador de Impacto do INCC no Custo pela Evolução Real da Obra**

🇬🇧 [English version](README.md)

O SINCERO mostra o custo real de comprar um apartamento na planta: a correção do INCC
sobre tudo o que ainda se deve durante a obra, os juros de obra cobrados pelo banco, os
custos de cartório, as parcelas SAC/PRICE após as chaves, o gap de crédito no repasse
("o gatilho da Caixa") — e o que muda quando se coloca mais dinheiro na mesa.

> Exemplo: um apartamento de R$ 440.000 com entrega em 19 meses, 20% de entrada e
> R$ 13.000 de FGTS na assinatura → R$ 86.155 (19,6%) acima do preço de tabela antes da
> primeira parcela do banco, e o banco precisa aprovar R$ 39.802 a mais do que pré-aprovou.

## Estrutura do projeto

```
.
├── backend/                  Python (MVC) — models, views, controllers, suíte behave
│   ├── app/models/           modelo de domínio (Python puro)
│   ├── app/views/            payload JSON (contrato da API / front-end) e relatório em texto
│   ├── app/controllers/      CLI hoje; API Flask no marco 5
│   ├── features/             especificação executável (Gherkin, inglês) + steps do behave
│   ├── features_pt_br/       os mesmos cenários em português — apenas documentação, não executados
│   ├── support/              biblioteca de apoio do behave (sem imports do behave)
│   └── tests/                testes unitários pytest
├── docs/                     notas de projeto e funcionalidades futuras
├── context.md, handoff-*.md  contexto de negócio original
└── ROADMAP.md                marcos e decisões
```

## Executando a aplicação

Requisito: Python 3.11+.

```bash
cd backend
pip install -r requirements-dev.txt        # runtime + behave + pytest
```

### Linha de comando (disponível agora)

```bash
# Os cinco imóveis de referência (SO, F, SV, F4, RA) com 20% de entrada e R$ 13.000 de FGTS
python cli.py

# Um imóvel: preço, meses RESTANTES até a entrega, FGTS, parcela mensal à construtora e os meses com
# parcela balão — o VALOR do balão é derivado, nunca digitado
python cli.py --name RA --price 440000 --months 19 --fgts 13000 \
              --installment 2500 --balloon-month 6 --balloon-month 12

# Simulação "com mais dinheiro": o mesmo contrato com valores crescentes na assinatura
python cli.py --price 440000 --months 19 --fgts 13000 --cash-ladder 0,30000,75000,100000

# Custos de cartório, teto de renda e prazo do pro-soluto
python cli.py --price 440000 --months 19 --itbi 3 --registry 1 --income-ratio 0.35 --pro-soluto-months 24

# Payload JSON completo (mesmo formato que a API e o front-end usarão)
python cli.py --price 440000 --months 19 --json

python cli.py --help                        # todas as opções (INCC, taxa do banco, prazo, ITBI, crédito pré-aprovado…)
```

Todas as opções:

| Opção | Significado | Padrão |
|---|---|---|
| `--price`, `--months` | preço de tabela e **meses restantes até a entrega** (tempo que falta, não a duração total da obra) | obrigatórios |
| `--down-payment-pct` | entrada exigida pela construtora (% do preço) | 20 |
| `--fgts`, `--cash` | pagos na assinatura; o excedente acima da entrada reduz o saldo financiado | 0 |
| `--installment` | valor mensal pago à construtora durante a obra | saldo ÷ meses |
| `--balloon-month` | mês de obra com balão (repetível); valor = saldo descoberto ÷ nº de balões | nenhum |
| `--incc`, `--bank-rate` | INCC e taxa do banco (% ao ano) | 7,0 e 10,26 |
| `--term` | prazo do financiamento bancário (meses) | 360 |
| `--itbi`, `--registry` | ITBI e custos de registro/escritura (% do preço) | 2,0 e 0,5 |
| `--income-ratio` | fração máxima da renda familiar que o banco aceita como parcela (0–1) | 0,30 |
| `--pre-approved` | crédito pré-aprovado pelo banco na assinatura | saldo nominal |
| `--pro-soluto-months` | meses para pagar à construtora um eventual gap de crédito | 12 |

Os padrões são definidos uma única vez, nos DTOs de entrada do modelo (`ContractData`, `MarketData`, `BankCreditData`); `--help` os exibe.

### API e front-end web

Planejados: API Flask (marco 5), front-end React + TypeScript + Plotly (marco 6),
Docker Compose (marco 7). Veja [ROADMAP.md](ROADMAP.md).

## Executando os testes

```bash
cd backend
make features                     # behave — todos os cenários de negócio (52)
make feature name=credit_gap      # um arquivo de feature
make tags tag=@more-cash          # uma fatia por tag (@construction, @financing, @what-if, @validation…)
make unit                         # pytest — invariantes do modelo, contrato da view, biblioteca de apoio
make test                         # ambos
make report                       # relatório Allure 3 (requer: npm install -g allure)
```

A suíte executa apenas as features em inglês (`backend/features/`). As traduções em
`backend/features_pt_br/` existem para leitura das partes interessadas.

## Modelo de negócio em uma tabela

| Tema | Regra |
|---|---|
| Numeração dos meses | 0 = assinatura; 1..N = os N meses restantes até a entrega; N = entrega das chaves; parcelas do banco a partir de N+1 |
| Taxas | anual → mensal por capitalização composta: `(1 + r)^(1/12) − 1` |
| Entrada | `preço × %`; FGTS + dinheiro na assinatura abatidos primeiro; o excedente reduz o saldo financiado |
| Parcelas da construtora | valor mensal escolhido pelo comprador (ou saldo ÷ N); cada pagamento no mês k × `(1 + INCC)^k` |
| Parcelas balão | **derivadas**: `(saldo da entrada − parcela × N) ÷ nº de meses de balão`, corrigidas pelo INCC no seu mês |
| Saldo do financiamento | `preço − max(entrada, pago na assinatura)`, × `(1 + INCC)^N` na entrega → "dívida fantasma do INCC" |
| Juros de obra | o banco libera o saldo uniformemente pelos meses restantes (k/N após o mês k); juros do mês k = saldo corrigido × k/N × taxa do banco; nunca amortizam. Avanço físico na assinatura: [funcionalidade futura](docs/future-features/physical-progress.pt-br.md) |
| Custos de cartório | ITBI 2,0% + registro/escritura 0,5% do preço (configuráveis) |
| Financiamento bancário | SAC e PRICE no prazo; renda mínima = primeira parcela ÷ 30% |
| Gap de crédito | `max(0, saldo corrigido − pré-aprovado)`; pro-soluto dividido linearmente nos meses escolhidos |

Detalhes e vocabulário completo dos passos: [`backend/features/README.md`](backend/features/README.md).
Estrutura técnica do backend: [`backend/README.md`](backend/README.md).
