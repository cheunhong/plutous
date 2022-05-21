from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_insert_exchage_transactions = DDL("""
    DROP TRIGGER IF EXISTS insert_exchage_transactions
""")

insert_exchage_transactions = DDL("""
    CREATE TRIGGER insert_exchage_transactions
        AFTER INSERT
        ON currency_exchanges FOR EACH ROW
    BEGIN
        DECLARE ce_account1 INT;
        DECLARE ce_account2 INT;
        SET ce_account1 = (SELECT acquire_t_account_by_group('currency_exchange', NEW.debit_account_id));
        SET ce_account2 = (SELECT acquire_t_account_by_group('currency_exchange', NEW.credit_account_id));

        INSERT INTO transactions (
            debit_account_id, credit_account_id, amount,
            transacted_at, transactable_id, transactable_type
        )
        VALUES (
            NEW.debit_account_id , ce_account1, NEW.debit_amount,
            NEW.transacted_at , NEW.id, 'CurrencyExchange'
        ), (
            ce_account2, NEW.credit_account_id, NEW.credit_amount,
            NEW.transacted_at, NEW.id , 'CurrencyExchange'
        )
        ;
    END
""")


drop_update_exchage_transactions = DDL("""
    DROP TRIGGER IF EXISTS update_exchage_transactions
""")

update_exchage_transactions = DDL("""
    CREATE TRIGGER update_exchage_transactions
        BEFORE UPDATE
        ON currency_exchanges FOR EACH ROW
    BEGIN
        DECLARE ce_account1 INT;
        DECLARE ce_account2 INT;
        SET ce_account1 = (SELECT acquire_t_account_by_group('currency_exchange', NEW.debit_account_id));
        SET ce_account2 = (SELECT acquire_t_account_by_group('currency_exchange', NEW.credit_account_id));

        UPDATE transactions
        SET
            amount = CASE
                WHEN debit_account_id = OLD.debit_account_id THEN NEW.debit_amount
                ELSE NEW.credit_amount
            END,
            debit_account_id = CASE
                WHEN debit_account_id = OLD.debit_account_id THEN NEW.debit_account_id
                ELSE ce_account2
            END,
            credit_account_id = CASE
                WHEN credit_account_id = OLD.credit_account_id THEN NEW.credit_account_id
                ELSE ce_account1
            END,
            transacted_at = NEW.transacted_at
        WHERE
            transactable_id = OLD.id
            AND transactable_type = 'CurrencyExchange'
        ;
    END
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_insert_exchage_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    insert_exchage_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    drop_update_exchage_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    update_exchage_transactions.execute_if(dialect='mysql')
)
