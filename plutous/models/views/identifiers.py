from sqlmodel import SQLModel
from sqlalchemy import DDL, event


drop_identifiers_view = DDL("""
    DROP VIEW IF EXISTS identifiers_view;
""")

identifiers_view = DDL("""
    CREATE VIEW identifiers_view AS
    SELECT
        i.id
        , i.keyword
        , i.description
        , i.tag_id
        , t.name AS tag
        , coalesce(
            i.debit_account_id,
            t.debit_account_id
        ) as debit_account_id
        , coalesce(
            i.credit_account_id,
            t.credit_account_id
        ) as credit_account_id
        , coalesce(
            a.name,
            t.debit_account
        ) as debit_account
        , coalesce(
            b.name,
            t.credit_account
        ) as credit_account
        , i.base_account_id
        , base.name as base_account
        , i.created_at
        , i.updated_at
    FROM identifiers AS i
    LEFT JOIN tags_view AS t
        ON t.id = i.tag_id
    LEFT JOIN t_accounts AS a
        ON a.id = i.debit_account_id
    LEFT JOIN t_accounts AS b
        ON b.id = i.credit_account_id
    JOIN t_accounts as base
        ON base.id = i.base_account_id
    ;
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_identifiers_view.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    identifiers_view.execute_if(dialect='mysql')
)
