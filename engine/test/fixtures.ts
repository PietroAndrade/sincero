/** The reference property RA with a developer plan, as the Python unit tests built it. */
import { BankCreditData, ContractData, MarketData, SimulationInput } from "../src/index.js";

export const C = new ContractData({
  name: "RA",
  list_price: 440_000,
  months_remaining: 19,
  fgts_upfront: 13_000,
  developer_installment: 2_500,
  balloon_months: [6, 12],
});
export const M = new MarketData();
export const B = new BankCreditData();
export const ra = new SimulationInput(C);
