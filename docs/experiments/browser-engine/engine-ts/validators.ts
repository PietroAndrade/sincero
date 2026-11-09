/**
 * Port of app/models/validators.py: the same rules, in the same order, with the same messages
 * (the behave suite compares them verbatim). The first broken rule wins.
 */
import { pyMoney } from "./pyfloat.js";
import { BankCreditData, ContractData, MarketData, SimulationError, SimulationInput, upfront } from "./inputs.js";

type Validator<T> = (data: T) => void;

// ----- contract with the developer ---------------------------------------------------------------
const property: Validator<ContractData> = (c) => {
  if (c.list_price <= 0) throw new SimulationError("list price must be greater than zero");
  if (c.months_remaining < 1) throw new SimulationError("months remaining until delivery must be at least 1");
  if (!(0 <= c.down_payment_pct && c.down_payment_pct <= 100))
    throw new SimulationError("down payment percentage must be between 0 and 100");
};

const upfrontPayments: Validator<ContractData> = (c) => {
  if (c.fgts_upfront < 0 || c.cash_upfront < 0) throw new SimulationError("upfront payments must not be negative");
  if (upfront(c) > c.list_price)
    throw new SimulationError(
      `upfront payments of R$ ${pyMoney(upfront(c))} exceed the list price of R$ ${pyMoney(c.list_price)}`,
    );
};

const developerPlan: Validator<ContractData> = (c) => {
  if (c.developer_installment !== null && c.developer_installment < 0)
    throw new SimulationError("the monthly developer installment must not be negative");
  for (const month of c.balloon_months) {
    if (month > c.months_remaining)
      throw new SimulationError(`balloon month ${month} is after delivery (month ${c.months_remaining})`);
    if (month < 1) throw new SimulationError(`balloon month ${month} must be at least 1`);
  }
  if (new Set(c.balloon_months).size !== c.balloon_months.length)
    throw new SimulationError("balloon months must not repeat");
};

// ----- market -------------------------------------------------------------------------------------
const marketRates: Validator<MarketData> = (m) => {
  if (m.incc_rate_pa <= -100) throw new SimulationError("INCC rate must be greater than -100% per year");
  if (m.bank_rate_pa < 0) throw new SimulationError("bank interest rate must not be negative");
};

const financing: Validator<MarketData> = (m) => {
  if (m.term_months < 1) throw new SimulationError("financing term must be at least 1 month");
  if (!(0 < m.income_commitment_ratio && m.income_commitment_ratio <= 1))
    throw new SimulationError("income commitment ratio must be between 0 and 1");
};

const closingCosts: Validator<MarketData> = (m) => {
  if (m.itbi_pct < 0 || m.registry_pct < 0) throw new SimulationError("closing cost percentages must not be negative");
};

// ----- bank credit --------------------------------------------------------------------------------
const bankCredit: Validator<BankCreditData> = (b) => {
  if (b.pre_approved_credit !== null && b.pre_approved_credit < 0)
    throw new SimulationError("pre-approved credit must not be negative");
  if (b.pro_soluto_months < 1) throw new SimulationError("pro-soluto term must be at least 1 month");
};

// ----- DEFAULT_POLICY: contract -> market -> bank credit -------------------------------------------
export function validate(inp: SimulationInput): SimulationInput {
  for (const v of [property, upfrontPayments, developerPlan]) v(inp.contract);
  for (const v of [marketRates, financing, closingCosts]) v(inp.market);
  for (const v of [bankCredit]) v(inp.bank_credit);
  return inp;
}
