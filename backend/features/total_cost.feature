@overview @total-cost
@allure.label.parentSuite:Overview
Feature: Total cost of the apartment until key handover
  The real cost is the list price plus the INCC correction on the down payment, the
  INCC correction on the mortgage balance, the construction interest and the closing
  costs (ITBI, deed and registry).

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And a property "RA" listed at R$ 440,000.00 with 19 months remaining until delivery
    And the developer requires a down payment of 20.0% of the list price

  @allure.label.suite:TotalCost @allure.label.subSuite:Breakdown
  Scenario: The cost breakdown shows almost 20% on top of the list price
    Given the buyer pays R$ 13,000.00 of FGTS upfront
    And closing costs of ITBI 2.0% and registry 0.5% of the list price
    When the buyer runs the simulation
    Then the cost breakdown should be:
      | component             | base_value | additional | final_value |
      | Down payment          | 88,000.00  | 4,387.99   | 92,387.99   |
      | Mortgage balance      | 352,000.00 | 39,802.30  | 391,802.30  |
      | Construction interest | 0.00       | 30,965.10  | 30,965.10   |
      | Closing costs         | 0.00       | 11,000.00  | 11,000.00   |
      | Total                 | 440,000.00 | 86,155.39  | 526,155.39  |
    And the total extra cost over the list price should be 19.58%

  @allure.label.suite:TotalCost @allure.label.subSuite:ClosingCosts
  Scenario: Closing costs are split between ITBI and registry
    Given closing costs of ITBI 2.0% and registry 0.5% of the list price
    When the buyer runs the simulation
    Then the ITBI should be R$ 8,800.00
    And the registry and deed costs should be R$ 2,200.00
