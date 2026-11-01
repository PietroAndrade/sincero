@financing @credit-gap
@allure.label.parentSuite:FinancingPhase
Feature: Credit gap when the balance is transferred to the bank
  The bank pre-approves a credit based on the nominal balance at signing. At delivery
  the balance has been corrected by INCC, so the buyer needs a larger approval. Any
  amount the bank does not cover becomes a short-term debt with the developer
  (pro-soluto).

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And a property "RA" listed at R$ 440,000.00 with 19 months to delivery
    And the developer requires a down payment of 20.0% of the list price
    And any pro-soluto debt is paid to the developer over 12 months

  @allure.label.suite:CreditGap @allure.label.subSuite:PreApproval
  Scenario Outline: The bank's pre-approval decides the size of the pro-soluto debt
    Given the bank pre-approved a credit of R$ <pre_approved>
    When the buyer runs the simulation
    Then the credit needed at delivery should be R$ 391,802.30
    And the credit gap should be R$ <gap>
    And the pro-soluto monthly installment should be R$ <pro_soluto>

    Examples:
      | pre_approved | gap       | pro_soluto |
      | 352,000.00   | 39,802.30 | 3,316.86   |
      | 370,000.00   | 21,802.30 | 1,816.86   |
      | 400,000.00   | 0.00      | 0.00       |

  @allure.label.suite:CreditGap @allure.label.subSuite:ProSolutoTerm
  Scenario: A longer pro-soluto term halves the monthly burden
    Given the bank pre-approved a credit of R$ 352,000.00
    And any pro-soluto debt is paid to the developer over 24 months
    When the buyer runs the simulation
    Then the pro-soluto monthly installment should be R$ 1,658.43

  @allure.label.suite:CreditGap @allure.label.subSuite:DefaultPreApproval
  Scenario: Without an explicit pre-approval the nominal balance is assumed
    When the buyer runs the simulation
    Then the credit gap should be R$ 39,802.30
