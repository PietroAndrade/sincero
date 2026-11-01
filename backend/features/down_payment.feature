@construction @down-payment
@allure.label.parentSuite:ConstructionPhase
Feature: Down payment owed to the developer during construction
  The developer requires a percentage of the list price as down payment (entrada).
  Whatever the buyer pays at signing (FGTS or cash) is deducted immediately; the rest
  is split into equal nominal installments until delivery, each one corrected by the
  INCC accumulated up to the month it is paid.

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And a property "RA" listed at R$ 440,000.00 with 19 months remaining until delivery
    And the developer requires a down payment of 20.0% of the list price

  @allure.label.suite:DownPayment @allure.label.subSuite:Upfront
  Scenario: FGTS paid at signing is deducted before the down payment is split into installments
    Given the buyer pays R$ 13,000.00 of FGTS upfront
    When the buyer runs the simulation
    Then the required down payment should be R$ 88,000.00
    And the down payment balance to be paid during construction should be R$ 75,000.00
    And the nominal monthly developer installment should be R$ 3,947.37

  @incc
  @allure.label.suite:DownPayment @allure.label.subSuite:InccCorrection
  Scenario: Every developer installment grows with the INCC accumulated until it is paid
    Given the buyer pays R$ 13,000.00 of FGTS upfront
    When the buyer runs the simulation
    Then the developer installment in month 1 should be R$ 3,969.69
    And the developer installment in month 19 should be R$ 4,393.72
    And the total paid to the developer during construction should be R$ 79,387.99
    And the INCC correction on the down payment should be R$ 4,387.99

  @what-if @more-cash
  @allure.label.suite:DownPayment @allure.label.subSuite:MoreCash
  Scenario Outline: More cash at signing lowers the developer installment and, beyond the down payment, the financed balance
    Given the buyer pays R$ 13,000.00 of FGTS upfront
    And the buyer pays R$ <cash> in cash upfront
    When the buyer runs the simulation
    Then the down payment balance to be paid during construction should be R$ <remaining>
    And the nominal monthly developer installment should be R$ <installment>
    And the nominal mortgage balance should be R$ <mortgage_balance>

    Examples:
      | cash       | remaining | installment | mortgage_balance |
      | 0.00       | 75,000.00 | 3,947.37    | 352,000.00       |
      | 30,000.00  | 45,000.00 | 2,368.42    | 352,000.00       |
      | 75,000.00  | 0.00      | 0.00        | 352,000.00       |
      | 100,000.00 | 0.00      | 0.00        | 327,000.00       |

  @allure.label.suite:DownPayment @allure.label.subSuite:NoUpfront
  Scenario: Without any upfront payment the whole down payment is split into installments
    When the buyer runs the simulation
    Then the down payment balance to be paid during construction should be R$ 88,000.00
    And the nominal monthly developer installment should be R$ 4,631.58
