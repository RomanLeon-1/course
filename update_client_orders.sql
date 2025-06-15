create or replace function update_client_orders()
returns trigger as $$
begin
    update client
    set client_orders = client_orders + 1
    where client_id = new.client_id;
    return new;
end;
$$ language plpgsql;
create trigger after_order_insert
after insert on "order"
for each row
execute function update_client_orders();
