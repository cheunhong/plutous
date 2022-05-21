from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_insert_commission_transactions = DDL("""
    DROP TRIGGER IF EXISTS insert_commission_transactions
""")

insert_commission_transactions = DDL("""
    CREATE TRIGGER insert_commission_transactions
        AFTER INSERT
        ON commissions FOR EACH ROW
    BEGIN
        DECLARE c_account INT;
        SET c_account = (SELECT acquire_t_account_by_group('commission', NEW.t_account_id));

        INSERT INTO transactions (
            debit_account_id, credit_account_id, amount,
            transacted_at, transactable_id, transactable_type
        )
        VALUES (
            c_account , NEW.t_account_id, NEW.amount,
            NEW.charged_at , NEW.id, 'Commission'
        )
        ;
    END
""")


drop_update_commission_transactions = DDL("""
    DROP TRIGGER IF EXISTS update_commission_transactions
""")

update_commission_transactions = DDL("""
    CREATE TRIGGER update_commission_transactions
        BEFORE UPDATE
        ON commissions FOR EACH ROW
    BEGIN
        DECLARE c_account INT;
        SET c_account = (SELECT acquire_t_account_by_group('commission', NEW.t_account_id));

        UPDATE transactions
        SET
            amount = NEW.amount,
            debit_account_id = c_account,
            credit_account_id = NEW.t_account_id,
            transacted_at = NEW.charged_at
        WHERE
            transactable_id = OLD.id
            AND transactable_type = 'Commission'
        ;
    END
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_insert_commission_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    insert_commission_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    drop_update_commission_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    update_commission_transactions.execute_if(dialect='mysql')
)
