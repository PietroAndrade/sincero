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
