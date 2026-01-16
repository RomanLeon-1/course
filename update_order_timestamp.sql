CREATE OR REPLACE FUNCTION update_order_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_update_timestamp
BEFORE UPDATE ON "Order"
FOR EACH ROW
EXECUTE FUNCTION update_order_timestamp();
