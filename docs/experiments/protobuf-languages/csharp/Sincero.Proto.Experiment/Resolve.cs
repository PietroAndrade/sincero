// What the .proto says about each field, read from the `(sincero.field)` option through
// reflection, and the one piece of glue a DTO needs: defaults applied, required fields checked.
using Google.Protobuf.Reflection;

namespace Sincero;

public sealed record FieldInfo(FieldDescriptor Field, Group Group, bool Required, bool Nullable, object? Default);

public static class Inputs
{
    public const string DefaultName = "CUSTOM";   // the controllers' label for an unnamed input (api-contract, open question)

    public static readonly IReadOnlyList<FieldInfo> Fields = SimulationInput.Descriptor.Fields.InFieldOrder()
        .Select(f =>
        {
            var meta = f.GetOptions().GetExtension(SimulationInputExtensions.Field);
            object? dflt = meta.DefaultCase switch
            {
                FieldMeta.DefaultOneofCase.DefaultNumber => meta.DefaultNumber,
                FieldMeta.DefaultOneofCase.DefaultInteger => meta.DefaultInteger,
                FieldMeta.DefaultOneofCase.DefaultString => meta.DefaultString,
                _ => f.IsRepeated ? Array.Empty<int>() : null,
            };
            return new FieldInfo(f, meta.Group, Required: !f.HasPresence && !f.IsRepeated, meta.Nullable, dflt);
        }).ToList();

    /// <summary>Defaults applied, required fields checked; throws on a missing required field.</summary>
    public static SimulationInput Resolve(SimulationInput input)
    {
        var output = input.Clone();
        foreach (var info in Fields)
        {
            var accessor = info.Field.Accessor;
            bool set = info.Field.HasPresence ? accessor.HasValue(output)
                     : info.Field.IsRepeated ? true
                     : !Equals(accessor.GetValue(output), info.Field.FieldType == FieldType.String ? "" : 0.0);  // implicit presence: 0 reads as unset
            if (info.Field.Name == "name" && !set) { output.Name = DefaultName; continue; }
            if (info.Required && !set) throw new ArgumentException($"{info.Field.Name} is required");
            if (!set && info.Default is not null && !info.Nullable && !info.Field.IsRepeated) accessor.SetValue(output, info.Default);
        }
        return output;
    }

    /// <summary>The three DTOs of the Python model, as a split by group.</summary>
    public static Dictionary<string, Dictionary<string, object?>> Split(SimulationInput input) =>
        Fields.GroupBy(i => i.Group).ToDictionary(
            g => g.Key.ToString().ToLowerInvariant(),
            g => g.ToDictionary(i => i.Field.Name, i => i.Field.HasPresence && !i.Field.Accessor.HasValue(input) ? null : i.Field.Accessor.GetValue(input)));
}
