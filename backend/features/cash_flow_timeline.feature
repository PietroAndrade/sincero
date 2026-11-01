@overview @timeline
@allure.label.parentSuite:Overview
Feature: Monthly cash flow timeline
  Month 0 is the signing (upfront payments). Months 1..N are the construction phase
  (developer installments, balloon payments and construction interest). From month
  N+1 on only the bank installment is paid.

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And a property "RA" listed at R$ 440,000.00 with 19 months remaining until delivery
    And the developer requires a down payment of 20.0% of the list price

  @allure.label.suite:Timeline @allure.label.subSuite:DoubleBilling
  Scenario: The timeline shows where developer bills end and bank bills begin
    Given the buyer pays R$ 13,000.00 of FGTS upfront
    And the buyer pays the developer R$ 2,500.00 per month
    And the contract has balloon payments in months 6 and 12
    When the buyer runs the simulation
    Then the timeline should have 380 months
    And the timeline in month 0 should be:
      | developer_installment | balloon | construction_interest | bank_installment | total     |
      | 0.00                  | 0.00    | 0.00                  | 0.00             | 13,000.00 |
    And the timeline in month 6 should be:
      | developer_installment | balloon   | construction_interest | bank_installment | total     |
      | 2,586.02              | 14,223.11 | 939.69                | 0.00             | 17,748.82 |
    And the timeline in month 19 should be:
      | developer_installment | balloon | construction_interest | bank_installment | total    |
      | 2,782.69              | 0.00    | 3,201.99              | 0.00             | 5,984.68 |
    And the timeline in month 20 should be:
      | developer_installment | balloon | construction_interest | bank_installment | total    |
      | 0.00                  | 0.00    | 0.00                  | 4,290.33         | 4,290.33 |

  @allure.label.suite:Timeline @allure.label.subSuite:PeakMonth
  Scenario: The balloon month is the hardest month of the construction phase
    Given the buyer pays R$ 13,000.00 of FGTS upfront
    And the buyer pays the developer R$ 2,500.00 per month
    And the contract has balloon payments in months 6 and 12
    When the buyer runs the simulation
    Then the peak monthly outflow should be R$ 19,331.55 in month 12
    And the total outflow during the construction phase should be R$ 123,179.77
