from enum import Enum


class AssetType(int, Enum):
    cash: int = 1
    stock: int = 2
    crypto: int = 3
    etf: int = 4
    fund: int = 5
    property: int = 6
    commodity: int = 7
    nft: int = 8
    stock_futures: int = 9
    stock_option: int = 10
    commodity_futures: int = 11
    commodity_option: int = 12
    crypto_futures: int = 13
    crypto_inverse_futures: int = 14
    crypto_option: int = 15
    crypto_perp: int = 16
    crypto_inverse_perp: int = 17
