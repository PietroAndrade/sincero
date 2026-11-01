"""
Behave hooks. The engine gateway is built once; the scenario world is reset before
every scenario so each one passes alone and in any order.
"""
import os
import sys

# Make `support/` and the engine importable regardless of the working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from behave import register_type  # noqa: E402

from support.gateway import EngineGateway  # noqa: E402
from support.metrics import METRIC_PATTERN, parse_metric  # noqa: E402
from support.money import MONEY_PATTERN, PERCENT_PATTERN, parse_money, parse_percent  # noqa: E402
from support.world import SimulationWorld  # noqa: E402

# Custom `parse` types for the step patterns: {x:Money}, {x:Percent}, {x:Metric}.
# Registered here because hooks load before any step module.
parse_money.pattern = MONEY_PATTERN
parse_percent.pattern = PERCENT_PATTERN
parse_metric.pattern = METRIC_PATTERN
register_type(Money=parse_money, Percent=parse_percent, Metric=parse_metric)

_engine = EngineGateway()
_world = SimulationWorld(engine=_engine)


def before_all(context):
    context.world = _world


def before_scenario(context, scenario):
    context.world.reset()
