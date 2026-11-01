from behave import given, then, when

from support.money import describe_mismatch, is_close, parse_money


@given("the candidate properties:")
def step_candidates(context):
    context.world.set_candidates([
        dict(name=row["name"], list_price=parse_money(row["price"]), months_remaining=int(row["months"]))
        for row in context.table
    ])


@when("the buyer compares the candidate properties")
def step_compare(context):
    context.world.compare_candidates()


@when("the buyer compares paying the following cash upfront:")
def step_compare_cash(context):
    context.world.compare_cash([parse_money(row["cash"]) for row in context.table])


@when("the buyer re-runs the simulation with the INCC at {rate:Percent}% per year")
def step_rerun_incc(context, rate):
    context.world.rerun(incc_rate_pa=rate)


@when("the buyer re-runs the simulation with R$ {amount:Money} in cash upfront")
def step_rerun_cash(context, amount):
    context.world.rerun(cash_upfront=amount)


def _assert_table_matches(expected_rows, observed_rows, key):
    expected_keys = [row[key] for row in expected_rows]
    observed_keys = [str(row[key]) if key == "name" else row[key] for row in observed_rows]
    assert len(expected_rows) == len(observed_rows), (
        f"rows: expected {len(expected_rows)}, observed {len(observed_rows)}")
    for expected, observed in zip(expected_rows, observed_rows):
        for column in expected.headings:
            if column == key:
                continue
            want = parse_money(expected[column])
            assert is_close(observed[column], want), describe_mismatch(f"{expected[key]}.{column}", want, observed[column])
    return expected_keys, observed_keys


@then("the comparison table should be:")
def step_comparison_table(context):
    assert context.world.comparison is not None, "the properties were never compared"
    names = [row["name"] for row in context.table]
    observed = [row["name"] for row in context.world.comparison]
    assert names == observed, f"comparison order: expected {names}, observed {observed}"
    _assert_table_matches(context.table.rows, context.world.comparison, key="name")


@then("the cash ladder should be:")
def step_cash_ladder(context):
    assert context.world.cash_ladder is not None, "the cash amounts were never compared"
    amounts = [parse_money(row["cash"]) for row in context.table]
    observed = [row["cash"] for row in context.world.cash_ladder]
    assert amounts == observed, f"cash ladder: expected {amounts}, observed {observed}"
    _assert_table_matches(context.table.rows, context.world.cash_ladder, key="cash")
