# Funcionalidade futura: avanço físico da obra na assinatura

*Status: ideia, não agendada. [English version](physical-progress.md)*

## O que o modelo faz hoje

A única dimensão de tempo de um imóvel é **meses restantes até a entrega**. Ela não diz
nada sobre quanto da obra já está pronta. Os juros de obra são modelados como se o banco
liberasse o saldo financiado **uniformemente pelos meses restantes**: após k de N meses,
k/N do saldo corrigido pelo INCC foi liberado e o comprador paga a taxa do banco sobre ele.

```
fração_liberada(k) = k / N                      N = meses restantes
juros(k)           = saldo(k) × fração_liberada(k) × taxa_banco_mensal
```

É deliberadamente simples e coerente com a entrada: um imóvel "a 4 meses da entrega" é
descrito só por esses 4 meses. Uma versão anterior tinha um campo "obra X% concluída na
assinatura"; foi removido porque contradiz o significado do campo de meses (um prédio a
4 meses da entrega nunca está 0% concluído) e porque o comprador raramente conhece o
número com precisão.

## O que a funcionalidade acrescentaria

No crédito associativo da Caixa o banco libera recursos à construtora proporcionalmente
ao **avanço físico medido** da obra, não ao tempo decorrido. Quem assina com o prédio já
80% construído começa pagando juros sobre ~80% do saldo financiado desde o primeiro mês.
Para o SO (R$ 300 mil, 4 meses restantes) é a diferença entre ≈ R$ 4.987 (liberação
uniforme) e ≈ R$ 7.363 (80% na assinatura) de juros de obra — cerca de 48% a mais.

Entradas possíveis, da menos à mais exigente para o usuário:

1. **Duração total da obra** (ex.: 36 meses) → o avanço na assinatura é inferido como
   `1 − meses_restantes / duração_total`, depois linear até 100%.
2. **Avanço na assinatura (%)** conforme o relatório mensal da construtora.
3. **Uma curva de avanço** (curva S ou cronograma publicado) em vez de linear.

## Impacto no código

- `SimulationInput`: um campo opcional (`total_construction_months` ou `progress_at_signing_pct`).
- `app/models/construction.py`: `LinearRelease` já é o ponto de extensão — adicionar uma
  estratégia `ProgressRelease` com `at(month)` e usá-la quando a entrada for informada.
- Features: novo Esquema do Cenário em `construction_interest` ("um prédio já adiantado
  paga mais juros desde o primeiro dia"); os números de referência acima já estão calculados.
- API/front-end: um campo opcional com texto de ajuda indicando onde achar o número.
