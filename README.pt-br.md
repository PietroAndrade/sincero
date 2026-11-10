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

O motor é TypeScript e roda **no navegador do comprador**: nenhum servidor calcula nada e nenhum
dado sai do aparelho ([decisão](docs/decisions/engine-in-the-browser.md)). O mesmo motor roda a
linha de comando e os cenários de negócio. A página web é o próximo passo ([ROADMAP.md](ROADMAP.md)).

## Estrutura do projeto

```
.
├── engine/                   @sincero/engine — o modelo e sua view JSON, TypeScript puro (sem DOM, sem dependências)
│   ├── src/                  entradas, regras, modelo, comparação, view, erros estruturados
│   ├── test/                 testes unitários e a verificação do golden master
│   └── golden/               as respostas do motor Python aposentado, congeladas: 456 casos, comparados ao bit
├── features/                 @sincero/features — a especificação executável (Gherkin, inglês), rodada pelo cucumber-js
│   ├── steps/, support/      definições dos passos, o "world" do cenário, leitura de valores e métricas
│   └── pt_br/                os mesmos cenários em português — apenas documentação, não executados
├── cli/                      @sincero/cli — a linha de comando, `npx sincero`
├── legacy/backend/           o motor Python aposentado: o oráculo do golden master (também na tag python-engine-final)
├── docs/                     decisões, planos, experimentos, funcionalidades futuras
└── ROADMAP.md                marcos e decisões
```

Um workspace npm: um `npm ci`, um `npm test`.

## Primeiros passos

Requisitos: **Node.js 24** ou mais novo (`.nvmrc`). Mais nada: sem Python, sem Docker, sem servidor.

```bash
nvm use              # Node 24: o golden master é exato ao bit no V8 >= 13.6, e o npm recusa Node mais antigo
npm ci               # também aponta o git para .githooks/ (o hook de pre-push roda npm test)
npm test             # deve sair com código 0
```

## Linha de comando

```bash
# Os cinco imóveis de referência (SO, F, SV, F4, RA) com 20% de entrada e R$ 13.000 de FGTS
npx sincero

# Um imóvel: preço, meses RESTANTES até a entrega, FGTS, parcela mensal à construtora e os meses com
# parcela balão — o VALOR do balão é derivado, nunca digitado
npx sincero --name RA --price 440000 --months 19 --fgts 13000 \
            --installment 2500 --balloon-month 6 --balloon-month 12

# Simulação "com mais dinheiro": o mesmo contrato com valores crescentes na assinatura
npx sincero --price 440000 --months 19 --fgts 13000 --cash-ladder 0,30000,75000,100000

# Custos de cartório, teto de renda e prazo do pro-soluto
npx sincero --price 440000 --months 19 --itbi 3 --registry 1 --income-ratio 0.35 --pro-soluto-months 24

# Payload JSON completo (o mesmo objeto que a página web vai ler)
npx sincero --price 440000 --months 19 --json

npx sincero --help                          # todas as opções (INCC, taxa do banco, prazo, ITBI, crédito pré-aprovado…)
```

Todas as opções:

| Opção | Significado | Padrão |
|---|---|---|
| `--price`, `--months` | preço de tabela e **meses restantes até a entrega** (tempo que falta, não a duração total da obra) | obrigatórios |
| `--name` | rótulo do imóvel | CUSTOM |
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
| `--cash-ladder` | valores em dinheiro separados por vírgula, cada um não negativo, não acima do preço, crescentes | — |
| `--json` | o payload JSON em vez do relatório em texto | — |

Os padrões são definidos uma única vez, na tabela de campos do motor (`FIELDS` em
[`engine/src/input-dto.ts`](engine/src/input-dto.ts)); `--help` os exibe. Sem `--price`, são
mostrados os imóveis de referência. Uma entrada rejeitada imprime `error: <mensagem>` e sai com
código 2, assim como uma linha de comando malformada (com a linha de uso no stderr). O relatório e
as tabelas são os da CLI Python aposentada, caractere por caractere (`cli/test/fixtures/`).

## Executando os testes

```bash
npm test                                       # typecheck + testes do motor (golden master incluso) + CLI + todos os cenários
npm run features                               # cucumber-js — todos os cenários de negócio
npm run feature -- credit_gap.feature          # um arquivo de feature (caminho relativo a features/)
npm run features -- --tags @more-cash          # uma fatia por tag (@construction, @financing, @what-if, @validation…)
npm run report                                 # relatório Allure 3 em features/allure-report/
```

O que cada camada prova:

| Camada | Onde | Falha quando |
|---|---|---|
| Golden master | `engine/test/golden.test.ts` | qualquer valor dos 456 casos difere do motor Python aposentado, mesmo no último bit; uma mudança nos valores passa por `npm run golden:update` ([protocolo](engine/README.md#changing-the-figures)) |
| Testes unitários | `engine/test/`, `cli/test/`, `features/test/` | um invariante estrutural, uma regra, um código de erro ou a saída da CLI quebra |
| Cenários de negócio | `features/*.feature` | um valor da especificação erra por mais de meio centavo, ou uma mensagem muda |

O hook de pre-push (`.githooks/pre-push`, ativado pelo `npm ci`) roda `npm test`.

A suíte executa apenas as features em inglês (`features/`). As traduções em `features/pt_br/`
existem para leitura das partes interessadas.

## Página web

Próximo passo: uma página estática (Vite + React), em português e inglês, com o motor dentro dela —
sem API, nada a hospedar além de arquivos. Depois, Playwright no caminho principal em Chromium,
Firefox e WebKit. Veja o [ROADMAP.md](ROADMAP.md) e o [plano](docs/plan/typescript-port.md).

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

Detalhes e vocabulário completo dos passos: [`features/README.md`](features/README.md). O motor, sua
API e como mudar os valores: [`engine/README.md`](engine/README.md). Documentos:
[`docs/README.md`](docs/README.md).

## Licença

Apache License 2.0. Veja [`LICENSE`](LICENSE).
