// The generated `SimulationInput` is a *partial* class: the derived amounts of the Python
// `ContractData` are added here, in the same type, without touching generated code.
namespace Sincero;

public sealed partial class SimulationInput
{
    public double RequiredDownPayment => ListPrice * (HasDownPaymentPct ? DownPaymentPct : 20.0) / 100.0;
    public double Upfront => (HasFgtsUpfront ? FgtsUpfront : 0.0) + (HasCashUpfront ? CashUpfront : 0.0);
    public double RemainingDownPayment => Math.Max(0.0, RequiredDownPayment - Upfront);
}
