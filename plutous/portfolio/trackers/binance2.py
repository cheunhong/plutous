from plutous.trade.exchanges2 import Binance, BinanceUsdm, BinanceCoinm
from plutous.models.enums import Action, AssetType
from plutous.models import Trade, FundingFee
from plutous.utils import condecimal
from plutous.config import config
from plutous import database as db
from typing_extensions import Literal
from typing import Any, Dict, List
from datetime import timedelta
from decimal import Decimal
from .base import BaseTracker
import pandas as pd
import numpy as np
import itertools
import asyncio


TIMEZONE = config['timezone']
BASE_CURRENCY = config['position']['base_currency'][AssetType.crypto]
CASH_EQUIVALENTS = config['position']['cash_equivalents'][AssetType.crypto]
CONFIG = {
    'spot': {
        'exchange': Binance,
        'asset_type': AssetType.crypto, 
    },
    'future': {
        'exchange': BinanceUsdm,
        'asset_type': {
            'perp': AssetType.crypto_perp,
            'expiring': AssetType.crypto_futures,
        }
    },
    'delivery': {
        'exchange': BinanceCoinm,
        'asset_type': {
            'perp': AssetType.crypto_inverse_perp,
            'expiring': AssetType.crypto_inverse_futures,
        }
    }
}
Type = Literal['spot', 'future', 'delivery']


class BinanceTracker(BaseTracker):
    "Binance Tracker"

    def __init__(
        self, config: Dict[str, str], 
        account_id: int, type: Type,
    ):
        super().__init__(account_id)
        exchg_config = CONFIG[type]
        self.exchange: Binance = exchg_config['exchange'](config)
        self.asset_type = exchg_config['asset_type']

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        await self.close()

    async def close(self):
        self.conn.close()
        self.session.close()
        db.engine.dispose()
        await self.exchange.close()

    async def get_current_spot_balance(self) -> Dict[str, Decimal]:
        to_extract = ['spot', 'future', 'delivery']
        results = await asyncio.gather(*[
            self.exchange.fetch_wallet_balance({'type': type_})
            for type_ in to_extract
        ])
        self.current_spot_balance = (
            pd.DataFrame(results)
            .applymap(condecimal)
            .sum().to_dict()
        )
        return self.current_spot_balance

    def get_spot_balance(self) -> Dict[str, float]:
        positions = self.get_positions_df(asset_type=AssetType.crypto)
        self.spot_balance = positions.set_index('code')['size'].to_dict()
        return self.spot_balance

    async def get_spot_balance_discrepancy(self) -> pd.Series:
        current_balance = await self.get_current_spot_balance()
        balance = self.get_spot_balance()
        joint = pd.DataFrame([current_balance, balance]).T.applymap(condecimal)
        discrepancy = joint[0] - joint[1]
        self.spot_balance_discrepancy = discrepancy[discrepancy != 0]
        return self.spot_balance_discrepancy

    async def fetch_new_spot_trades(self) -> List[Dict[str, Any]]:
        market = await self.exchange.load_markets()
        discrepancy = await self.get_spot_balance_discrepancy()
        discrepancy = list(discrepancy.index)
        
        if not len(discrepancy):
            return []

        since = self.get_last_transacted_at(AssetType.crypto)
        _trades = await asyncio.gather(*[
            self.exchange.fetch_my_trades(f'{a}/{b}', since=since)
            for a, b in itertools.permutations(discrepancy, 2)
            if f'{a}/{b}' in market
        ])

        if not _trades:
            return []

        trades = []
        for trade in _trades:
            trades.extend(trade)
        return trades

    async def fetch_new_convert_history(self) -> List[Dict[str, Any]]:
        since = self.get_last_transacted_at(AssetType.crypto)
        return await self.exchange.fetch_convert_history(since=since)