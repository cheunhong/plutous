from plutous.models.enums import AssetType


TIMEZONE = 'UTC'
ENV_VAR_PREFIX = 'PLUTOUS'
STABLECOINS = ['USDT', 'BUSD', 'USDC']
POSITION_BASE_CURRENCY = {
    AssetType.crypto: 'USDT'
}
POSITION_CASH_EQUIVALENTS = {
    AssetType.crypto: STABLECOINS
}

DEFAULT_CONFIG = {
    'timezone': TIMEZONE,
    'db': {
        'host': 'localhost',
        'port': 3306,
        'username': 'root',
        'password': 'root',
        'database': 'plutous',
    },
    'position': {
        'base_currency': POSITION_BASE_CURRENCY,
        'cash_equivalents': POSITION_CASH_EQUIVALENTS,
    },
}