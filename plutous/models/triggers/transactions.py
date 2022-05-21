from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_insert_cashflow = DDL("""
    DROP TRIGGER IF EXISTS insert_cashflow
""")

insert_cashflow = DDL("""
    CREATE TRIGGER insert_cashflow
        AFTER INSERT
        ON transactions FOR EACH ROW
    BEGIN
        INSERT INTO cashflows (
            transaction_id, t_account_id, amount
        )
        VALUES
            (NEW.id, NEW.debit_account_id, NEW.amount),
            (NEW.id, NEW.credit_account_id, -1 * NEW.amount)
        ON DUPLICATE KEY UPDATE
            transaction_id = transaction_id
        ;
    END
""")


drop_update_cashflow = DDL("""
    DROP TRIGGER IF EXISTS update_cashflow
""")

update_cashflow = DDL("""
    CREATE TRIGGER update_cashflow
        BEFORE UPDATE
        ON transactions FOR EACH ROW
    BEGIN
        UPDATE cashflows
        SET
            transaction_id = NEW.id,
            amount = CASE
                WHEN t_account_id = OLD.debit_account_id THEN NEW.amount
                WHEN t_account_id = OLD.credit_account_id THEN -1 * NEW.amount
            END,
            t_account_id = CASE
                WHEN t_account_id = OLD.debit_account_id THEN NEW.debit_account_id
                WHEN t_account_id = OLD.credit_account_id THEN NEW.credit_account_id
            END
        WHERE
            transaction_id = OLD.id
        ;
    END
""")


drop_delete_cashflow = DDL("""
    DROP TRIGGER IF EXISTS delete_cashflow
""")

delete_cashflow = DDL("""
    CREATE TRIGGER delete_cashflow
        BEFORE DELETE
        ON transactions FOR EACH ROW
    BEGIN
        DELETE FROM cashflows
        WHERE transaction_id = OLD.id
        ;
    END
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_insert_cashflow.execute_if(dialect='mysql')
)
event.listen(
    SQLModel.metadata,
    'after_create',
    insert_cashflow.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    drop_update_cashflow.execute_if(dialect='mysql')
)
event.listen(
    SQLModel.metadata,
    'after_create',
    update_cashflow.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    drop_delete_cashflow.execute_if(dialect='mysql')
)
event.listen(
    SQLModel.metadata,
    'after_create',
    delete_cashflow.execute_if(dialect='mysql')
)
