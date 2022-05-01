from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_acquire_t_account_by_group = DDL("""
    DROP FUNCTION IF EXISTS acquire_t_account_by_group
""")

acquire_t_account_by_group = DDL("""
    CREATE FUNCTION acquire_t_account_by_group (
        g VARCHAR(20),
        t_account INT
    ) RETURNS INT DETERMINISTIC
        BEGIN
            DECLARE t_account_id INT;
            SET t_account_id = (SELECT get_t_account_by_group(g, t_account));

            IF t_account_id IS NULL THEN
                CALL insert_t_account_by_group(g, t_account, t_account_id);
            END IF
            ;

            RETURN t_account_id;
        END
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_acquire_t_account_by_group.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    acquire_t_account_by_group.execute_if(dialect='mysql')
)
