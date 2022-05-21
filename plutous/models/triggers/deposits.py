from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_insert_deposit_transactions = DDL("""
    DROP TRIGGER IF EXISTS insert_deposit_transactions
""")

insert_deposit_transactions = DDL("""
    CREATE TRIGGER insert_deposit_transactions
        AFTER INSERT
        ON deposits FOR EACH ROW
    BEGIN
        DECLARE debit_user INT;
        DECLARE credit_user INT;
        DECLARE deposit INT;

        SET debit_user = (
            SELECT a.user_id
            FROM t_accounts as ta
            JOIN accounts as a
                ON a.id = ta.account_id
            WHERE ta.id = NEW.debit_account_id
        );
        SET credit_user = (
            SELECT a.user_id
            FROM t_accounts as ta
            JOIN accounts as a
                ON a.id = ta.account_id
            WHERE ta.id = NEW.credit_account_id
        );


        IF debit_user = credit_user  THEN
            INSERT INTO transactions (
                debit_account_id, credit_account_id, amount,
                transacted_at, transactable_id, transactable_type
            )
            VALUES (
                NEW.debit_account_id, NEW.credit_account_id,
                NEW.amount, NEW.transacted_at, NEW.id, 'Deposit'
            );
        ELSE
            SET deposit = (
                SELECT acquire_t_account_by_group(
                    'deposit', COALESCE(NEW.debit_account_id, NEW.credit_account_id)
                )
            );

            IF NEW.debit_account_id IS NOT NULL THEN
                INSERT INTO transactions (
                    debit_account_id, credit_account_id, amount,
                    transacted_at, transactable_id, transactable_type
                )
                VALUES (
                    NEW.debit_account_id , deposit, NEW.amount,
                    NEW.transacted_at , NEW.id, 'Deposit'
                );
            END IF;
            IF NEW.credit_account_id IS NOT NULL THEN
                INSERT INTO transactions (
                    debit_account_id, credit_account_id, amount,
                    transacted_at, transactable_id, transactable_type
                )
                VALUES (
                    deposit, NEW.credit_account_id, NEW.amount,
                    NEW.transacted_at, NEW.id , 'Deposit'
                );
            END IF;
        END IF;
    END
""")


drop_update_deposit_transactions = DDL("""
    DROP TRIGGER IF EXISTS update_deposit_transactions
""")

update_deposit_transactions = DDL("""
    CREATE TRIGGER update_deposit_transactions
        BEFORE UPDATE
        ON deposits FOR EACH ROW
    BEGIN
        DECLARE debit_user INT;
        DECLARE credit_user INT;
        DECLARE deposit INT;

        SET debit_user = (
            SELECT a.user_id
            FROM t_accounts as ta
            JOIN accounts as a
                ON a.id = ta.account_id
            WHERE ta.id = NEW.debit_account_id
        );
        SET credit_user = (
            SELECT a.user_id
            FROM t_accounts as ta
            JOIN accounts as a
                ON a.id = ta.account_id
            WHERE ta.id = NEW.credit_account_id
        );
        SET deposit = (
            SELECT acquire_t_account_by_group(
                'deposit', COALESCE(NEW.debit_account_id, NEW.credit_account_id)
            )
        );

        UPDATE transactions
            SET debit_account_id = CASE
                    WHEN (
                        debit_account_id = OLD.debit_account_id
                        OR (OLD.debit_account_id IS NULL AND debit_user = credit_user)
                    ) THEN COALESCE(NEW.debit_account_id, deposit)
                    ELSE debit_account_id
                END,
                credit_account_id = CASE
                    WHEN (
                        credit_account_id = OLD.credit_account_id
                        OR (OLD.credit_account_id IS NULL AND debit_user = credit_user)
                    ) THEN COALESCE(NEW.credit_account_id, deposit)
                    ELSE credit_account_id
                END,
                transacted_at = NEW.transacted_at,
                amount = NEW.amount
        WHERE transactable_id = OLD.id
            AND transactable_type = 'Deposit'
        ;

        IF debit_user != credit_user THEN
            IF OLD.debit_account_id IS NULL AND NEW.debit_account_id IS NOT NULL THEN
                INSERT INTO transactions (
                    debit_account_id, credit_account_id, amount,
                    transacted_at, transactable_id, transactable_type
                )
                VALUES (
                    NEW.debit_account_id , deposit, NEW.amount,
                    NEW.transacted_at , NEW.id, 'Deposit'
                );
            END IF;
            IF OLD.credit_account_id IS NULL AND NEW.credit_account_id IS NOT NULL THEN
                INSERT INTO transactions (
                    debit_account_id, credit_account_id, amount,
                    transacted_at, transactable_id, transactable_type
                )
                VALUES (
                    deposit, NEW.credit_account_id, NEW.amount,
                    NEW.transacted_at, NEW.id , 'Deposit'
                );
            END IF;
        END IF;
    END
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_insert_deposit_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    insert_deposit_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    drop_update_deposit_transactions.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    update_deposit_transactions.execute_if(dialect='mysql')
)
