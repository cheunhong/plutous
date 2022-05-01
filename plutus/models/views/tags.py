from sqlmodel import SQLModel
from sqlalchemy import DDL, event


drop_tags_view = DDL("""
    DROP VIEW IF EXISTS tags_view;
""")

tags_view = DDL("""
    CREATE VIEW tags_view AS
    SELECT
        t.id
        , t.name
        , t.debit_account_id
        , t.credit_account_id
        , a.name AS debit_account
        , b.name AS credit_account
        , t.created_at
        , t.updated_at
    FROM tags AS t
    JOIN t_accounts AS a
        ON a.id = t.debit_account_id
    JOIN t_accounts AS b
        ON b.id = t.credit_account_id
    ;
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_tags_view.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    tags_view.execute_if(dialect='mysql')
)
