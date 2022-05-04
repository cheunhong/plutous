from ccxt.async_support import binance, binanceusdm, binancecoinm
from typing import Any, List, Dict, Optional, Union
from typing_extensions import Literal
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from .exchange import Exchange
import pandas as pd
import asyncio


ExchgArg = Literal['spot', 'usdm', 'coinm']
FuturesExchgArg = Literal['usdm', 'coinm']


class BinanceBase(Exchange):
    def __init__(self, exchange: ExchgArg, config: Dict[str, str]):
        super().__init__(exchange, config)
        self.api: Union[binance, binanceusdm, binancecoinm]

    async def fetch_my_trades(
        self, symbol: Optional[str] = None, 
        since: Optional[datetime] = None, 
        order_id: Optional[int] = None,
        from_id: Optional[int] = None, 
    ) -> List[Dict[str, Any]]:
        return await self._fetch_my_trades(symbol, since, order_id, from_id)

    async def _fetch_my_trades(
        self, symbol: str, 
        since: Optional[datetime] = None,
        order_id: Optional[int] = None,
        from_id: Optional[int] = None, 
        max_interval: Optional[timedelta] = None,
    ) -> List[Dict[str, Any]]:
        all_trades = []
        params = {}
        limit = 1000

        if order_id:
            params['orderId'] = order_id
            return await super().fetch_my_trades(
                symbol, limit=limit, params=params
            )
        if from_id:
            params['fromId'] = from_id
            trades = await super().fetch_my_trades(
                symbol, since=since, limit=limit, params=params,
            )
        if since:
            first_trade = await super().fetch_my_trades(
                symbol, limit=1, params={'fromId': 1},
            )
            if not first_trade:
                return []

            trades = []
            while not trades and since < datetime.now(timezone.utc):
                trades = await super().fetch_my_trades(
                    symbol, since=since, limit=limit,
                )
                if max_interval is None:
                    break
                since += max_interval

        all_trades.extend(trades)
        while trades:
            params['fromId'] = int(trades[-1]['id']) + 1
            trades = await super().fetch_my_trades(
                symbol, limit=limit, params=params,
            )
            all_trades.extend(trades)

        return all_trades


class BinanceFuturesBase(BinanceBase):
    def parse_income(
        self, income: Dict[str, Any], 
        market: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.api.parse_income(income, market)

    def parse_incomes(
        self, incomes: List[Dict[str, Any]], 
        market: Optional[Dict[str, Any]] = None,
        since: Optional[int] = None, 
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return self.api.parse_incomes(incomes, market, since, limit)
        
    async def fetch_asset_balance(self) -> Dict[str, Decimal]:
        assets = (await self.fetch_balance())['info']['assets']
        return {
            item['asset']: Decimal(item['walletBalance'])
            for item in assets 
            if float(item['walletBalance']) != 0.0
        }

    async def fetch_incomes(
        self, type: Optional[str] = None,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        return await self._fetch_incomes(
            'fapiPrivate_get_income',
            symbol=symbol, type=type, since=since,
        )

    async def fetch_commissions(
        self, symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]: 
        return await self.fetch_incomes('COMMISSION', symbol, since)

    async def fetch_funding_history(
        self, symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]: 
        return await self.fetch_incomes('FUNDING_FEE', symbol, since)

    async def _fetch_incomes(
        self, api: str,
        symbol: Optional[str] = None,
        type: Optional[str] = None,
        since: Optional[datetime] = None,
        max_interval: Optional[timedelta] = None,
    ) -> List[Dict[str, Any]]:
        limit = 1000
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        since_ms = int(since.timestamp() * 1000) if since else now
        diff = (
            int(max_interval.total_seconds() * 1000)
            if max_interval is not None
            else (now - since_ms + 1)
        )

        params = {'limit': limit}
        await self.load_markets()
        if symbol is not None:
            market = self.market(symbol)
            params['symbol'] = market['id']
        if type:
            params['incomeType'] = type

        async def fetch(since: Optional[int] = None) -> List[Dict[str, Any]]:
            all_incomes = []
            if since:
                params['startTime'] = since
                params['endTime'] = min(since + diff - 1, now)
            while True:
                incomes = await getattr(self.api, api)(params=params)
                all_incomes.extend(incomes)
                if len(incomes) != limit:
                    break
                params['startTime'] = int(incomes[-1]['time']) + 1

            return self.parse_incomes(all_incomes)

        if not since:
            return await fetch()

        results =  await asyncio.gather(*[
            fetch(since) for since in range(since_ms, now, diff)
        ])
        all_results = []
        for result in results:
            all_results.extend(result)
        return all_results
    

class BinanceSpot(BinanceBase):
    def __init__(self, config: Dict[str, str]):
        super().__init__('binance', config)

    async def fetch_asset_balance(self) -> Dict[str, Decimal]:
        balance = (await self.fetch_balance())['total']
        return {
            key: Decimal(str(val)) 
            for key, val in balance.items() 
            if val != 0.0
        }

    async def fetch_c2c_trades(
        self, since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        if not since: 
            return (
                await self.api.sapi_get_c2c_ordermatch_listuserorderhistory()
            )['data']

        since_ms = int(since.timestamp() * 1000)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        diff = int(timedelta(days=30).total_seconds() * 1000)

        trades =  await asyncio.gather(*[
            self.api.sapi_get_c2c_ordermatch_listuserorderhistory(
                params={
                    'startTimestamp': since,
                    'endTimestamp': since + diff - 1,
                }
            )
            for since in range(since_ms, now, diff)
        ])

        data = []
        for trade in trades:
            data.extend(trade['data'])
        
        return data

    async def fetch_convert_history(
        self, since: Optional[datetime] = (
            datetime.now(timezone.utc) - timedelta(days=30)
        )
    ) -> List[Dict[str, Any]]:
        since_ms = int(since.timestamp() * 1000)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        diff = int(timedelta(days=30).total_seconds() * 1000)

        trades =  await asyncio.gather(*[
            self.api.sapi_get_convert_tradeflow(
                params={
                    'startTime': since,
                    'endTime': since + diff - 1,
                }
            )
            for since in range(since_ms, now, diff)
        ])

        data = []
        for trade in trades:
            data.extend(trade['list'])
        
        return data


class BinanceUsdm(BinanceFuturesBase):
    def __init__(self, config: Dict[str, str]):
        super().__init__('binanceusdm', config)

    async def fetch_my_trades(
        self, symbol: Optional[str] = None, 
        since: Optional[datetime] = None, 
        order_id: Optional[int] = None,
        from_id: Optional[int] = None, 
    ) -> List[Dict[str, Any]]:
        return await self._fetch_my_trades(
            symbol, since, order_id, from_id, 
            max_interval=timedelta(days=7)
        )

    async def fetch_incomes(
        self, type: Optional[str] = None,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        return await self._fetch_incomes(
            'fapiPrivate_get_income',
            symbol=symbol, type=type, since=since,
        )


class BinanceCoinm(BinanceFuturesBase):
    def __init__(self, config: Dict[str, str]):
        super().__init__('binancecoinm', config)

    async def fetch_incomes(
        self, type: Optional[str] = None,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        return await self._fetch_incomes(
            'dapiPrivate_get_income',
            symbol=symbol, type=type, since=since,
            max_interval=timedelta(days=200),
        )


ExchangeDict = Dict[
    ExchgArg, Union[BinanceSpot, BinanceUsdm, BinanceCoinm]
]


class Binance:
    def __init__(
        self, config: Dict[str, str],
        exchange: Optional[ExchgArg] = None,
    ):
        self.exchanges: ExchangeDict = {
            'spot': BinanceSpot(config),
            'usdm': BinanceUsdm(config),
            'coinm': BinanceCoinm(config),
        }
        self.default_exchange = self.exchanges[exchange] if exchange else None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        await self.close()

    async def close(self):
        await asyncio.gather(*[
            exchange.close() for exchange 
            in self.exchanges.values()
        ])

    async def load_markets(
        self, exchange: Optional[ExchgArg] = None,
    ) -> Dict[str, Any]:
        if not exchange:
            exchange = 'spot'
            if self.default_exchange:
                exchange = self.default_exchange
        return await self.exchanges[exchange].load_markets()

    async def fetch_ticker(
        self, symbol: str,
        exchange: Optional[ExchgArg] = None, 
    ) -> Dict[str, Any]:
        if not exchange:
            exchange = 'spot'
            if self.default_exchange:
                exchange = self.default_exchange
        return await self.exchanges[exchange].fetch_ticker(symbol)

    async def fetch_trades(
        self, symbol: str,
        exchange: Optional[ExchgArg] = None, 
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not exchange:
            exchange = 'spot'
            if self.default_exchange:
                exchange = self.default_exchange
        return await self.exchanges[exchange].fetch_trades(symbol, since=since, limit=limit)

    async def fetch_current_price(
        self, symbol: str,
        exchange: Optional[ExchgArg] = None, 
    ) -> float:
        if not exchange:
            exchange = 'spot'
            if self.default_exchange:
                exchange = self.default_exchange
        return await self.exchanges[exchange].fetch_current_price(symbol)

    async def fetch_asset_balance(
        self, exchange: Optional[ExchgArg] = None,
    ) -> Dict[str, Decimal]:
        if not exchange:
            if not self.default_exchange:
                balances =  await asyncio.gather(*[
                    exchange.fetch_asset_balance()
                    for exchange in self.exchanges.values()
                ])
                return pd.DataFrame(balances).sum().to_dict()
            exchange = self.default_exchange
        return await self.exchanges[exchange].fetch_asset_balance()

    async def fetch_my_trades(
        self, symbol: str, 
        exchange: Optional[ExchgArg] = None, 
        since: Optional[datetime] = None,
        order_id: Optional[int] = None,
        from_id: Optional[int] = None, 
    ) -> List[Dict[str, Any]]:
        if not exchange:
            exchange = 'spot'
            if self.default_exchange:
                exchange = self.default_exchange
        return await self.exchanges[exchange].fetch_my_trades(
            symbol, since, order_id, from_id,
        )

    async def fetch_deposits(
        self, symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        return await self.exchanges['spot'].fetch_deposits(symbol, since=since)

    async def fetch_withdrawals(
        self, symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        return await self.exchanges['spot'].fetch_withdrawals(symbol, since=since)
    
    async def fetch_positions(
        self, exchange: Optional[FuturesExchgArg] = None,
    ) -> List[Dict[str, Any]]:
        if not exchange:
            if not self.default_exchange:
                usdm, coinm =  await asyncio.gather(
                    self.exchanges['usdm'].fetch_positions(),
                    self.exchanges['coinm'].fetch_positions(),
                )
                return usdm + coinm
            exchange = self.default_exchange
        return await self.exchanges[exchange].fetch_positions()

    async def fetch_commissions(
        self, symbol: Optional[str] = None,
        exchange: Optional[FuturesExchgArg] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]: 
        exchanges = [exchange or self.default_exchange]   
        if not exchange:
            if not self.default_exchange:
                exchanges = ['usdm', 'coinm']
        all_results = []
        results = await asyncio.gather(*[
            self.exchanges[exchange]
            .fetch_commissions(symbol, since=since)
            for exchange in exchanges
        ])
        for result in results:
            all_results.extend(result)
        return all_results

    async def fetch_funding_history(
        self, symbol: Optional[str] = None,
        exchange: Optional[FuturesExchgArg] = None, 
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        exchanges = [exchange or self.default_exchange]   
        if not exchange:
            if not self.default_exchange:
                exchanges = ['usdm', 'coinm']
        all_results = []
        results = await asyncio.gather(*[
            self.exchanges[exchange]
            .fetch_funding_history(symbol, since=since)
            for exchange in exchanges
        ])
        for result in results:
            all_results.extend(result)
        return all_results

    async def fetch_funding_rate_history(
        self, symbol: Optional[str] = None,
        exchange: Optional[FuturesExchgArg] = None, 
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        exchanges = [exchange or self.default_exchange]   
        if not exchange:
            if not self.default_exchange:
                exchanges = ['usdm', 'coinm']
        all_results = []
        results = await asyncio.gather(*[
            self.exchanges[exchange]
            .fetch_funding_rate_history(symbol, since=since)
            for exchange in exchanges
        ])
        for result in results:
            all_results.extend(result)
        return all_results

    async def fetch_orders(
        self, symbol: str,
        exchange: Optional[ExchgArg] = 'spot', 
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        return await self.exchanges[exchange].fetch_orders(symbol, since=since)

    async def fetch_convert_history(
        self, since: Optional[datetime] = (
            datetime.now(timezone.utc) - timedelta(days=30)
        )
    ) -> List[Dict[str, Any]]:
        return await self.exchanges['spot'].fetch_convert_history(since)

    async def fetch_c2c_trades(
        self, since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        return await self.exchanges['spot'].fetch_c2c_trades(since)