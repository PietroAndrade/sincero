@overview @comparison
@allure.label.parentSuite:Overview
Feature: Comparing properties and simulating more cash
  A buyer choosing between several off-plan apartments wants to see them side by side,
  and to test how putting more cash on the table changes each bill.

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And the developer requires a down payment of 20.0% of the list price
    And the construction is 0% complete at signing

  @allure.label.suite:Comparison @allure.label.subSuite:Properties
  Scenario: The five candidate properties side by side
    Given the buyer pays R$ 13,000.00 of FGTS upfront
    And the candidate properties:
      | name | price      | months |
      | SO   | 300,000.00 | 4      |
      | F    | 396,000.00 | 8      |
      | SV   | 233,000.00 | 17     |
      | F4   | 320,400.00 | 19     |
      | RA   | 440,000.00 | 19     |
    When the buyer compares the candidate properties
    Then the comparison table should be:
      | name | developer_installment | hidden_incc_debt | balance_at_delivery | construction_interest | sac_first_installment | min_income_sac |
      | SO   | 11,750.00             | 5,474.19         | 245,474.19          | 4,987.20              | 2,688.00              | 8,960.01       |
      | F    | 8,275.00              | 14,616.68        | 331,416.68          | 12,029.66             | 3,629.09              | 12,096.98      |
      | SV   | 1,976.47              | 18,750.66        | 205,150.66          | 14,646.21             | 2,246.45              | 7,488.17       |
      | F4   | 2,688.42              | 28,983.31        | 285,303.31          | 22,548.22             | 3,124.14              | 10,413.80      |
      | RA   | 3,947.37              | 39,802.30        | 391,802.30          | 30,965.10             | 4,290.33              | 14,301.10      |

  @what-if @more-cash
  @allure.label.suite:Comparison @allure.label.subSuite:MoreCash
  Scenario: A cash ladder shows what each extra real at signing buys
    Given a property "RA" listed at R$ 440,000.00 with 19 months to delivery
    And the buyer pays R$ 13,000.00 of FGTS upfront
    When the buyer compares paying the following cash upfront:
      | cash       |
      | 0.00       |
      | 30,000.00  |
      | 75,000.00  |
      | 100,000.00 |
    Then the cash ladder should be:
      | cash       | developer_installment | hidden_incc_debt | balance_at_delivery | sac_first_installment | min_income_sac |
      | 0.00       | 3,947.37              | 39,802.30        | 391,802.30          | 4,290.33              | 14,301.10      |
      | 30,000.00  | 2,368.42              | 39,802.30        | 391,802.30          | 4,290.33              | 14,301.10      |
      | 75,000.00  | 0.00                  | 39,802.30        | 391,802.30          | 4,290.33              | 14,301.10      |
      | 100,000.00 | 0.00                  | 36,975.43        | 363,975.43          | 3,985.62              | 13,285.40      |

  @what-if
  @allure.label.suite:Comparison @allure.label.subSuite:LowerIncc
  Scenario: Re-running with a lower INCC shows how much of the cost is indexation
    Given a property "RA" listed at R$ 440,000.00 with 19 months to delivery
    When the buyer runs the simulation
    And the buyer re-runs the simulation with the INCC at 4.00% per year
    Then the hidden INCC debt on the mortgage balance should drop from R$ 39,802.30 to R$ 22,552.00
    And the SAC installment in month 1 should drop from R$ 4,290.33 to R$ 4,101.44
