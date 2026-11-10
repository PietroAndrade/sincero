# Decision: reject upfront payments above the list price

*Status: accepted on 2026-11-01, implemented in `UpfrontPaymentsValidator` (since 2026-11-09 in
`engine/src/validators.ts`, code `upfront_above_list_price`).*

## Context

The mortgage balance is `list_price − max(down_payment, upfront)`, where upfront is FGTS plus cash at
signing. When upfront exceeds the list price the balance goes negative, and the INCC correction then
grows that negative debt. With R$ 500,000 of cash on a R$ 440,000 property and 19 months remaining,
the balance at delivery is R$ -66,784.48.

## Decision

A simulation whose FGTS + cash exceeds the list price is rejected with a `SimulationError`. Paying
exactly the list price stays valid and leaves a zero balance.

## Reason

Nobody pays more than the price of a property, so the amount is almost always a typing mistake.
Capping the balance at zero would hide that mistake and drop the excess from the total cost, and this
simulator exists to avoid misleading figures.

## Consequence

Validation runs for every step of a `--cash-ladder`, so one step above the list price fails the whole
ladder.
