# C# × protobuf — experiment

Uses `backend/proto/sincero/simulation_input.proto` unchanged.

```bash
dotnet run --project Sincero.Proto.Experiment     # the contract's JSON bodies through JsonParser; the option; Resolve()
dotnet test Sincero.Proto.Tests                   # 6 small tests (xunit)
```

| File | What |
|---|---|
| `Sincero.Proto.Experiment/*.csproj` | the whole code-generation configuration: two `PackageReference`s (`Google.Protobuf`, `Grpc.Tools`) and one `<Protobuf Include=…>` item — protoc ships inside `Grpc.Tools` and runs on every build |
| `generated/SimulationInput.g.cs` | what that build step produces (made here with `protoc --csharp_out`, 2,027 lines); committed for reading only — a real project never commits it |
| `SimulationInput.Derived.cs` | the derived amounts of the Python `ContractData`, added to the generated **partial** class |
| `Resolve.cs` | `Inputs.Fields` (defaults, group, nullable read from the option through reflection), `Resolve()`, `Split()` |
| `Program.cs` | the experiment |
| `restore-attempt.txt` | what `dotnet restore` answered in the sandbox |
| `Sincero.Proto.Tests/SimulationInputTests.cs` | the tests |

## Not run here

The sandbox this was written in resolves only a few package hosts (PyPI, npm, Maven Central, the
Ubuntu archive). The .NET 8 SDK was installed from the Ubuntu archive and `dotnet restore` was run;
it stops at `NU1301: Unable to load the service index for source https://api.nuget.org/v3/index.json`
— `Google.Protobuf` and `Grpc.Tools` exist only on NuGet, and no reachable source carries the C#
runtime. The code generation step was verified with the official `protoc` (3.21, from Maven
Central); the program and the tests are written against `Google.Protobuf` 3.29's documented API
(`JsonParser`, `JsonFormatter`, `FieldDescriptor.GetOptions().GetExtension`, `HasXxx` on
`optional` fields) and reflect the JSON-mapping behaviour of its `JsonParser` source: strings
accepted for numbers, `null` on a scalar = unset, both snake_case and camelCase names accepted,
unknown fields refused, fractional integers refused, `null` inside a repeated field refused.
Run `dotnet test` with NuGet access to confirm before relying on a specific case.
