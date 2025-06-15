create or replace function check_equipment_status()
returns trigger as $$
begin
    if (select equipment_status from equipment where equipment_id = new.equipment_id) != 'свободен' then
        raise exception 'оборудование с id % не доступно', new.equipment_id;
    end if;
    return new;
end;
$$ language plpgsql;
create trigger before_require_insert
before insert on require
for each row
execute function check_equipment_status();
