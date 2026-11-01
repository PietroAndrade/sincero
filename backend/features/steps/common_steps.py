"""
Shared vocabulary: the Givens that describe the market and the contract, the single
When, and the generic money assertions. Feature-specific steps live in their own file.
"""
from behave import given, then, when

from support.money import describe_mismatch, is_close


# ----- Given: market ---------------------------------------------------------
@given("INCC at {incc:Percent}% per year and bank financing at {bank:Percent}% per year over {term:d} months")
def step_market(context, incc, bank, term):
    context.world.set_market(incc_rate_pa=incc, bank_rate_pa=bank, term_months=term)


@given("the bank accepts installments up to {ratio:Percent}% of the household income")
def step_income_ratio(context, ratio):
    context.world.set(income_commitment_ratio=ratio / 100.0)


@given("closing costs of ITBI {itbi:Percent}% and registry {registry:Percent}% of the list price")
def step_closing_costs(context, itbi, registry):
    context.world.set(itbi_pct=itbi, registry_pct=registry)


# ----- Given: property and contract -----------------------------------------
@given('a property "{name}" listed at R$ {price:Money} with {months:d} months remaining until delivery')
def step_property(context, name, price, months):
    context.world.set_property(name, price, months)


@given("the developer requires a down payment of {percent:Percent}% of the list price")
def step_down_payment_pct(context, percent):
    context.world.set(down_payment_pct=percent)


@given("the buyer pays R$ {amount:Money} of FGTS upfront")
def step_fgts(context, amount):
    context.world.set(fgts_upfront=amount)


@given("the buyer pays R$ {amount:Money} in cash upfront")
def step_cash(context, amount):
    context.world.set(cash_upfront=amount)


@given("the buyer pays the developer R$ {amount:Money} per month")
def step_developer_installment(context, amount):
    context.world.set(developer_installment=amount)


@given("the contract has a balloon payment in month {month:d}")
def step_one_balloon_month(context, month):
    context.world.set(balloon_months=(month,))


@given("the contract has balloon payments in months {first:d} and {second:d}")
def step_two_balloon_months(context, first, second):
    context.world.set(balloon_months=(first, second))


@given("the bank pre-approved a credit of R$ {amount:Money}")
def step_pre_approved(context, amount):
    context.world.set(pre_approved_credit=amount)


@given("any pro-soluto debt is paid to the developer over {months:d} months")
def step_pro_soluto_term(context, months):
    context.world.set(pro_soluto_months=months)


# ----- When -----------------------------------------------------------------
@when("the buyer runs the simulation")
def step_run(context):
    context.world.run()


# ----- Then: generic money figures -------------------------------------------
@then("the {metric:Metric} should be R$ {expected:Money}")
def step_metric_is(context, metric, expected):
    actual = context.world.metric(metric)
    assert is_close(actual, expected), describe_mismatch(metric.label, expected, actual)


@then("the {metric:Metric} should drop from R$ {before:Money} to R$ {after:Money}")
def step_metric_drops(context, metric, before, after):
    was, now = context.world.previous_metric(metric), context.world.metric(metric)
    assert is_close(was, before), describe_mismatch(f"{metric.label} (before)", before, was)
    assert is_close(now, after), describe_mismatch(f"{metric.label} (after)", after, now)
    assert now < was, f"{metric.label} did not drop: {was:,.2f} -> {now:,.2f}"
