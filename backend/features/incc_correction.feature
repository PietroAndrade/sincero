@construction @incc
@allure.label.parentSuite:ConstructionPhase
Feature: INCC correction on the mortgage balance
  The part of the price not paid as down payment stays with the developer until
  delivery and is corrected monthly by the INCC. At handover the corrected balance is
  what the bank has to finance; the difference to the nominal balance is the "hidden
  debt" that surprises most buyers.

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And the developer requires a down payment of 20.0% of the list price

  @allure.label.suite:HiddenDebt @allure.label.subSuite:ByConstructionTerm
  Scenario Outline: The longer the construction, the larger the hidden INCC debt
    Given a property "<name>" listed at R$ <price> with <months> months to delivery
    When the buyer runs the simulation
    Then the nominal mortgage balance should be R$ <nominal>
    And the mortgage balance at delivery should be R$ <at_delivery>
    And the hidden INCC debt on the mortgage balance should be R$ <hidden_debt>

    Examples:
      | name | price      | months | nominal    | at_delivery | hidden_debt |
      | SO   | 300,000.00 | 4      | 240,000.00 | 245,474.19  | 5,474.19    |
      | F    | 396,000.00 | 8      | 316,800.00 | 331,416.68  | 14,616.68   |
      | RA   | 440,000.00 | 19     | 352,000.00 | 391,802.30  | 39,802.30   |

  @reference
  @allure.label.suite:HiddenDebt @allure.label.subSuite:ReferenceContract
  Scenario: The reference contract of the original analysis grows from R$ 223k to R$ 264k
    Given a property "REF" listed at R$ 274,000.00 with 30 months to delivery
    And the developer requires a down payment of 18.613% of the list price
    When the buyer runs the simulation
    Then the required down payment should be R$ 50,999.62
    And the nominal mortgage balance should be R$ 223,000.38
    And the mortgage balance at delivery should be R$ 264,097.96
    And the hidden INCC debt on the mortgage balance should be R$ 41,097.58

  @what-if
  @allure.label.suite:HiddenDebt @allure.label.subSuite:LowerIncc
  Scenario: A lower INCC shrinks the hidden debt
    Given INCC at 4.00% per year and bank financing at 10.26% per year over 360 months
    And a property "RA" listed at R$ 440,000.00 with 19 months to delivery
    When the buyer runs the simulation
    Then the hidden INCC debt on the mortgage balance should be R$ 22,552.00
