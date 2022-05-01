from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_get_t_account_by_group = DDL("""
    DROP FUNCTION IF EXISTS get_t_account_by_group
""")

get_t_account_by_group = DDL("""
    CREATE FUNCTION get_t_account_by_group (
        g VARCHAR(20),
        t_account INT
    ) RETURNS INT
        RETURN (
            SELECT ta2.id
            FROM t_accounts AS ta1
            JOIN t_accounts as ta2
                ON ta2.currency = ta1.currency
            JOIN groups AS g
                ON g.id = ta2.group_id
                AND g.name = g
            WHERE ta1.id = t_account
        );
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_get_t_account_by_group.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    get_t_account_by_group.execute_if(dialect='mysql')
)
