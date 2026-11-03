// Experiment: the contract's JSON bodies through Google.Protobuf's JsonParser, the custom
// option through reflection, and the generated class as the DTO.
//
//     dotnet run --project Sincero.Proto.Experiment
using Google.Protobuf;
using Sincero;

var parser = new JsonParser(JsonParser.Settings.Default.WithIgnoreUnknownFields(false));
string Minimal(string extra = "") => $"{{\"list_price\": 440000, \"months_remaining\": 19{extra}}}";

var cases = new (string Label, string Body, string Contract)[]
{
    ("body is an array", "[1, 2]", "400 wrong_type body"),
    ("string for a number", "{\"list_price\": \"440000\", \"months_remaining\": 19}", "400 wrong_type list_price"),
    ("boolean for a number", "{\"list_price\": true, \"months_remaining\": 19}", "400 wrong_type list_price"),
    ("19.0 for an integer", "{\"list_price\": 440000, \"months_remaining\": 19.0}", "accepted (19)"),
    ("19.5 for an integer", "{\"list_price\": 440000, \"months_remaining\": 19.5}", "400 wrong_type months_remaining"),
    ("\"19\" for an integer", "{\"list_price\": 440000, \"months_remaining\": \"19\"}", "400 wrong_type months_remaining"),
    ("two unknown fields", Minimal(", \"fgts_upfrnt\": 13000, \"foo\": 1"), "400 unknown_field fgts_upfrnt"),
    ("camelCase alias", "{\"listPrice\": 440000, \"monthsRemaining\": 19}", "400 unknown_field listPrice"),
    ("missing months_remaining", "{\"list_price\": 440000}", "400 missing_field months_remaining"),
    ("null on itbi_pct", Minimal(", \"itbi_pct\": null"), "400 null_not_allowed itbi_pct"),
    ("null on developer_installment", Minimal(", \"developer_installment\": null"), "accepted (absent)"),
    ("\"NaN\" (string)", "{\"list_price\": \"NaN\", \"months_remaining\": 19}", "400 wrong_type list_price"),
    ("months_remaining 5000", "{\"list_price\": 440000, \"months_remaining\": 5000}", "400 out_of_range months_remaining"),
    ("balloon item 6.5", Minimal(", \"balloon_months\": [6, 6.5]"), "400 wrong_type balloon_months[1]"),
    ("balloon item \"12\"", Minimal(", \"balloon_months\": [6, \"12\"]"), "400 wrong_type balloon_months[1]"),
    ("balloon item null", Minimal(", \"balloon_months\": [6, null]"), "400 null_not_allowed balloon_months[1]"),
    ("omitted defaults", Minimal(), "accepted; down_payment_pct resolves to 20.0"),
    ("the RA example", "{\"name\": \"RA\", \"list_price\": 440000, \"months_remaining\": 19, \"fgts_upfront\": 13000, \"developer_installment\": 2500, \"balloon_months\": [6, 12]}", "accepted"),
};

Console.WriteLine("=== the .proto, read through the custom option ===");
foreach (var f in Inputs.Fields)
    Console.WriteLine($"  {f.Field.Name,-24} {f.Group,-12} {(f.Required ? "required" : f.Nullable ? "nullable" : "default " + f.Default)}");

Console.WriteLine("\n=== POST /api/simulations — proto3 JSON mapping (Google.Protobuf) vs the contract ===\n");
var formatter = new JsonFormatter(JsonFormatter.Settings.Default.WithPreserveProtoFieldNames(true));
foreach (var (label, body, contract) in cases)
{
    string verdict;
    try { verdict = "accepted -> " + formatter.Format(Inputs.Resolve(parser.Parse<SimulationInput>(body))); }
    catch (Exception e) { verdict = $"{e.GetType().Name}: {e.Message}"; }
    Console.WriteLine($"# {label}\n  contract : {contract}\n  protobuf : {verdict}\n");
}

var ra = Inputs.Resolve(parser.Parse<SimulationInput>(cases[^1].Body));
Console.WriteLine("=== the RA input as the three DTOs ===");
foreach (var (group, fields) in Inputs.Split(ra))
    Console.WriteLine($"  {group}: {string.Join(", ", fields.Select(kv => $"{kv.Key}={kv.Value ?? "null"}"))}");
Console.WriteLine($"  required down payment: {ra.RequiredDownPayment} remaining: {ra.RemainingDownPayment}");

var sw = System.Diagnostics.Stopwatch.StartNew();
const int n = 20000;
for (int i = 0; i < n; i++) Inputs.Resolve(parser.Parse<SimulationInput>(cases[^1].Body));
Console.WriteLine($"\n=== timing: Parse + Resolve, the RA body, mean of {n}: {sw.Elapsed.TotalMilliseconds * 1000 / n:F1} us");
