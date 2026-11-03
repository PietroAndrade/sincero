"""What the generated document must satisfy. Run after gen_openapi.py (see its docstring)."""
import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

from app.controllers.api_requests import FIELD_SPECS, UPPER_BOUNDS, simulation_input, ApiError

doc = yaml.safe_load(open("openapi.yaml"))
validate(doc)
print("1. valid OpenAPI 3.1: ok")

schema = doc["components"]["schemas"]["SimulationInput"]
props = schema["properties"]
ok = True

def bad(msg):
    global ok
    ok = False
    print("   DRIFT:", msg)

names = [s.name for s in FIELD_SPECS]
if list(props) != names:
    bad(f"field order/set differs: {list(props)} vs {names}")
for s in FIELD_SPECS:
    p = props.get(s.name)
    if p is None:
        continue
    t = p["type"] if not isinstance(p["type"], list) else "|".join(p["type"])
    if p["type"] == "array":
        t = "integer[]"
    want = s.type.replace("|null", "|null")
    if t != want and not (isinstance(p["type"], list) and "|".join(p["type"]) == want):
        bad(f"{s.name}: type {t} vs {want}")
    if p.get("default") != s.default and not (s.default is None and "default" not in p):
        bad(f"{s.name}: default {p.get('default')!r} vs {s.default!r}")
    mx = (p.get("items") or p).get("maximum")
    if mx != UPPER_BOUNDS.get(s.name) and not (s.type == "integer[]"):
        bad(f"{s.name}: maximum {mx!r} vs {UPPER_BOUNDS.get(s.name)!r}")
if set(schema["required"]) != {s.name for s in FIELD_SPECS if s.required}:
    bad(f"required {schema['required']}")
print("2. SimulationInput <=> FIELD_SPECS:", "ok" if ok else "DRIFT (listed above)")

# 3. does the generated schema accept/refuse the same bodies as the shape layer?
v = Draft202012Validator(schema)
cases = {
    "RA": {"list_price": 440000, "months_remaining": 19, "balloon_months": [6, 12]},
    "string for number": {"list_price": "440000", "months_remaining": 19},
    "true for number": {"list_price": True, "months_remaining": 19},
    "19.5 for integer": {"list_price": 440000, "months_remaining": 19.5},
    "19.0 for integer": {"list_price": 440000, "months_remaining": 19.0},
    "unknown key": {"list_price": 440000, "months_remaining": 19, "foo": 1},
    "missing required": {"list_price": 440000},
    "null itbi": {"list_price": 440000, "months_remaining": 19, "itbi_pct": None},
    "null developer_installment": {"list_price": 440000, "months_remaining": 19, "developer_installment": None},
    "61 balloons": {"list_price": 440000, "months_remaining": 19, "balloon_months": list(range(61))},
    "months 5000": {"list_price": 440000, "months_remaining": 5000},
}
agree = 0
for label, body in cases.items():
    s_ok = v.is_valid(body)
    try:
        simulation_input(body); l_ok = True
    except ApiError:
        l_ok = False
    flag = "same" if s_ok == l_ok else "DIFFERENT"
    agree += s_ok == l_ok
    print(f"3. {label:28} schema={'accept' if s_ok else 'refuse':6} layer={'accept' if l_ok else 'refuse':6} {flag}")
print(f"   {agree}/{len(cases)} agree")
