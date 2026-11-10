# Scenarios waiting for G2

*Drafts, not specification yet.* The decision record says no scenario may change before G2 (54/54
on cucumber-js), except for a bug found by the port. The rules below were built in phase 1, so
until then they are pinned by the engine's unit tests and the golden master. **G2 passed on
2026-11-09**, so they can now go into the `.feature` files, with their step definitions
(`features/steps/`): a call for whoever owns the BDD suite.

## P1.6: the cash ladder's amount rules (backlog US-07 AC4–AC5)

Pinned today by `engine/test/cash-ladder.test.ts` and the golden master's cases #429–#433 and
#450–#455. The existing scenario "A cash ladder shows what each extra real at signing buys" runs
one simulation per amount (`compare`), not the engine's `cashLadder`, so it does not reach these
rules. Both new steps below need definitions: run the amounts through `cashLadder`, and read the
refusal.

`features/scenario_comparison.feature`:

```gherkin
  @what-if @more-cash
  @allure.label.suite:Comparison @allure.label.subSuite:MoreCash
  Scenario Outline: A cash ladder names the first amount it cannot use, and shows no row
    Given a property "RA" listed at R$ 440,000.00 with 19 months remaining until delivery
    And the buyer pays R$ 13,000.00 of FGTS upfront
    When the buyer runs a cash ladder of "<amounts>"
    Then the cash ladder should be refused with the error "<error>"

    Examples:
      | amounts                       | error                                                                    |
      | 100,000.00; 0.00; 30,000.00   | cash ladder amounts must increase: R$ 0.00 comes after R$ 100,000.00     |
      | 0.00; 30,000.00; 30,000.00    | cash ladder amounts must increase: R$ 30,000.00 comes after R$ 30,000.00 |
      | 0.00; -1,000.00               | cash ladder amount R$ -1,000.00 must not be negative                     |
      | 0.00; 500,000.00              | cash ladder amount R$ 500,000.00 exceeds the list price of R$ 440,000.00 |
```

`features/pt_br/comparacao_de_cenarios.feature` (documentation, not run; the messages
translated as in `validacao_de_entradas.feature`):

```gherkin
  Esquema do Cenário: Uma escada de dinheiro aponta o primeiro valor que não pode usar, e não mostra linhas
    Dado um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E o comprador paga R$ 13.000,00 de FGTS na assinatura
    Quando o comprador monta uma escada de dinheiro com "<valores>"
    Então a escada de dinheiro deve ser recusada com o erro "<erro>"

    Exemplos:
      | valores                       | erro                                                                                  |
      | 100.000,00; 0,00; 30.000,00   | os valores da escada de dinheiro devem aumentar: R$ 0,00 vem depois de R$ 100.000,00  |
      | 0,00; 30.000,00; 30.000,00    | os valores da escada de dinheiro devem aumentar: R$ 30.000,00 vem depois de R$ 30.000,00 |
      | 0,00; -1.000,00               | o valor da escada de dinheiro de R$ -1.000,00 não pode ser negativo                    |
      | 0,00; 500.000,00              | o valor da escada de dinheiro de R$ 500.000,00 excede o preço de tabela de R$ 440.000,00 |
```

## P1.5: structured errors

No scenario: `code`, `fields` and `params` are for the UI, and the messages the scenarios pin did
not change (the golden master checks every one). US-08's scenarios (a field marked, the message in
Portuguese) belong to the UI's end-to-end suite (phase 5). The Portuguese feature files already
translate every message; they are the natural source of the UI's Portuguese table (P4.1), keyed by
the codes of `engine/src/errors.ts`.
