from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_insert_cashflow_balance = DDL("""
    DROP TRIGGER IF EXISTS insert_cashflow_balance
""")

insert_cashflow_balance = DDL("""
    CREATE TRIGGER insert_cashflow_balance
        BEFORE INSERT
        ON cashflows FOR EACH ROW
    BEGIN
        UPDATE t_accounts
        SET balance = balance + NEW.amount
        WHERE
            t_accounts.id = NEW.t_account_id
        ;
    END
""")


drop_update_cashflow_balance = DDL("""
    DROP TRIGGER IF EXISTS update_cashflow_balance
""")

update_cashflow_balance = DDL("""
    CREATE TRIGGER update_cashflow_balance
        BEFORE UPDATE
        ON cashflows FOR EACH ROW
    BEGIN
        UPDATE t_accounts
        SET balance = balance - OLD.amount
        WHERE
            t_accounts.id = OLD.t_account_id
        ;
        UPDATE t_accounts
        SET balance = balance + NEW.amount
        WHERE
            t_accounts.id = NEW.t_account_id
        ;
    END
""")


drop_delete_cashflow_balance = DDL("""
    DROP TRIGGER IF EXISTS delete_cashflow_balance
""")

delete_cashflow_balance = DDL("""
    CREATE TRIGGER delete_cashflow_balance
        BEFORE DELETE
        ON cashflows FOR EACH ROW
    BEGIN
        UPDATE t_accounts
        SET balance = balance - OLD.amount
        WHERE
            t_accounts.id = OLD.t_account_id
        ;
    END
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_insert_cashflow_balance.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    insert_cashflow_balance.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    drop_update_cashflow_balance.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    update_cashflow_balance.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    drop_delete_cashflow_balance.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    delete_cashflow_balance.execute_if(dialect='mysql')
)
