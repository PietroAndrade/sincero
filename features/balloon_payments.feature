@construction @balloon
@allure.label.parentSuite:ConstructionPhase
Feature: Balloon payments to the developer
  The buyer chooses how much to pay the developer every month. Whatever the monthly
  installments do not cover of the down payment balance is paid as balloon payments
  (parcelas balão) in the agreed construction months — the balloon amount is derived,
  never typed in. Balloons are corrected by INCC like any other developer payment.

  Background:
    Given INCC at 7.00% per year and bank financing at 10.26% per year over 360 months
    And a property "RA" listed at R$ 440,000.00 with 19 months remaining until delivery
    And the developer requires a down payment of 20.0% of the list price
    And the buyer pays R$ 13,000.00 of FGTS upfront

  @allure.label.suite:Balloons @allure.label.subSuite:DerivedAmount
  Scenario: The balloons absorb exactly what the monthly installments leave uncovered
    Given the buyer pays the developer R$ 2,500.00 per month
    And the contract has balloon payments in months 6 and 12
    When the buyer runs the simulation
    Then the down payment balance to be paid during construction should be R$ 75,000.00
    And the nominal monthly developer installment should be R$ 2,500.00
    And the amount not covered by the monthly installments should be R$ 27,500.00
    And the nominal balloon payment should be R$ 13,750.00
    And the balloon payment in month 6 should be R$ 14,223.11
    And the balloon payment in month 12 should be R$ 14,712.50
    And the total paid to the developer during construction should be R$ 79,214.67
    And the INCC correction on the down payment should be R$ 4,214.67

  @allure.label.suite:Balloons @allure.label.subSuite:SingleBalloon
  Scenario: A single balloon takes the whole uncovered amount
    Given the buyer pays the developer R$ 3,000.00 per month
    And the contract has a balloon payment in month 10
    When the buyer runs the simulation
    Then the nominal balloon payment should be R$ 18,000.00
    And the balloon payment in month 10 should be R$ 19,044.04

  @allure.label.suite:Balloons @allure.label.subSuite:NoBalloonNeeded
  Scenario: Installments that cover the balance exactly need no balloon
    Given the buyer pays the developer R$ 3,947.37 per month
    When the buyer runs the simulation
    Then the amount not covered by the monthly installments should be R$ 0.00
    And the nominal balloon payment should be R$ 0.00

  @validation
  @allure.label.suite:Balloons @allure.label.subSuite:Validation
  Scenario: Installments that leave an uncovered amount without a balloon month are rejected
    Given the buyer pays the developer R$ 2,000.00 per month
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "monthly installments of R$ 38,000.00 do not cover the down payment balance of R$ 75,000.00; R$ 37,000.00 is missing — add balloon months or raise the installment"

  @validation
  @allure.label.suite:Balloons @allure.label.subSuite:Validation
  Scenario Outline: A balloon schedule that does not fit the contract is rejected
    Given the buyer pays the developer R$ <installment> per month
    And the contract has a balloon payment in month <month>
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "<error>"

    Examples:
      | installment | month | error                                                                            |
      | 5,000.00    | 6     | monthly installments of R$ 95,000.00 exceed the down payment balance of R$ 75,000.00 |
      | 2,000.00    | 24    | balloon month 24 is after delivery (month 19)                                    |

  @validation
  @allure.label.suite:Balloons @allure.label.subSuite:Validation
  Scenario: A balloon month without a chosen monthly installment cannot be sized
    Given the contract has a balloon payment in month 6
    When the buyer runs the simulation
    Then the simulation should be rejected with the error "a monthly developer installment is required to size the balloon payments"
