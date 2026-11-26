package de.backendlab.catalog;

import de.backendlab.cache.Changes;
import de.backendlab.cache.Product;
import de.backendlab.cache.ProductGenerator;
import de.backendlab.cache.Watermark;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

import java.sql.Statement;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.Supplier;

/** JDBC keeps SQL visibility, watermark predicates and acknowledgement explicit. */
@Repository
public class ProductStore {
    private final JdbcTemplate jdbc;
    private final NamedParameterJdbcTemplate named;
    private final TransactionTemplate tx;

    private static final RowMapper<Product> MAPPER = (rs, rowNumber) -> {
        var time = rs.getObject("last_updated_time", LocalDateTime.class);
        return new Product(rs.getLong("id"), rs.getString("name"),
                time == null ? null : time.toInstant(ZoneOffset.UTC));
    };

    public ProductStore(JdbcTemplate jdbc, PlatformTransactionManager manager) {
        this.jdbc = jdbc;
        this.named = new NamedParameterJdbcTemplate(jdbc);
        this.tx = new TransactionTemplate(manager);
        tx.setIsolationLevel(TransactionDefinition.ISOLATION_REPEATABLE_READ);
    }

    public <T> T transaction(Supplier<T> work) {
        return tx.execute(status -> work.get());
    }

    public void seedOnce(int count) {
        if (count < 0 || count > 1_000_000) {
            throw new IllegalArgumentException("seed count 0..1000000");
        }
        transaction(() -> {
            if (jdbc.queryForObject("SELECT COUNT(*) FROM lab_seed_state", Long.class) > 0) {
                return null;
            }
            if (jdbc.queryForObject("SELECT COUNT(*) FROM products", Long.class) == 0) {
                var products = ProductGenerator.generate(count);
                jdbc.batchUpdate("INSERT INTO products(id,name,last_updated_time) VALUES(?,?,NULL)",
                        products, 1000, (ps, p) -> {
                            ps.setLong(1, p.id());
                            ps.setString(2, p.name());
                        });
            }
            jdbc.update("INSERT INTO lab_seed_state(id) VALUES(1)");
            return null;
        });
    }

    public List<Product> all() {
        return jdbc.query("SELECT id,name,last_updated_time FROM products ORDER BY id", MAPPER);
    }

    public List<Product> after(Watermark mark) {
        return jdbc.query("""
                SELECT id,name,last_updated_time FROM products
                WHERE id > ? OR last_updated_time >= ?
                ORDER BY id
                """, MAPPER, mark.id(), LocalDateTime.ofInstant(mark.timestamp(), ZoneOffset.UTC));
    }

    public record JournalEntry(long changeId, long productId) {}

    public List<JournalEntry> pending(int limit) {
        return jdbc.query("SELECT change_id,product_id FROM product_changes ORDER BY change_id LIMIT ?",
                (rs, n) -> new JournalEntry(rs.getLong(1), rs.getLong(2)), limit);
    }

    public List<Long> allPendingIds() {
        return jdbc.queryForList("SELECT change_id FROM product_changes ORDER BY change_id", Long.class);
    }

    /** Call within the same consistent-read transaction as pending(). */
    public Changes currentChanges(List<JournalEntry> events) {
        if (events.isEmpty()) {
            return new Changes(List.of(), Set.of());
        }
        var ids = new HashSet<Long>();
        events.forEach(e -> ids.add(e.productId()));
        var rows = named.query("SELECT id,name,last_updated_time FROM products WHERE id IN (:ids)",
                Map.of("ids", ids), MAPPER);
        var deleted = new HashSet<>(ids);
        rows.forEach(p -> deleted.remove(p.id()));
        return new Changes(rows, deleted);
    }

    public void acknowledge(List<Long> ids) {
        // Bound the SQL statement size, while retaining the caller's transaction.
        for (int start = 0; start < ids.size(); start += 1000) {
            named.update("DELETE FROM product_changes WHERE change_id IN (:ids)",
                    Map.of("ids", ids.subList(start, Math.min(start + 1000, ids.size()))));
        }
    }

    public long create(String name) {
        var keys = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            var statement = connection.prepareStatement(
                    "INSERT INTO products(name,last_updated_time) VALUES(?,NULL)",
                    Statement.RETURN_GENERATED_KEYS);
            statement.setString(1, name);
            return statement;
        }, keys);
        return Objects.requireNonNull(keys.getKey()).longValue();
    }

    public boolean rename(long id, String name) {
        return jdbc.update("UPDATE products SET name=?, last_updated_time=UTC_TIMESTAMP(6) WHERE id=?",
                name, id) > 0;
    }

    public boolean delete(long id) {
        return jdbc.update("DELETE FROM products WHERE id=?", id) > 0;
    }
}
