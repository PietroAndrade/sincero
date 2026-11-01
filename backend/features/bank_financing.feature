@financing @bank
@allure.label.parentSuite:FinancingPhase
Feature: Bank financing after key handover
  At delivery the INCC-corrected mortgage balance is financed by the bank over the
  contracted term, either by SAC (constant amortization, decreasing installments) or
  by PRICE (fixed installment). The bank requires the first installment to fit within
  a share of the household income.

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And a property "RA" listed at R$ 440,000.00 with 19 months remaining until delivery
    And the developer requires a down payment of 20.0% of the list price

  @sac
  @allure.label.suite:Amortization @allure.label.subSuite:SAC
  Scenario: SAC installments start high and decrease every month
    When the buyer runs the simulation
    Then the SAC monthly amortization should be R$ 1,088.34
    And the SAC installment in month 1 should be R$ 4,290.33
    And the SAC installment in month 2 should be R$ 4,281.44
    And the SAC installment in month 180 should be R$ 2,698.23
    And the SAC installment in month 360 should be R$ 1,097.23
    And the total interest paid under SAC should be R$ 577,959.37

  @price
  @allure.label.suite:Amortization @allure.label.subSuite:PRICE
  Scenario: PRICE keeps the installment fixed but costs more interest in total
    When the buyer runs the simulation
    Then the PRICE installment should be R$ 3,382.59
    And the PRICE interest in month 1 should be R$ 3,201.99
    And the PRICE amortization in month 1 should be R$ 180.60
    And the total interest paid under PRICE should be R$ 825,929.20

  @income
  @allure.label.suite:Income @allure.label.subSuite:MinimumIncome
  Scenario: The minimum income follows from the first installment and the bank's income ceiling
    Given the bank accepts installments up to 30% of the household income
    When the buyer runs the simulation
    Then the minimum income for SAC should be R$ 14,301.10
    And the minimum income for PRICE should be R$ 11,275.29

  @what-if
  @allure.label.suite:Amortization @allure.label.subSuite:LowerIncc
  Scenario: A lower INCC during construction also lowers the bank installment
    Given INCC at 4.00% per year and bank financing at 10.26% per year over 360 months
    When the buyer runs the simulation
    Then the SAC installment in month 1 should be R$ 4,101.44
