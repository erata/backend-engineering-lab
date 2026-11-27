using System.Collections.Concurrent;
using System.Collections.Immutable;
using MySqlConnector;
using StackExchange.Redis;
using Microsoft.Extensions.Caching.Memory;
using OpenTelemetry.Metrics;
using OpenTelemetry.Trace;
using OpenTelemetry.Resources;
var builder=WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<Catalog>();builder.Services.AddSingleton<PriceService>();builder.Services.AddSingleton<OutboxSignal>();builder.Services.AddHostedService<OutboxDispatcher>();builder.Services.AddHostedService<RefreshWorker>();builder.Services.AddHttpClient();builder.Services.AddScoped<RequestData>();builder.Services.AddSingleton<SharedData>();
// Lab 06: a scoped service captured by a singleton. Resolved from the root provider on first use; in Development
// (ValidateScopes=true) this throws "Cannot resolve scoped service from root provider", in Production it silently
// creates one RequestContext that lives forever (captive dependency).
builder.Services.AddScoped<RequestContext>();builder.Services.AddSingleton<CaptiveHolder>(sp=>new CaptiveHolder(sp.GetRequiredService<RequestContext>()));
builder.Services.AddSingleton<RedisLab>();builder.Services.AddSingleton<SingletonUserHolder>();builder.Services.AddScoped<RequestUserHolder>();builder.Services.AddTransient<OwnedResource>();
if(!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT")))builder.Services.AddOpenTelemetry().ConfigureResource(r=>r.AddService("backendlab-dotnet")).WithTracing(t=>t.AddAspNetCoreInstrumentation().AddHttpClientInstrumentation().AddOtlpExporter()).WithMetrics(m=>m.AddAspNetCoreInstrumentation().AddHttpClientInstrumentation().AddOtlpExporter());
var app=builder.Build();var catalog=app.Services.GetRequiredService<Catalog>();await catalog.Initialize();if(Environment.GetEnvironmentVariable("LAB_ENABLED")=="true")await PriceService.EnsureSchema();
app.MapGet("/api/products",(int? page,int? size,string? search)=>{int p=page??1,s=size??10;if(p<1||s<1||s>100)return Results.BadRequest();var all=catalog.Read().Where(x=>x.Name.Contains(search??"",StringComparison.OrdinalIgnoreCase)).OrderBy(x=>x.Id).ToArray();return Results.Ok(new{page=p,size=s,total=all.Length,items=all.Skip((int)Math.Min((long)(p-1)*s,all.Length)).Take(s)});});
app.MapGet("/api/products/{id:long}",(long id)=>catalog.Get(id) is Product p?Results.Ok(p):Results.NotFound());
app.MapPost("/api/products",async(NameRequest req)=>{if(!Valid(req))return Results.BadRequest();long id=await catalog.Create(req.Name.Trim());return Results.Created($"/api/products/{id}",new{id,cacheVisibility="after refresh"});});
app.MapPut("/api/products/{id:long}",async(long id,NameRequest req)=>{if(!Valid(req))return Results.BadRequest();return await catalog.Rename(id,req.Name.Trim())?Results.NoContent():Results.NotFound();});
app.MapDelete("/api/products/{id:long}",async(long id)=>await catalog.Delete(id)?Results.NoContent():Results.NotFound());
app.MapGet("/api/cache/status",()=>new{count=catalog.Read().Length,sync=catalog.Sync});
if(Environment.GetEnvironmentVariable("LAB_ENABLED")=="true"){
app.MapPost("/lab/cache/refresh",async()=>{await catalog.Refresh();return Results.Ok();});
app.MapPost("/lab/concurrency/reserve",(string? mode,int? stock,int? requests)=>Lab.Reserve(mode??"atomic",stock??1000,requests??2000));
app.MapGet("/lab/cpu/{mode}",(string mode,int? count,int? rounds,int? workers)=>Lab.Cpu(count??100000,rounds??100,mode=="sequential"?1:workers??4));
app.MapGet("/lab/io/{mode}",async(string mode,IHttpClientFactory factory,CancellationToken ct)=>{var client=factory.CreateClient();client.Timeout=TimeSpan.FromSeconds(5);var url=Environment.GetEnvironmentVariable("LAB_MOCK_URL")??"http://localhost:8090";var paths=new[]{"product","inventory","pricing"};if(mode=="concurrent")return await Task.WhenAll(paths.Select(p=>client.GetStringAsync(url+"/"+p,ct)));var result=new List<string>();foreach(var p in paths){if(mode=="blocking"||mode=="sync-over-async")result.Add(client.GetStringAsync(url+"/"+p,ct).GetAwaiter().GetResult());else result.Add(await client.GetStringAsync(url+"/"+p,ct));}return result.ToArray();});
app.MapGet("/lab/threads/info",()=>new{runtime=Environment.Version.ToString(),processors=Environment.ProcessorCount,threadPool=ThreadPool.ThreadCount});
app.MapGet("/lab/di/instances",(string? mode,IServiceProvider services)=>mode=="request"?new{id=services.GetRequiredService<RequestData>().Id,count=100000}:new{id=services.GetRequiredService<SharedData>().Id,count=100000});
app.MapGet("/lab/resources/stampede",async(bool? single,int? requests)=>await Lab.Stampede(single??true,requests??32));
app.MapGet("/lab/resources/pool",async(int? requests,int? permits)=>await Lab.Pool(requests??32,permits??5));
app.MapPost("/lab/events/price-change",async(PriceService prices,long? id,long? cents,string? mode,bool? rollback,bool? failAudit)=>{var m=mode??"event";if((id??1)<1||(cents??100)<0||m is not ("direct" or "event"))return Results.BadRequest(new{error="mode direct|event"});
 try{await prices.Change(id??1,cents??100,m,rollback==true,failAudit==true);return Results.Ok(new{id=id??1,cents=cents??100,mode=m});}catch(RolledBackException e){return Results.Problem(e.Message,statusCode:500);}});
app.MapGet("/lab/events/state",async(PriceService prices,long? id)=>Results.Ok(await prices.State(id??1)));
app.MapGet("/lab/di/captive",(string? mode,CaptiveHolder holder,IServiceProvider services)=>(mode??"captured") switch{"captured"=>Results.Ok(new{mode="captured",id=holder.Captured}),"scoped"=>Results.Ok(new{mode="scoped",id=services.GetRequiredService<RequestContext>().Id}),_=>Results.BadRequest(new{error="mode captured|scoped"})});
app.MapGet("/lab/di/mutable",async(string? mode,string? user,int? delayMs,SingletonUserHolder singleton,RequestUserHolder scoped)=>{
 if(user is null||(delayMs??5) is <0 or >100)return Results.BadRequest(new{error="user required, delayMs 0..100"});
 IUserHolder? holder=(mode??"singleton") switch{"singleton"=>singleton,"request"=>scoped,_=>null};if(holder is null)return Results.BadRequest(new{error="mode singleton|request"});
 holder.User=user;await Task.Delay(delayMs??5);var seen=holder.User;return Results.Ok(new{mode=mode??"singleton",expected=user,actual=seen,correct=user==seen});});
// Ownership as in a BackgroundService: resolving a disposable transient from the root provider makes the root its owner
// (disposed only at application shutdown = a leak per call); a scope per unit of work disposes it at the end of the scope.
app.MapGet("/lab/di/ownership",(string? mode,int? n)=>{int count=n??100;if(count is <1 or >10000)return Results.BadRequest(new{error="n 1..10000"});
 long c0=Interlocked.Read(ref OwnedResource.Created),d0=Interlocked.Read(ref OwnedResource.Disposed);
 switch(mode??"root"){case "root":for(int i=0;i<count;i++)app.Services.GetRequiredService<OwnedResource>();break;
  case "scope":for(int i=0;i<count;i++){using var scope=app.Services.CreateScope();scope.ServiceProvider.GetRequiredService<OwnedResource>();}break;
  default:return Results.BadRequest(new{error="mode root|scope"});}
 return Results.Ok(new{mode=mode??"root",created=Interlocked.Read(ref OwnedResource.Created)-c0,disposed=Interlocked.Read(ref OwnedResource.Disposed)-d0});});
app.MapGet("/lab/resources/db",async(int? pool,int? ms)=>{int p=pool??5,d=ms??30;if(p is not (5 or 20)||d is <1 or >1000)return Results.BadRequest(new{error="pool 5|20, ms 1..1000"});
 var sw=System.Diagnostics.Stopwatch.StartNew();
 try{await using var c=new MySqlConnection(Pools.For(p));await c.OpenAsync();var waitMs=sw.Elapsed.TotalMilliseconds;await using var cmd=c.CreateCommand();cmd.CommandText="SELECT SLEEP(@s)";cmd.Parameters.AddWithValue("@s",d/1000.0);await cmd.ExecuteScalarAsync();return Results.Ok(new{pool=p,waitMs});}
 catch(MySqlException e){return Results.Json(new{pool=p,error=e.Message},statusCode:503);}});
app.MapGet("/lab/redis/product/{id:long}",(long id,string? mode,RedisLab redis)=>redis.Product(id,mode??"distributed"));
app.MapPost("/lab/redis/invalidate",async(long? id,RedisLab redis)=>Results.Ok(new{invalidated=await redis.Db.KeyDeleteAsync($"lab:product:{id??42}")}));
app.MapPost("/lab/redis/reset",async(long? id,RedisLab redis)=>{long i=id??42;await redis.Db.KeyDeleteAsync(new RedisKey[]{$"lab:product:{i}",$"lab:loads:{i}",$"lab:lock:{i}"});return Results.Ok(new{reset=i});});
app.MapGet("/lab/redis/loads",async(long? id,RedisLab redis)=>{long i=id??42;var v=await redis.Db.StringGetAsync($"lab:loads:{i}");return Results.Ok(new{id=i,loads=v.IsNull?0:(long)v,fallbacks=Interlocked.Read(ref RedisLab.Fallbacks),client="StackExchange.Redis"});});
}app.Run();
static bool Valid(NameRequest? req)=>req?.Name is {Length: >0 and <=255} n&&!string.IsNullOrWhiteSpace(n);
public sealed record NameRequest(string Name);
// ---- Lab 06: DI lifetimes ----------------------------------------------------------------------------------
public sealed class RequestContext{public Guid Id{get;}=Guid.NewGuid();}
public sealed class CaptiveHolder(RequestContext captured){public Guid Captured=>captured.Id;}
public interface IUserHolder{string? User{get;set;}}
public sealed class SingletonUserHolder:IUserHolder{public string? User{get;set;}}
public sealed class OwnedResource:IDisposable{public static long Created,Disposed;public OwnedResource(){Interlocked.Increment(ref Created);}public void Dispose()=>Interlocked.Increment(ref Disposed);}
public sealed class RequestUserHolder:IUserHolder{public string? User{get;set;}}

// ---- Lab 08: two real MySqlConnector pools (5 / 20), 1 s wait for a free connection --------------------------
public static class Pools{
 static readonly string Cs=Environment.GetEnvironmentVariable("DB_CONNECTION")??"Server=localhost;Database=backendlab;User ID=lab;Password=local-lab-password";
 public static string For(int size)=>$"{Cs};Minimum Pool Size={size};Maximum Pool Size={size};Connection Timeout=1;Application Name=lab-pool-{size}";
}

// ---- Lab 08: Redis shared cache with StackExchange.Redis -----------------------------------------------------
// Same contract as the Spring (Lettuce) and Jakarta (Jedis) ports: cache-aside on lab:product:{id}, MySQL + 100 ms on a
// miss, 30 s TTL, lab:loads:{id} counts loads across instances; mode none | local (in-process single-flight) |
// distributed (SET NX PX lock). One multiplexed connection is shared by all requests (the client's design); it is
// created lazily, so editions without Redis never connect. Timeouts are 500 ms like the other ports (client default
// is 5 s); AbortOnConnectFail=false keeps reconnecting in the background instead of failing at startup.
// Lab simplification as in Spring: the lock is released with GET + DEL and has no fencing token.
public sealed class RedisLab{
 public static long Fallbacks;
 static readonly string Cs=Environment.GetEnvironmentVariable("DB_CONNECTION")??"Server=localhost;Database=backendlab;User ID=lab;Password=local-lab-password";
 static readonly TimeSpan Ttl=TimeSpan.FromSeconds(30),Lease=TimeSpan.FromSeconds(3);
 readonly Lazy<ConnectionMultiplexer> mux=new(()=>ConnectionMultiplexer.Connect(new ConfigurationOptions{
  EndPoints={{Environment.GetEnvironmentVariable("REDIS_HOST")??"localhost",6379}},AbortOnConnectFail=false,ConnectTimeout=500,SyncTimeout=500,AsyncTimeout=500}));
 readonly ConcurrentDictionary<string,Task<string>> inflight=new();
 readonly string instance=Environment.MachineName;
 public IDatabase Db=>mux.Value.GetDatabase();
 public async Task<IResult> Product(long id,string mode){
  if(mode is not ("none" or "local" or "distributed"))return Results.BadRequest(new{error="mode none|local|distributed"});
  var sw=System.Diagnostics.Stopwatch.StartNew();string key=$"lab:product:{id}";
  try{
   string? value=await Db.StringGetAsync(key);string source="redis";
   if(value is null){source="loaded-or-waited";value=mode switch{"none"=>await Load(id,key),"local"=>await Local(id,key),_=>await Distributed(id,key)};}
   return Results.Ok(new{value,source,instance,ms=sw.Elapsed.TotalMilliseconds});
  }catch(Exception e) when(e is RedisException or TimeoutException){
   // Fail open, as in the other ports: serve from MySQL without caching.
   Interlocked.Increment(ref Fallbacks);
   return Results.Ok(new{value=Json(id,await Name(id)),source="db-fallback",instance,ms=sw.Elapsed.TotalMilliseconds,error=e.GetType().Name});
  }
 }
 static string Json(long id,string name)=>System.Text.Json.JsonSerializer.Serialize(new{id,name});
 static async Task<string> Name(long id){await using var c=new MySqlConnection(Cs);await c.OpenAsync();await using var cmd=c.CreateCommand();cmd.CommandText="SELECT name FROM products WHERE id=@id";cmd.Parameters.AddWithValue("@id",id);return (string)(await cmd.ExecuteScalarAsync())!;}
 async Task<string> Load(long id,string key){
  await Db.StringIncrementAsync($"lab:loads:{id}");var json=Json(id,await Name(id));await Task.Delay(100);
  await Db.StringSetAsync(key,json,Ttl);return json;
 }
 async Task<string> Local(long id,string key){
  var mine=new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
  var leader=inflight.GetOrAdd(key,mine.Task);if(leader!=mine.Task)return await leader;
  try{string? v=await Db.StringGetAsync(key);v??=await Load(id,key);mine.SetResult(v);return v;}
  catch(Exception e){mine.SetException(e);_=mine.Task.Exception;throw;}
  finally{inflight.TryRemove(new KeyValuePair<string,Task<string>>(key,mine.Task));}
 }
 async Task<string> Distributed(long id,string key){
  string lockKey=$"lab:lock:{id}";var deadline=DateTime.UtcNow+Lease;
  while(DateTime.UtcNow<deadline){
   string token=$"{instance}-{Guid.NewGuid()}";
   if(await Db.StringSetAsync(lockKey,token,Lease,When.NotExists)){
    try{string? v=await Db.StringGetAsync(key);return v??await Load(id,key);}
    finally{if(await Db.StringGetAsync(lockKey)==token)await Db.KeyDeleteAsync(lockKey);}
   }
   await Task.Delay(10);string? w=await Db.StringGetAsync(key);if(w is not null)return w;
  }
  throw new InvalidOperationException("lock not acquired within lease");
 }
}

// ---- Lab 07: price change with a transactional outbox ------------------------------------------------------------
// direct: price + audit in one MySQL transaction.
// event : price + outbox row in one transaction (the event is committed atomically with the state change);
//         OutboxDispatcher turns outbox rows into audit rows in a second transaction (at-least-once, here exactly-once
//         because the outbox row is deleted in the same transaction as the audit insert).
// rollback=true: the transaction is rolled back after the update -> neither price, audit nor outbox row persists.
public sealed class RolledBackException(string m):Exception(m);
public sealed class OutboxSignal{public readonly SemaphoreSlim Ready=new(0);}
public sealed class PriceService(OutboxSignal signal){
 static readonly string Cs=Environment.GetEnvironmentVariable("DB_CONNECTION")??"Server=localhost;Database=backendlab;User ID=lab;Password=local-lab-password";
 public static async Task EnsureSchema(){await using var c=new MySqlConnection(Cs);await c.OpenAsync();await using var cmd=c.CreateCommand();
  cmd.CommandText="CREATE TABLE IF NOT EXISTS lab_prices(product_id BIGINT PRIMARY KEY,cents BIGINT NOT NULL);CREATE TABLE IF NOT EXISTS lab_price_audit(id BIGINT AUTO_INCREMENT PRIMARY KEY,product_id BIGINT NOT NULL,cents BIGINT NOT NULL);CREATE TABLE IF NOT EXISTS lab_outbox(id BIGINT AUTO_INCREMENT PRIMARY KEY,product_id BIGINT NOT NULL,cents BIGINT NOT NULL,created DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6))";await cmd.ExecuteNonQueryAsync();
  // fail_remaining simulates a failing handler: the dispatcher leaves the row in the outbox and retries it on the next poll.
  cmd.CommandText="ALTER TABLE lab_outbox ADD COLUMN fail_remaining INT NOT NULL DEFAULT 0";try{await cmd.ExecuteNonQueryAsync();}catch(MySqlException e) when(e.Number==1060){/* column exists */}}
 public async Task Change(long id,long cents,string mode,bool rollback,bool failAudit=false){
  await using var c=new MySqlConnection(Cs);await c.OpenAsync();await using var tx=await c.BeginTransactionAsync();await using var cmd=c.CreateCommand();cmd.Transaction=tx;
  cmd.CommandText="INSERT INTO lab_prices(product_id,cents) VALUES(@id,@c) ON DUPLICATE KEY UPDATE cents=VALUES(cents)";cmd.Parameters.AddWithValue("@id",id);cmd.Parameters.AddWithValue("@c",cents);await cmd.ExecuteNonQueryAsync();
  if(mode=="direct"&&failAudit){await tx.RollbackAsync();throw new RolledBackException("audit failed inside the transaction: price change rolled back");}
  cmd.CommandText=mode=="direct"?"INSERT INTO lab_price_audit(product_id,cents) VALUES(@id,@c)":"INSERT INTO lab_outbox(product_id,cents,fail_remaining) VALUES(@id,@c,@f)";cmd.Parameters.AddWithValue("@f",failAudit?2:0);await cmd.ExecuteNonQueryAsync();
  if(rollback){await tx.RollbackAsync();throw new RolledBackException("intentional rollback: price, audit and outbox row discarded");}
  await tx.CommitAsync();if(mode=="event")signal.Ready.Release();
 }
 public async Task<object> State(long id){await using var c=new MySqlConnection(Cs);await c.OpenAsync();await using var cmd=c.CreateCommand();
  cmd.CommandText="SELECT (SELECT COUNT(*) FROM lab_price_audit WHERE product_id=@id),(SELECT COALESCE(MAX(cents),-1) FROM lab_prices WHERE product_id=@id),(SELECT COUNT(*) FROM lab_outbox WHERE product_id=@id)";cmd.Parameters.AddWithValue("@id",id);
  await using var r=await cmd.ExecuteReaderAsync();await r.ReadAsync();return new{id,auditCount=r.GetInt64(0),cents=r.GetInt64(1),outboxPending=r.GetInt64(2)};}
 public static async Task<int> DispatchBatch(){
  await using var c=new MySqlConnection(Cs);await c.OpenAsync();await using var tx=await c.BeginTransactionAsync();await using var cmd=c.CreateCommand();cmd.Transaction=tx;
  cmd.CommandText="SELECT id,product_id,cents,fail_remaining FROM lab_outbox ORDER BY id LIMIT 500 FOR UPDATE SKIP LOCKED";var all=new List<(long Id,long P,long C,int F)>();
  await using(var r=await cmd.ExecuteReaderAsync()){while(await r.ReadAsync())all.Add((r.GetInt64(0),r.GetInt64(1),r.GetInt64(2),r.GetInt32(3)));}
  var failing=all.Where(x=>x.F>0).ToList();var rows=all.Where(x=>x.F==0).ToList();
  if(failing.Count>0){cmd.CommandText="UPDATE lab_outbox SET fail_remaining=fail_remaining-1 WHERE id IN ("+string.Join(",",failing.Select(x=>x.Id))+")";await cmd.ExecuteNonQueryAsync();}
  if(rows.Count==0){await tx.CommitAsync();return 0;}   // failing rows stay and are retried on the next poll
  cmd.CommandText="INSERT INTO lab_price_audit(product_id,cents) VALUES "+string.Join(",",rows.Select(x=>$"({x.P},{x.C})"));await cmd.ExecuteNonQueryAsync();
  cmd.CommandText="DELETE FROM lab_outbox WHERE id IN ("+string.Join(",",rows.Select(x=>x.Id))+")";await cmd.ExecuteNonQueryAsync();
  await tx.CommitAsync();return rows.Count;
 }
}
public sealed class OutboxDispatcher(OutboxSignal signal,ILogger<OutboxDispatcher> log):BackgroundService{
 protected override async Task ExecuteAsync(CancellationToken ct){
  if(Environment.GetEnvironmentVariable("LAB_ENABLED")!="true")return;
  while(!ct.IsCancellationRequested){
   await signal.Ready.WaitAsync(TimeSpan.FromSeconds(1),ct);   // wake on commit, or poll every second (crash recovery)
   try{while(await PriceService.DispatchBatch()>0){}}catch(Exception e){log.LogError(e,"outbox dispatch failed");}
  }
 }
}

public sealed record Product(long Id,string Name,DateTime? LastUpdatedTime);
public sealed class Catalog {
 private readonly string cs=Environment.GetEnvironmentVariable("DB_CONNECTION")??"Server=localhost;Database=backendlab;User ID=lab;Password=local-lab-password";
 public string Sync {get;}=Environment.GetEnvironmentVariable("LAB_SYNC_STRATEGY")??"journal";private bool initialized;private long markId;private DateTime markTime=new(1970,1,1);
 private readonly string mode=Environment.GetEnvironmentVariable("LAB_CACHE_STRATEGY")??"snapshot";private readonly object gate=new();private readonly SemaphoreSlim refreshGate=new(1);private Dictionary<long,Product> map=new();private ConcurrentDictionary<long,Product> concurrent=new();private readonly MemoryCache library=new(new MemoryCacheOptions());private readonly ConcurrentDictionary<long,byte> keys=new();private ImmutableDictionary<long,Product> snapshot=ImmutableDictionary<long,Product>.Empty;
 public Product[] Read(){if(mode=="library")return keys.Keys.Select(id=>library.Get<Product>(id)).OfType<Product>().ToArray();if(mode=="snapshot")return Volatile.Read(ref snapshot).Values.ToArray();if(mode=="concurrent")return concurrent.Values.ToArray();if(mode=="unsafe")return map.Values.ToArray();lock(gate)return map.Values.ToArray();}
 public Product? Get(long id){if(mode=="library")return library.Get<Product>(id);if(mode=="snapshot")return Volatile.Read(ref snapshot).GetValueOrDefault(id);if(mode=="concurrent")return concurrent.GetValueOrDefault(id);if(mode=="unsafe")return map.GetValueOrDefault(id);lock(gate)return map.GetValueOrDefault(id);}
 public async Task<long> Create(string name){await using var c=new MySqlConnection(cs);await c.OpenAsync();await using var cmd=c.CreateCommand();cmd.CommandText="INSERT INTO products(name,last_updated_time) VALUES(@name,NULL)";cmd.Parameters.AddWithValue("@name",name);await cmd.ExecuteNonQueryAsync();return cmd.LastInsertedId;}
 public async Task<bool> Rename(long id,string name){await using var c=new MySqlConnection(cs);await c.OpenAsync();await using var cmd=c.CreateCommand();cmd.CommandText="UPDATE products SET name=@name,last_updated_time=UTC_TIMESTAMP(6) WHERE id=@id";cmd.Parameters.AddWithValue("@name",name);cmd.Parameters.AddWithValue("@id",id);return await cmd.ExecuteNonQueryAsync()>0;}
 public async Task<bool> Delete(long id){await using var c=new MySqlConnection(cs);await c.OpenAsync();await using var cmd=c.CreateCommand();cmd.CommandText="DELETE FROM products WHERE id=@id";cmd.Parameters.AddWithValue("@id",id);return await cmd.ExecuteNonQueryAsync()>0;}
 public async Task Initialize(){if((mode=="unsafe"||Sync=="watermark")&&Environment.GetEnvironmentVariable("LAB_ENABLED")!="true")throw new InvalidOperationException("lab required");await using var c=new MySqlConnection(cs);await c.OpenAsync();await using var cmd=c.CreateCommand();cmd.CommandText="CREATE TABLE IF NOT EXISTS products(id BIGINT AUTO_INCREMENT PRIMARY KEY,name VARCHAR(255) NOT NULL,last_updated_time DATETIME(6) NULL)";await cmd.ExecuteNonQueryAsync();cmd.CommandText="SELECT COUNT(*) FROM products";if(Convert.ToInt64(await cmd.ExecuteScalarAsync())==0){await using var tx=await c.BeginTransactionAsync();cmd.Transaction=tx;for(int i=1;i<=100000;i+=1000){cmd.CommandText="INSERT INTO products(id,name) VALUES "+string.Join(",",Enumerable.Range(i,1000).Select(n=>$"({n},'Product {n}')"));await cmd.ExecuteNonQueryAsync();}await tx.CommitAsync();}await Refresh();}
 private async Task<List<Product>> Rows(MySqlCommand cmd){var result=new List<Product>();await using var reader=await cmd.ExecuteReaderAsync();while(await reader.ReadAsync())result.Add(new(reader.GetInt64(0),reader.GetString(1),reader.IsDBNull(2)?null:reader.GetDateTime(2)));return result;}
 private void Advance(IEnumerable<Product> rows){foreach(var p in rows){markId=Math.Max(markId,p.Id);if(p.LastUpdatedTime is DateTime t&&t>markTime)markTime=t;}}
 private void Apply(List<Product> upserts,HashSet<long> deletes,bool replace){if(mode=="library"){if(replace){foreach(long id in keys.Keys)library.Remove(id);keys.Clear();}foreach(long id in deletes){library.Remove(id);keys.TryRemove(id,out _);}foreach(var p in upserts){library.Set(p.Id,p);keys[p.Id]=0;}return;}if(mode=="snapshot"){var b=replace?ImmutableDictionary.CreateBuilder<long,Product>():Volatile.Read(ref snapshot).ToBuilder();foreach(long id in deletes)b.Remove(id);foreach(var p in upserts)b[p.Id]=p;Interlocked.Exchange(ref snapshot,b.ToImmutable());return;}if(mode=="concurrent"){if(replace)concurrent.Clear();foreach(long id in deletes)concurrent.TryRemove(id,out _);foreach(var p in upserts)concurrent[p.Id]=p;return;}void Update(){if(replace)map.Clear();foreach(long id in deletes)map.Remove(id);foreach(var p in upserts)map[p.Id]=p;}if(mode=="unsafe")Update();else if(mode=="synchronized")lock(gate)Update();else throw new InvalidOperationException("unknown cache strategy");}
 public async Task Refresh(){await refreshGate.WaitAsync();try{await using var c=new MySqlConnection(cs);await c.OpenAsync();await using var tx=await c.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead);await using var cmd=c.CreateCommand();cmd.Transaction=tx;var events=new List<(long Change,long Product)>();async Task ReadEvents(bool bounded){cmd.Parameters.Clear();cmd.CommandText="SELECT change_id,product_id FROM product_changes ORDER BY change_id"+(bounded?" LIMIT 1000":"");await using var rr=await cmd.ExecuteReaderAsync();while(await rr.ReadAsync())events.Add((rr.GetInt64(0),rr.GetInt64(1)));}
 if(!initialized||Sync=="full"){cmd.CommandText="SELECT id,name,last_updated_time FROM products";var all=await Rows(cmd);Apply(all,new(),true);Advance(all);if(Sync=="journal")await ReadEvents(false);}
 else if(Sync=="watermark"){cmd.CommandText="SELECT id,name,last_updated_time FROM products WHERE id>@id OR last_updated_time>=@time";cmd.Parameters.AddWithValue("@id",markId);cmd.Parameters.AddWithValue("@time",markTime);var changes=await Rows(cmd);Apply(changes,new(),false);Advance(changes);}
 else if(Sync=="journal"){await ReadEvents(true);var upserts=new List<Product>();var deletes=new HashSet<long>();foreach(long id in events.Select(e=>e.Product).Distinct()){cmd.Parameters.Clear();cmd.CommandText="SELECT id,name,last_updated_time FROM products WHERE id=@id";cmd.Parameters.AddWithValue("@id",id);var found=await Rows(cmd);if(found.Count==0)deletes.Add(id);else upserts.Add(found[0]);}Apply(upserts,deletes,false);}
 else throw new InvalidOperationException("sync strategy");foreach(var batch in events.Chunk(1000)){cmd.Parameters.Clear();cmd.CommandText="DELETE FROM product_changes WHERE change_id IN ("+string.Join(",",batch.Select(e=>e.Change.ToString(System.Globalization.CultureInfo.InvariantCulture)))+")";await cmd.ExecuteNonQueryAsync();}await tx.CommitAsync();initialized=true;
 }finally{refreshGate.Release();}}

}
public sealed class RefreshWorker(Catalog cache,ILogger<RefreshWorker> log):BackgroundService{protected override async Task ExecuteAsync(CancellationToken ct){using var timer=new PeriodicTimer(TimeSpan.FromSeconds(10));while(await timer.WaitForNextTickAsync(ct)){try{await cache.Refresh();}catch(Exception e){log.LogError(e,"refresh failed");}}}}
public sealed class RequestData{private readonly string[] data=Enumerable.Range(1,100000).Select(n=>$"Product {n}").ToArray();public Guid Id{get;}=Guid.NewGuid();}
public sealed class SharedData{private readonly string[] data=Enumerable.Range(1,100000).Select(n=>$"Product {n}").ToArray();public Guid Id{get;}=Guid.NewGuid();}
public static class Lab {
 public static object Reserve(string mode,int stock,int requests){if(stock<0||requests<1||requests>2000)throw new ArgumentException();int remaining=stock,accepted=0;object gate=new();Parallel.For(0,requests,i=>{bool ok=false;if(mode=="unsafe"){int n=remaining;Thread.Yield();if(n>0){remaining=n-1;ok=true;}}else if(mode=="lock"){lock(gate){if(remaining>0){remaining--;ok=true;}}}else if(mode=="atomic"){int n;do{n=Volatile.Read(ref remaining);if(n<=0)break;}while(Interlocked.CompareExchange(ref remaining,n-1,n)!=n);ok=n>0;}else throw new ArgumentException();if(ok)Interlocked.Increment(ref accepted);});return new{accepted,remaining,correct=accepted==Math.Min(stock,requests)&&remaining==Math.Max(0,stock-requests)};}
 public static long Work(int i,int rounds){unchecked{ulong x=(ulong)i+1;for(int j=0;j<rounds;j++){x^=x<<13;x^=x>>7;x^=x<<17;}return (long)x;}}
 public static object Cpu(int count,int rounds,int workers){if(count<1||count>100000||rounds<1||rounds>1000||workers<1||workers>32)throw new ArgumentException();var sw=System.Diagnostics.Stopwatch.StartNew();long sum=0;Parallel.For(0,workers,new ParallelOptions{MaxDegreeOfParallelism=workers},k=>{long local=0;unchecked{for(int i=k;i<count;i+=workers)local+=Work(i,rounds);}Interlocked.Add(ref sum,local);});return new{checksum=sum.ToString(),elapsedNs=sw.Elapsed.TotalNanoseconds,processors=Environment.ProcessorCount};}
 public static async Task<object> Stampede(bool single,int requests){if(requests<1||requests>100)throw new ArgumentException();int loads=0;string? value=null;using var gate=new SemaphoreSlim(1);async Task Load(){Interlocked.Increment(ref loads);await Task.Delay(20);Volatile.Write(ref value,"product");}await Task.WhenAll(Enumerable.Range(0,requests).Select(async _=>{if(Volatile.Read(ref value)!=null)return;if(single){await gate.WaitAsync();try{if(value==null)await Load();}finally{gate.Release();}}else await Load();}));return new{loads,requests};}
 public static async Task<object> Pool(int requests,int permits){if(requests<1||requests>100||permits<1||permits>50)throw new ArgumentException();using var gate=new SemaphoreSlim(permits);int active=0,peak=0,rejected=0;object sync=new();await Task.WhenAll(Enumerable.Range(0,requests).Select(async _=>{if(!await gate.WaitAsync(100)){Interlocked.Increment(ref rejected);return;}try{lock(sync){active++;peak=Math.Max(peak,active);}await Task.Delay(30);}finally{lock(sync)active--;gate.Release();}}));return new{peak,rejected,permits};}
}
