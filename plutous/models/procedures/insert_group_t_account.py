from sqlalchemy import DDL, event
from sqlmodel import SQLModel


drop_insert_t_account_by_group = DDL("""
    DROP PROCEDURE IF EXISTS insert_t_account_by_group
""")

insert_t_account_by_group = DDL("""
    CREATE PROCEDURE insert_t_account_by_group (
        IN g VARCHAR(20),
        IN t_account INT,
        OUT result_id INT
    )
        BEGIN
            IF g IN (
                'currency_exchange',
                'realized_pnl',
                'commission',
                'capital',
                'deposit'
            ) THEN
                INSERT INTO t_accounts (
                    name, type, currency, group_id
                )
                SELECT
                    CONCAT(
                        CASE g
                            WHEN 'currency_exchange' THEN 'Currency Exchange'
                            WHEN 'realized_pnl' THEN 'Realized Pnl'
                            WHEN 'commission' THEN 'Commission'
                            WHEN 'capital' THEN 'Capital'
                            WHEN 'deposit' THEN 'Deposit'
                        END,
                        ' (', ta.currency, ')'
                    )
                    , CASE g
                        WHEN 'currency_exchange' THEN 'income'
                        WHEN 'realized_pnl' THEN 'income'
                        WHEN 'commission' THEN 'expense'
                        WHEN 'capital' THEN 'equity'
                        WHEN 'deposit' THEN 'income'
                      END
                    , ta.currency
                    , (SELECT id FROM groups WHERE name = g)
                FROM t_accounts AS ta
                WHERE ta.id = t_account
                ON DUPLICATE KEY UPDATE t_accounts.name = t_accounts.name
                ;

                SET result_id = LAST_INSERT_ID();
            END IF;
        END
""")


event.listen(
    SQLModel.metadata,
    'after_create',
    drop_insert_t_account_by_group.execute_if(dialect='mysql')
)

event.listen(
    SQLModel.metadata,
    'after_create',
    insert_t_account_by_group.execute_if(dialect='mysql')
)
