> Scope: original Spring Boot cache edition (v0.1). For the expanded implementation, see the [root README](../README.md), [coverage](ROADMAP.md) and [extended protocol](EXPERIMENT_PROTOCOL.md).

# API and local user guide

Base URL: `http://localhost:8080`. The portable contract is [openapi.yaml](../shared/contracts/openapi.yaml). It is a static specification, not a hosted Swagger UI.

| Method | Path | Expected behaviour |
|---|---|---|
| GET | `/api/products?page=1&size=10&search=` | Filter by case-insensitive substring, sort by ID ascending, return page and total |
| GET | `/api/products/{id}` | Get one cached product, or 404 |
| POST | `/api/products` | Insert into MySQL with null timestamp; 201 and Location header |
| PUT | `/api/products/{id}` | Rename existing product and assign UTC timestamp; 204 or 404 |
| DELETE | `/api/products/{id}` | Delete from MySQL; 204 or 404 |
| GET | `/api/cache/status` | Cache strategy, sync strategy, readiness and last refresh observations |
| POST | `/lab/cache/refresh` | Local lab profile only; 200 on completion, 409 if busy/not ready |
| GET | `/actuator/health` | Basic application/dependency health |

Catalogue operations return 503 until initial loading completes. Invalid page/size/name input returns 400. Page is 1-based, default size 10, accepted size 1–100. An out-of-range page returns an empty list. Search length is at most 255 characters. Names must be nonblank and at most 255 Java characters before stripping whitespace.

After a successful write, a GET may still return the previous cached state or 404 until a refresh processes the change. Clients must not assume read-your-writes. The baseline does not reflect hard deletes until restart. For ordinary demonstrations use the default journal mode. A response with code 201 or 204 confirms a database write, not cache publication.

### Example response shape (illustrative, not a captured runtime response)

```json
{
  "page": 1,
  "size": 10,
  "total": 100000,
  "items": [{"id": 1, "name": "Product 1", "lastUpdatedTime": null}]
}
```

The real default first page contains ten items; this is abbreviated to show the schema.

## Bash / curl demonstration

```bash
cp .env.example .env
docker compose up -d --build
curl -fsS http://localhost:8080/api/cache/status
curl -fsS 'http://localhost:8080/api/products?page=2&size=10'
curl -fsS 'http://localhost:8080/api/products?search=Product%20100'
curl -i -X POST http://localhost:8080/api/products \
  -H 'Content-Type: application/json' -d '{"name":"New product"}'
```

Copy the returned ID and use it below. The example ID is appropriate only for an untouched 100,000-row seed; use the actual returned ID in your run.

```bash
id=100001
sleep 12
curl -fsS "http://localhost:8080/api/products/$id"
curl -i -X PUT "http://localhost:8080/api/products/$id" \
  -H 'Content-Type: application/json' -d '{"name":"Renamed product"}'
sleep 12
curl -fsS "http://localhost:8080/api/products/$id"
curl -i -X DELETE "http://localhost:8080/api/products/$id"
```

For repeatable smoke tests, enable the lab profile but keep `LAB_CACHE_STRATEGY=snapshot` and `LAB_SYNC_STRATEGY=journal`. Restart the app, then run `python tools/smoke_api.py`. Use a clean disposable database with no background writer/backlog. The script creates, renames, and deletes one uniquely named product. Manual refresh may return 409 if the scheduler holds the writer lock; the script retries that case.

## Configuration reference

| Variable | Default | Meaning |
|---|---|---|
| `LAB_SEED_COUNT` | `100000` | First startup seed, 0–1,000,000 |
| `LAB_CACHE_STRATEGY` | `snapshot` | `unsafe`, `synchronized`, `concurrent`, `snapshot`, `caffeine` |
| `LAB_SYNC_STRATEGY` | `journal` | `journal` or `watermark` |
| `LAB_REFRESH_INTERVAL` | `10s` | Fixed delay and initial delay |
| `LAB_BATCH_SIZE` | `1000` | Journal notifications per refresh, 1–10000 |
| `SPRING_PROFILES_ACTIVE` | `default` | Set `lab` for negative/manual experiments |
| `LAB_PORT` | `8080` | Host port for Compose |
| `DB_URL` | Local MySQL JDBC URL | Compose supplies the internal host `mysql` |
| `DB_USER` | `lab` | Local schema user |
| `DB_PASSWORD` | `local-lab-password` | Local demo credential |
| `DB_ROOT_PASSWORD` | `local-root-password` | MySQL container bootstrap credential |
| `SERVER_ADDRESS` | `127.0.0.1` | Bind address; Compose uses internal `0.0.0.0` |

To run the app outside Docker, build with Maven (`mvn -f implementations/spring-boot/pom.xml -pl app -am package`), provide a reachable MySQL 8.4 database and credentials using environment variables, and run `java -jar implementations/spring-boot/app/target/app-0.1.0.jar`. You need a schema with permission to create tables and triggers. The default Compose database is intentionally not host-published; use a separate local database or explicitly add a loopback port mapping if needed.
