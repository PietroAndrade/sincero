"""
Controllers: the CLI (`cli_controller.py`) and the HTTP API.

`api_requests.py` is the API's request side — the shape rules of `docs/api-contract.md` that
turn a parsed JSON body into simulation inputs (`400`, with `code`/`field`/`index`) and run
the model on them (`422`). It has no Flask dependency; the Flask blueprint (milestone 5)
parses the body, calls it and maps `ApiError` to a response.

The Connect service (contract revision 7) replaces that layer: `connect_errors.py` maps the
`buf.validate` rules and the model's `SimulationError` to Connect errors, `connect_app.py` builds
the generated ASGI/WSGI applications with the contract's codecs.
"""
