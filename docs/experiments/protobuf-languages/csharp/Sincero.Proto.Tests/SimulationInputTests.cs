// Small tests pinning the findings of docs/protobuf-languages.md for C#.     dotnet test
using Google.Protobuf;
using Sincero;
using Xunit;

public class SimulationInputTests
{
    static readonly JsonParser Parser = new(JsonParser.Settings.Default.WithIgnoreUnknownFields(false));
    const string RA = "{\"name\": \"RA\", \"list_price\": 440000, \"months_remaining\": 19, \"fgts_upfront\": 13000, \"developer_installment\": 2500, \"balloon_months\": [6, 12]}";

    static SimulationInput Parse(string json) => Inputs.Resolve(Parser.Parse<SimulationInput>(json));

    [Fact]
    public void TheGeneratedClassIsTheDto_WithPresenceAndDerivedAmounts()
    {
        var ra = Parser.Parse<SimulationInput>(RA);
        Assert.Equal(440000, ra.ListPrice);
        Assert.True(ra.HasDeveloperInstallment);
        Assert.False(ra.HasInccRatePa);                      // `optional` + omitted: absent, not 0
        Assert.Equal(new[] { 6, 12 }, ra.BalloonMonths);
        Assert.Equal(88000, Parse(RA).RequiredDownPayment);  // the partial class
        Assert.Equal(75000, Parse(RA).RemainingDownPayment);
    }

    [Fact]
    public void TheProtoDefaultsGroupsAndNullabilityAreReadableFromTheOption()
    {
        var byName = Inputs.Fields.ToDictionary(f => f.Field.Name);
        Assert.Equal(16, Inputs.Fields.Count);
        Assert.Equal(20.0, byName["down_payment_pct"].Default);
        Assert.Equal(360, byName["term_months"].Default);
        Assert.True(byName["developer_installment"].Nullable);
        Assert.True(byName["list_price"].Required);
        Assert.Equal(new[] { "contract", "market", "bank_credit" }, Inputs.Split(Parse(RA)).Keys);
    }

    [Fact]
    public void ResolveAppliesDefaultsAndReportsMissingRequiredFields()
    {
        var r = Parse("{\"list_price\": 440000, \"months_remaining\": 19}");
        Assert.Equal(20.0, r.DownPaymentPct);
        Assert.Equal(7.0, r.InccRatePa);
        Assert.Equal(Inputs.DefaultName, r.Name);
        Assert.False(r.HasDeveloperInstallment);
        Assert.Throws<ArgumentException>(() => Parse("{\"list_price\": 440000}"));
        Assert.Throws<ArgumentException>(() => Parse("{\"list_price\": 0, \"months_remaining\": 19}"));  // implicit presence
    }

    [Theory]
    [InlineData("[1, 2]")]
    [InlineData("{\"list_price\": 440000, \"months_remaining\": 19.5}")]
    [InlineData("{\"list_price\": 440000, \"months_remaining\": 19, \"foo\": 1}")]
    [InlineData("{\"list_price\": 440000, \"months_remaining\": 2147483648}")]
    [InlineData("{\"list_price\": 440000, \"months_remaining\": 19, \"balloon_months\": [6, 6.5]}")]
    [InlineData("{\"list_price\": 440000, \"months_remaining\": 19, \"balloon_months\": [6, null]}")]
    public void Proto3JsonRefusesWhatTheContractRefuses(string body) =>
        Assert.Throws<InvalidProtocolBufferException>(() => Parser.Parse<SimulationInput>(body));

    [Fact]
    public void Proto3JsonAcceptsWhatTheContractRefuses()
    {
        Assert.Equal(440000, Parse("{\"list_price\": \"440000\", \"months_remaining\": 19}").ListPrice);    // strings are numbers
        Assert.Equal(440000, Parse("{\"listPrice\": 440000, \"monthsRemaining\": 19}").ListPrice);          // camelCase alias
        Assert.Equal(2.0, Parse("{\"list_price\": 440000, \"months_remaining\": 19, \"itbi_pct\": null}").ItbiPct); // null = unset
        Assert.True(double.IsNaN(Parse("{\"list_price\": \"NaN\", \"months_remaining\": 19}").ListPrice));
        Assert.Equal(5000, Parse("{\"list_price\": 440000, \"months_remaining\": 5000}").MonthsRemaining);  // no API limits
    }

    [Fact]
    public void TheWireStaysSnakeCase()
    {
        var json = new JsonFormatter(JsonFormatter.Settings.Default.WithPreserveProtoFieldNames(true)).Format(Parse(RA));
        Assert.StartsWith("{ \"name\": \"RA\", \"list_price\": 440000, \"months_remaining\": 19", json);
        Assert.Contains("\"listPrice\"", JsonFormatter.Default.Format(Parse(RA)));                         // the default
    }
}
