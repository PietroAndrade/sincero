from behave import then

from support.money import describe_mismatch, is_close, parse_money


@then("the timeline should have {count:d} months")
def step_timeline_length(context, count):
    actual = len(context.world.current()["timeline"]["months"])
    assert actual == count, f"timeline length: expected {count} months, observed {actual}"


@then("the timeline in month {month:d} should be:")
def step_timeline_month(context, month):
    row = context.world.current()["timeline"]["months"][month]
    assert row["month"] == month, f"timeline row {month} is labelled month {row['month']}"
    (expected,) = context.table.rows
    for column in context.table.headings:
        assert is_close(row[column], parse_money(expected[column])), (
            describe_mismatch(f"month {month}.{column}", parse_money(expected[column]), row[column]))


@then("the peak monthly outflow should be R$ {amount:Money} in month {month:d}")
def step_peak(context, amount, month):
    timeline = context.world.current()["timeline"]
    assert timeline["peak_month"] == month, f"peak month: expected {month}, observed {timeline['peak_month']}"
    assert is_close(timeline["peak_total"], amount), describe_mismatch("peak total", amount, timeline["peak_total"])


@then("the total outflow during the construction phase should be R$ {amount:Money}")
def step_construction_phase_total(context, amount):
    actual = context.world.current()["timeline"]["construction_phase_total"]
    assert is_close(actual, amount), describe_mismatch("construction phase total", amount, actual)
