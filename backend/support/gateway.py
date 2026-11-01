"""
The one place the test support knows how to talk to the application.

Givens accumulate plain dicts; the gateway turns them into model inputs, runs the
models and presents the results through the JSON view — the same payload the API and
the front-end consume.
"""
from __future__ import annotations

from app.models import SimulationError, compare, simulate
from app.views import comparison_to_dict, input_from_dict, simulation_to_dict


class EngineGateway:
    error_type = SimulationError

    @staticmethod
    def make_input(data: dict):
        return input_from_dict(dict(data))

    def simulate(self, data: dict) -> dict:
        return simulation_to_dict(simulate(self.make_input(data)))

    def compare(self, rows: list[dict]) -> list[dict]:
        return comparison_to_dict(compare([self.make_input(r) for r in rows]))
