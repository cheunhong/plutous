from sqlmodel import SQLModel
from sqlalchemy import DDL, event


drop_cashflows_view = DDL("""
    DROP VIEW IF EXISTS cashflows_view;
""")

cashflows_view = DDL("""
    CREATE VIEW cashflows_view AS
    SELECT
        c.id
        , c.transaction_id
        , tg.name AS tag
        , t.description
        , c.t_account_id
        , ta.name AS account
        , ta.type AS account_type
        , CASE
            WHEN ta.type IN ('liability', 'income') THEN c.amount * -1
            ELSE c.amount
        END AS amount
        , ta.currency
        , u.name AS user_name
        , t.transacted_at
        , CAST(DATE_FORMAT(t.transacted_at, '%%Y-%%m-01') AS DATE) AS transacted_month
        , c.created_at
        , c.updated_at
    FROM cashflows AS c
    JOIN transactions AS t
        ON t.id = c.transaction_id
    LEFT JOIN tags AS tg
        ON tg.id = t.tag_id
    JOIN t_accounts AS ta
        ON ta.id = c.t_account_id
    JOIN t_accounts AS ta1
        ON ta1.id = t.debit_account_id
    JOIN t_accounts AS ta2
        ON ta2.id = t.credit_account_id
    LEFT JOIN accounts AS a
        on a.id = COALESCE(ta.account_id, ta1.account_id, ta2.account_id)
    LEFT JOIN users as u
        on u.id = a.user_id
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_cashflows_view.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    cashflows_view.execute_if(dialect='mysql')
)
