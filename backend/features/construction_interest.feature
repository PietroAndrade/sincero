@construction @construction-interest
@allure.label.parentSuite:ConstructionPhase
Feature: Construction interest charged by the bank
  During construction the bank releases money to the developer as the building
  progresses, and the buyer pays interest (juros de obra) on what has been released.
  Progress grows linearly from its level at signing to 100% at delivery. This charge
  never reduces the mortgage balance.

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And the developer requires a down payment of 20.0% of the list price

  @allure.label.suite:ConstructionInterest @allure.label.subSuite:GrowsWithProgress
  Scenario: Construction interest grows month by month with the physical progress
    Given a property "RA" listed at R$ 440,000.00 with 19 months to delivery
    And the construction is 0% complete at signing
    When the buyer runs the simulation
    Then the construction interest in month 1 should be R$ 152.26
    And the construction interest in month 19 should be R$ 3,201.99
    And the total construction interest should be R$ 30,965.10

  @allure.label.suite:ConstructionInterest @allure.label.subSuite:ProgressAtSigning
  Scenario Outline: Buying a building that is already advanced means paying more interest from day one
    Given a property "SO" listed at R$ 300,000.00 with 4 months to delivery
    And the construction is <progress>% complete at signing
    When the buyer runs the simulation
    Then the construction interest in month 1 should be R$ <first_month>
    And the total construction interest should be R$ <total>

    Examples:
      | progress | first_month | total    |
      | 0        | 493.12      | 4,987.20 |
      | 80       | 1,676.61    | 7,363.12 |

  @allure.label.suite:ConstructionInterest @allure.label.subSuite:NoAmortization
  Scenario: Construction interest does not reduce the balance financed at delivery
    Given a property "RA" listed at R$ 440,000.00 with 19 months to delivery
    And the construction is 0% complete at signing
    When the buyer runs the simulation
    Then the mortgage balance at delivery should be R$ 391,802.30
