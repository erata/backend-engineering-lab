using Xunit;using System.Text.Json;
public class ExperimentTests {
 [Theory][InlineData("lock")][InlineData("atomic")]public void StockInvariant(string mode){var x=JsonSerializer.SerializeToElement(Lab.Reserve(mode,100,200));Assert.True(x.GetProperty("correct").GetBoolean());}
 [Fact] public void SameChecksum(){var a=JsonSerializer.SerializeToElement(Lab.Cpu(10000,100,1));var b=JsonSerializer.SerializeToElement(Lab.Cpu(10000,100,4));Assert.Equal(a.GetProperty("checksum").GetString(),b.GetProperty("checksum").GetString());}
 [Fact]public async Task SingleFlight(){var x=JsonSerializer.SerializeToElement(await Lab.Stampede(true,32));Assert.Equal(1,x.GetProperty("loads").GetInt32());}
}
