
from plutus.trade.exchanges.binance import (
    Binance, ExchgArg, FuturesExchgArg
)
from plutus.models.enums import Action, AssetType
from plutus.models import Trade, FundingFee
from plutus.config import config
from plutus.utils import condecimal
from plutus import database as db
from typing import Any, Dict, List
from datetime import timedelta
from .base import BaseTracker
import pandas as pd
import numpy as np
import itertools
import asyncio


TIMEZONE = config['timezone']
BASE_CURRENCY = config['position']['base_currency'][AssetType.crypto]
CASH_EQUIVALENTS = config['position']['cash_equivalents'][AssetType.crypto]


class BinanceTracker(BaseTracker):
    "Binance Tracker"

    def __init__(self, config: Dict[str, str], account_id: int):
        super().__init__(account_id)
        self.binance = Binance(config)
        self.asset_types = {
            'spot': AssetType.crypto,
            'usdm': AssetType.crypto_perp,
            'coinm': AssetType.crypto_inverse_perp
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        await self.close()

    async def close(self):
        self.conn.close()
        self.session.close()
        db.engine.dispose()
        await self.binance.close()

    async def get_current_spot_balance(self) -> Dict[str, float]:
        self.current_spot_balance = await self.binance.fetch_asset_balance()
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
        market = await self.binance.load_markets('spot')
        discrepancy = await self.get_spot_balance_discrepancy()
        discrepancy = list(discrepancy.index)
        
        if not len(discrepancy):
            return []

        since = self.get_last_transacted_at(AssetType.crypto)
        _trades = await asyncio.gather(*[
            self.binance.fetch_my_trades(f'{a}/{b}', since=since)
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
        return await self.binance.fetch_convert_history(since=since)

    async def fetch_new_futures_trades(
        self, exchange: FuturesExchgArg,
    ) -> List[Dict[str, Any]]:
        asset_type = self.asset_types[exchange]
        last_transacted = self.get_last_transacted_at(asset_type)
        comms = await self.binance.fetch_commissions(
            exchange=exchange, since=last_transacted
        )
        if not comms:
            return []

        comms = pd.DataFrame(comms)
        comms_info = comms['info'].apply(pd.Series)
        ids = comms_info.groupby('symbol')['info'].min().to_dict()
        all_trades = await asyncio.gather(*[
            self.binance.fetch_my_trades(
                symbol, exchange, from_id=from_id
            ) for symbol, from_id in ids.items()
        ])

        if not all_trades:
            return []

        trades = []
        for trade in all_trades:
            trades.extend(trade)
        return trades

    async def fetch_new_funding_fees(
        self, exchange: FuturesExchgArg,
    ) -> pd.DataFrame:
        asset_type = self.asset_types[exchange]
        funding_fee = self.account.get_latest_funding_history(asset_type)
        last_charged_at = (
            funding_fee.charged_at if funding_fee 
            else self.account.init_balance_at
        )
        last_charged_at = (
            pd.Timestamp(last_charged_at)
            .tz_localize(TIMEZONE)
            .tz_convert('UTC')
        ) + timedelta(minutes=10)

        funding_history = await self.binance.fetch_funding_history(
            exchange=exchange, since=last_charged_at
        )
        if not funding_history:
            return pd.DataFrame()
        funding_history = pd.DataFrame(funding_history)
        funding_history['datetime'] = (
            pd.to_datetime(funding_history['datetime']).dt.round('1h')
        )

        since_dict = funding_history.groupby(['symbol'])['datetime'].min().to_dict()
        funding_rate_histories = await asyncio.gather(*[
            self.binance.fetch_funding_rate_history(
                symbol, exchange=exchange, since=since
            ) for symbol, since in since_dict.items()
        ])
        funding_rate_history = []
        for frh in funding_rate_histories:
            funding_rate_history.extend(frh)

        funding_rate_history = pd.DataFrame(funding_rate_history)[
            ['symbol', 'datetime', 'fundingRate']
        ]
        funding_rate_history['datetime'] = (
            pd.to_datetime(funding_rate_history['datetime']).dt.round('1h')
        )
        funding_history = funding_history.merge(
            funding_rate_history, how='left',
            on=['symbol', 'datetime'],
        )
        funding_history['account'] = [self.account] * len(funding_history)
        funding_history['amount'] = -1 * funding_history['amount']
        funding_history['asset_type'] = asset_type
        funding_history.rename(columns={
            'fundingRate': 'funding_rate',
            'datetime': 'charged_at',
            'id': 'reference_id',
            'code': 'currency',
            'symbol': 'code',
        }, inplace=True)
        funding_history['charged_at'] = (
            funding_history['charged_at']
            .dt.tz_convert(TIMEZONE)
            .astype(str)
        )
        fields = (
            list(FundingFee.__fields__.keys()) +
            list(FundingFee.__sqlmodel_relationships__.keys())
        )
        return funding_history[funding_history.columns.intersection(fields)]

    async def init_spot_balance(self):
        if self.account.init_balance_at:
            return 'Balance already initiated'

        balance = await self.get_current_spot_balance()
        init_balance_at = str(
            pd.Timestamp
            .now(tz=TIMEZONE)
            .to_pydatetime()
            .strftime('%Y-%m-%d %H:%M:%S.%f')
        )
        async def fetch_prices(code):
            if code == BASE_CURRENCY:
                return 1.0
            return await (
                self.binance.fetch_current_price(
                    f'{code}/{BASE_CURRENCY}'
                )
            )
        prices = await asyncio.gather(*[
            fetch_prices(code) for code in balance 
        ])

        trades = pd.DataFrame(
            [self.current_spot_balance], index=['size'],
        ).T
        trades['code'] = trades.index
        trades['transacted_at'] = init_balance_at
        trades['currency'] = BASE_CURRENCY
        trades['price'] = prices
        trades['price'] = trades['price'].apply(condecimal)
        trades['asset_type'] = AssetType.crypto
        trades['action'] = Action.buy
        trades['account'] = len(self.account) * len(trades)
        trades['amount'] = (trades['price'] * trades['size']).apply(round, ndigits=8)

        for trade in trades.to_dict('records'):
            t_account = self.account.acquire_t_account(
                currency=trade['code'], 
                asset_type=AssetType.crypto
            )
            transaction = t_account.open_balance(
                amount=trade['size'], 
                transacted_at=trade['transacted_at'],
            )
            position = t_account.acquire_position()
            position.increase(
                price=trade['price'],
                size=trade['size'],
                transacted_at=trade['transacted_at'],
                transaction_id=transaction.id,
            )

        self.account.init_balance_at = init_balance_at
        self.account.add(self.session)
        self.session.commit()

    async def record_spot_trades(self):
        spot_trades, convert_history = await asyncio.gather(
            self.fetch_new_spot_trades(), self.fetch_new_convert_history(),
        )
        spot_trades = self.process_my_trades('spot', spot_trades)
        convert_history = await self.process_convert_history(convert_history)

        all_trades: pd.DataFrame = pd.concat([spot_trades, convert_history])
        if all_trades.empty:
            return 

        all_trades.sort_values('transacted_at', inplace=True)
        all_trades.replace({np.nan: None}, inplace=True)

        for params in all_trades.to_dict('records'):
            Trade(**params).add(self.session)
        self.session.commit()

    async def record_futures_trades(self):
        async def process(exchange: FuturesExchgArg) -> pd.DataFrame:
            trades = await self.fetch_new_futures_trades(exchange)
            return self.process_my_trades(exchange, trades)

        usdm_trades, coinm_trades = await asyncio.gather(
            process('usdm'), process('coinm'),
        )

        all_trades = pd.concat([usdm_trades, coinm_trades])
        if all_trades.empty:
            return 
        all_trades.sort_values('transacted_at', inplace=True)
        all_trades.replace({np.nan: None}, inplace=True)

        for params in all_trades.to_dict('records'):
            Trade(**params).add(self.session)
        self.session.commit()

    async def record_funding_history(self):
        usdm, coinm = await asyncio.gather(
            self.fetch_new_funding_fees('usdm'), 
            self.fetch_new_funding_fees('coinm'),
        )

        all_funding_fees = pd.concat([usdm, coinm])
        if all_funding_fees.empty:
            return 

        all_funding_fees.sort_values('charged_at', inplace=True)
        all_funding_fees.replace({np.nan: None}, inplace=True)

        for params in all_funding_fees.to_dict('records'):
            FundingFee(**params).add(self.session)
        self.session.commit()

    def process_my_trades(
        self, exchange: ExchgArg,
        my_trades: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        if not my_trades:
            return pd.DataFrame()

        trades = pd.DataFrame(my_trades)
        trades_info = trades['info'].apply(pd.Series)
        trades_info.columns = [f'{col}_info' for col in trades_info.columns]
        trades = pd.concat([trades, trades_info], axis=1)
        trades['currency'] = trades['symbol'].apply(lambda x: x.split('/')[1])
        trades['code'] = trades['symbol'].apply(lambda x: x.split('/')[0])
        trades['transacted_at'] = (
            pd.to_datetime(trades['datetime'])
            .dt.tz_convert(TIMEZONE)
            .astype(str)
        )
        trades['account'] = [self.account] * len(trades)
        trades['asset_type'] = self.asset_types[exchange]
        trades['reference_id'] = trades['id']
        trades['source'] = 'my_trades'
        trades['exchange'] = exchange
        trades.rename(
            columns={
                'commissionAsset_info': 'comms_currency',
                'commission_info': 'comms',
                'qty_info': 'size',
                'order': 'orderId',
            },
            inplace=True,
        )
        trades["details"] = trades[[
            'takerOrMaker', 'orderId', 'id',
            'source', 'exchange', 'symbol',
        ]].to_dict("records")

        if exchange in FuturesExchgArg.__args__:
            long_cond = (
                (trades['positionSide_info'] == 'LONG') & 
                (trades['side_info'] == 'BUY')
            )
            short_cond = (
                (trades['positionSide_info'] == 'SHORT') & 
                (trades['side_info'] == 'SELL')
            )
            act = pd.Series(np.where(long_cond | short_cond, 'open', 'close'))
            side = trades['positionSide_info'].str.lower()
            action = act.str.cat(side, sep='_')
            trades['action'] = action.apply(lambda x: getattr(Action, x))
            trades['margin_currency'] = trades['marginAsset_info']
            trades['pnl_currency'] = trades['marginAsset_info']
            trades['pnl'] = trades['realizedPnl_info']
            if exchange == 'coinm':
                trades['size'] = trades['cost']
        elif exchange == 'spot':
            trades['action'] = trades['side'].apply(lambda x: getattr(Action, x))

        trades.drop('id', axis=1, inplace=True)
        trades.sort_values('transacted_at', inplace=True)
        fields = (
            list(Trade.__fields__.keys()) +
            list(Trade.__sqlmodel_relationships__.keys())
        )
        return trades[trades.columns.intersection(fields)]

    async def process_convert_history(self, convert_history: List[Dict[str, Any]]) -> pd.DataFrame:
        if not convert_history:
            return pd.DataFrame()

        trades = pd.DataFrame(convert_history)
        trades = trades[trades['orderStatus'] == 'SUCCESS']

        if trades.empty:
            return pd.DataFrame()

        market = await self.binance.load_markets('spot')
        def get_inverse(d):
            if f"{d['toAsset']}/{d['fromAsset']}" not in market:
                return True
        
        trades['inverse'] = trades[['fromAsset', 'toAsset']].apply(get_inverse, axis=1)
        trades['code'] = np.where(trades.inverse, trades['fromAsset'], trades['toAsset'])
        trades['currency'] = np.where(trades.inverse, trades['toAsset'], trades['fromAsset'])
        trades['size'] = np.where(trades.inverse, trades['fromAmount'], trades['toAmount'])
        trades['price'] = np.where(trades.inverse, trades['ratio'], trades['inverseRatio'])
        trades['action'] = np.where(trades['code'] == trades['toAsset'], Action.buy, Action.sell)
        trades['transacted_at'] = (
            pd.to_datetime(trades['createTime'],  unit='ms', utc=True)
            .dt.tz_convert(TIMEZONE)
            .astype(str)
        )
        trades['reference_id'] = trades['orderId']
        trades['asset_type'] = AssetType.crypto
        trades['account'] = [self.account] * len(trades)
        trades['source'] = 'convert_history'
        trades["details"] = trades[
            ['quoteId', 'orderId', 'source']
        ].to_dict("records")
        trades.sort_values('transacted_at', inplace=True)
        fields = (
            list(Trade.__fields__.keys()) +
            list(Trade.__sqlmodel_relationships__.keys())
        )
        return trades[trades.columns.intersection(fields)]

    async def update_spot_positions(self):
        async def fetch_prices(code, currency):
            if code == BASE_CURRENCY:
                return 1.0
            return await (
                self.binance.fetch_current_price(
                    f'{code}/{currency}'
                )
            )

        positions = self.get_positions(asset_type=AssetType.crypto)
        latest_prices = await asyncio.gather(*[
            fetch_prices(position.code, position.currency)
            for position in positions 
        ])

        for position, price in zip(positions, latest_prices):
            position.price = condecimal(price)
            position.unrealized_pnl = round(
                (position.price - position.entry_price) * position.size, 8
            )
        self.session.add_all(positions)
        self.session.commit()