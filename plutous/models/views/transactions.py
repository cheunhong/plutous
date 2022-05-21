from sqlmodel import SQLModel
from sqlalchemy import DDL, event


drop_transactions_view = DDL("""
    DROP VIEW IF EXISTS transactions_view;
""")

transactions_view = DDL("""
    CREATE VIEW transactions_view AS
    SELECT
        t.id
        , t.amount
        , ta1.currency
        , t.tag_id
        , tg.name AS tag
        , t.description
        , t.debit_account_id
        , t.credit_account_id
        , ta1.name AS debit_account
        , ta2.name AS credit_account
        , ta1.type as debit_account_type
        , ta2.type as credit_account_type
        , u1.name AS debit_account_user
        , u2.name AS credit_account_user
        , t.transacted_at
        , CAST(DATE_FORMAT(t.transacted_at, '%%Y-%%m-01') AS date) as transacted_month
        , t.transactable_id
        , t.transactable_type
        , t.created_at
        , t.updated_at
    FROM transactions AS t
    LEFT JOIN tags AS tg
        ON tg.id = t.tag_id
    JOIN t_accounts AS ta1
        ON ta1.id = t.debit_account_id
    LEFT JOIN accounts as a1
        ON a1.id =  ta1.account_id
    LEFT JOIN users as u1
        on u1.id = a1.user_id
    JOIN t_accounts AS ta2
        ON ta2.id = t.credit_account_id
    LEFT JOIN accounts as a2
        ON a2.id =  ta2.account_id
    LEFT JOIN users as u2
        on u2.id = a2.user_id
    ;
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_transactions_view.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    transactions_view.execute_if(dialect='mysql')
)
