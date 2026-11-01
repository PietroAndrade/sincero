"""
SINCERO backend — MVC layout.

    app/models/       the domain: inputs, INCC correction, developer plan, construction
                      interest, SAC/PRICE, credit gap, timeline. Pure Python, no I/O,
                      no serialization.
    app/views/        presenters: turn a SimulationResult into the JSON payload used by
                      the API/front-end, or into a text report for the CLI.
    app/controllers/  entry points: parse what the user asked (CLI args, HTTP request),
                      call the models, pick a view.
"""
