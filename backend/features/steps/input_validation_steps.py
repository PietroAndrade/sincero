from behave import then


@then('the simulation should be rejected with the error "{message}"')
def step_rejected(context, message):
    error = context.world.error
    assert error is not None, "the simulation was expected to be rejected but it succeeded"
    assert error == message, f"rejection message: expected '{message}', observed '{error}'"
