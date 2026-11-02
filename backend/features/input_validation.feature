@validation
@allure.label.parentSuite:Validation
Feature: Input validation
  Invalid inputs are rejected with a clear message instead of producing a misleading
  simulation.

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And the developer requires a down payment of 20.0% of the list price

  @allure.label.suite:Validation @allure.label.subSuite:PropertyData
  Scenario Outline: Impossible property data is rejected
    Given a property "X" listed at R$ <price> with <months> months remaining until delivery
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "<error>"

    Examples:
      | price      | months | error                                              |
      | 0.00       | 12     | list price must be greater than zero               |
      | 440,000.00 | 0      | months remaining until delivery must be at least 1 |

  @allure.label.suite:Validation @allure.label.subSuite:Contract
  Scenario Outline: An impossible down payment percentage is rejected
    Given a property "X" listed at R$ 440,000.00 with 19 months remaining until delivery
    And the developer requires a down payment of <percent>% of the list price
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "down payment percentage must be between 0 and 100"

    Examples:
      | percent |
      | -10     |
      | 150     |

  @allure.label.suite:Validation @allure.label.subSuite:Contract
  Scenario: Negative upfront payments are rejected
    Given a property "X" listed at R$ 440,000.00 with 19 months remaining until delivery
    And the buyer pays R$ -1,000.00 in cash upfront
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "upfront payments must not be negative"

  @allure.label.suite:Validation @allure.label.subSuite:MarketData
  Scenario Outline: Impossible market rates are rejected instead of crashing the simulation
    Given INCC at <incc>% per year and bank financing at <bank>% per year over <term> months
    And a property "X" listed at R$ 440,000.00 with 19 months remaining until delivery
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "<error>"

    Examples:
      | incc | bank  | term | error                                          |
      | -100 | 10.26 | 360  | INCC rate must be greater than -100% per year |
      | 7.00 | -1.00 | 360  | bank interest rate must not be negative        |
      | 7.00 | 10.26 | 0    | financing term must be at least 1 month        |

  @allure.label.suite:Validation @allure.label.subSuite:MarketData
  Scenario: A deflationary INCC is unusual but valid
    Given INCC at -2.00% per year and bank financing at 10.26% per year over 360 months
    And a property "X" listed at R$ 440,000.00 with 19 months remaining until delivery
    When the buyer runs the simulation
    Then the hidden INCC debt on the mortgage balance should be R$ -11,081.46

  @allure.label.suite:Validation @allure.label.subSuite:ClosingCosts
  Scenario: Negative closing costs are rejected
    Given a property "X" listed at R$ 440,000.00 with 19 months remaining until delivery
    And closing costs of ITBI -3.0% and registry 0.5% of the list price
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "closing cost percentages must not be negative"

  @allure.label.suite:Validation @allure.label.subSuite:BankCredit
  Scenario: A negative pre-approved credit is rejected
    Given a property "X" listed at R$ 440,000.00 with 19 months remaining until delivery
    And the bank pre-approved a credit of R$ -1,000.00
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "pre-approved credit must not be negative"

  @allure.label.suite:Validation @allure.label.subSuite:BankCredit
  Scenario: A pro-soluto term of zero months cannot split the credit gap
    Given a property "X" listed at R$ 440,000.00 with 19 months remaining until delivery
    And any pro-soluto debt is paid to the developer over 0 months
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "pro-soluto term must be at least 1 month"
