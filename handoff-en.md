# Handoff: off-plan real estate financing calculation engine

## 1. Scope and business rules

This tool addresses an information asymmetry in the Brazilian off-plan (na planta) market: the "hidden debt" created by overlapping financial indexers during construction.

- Construction phase (INCC indexer): adjusted monthly on both the remaining down payment balance owed to the developer and the projected bank mortgage balance. Calculations use a historical average of 7.00% p.a.
- Construction interest (evolução de obra): charged by Caixa Econômica Federal in proportion to the building's physical progress. These charges do not amortize the principal mortgage debt.
- Amortization phase (after key handover): traditional Caixa financing (SBPE) at 10.26% p.a. + TR over 360 months (30 years). Supported systems are SAC (decreasing installments) and PRICE (fixed installments).

## 2. Project data (base date: November 2026)

The system is configured for these baseline scenarios, taken from your current inputs:

- SO: R$ 300,000, delivery in March 2027 (4 months remaining)
- F: R$ 396,000, delivery in July 2027 (8 months remaining)
- SV: R$ 233,000, delivery in April 2028 (17 months remaining)
- F4: R$ 320,400, delivery in June 2028 (19 months remaining)
- RA: R$ 440,000, delivery in June 2028 (19 months remaining)

## 3. Engine source code (financing_engine.py)

The `OffPlanFinancingCalculator` class projects the INCC adjustment over the exact construction timeline, computes the developer's linear monthly installments after deducting the down payment credits (FGTS and cash), and calculates the SAC and Price bank amortization values.

```python
import math

class OffPlanFinancingCalculator:
    def __init__(self, incc_rate_pa=7.0, bank_rate_pa=10.26, term_months=360):
        """
        Initializes the financial engine for off-plan real estate calculations in Brazil.
        """
        self.incc_rate_pm = (1 + incc_rate_pa / 100) ** (1 / 12) - 1
        self.bank_rate_pm = (1 + bank_rate_pa / 100) ** (1 / 12) - 1
        self.term_months = term_months

    def calculate_scenario(self, name, list_price, months_to_delivery, fgts_down_payment, initial_cash_down=0):
        # 1. Standard down payment proportion required by developers (~18.613%)
        down_payment_proportion = 0.18613
        required_total_down_payment = list_price * down_payment_proportion
        
        # 2. Nominal mortgage balance that will be sent for bank financing
        nominal_mortgage_balance = list_price - required_total_down_payment
        
        # 3. Developer cash flow calculation (Deducting upfront down payment credits immediately)
        total_upfront = fgts_down_payment + initial_cash_down
        remaining_down_payment_to_finance = max(0.0, required_total_down_payment - total_upfront)
        developer_monthly_installment = remaining_down_payment_to_finance / months_to_delivery if months_to_delivery > 0 else 0
        
        # 4. Compounding the INCC effect on the future Bank Mortgage Balance during construction
        adjusted_mortgage_balance = nominal_mortgage_balance * ((1 + self.incc_rate_pm) ** months_to_delivery)
        hidden_incc_debt = adjusted_mortgage_balance - nominal_mortgage_balance
        
        # 5. Post-Delivery Financing: SAC System (1st Installment)
        sac_amortization = adjusted_mortgage_balance / self.term_months
        sac_first_month_interest = adjusted_mortgage_balance * self.bank_rate_pm
        sac_first_installment = sac_amortization + sac_first_month_interest
        sac_last_installment = sac_amortization + (sac_amortization * self.bank_rate_pm)
        
        # 6. Post-Delivery Financing: Price System (Fixed Installment)
        if self.bank_rate_pm > 0:
            price_installment = (adjusted_mortgage_balance * self.bank_rate_pm) / (1 - (1 + self.bank_rate_pm) ** (-self.term_months))
        else:
            price_installment = adjusted_mortgage_balance / self.term_months

        return {
            "name": name,
            "construction_term_months": months_to_delivery,
            "required_down_payment": round(required_total_down_payment, 2),
            "developer_monthly_installment": round(developer_monthly_installment, 2),
            "original_bank_mortgage_base": round(nominal_mortgage_balance, 2),
            "accumulated_incc_adjustment": round(hidden_incc_debt, 2),
            "final_financed_balance": round(adjusted_mortgage_balance, 2),
            "sac_first_installment": round(sac_first_installment, 2),
            "sac_last_installment": round(sac_last_installment, 2),
            "price_fixed_installment": round(price_installment, 2),
            "min_required_income_sac": round(sac_first_installment / 0.3, 2)
        }

# --- ENGINE EXECUTION EXAMPLE ---
if __name__ == "__main__":
    engine = OffPlanFinancingCalculator()
    
    # List of properties using data captured from the user's context
    properties = [
        {"name": "SO", "price": 300000, "months": 4},
        {"name": "F", "price": 396000, "months": 8},
        {"name": "SV", "price": 233000, "months": 17},
        {"name": "F4", "price": 320400, "months": 19},
        {"name": "RA", "price": 440000, "months": 19}
    ]
    
    print("=== BASE SCENARIO: R$ 13,000 FGTS USED AS SINAL ===")
    for prop in properties:
        res = engine.calculate_scenario(prop["name"], prop["price"], prop["months"], fgts_down_payment=13000)
        print(f"\n🏠 {res['name']} (Timeline: {res['construction_term_months']} months remaining)")
        print(f"   └─ Developer Monthly Bill: R$ {res['developer_monthly_installment']:.2f}")
        print(f"   └─ Hidden INCC Inflation Impact: R$ {res['accumulated_incc_adjustment']:.2f}")
        print(f"   └─ Total Financed Balance at Delivery: R$ {res['final_financed_balance']:.2f}")
        print(f"   └─ Bank Financing (1st Installment SAC): R$ {res['sac_first_installment']:.2f}")
        print(f"   └─ Bank Financing (Fixed Installment Price): R$ {res['price_fixed_installment']:.2f}")
```

## 4. Next steps

To turn the script into a market-ready app (like CRIF or SIMPL), the next features to build are:

1. Live index API: replace the static 7.0% INCC default with a scraper or web service that fetches the monthly index published by the FGV.
2. Custom balloon schedules: let users place balloon payments (parcelas balão) at chosen months (for example month 12 and 24) and see how much their regular developer installments drop.
3. Double-invoicing timeline chart: a stacked chart showing the transition where developer construction bills end, construction interest peaks, and the long-term amortization begins.

Open questions: a sample JSON payload schema for the API endpoints, and the formula for the variable construction interest ceiling (evolução de obra).
