from behave import then

from support.money import describe_mismatch, is_close, parse_money, parse_percent

COLUMNS = ("base_value", "additional", "final_value")


@then("the cost breakdown should be:")
def step_cost_breakdown(context):
    observed = {row["component"]: row for row in context.world.current()["total_cost"]["breakdown"]}
    expected_components = [row["component"] for row in context.table]
    assert expected_components == list(observed), (
        f"breakdown rows: expected {expected_components}, observed {list(observed)}")
    for row in context.table:
        for column in COLUMNS:
            expected, actual = parse_money(row[column]), observed[row["component"]][column]
            assert is_close(actual, expected), describe_mismatch(f"{row['component']}.{column}", expected, actual)


@then("the total extra cost over the list price should be {percent:Percent}%")
def step_extra_pct(context, percent):
    actual = context.world.current()["total_cost"]["extra_pct"]
    assert is_close(actual, percent), f"extra cost: expected {percent:.2f}%, observed {actual:.2f}%"
