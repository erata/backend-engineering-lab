CREATE TABLE IF NOT EXISTS products (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    last_updated_time DATETIME(6) NULL,
    INDEX ix_products_updated(last_updated_time)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS product_changes (
    change_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT NOT NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS lab_seed_state (id INT NOT NULL PRIMARY KEY) ENGINE=InnoDB;
CREATE TRIGGER IF NOT EXISTS products_after_insert AFTER INSERT ON products FOR EACH ROW INSERT INTO product_changes(product_id) VALUES(NEW.id);
CREATE TRIGGER IF NOT EXISTS products_after_update AFTER UPDATE ON products FOR EACH ROW INSERT INTO product_changes(product_id) VALUES(NEW.id);
CREATE TRIGGER IF NOT EXISTS products_after_delete AFTER DELETE ON products FOR EACH ROW INSERT INTO product_changes(product_id) VALUES(OLD.id);

CREATE TABLE IF NOT EXISTS lab_prices(product_id BIGINT PRIMARY KEY,cents BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS lab_price_audit(id BIGINT AUTO_INCREMENT PRIMARY KEY,product_id BIGINT NOT NULL,cents BIGINT NOT NULL);
