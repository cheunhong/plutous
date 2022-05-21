from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_insert_realized_pnl_transactions = DDL("""
    DROP TRIGGER IF EXISTS insert_realized_pnl_transactions
""")

insert_realized_pnl_transactions = DDL("""
    CREATE TRIGGER insert_realized_pnl_transactions
        AFTER INSERT
        ON realized_pnls FOR EACH ROW
    BEGIN
        DECLARE c_account INT;
        SET c_account = (SELECT acquire_t_account_by_group('realized_pnl', NEW.t_account_id));

        INSERT INTO transactions (
            debit_account_id, credit_account_id, amount,
            transacted_at, transactable_id, transactable_type
        )
        SELECT
            CASE
                WHEN NEW.amount >= 0.0 THEN NEW.t_account_id
                ELSE c_account
            END AS debit_account_id
            , CASE
                WHEN NEW.amount >= 0.0 THEN c_account
                ELSE NEW.t_account_id
            END AS credit_account_id
            , NEW.amount
            , NEW.granted_at
            , NEW.id
            , 'RealizedPnl'
        ;
    END
""")


drop_update_realized_pnl_transactions = DDL("""
    DROP TRIGGER IF EXISTS update_realized_pnl_transactions
""")

update_realized_pnl_transactions = DDL("""
    CREATE TRIGGER update_realized_pnl_transactions
        BEFORE UPDATE
        ON realized_pnls FOR EACH ROW
    BEGIN
        DECLARE c_account INT;
        SET c_account = (SELECT acquire_t_account_by_group('realized_pnl', NEW.t_account_id));

        UPDATE transactions
        SET
            debit_account_id = CASE
                WHEN NEW.amount >= 0.0 THEN NEW.t_account_id
                ELSE c_account
            END,
            credit_account_id = CASE
                WHEN NEW.amount >= 0.0 THEN c_account
                ELSE NEW.t_account_id
            END,
            amount = NEW.amount,
            transacted_at = NEW.granted_at
        WHERE
            transactable_id = OLD.id
            AND transactable_type = 'RealizedPnl'
        ;
    END
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_insert_realized_pnl_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    insert_realized_pnl_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    drop_update_realized_pnl_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    update_realized_pnl_transactions.execute_if(dialect='mysql')
)
