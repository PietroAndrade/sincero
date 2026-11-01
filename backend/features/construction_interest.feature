@construction @construction-interest
@allure.label.parentSuite:ConstructionPhase
Feature: Construction interest charged by the bank
  During the months remaining until delivery the bank releases the financed balance to
  the developer, and the buyer pays interest (juros de obra) on what has been released
  so far. The release is spread evenly over the remaining months. This charge never
  reduces the mortgage balance.

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And the developer requires a down payment of 20.0% of the list price

  @allure.label.suite:ConstructionInterest @allure.label.subSuite:GrowsEveryMonth
  Scenario: Construction interest grows month by month as more of the balance is released
    Given a property "RA" listed at R$ 440,000.00 with 19 months remaining until delivery
    When the buyer runs the simulation
    Then the construction interest in month 1 should be R$ 152.26
    And the construction interest in month 19 should be R$ 3,201.99
    And the total construction interest should be R$ 30,965.10

  @allure.label.suite:ConstructionInterest @allure.label.subSuite:ByMonthsRemaining
  Scenario Outline: The fewer months remaining, the less construction interest is paid
    Given a property "<name>" listed at R$ <price> with <months> months remaining until delivery
    When the buyer runs the simulation
    Then the construction interest in month 1 should be R$ <first_month>
    And the total construction interest should be R$ <total>

    Examples:
      | name | price      | months | first_month | total     |
      | SO   | 300,000.00 | 4      | 493.12      | 4,987.20  |
      | F    | 396,000.00 | 8      | 325.46      | 12,029.66 |
      | RA   | 440,000.00 | 19     | 152.26      | 30,965.10 |

  @allure.label.suite:ConstructionInterest @allure.label.subSuite:NoAmortization
  Scenario: Construction interest does not reduce the balance financed at delivery
    Given a property "RA" listed at R$ 440,000.00 with 19 months remaining until delivery
    When the buyer runs the simulation
    Then the mortgage balance at delivery should be R$ 391,802.30
