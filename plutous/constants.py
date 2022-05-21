from .models.enums import AssetType


TIMEZONE = 'UTC'
ENV_VAR_PREFIX = 'PLUTOUS'
STABLECOINS = ['USDT', 'BUSD', 'USDC']
POSITION_BASE_CURRENCY = {
    AssetType.crypto: 'USDT'
}
POSITION_CASH_EQUIVALENTS = {
    AssetType.crypto: STABLECOINS
}