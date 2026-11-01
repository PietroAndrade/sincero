# Future feature: physical progress of the building at signing

*Status: idea, not scheduled. [Versão em português](physical-progress.pt-br.md)*

## What the model does today

The only time dimension of a property is **months remaining until delivery**. It says
nothing about how far the building already is. Construction interest (juros de obra) is
modelled as the bank releasing the financed balance **evenly over the remaining months**:
after k of N months, k/N of the INCC-corrected balance has been released and the buyer
pays the bank rate on it.

```
released_share(k) = k / N                       N = months remaining
interest(k)       = balance(k) × released_share(k) × bank_rate_pm
```

This is deliberately simple and consistent with the input: a property "4 months from
delivery" is described only by those 4 months. An earlier draft had a
"construction is X% complete at signing" input; it was removed because it contradicts the
meaning of the months field (a building 4 months from delivery is never 0% complete) and
because the buyer rarely knows the figure with precision.

## What the feature would add

In Caixa's *crédito associativo* the bank releases money to the developer in proportion
to the **measured physical progress** of the works, not to elapsed time. A buyer who signs
when the building is already 80% built starts paying interest on ~80% of the financed
balance from the first month. For SO (R$ 300k, 4 months remaining) that is the
difference between ≈ R$ 4,987 (even release) and ≈ R$ 7,363 (80% at signing) of
construction interest — about 48% more.

Possible inputs, from least to most demanding for the user:

1. **Total construction duration** (e.g. 36 months) → progress at signing is inferred as
   `1 − months_remaining / total_duration`, then linear to 100%.
2. **Progress at signing (%)** as published in the developer's monthly report.
3. **A progress curve** (S-curve or the developer's published schedule) instead of linear.

## Impact on the codebase

- `SimulationInput`: one optional field (`total_construction_months` or `progress_at_signing_pct`).
- `app/models/construction.py`: `LinearRelease` is already the seam — add a
  `ProgressRelease` strategy implementing `at(month)` and pick it when the input is given.
- Features: a new `construction_interest` Outline ("a building already advanced pays more
  interest from day one"); the reference numbers above are already computed.
- API/front-end: one optional field and a hint text explaining where to find the figure.
