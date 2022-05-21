from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_insert_position_flows = DDL("""
    DROP TRIGGER IF EXISTS insert_position_flows
""")

insert_position_flows = DDL("""
    CREATE TRIGGER insert_position_flows
        BEFORE INSERT
        ON position_flows FOR EACH ROW
    BEGIN
        UPDATE positions
        SET
            price = NEW.price,
            size = size + NEW.size,
            cost = cost + NEW.size * NEW.price + NEW.pnl,
            entry_price = cost / size,
            realized_pnl = realized_pnl + NEW.pnl,
            opened_at = CASE
                WHEN opened_at IS NULL THEN NEW.transacted_at
                ELSE opened_at
            END,
            closed_at = CASE
                WHEN size = 0 THEN NEW.transacted_at
                ELSE closed_at
            END
        WHERE
            positions.id = NEW.position_id
        ;
    END
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_insert_position_flows.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    insert_position_flows.execute_if(dialect='mysql')
)
