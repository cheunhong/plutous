from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
import ccxt.async_support as ccxt
import pandas as pd
import asyncio


class Exchange:
    def __init__(self, exchange: str, config: Dict[str, str]):
        self.api: ccxt.Exchange = getattr(ccxt, exchange)(config)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        await self.close()
    
    async def close(self):
        await self.api.close()

    @property
    def markets(self) -> Dict[str, Any]:
        return self.api.markets

    @property
    def currencies(self) -> Dict[str, Any]:
        return self.api.currencies

    def market(self, symbol: str) -> Dict[str, Any]:
        return self.api.market(symbol)

    def currency(self, symbol: str) -> Dict[str, Any]:
        return self.api.currency(symbol)

    async def load_markets(self) -> Dict[str, Any]:
        return await self.api.load_markets()

    async def fetch_ohlcv_asof(
        self, symbol: str, 
        timestamp: datetime,
    ) -> Dict[str, float]:
        since = int(timestamp.timestamp() * 1000)
        response = await self.api.fetch_ohlcv(symbol, '1m', since=since, limit=1)
        response = dict(zip(['date', 'open', 'high', 'low', 'close', 'volume'], response[0]))
        response['date'] = datetime.fromtimestamp(response['date'] / 1000)
        return response

    async def fetch_ohlcv(
        self, symbol: str, 
        timeframe: str, 
        since: datetime,
    ) -> List[Tuple[float]]:
        since_ms = int(since.timestamp() * 1000)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        test_fetch = await self.api.fetch_ohlcv(symbol, timeframe, since=None, limit=None)
        candle_limit = len(test_fetch)

        one_call = self.api.parse_timeframe(timeframe) * 1000 * candle_limit

        input_coroutines = [
            self.api.fetch_ohlcv(symbol, timeframe, since=since, limit=candle_limit) 
            for since in range(since_ms, now, one_call)
        ]

        results = await asyncio.gather(*input_coroutines, return_exceptions=True)

        data = []
        for result in results:
            data.extend(result)

        return data

    async def fetch_ohlcv_dataframe(
        self, symbol: str, 
        timeframe: str, 
        since: datetime,
    ) -> pd.DataFrame:
        data = await self.fetch_ohlcv(symbol, timeframe, since)
        data = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        data['date'] = pd.to_datetime(data['date'], unit='ms')
        data.set_index('date', inplace=True)
        return data

    async def get_top_of_book(self, symbol: str) -> List[float]:
        res = await self.api.fetch_order_book(symbol)
        top_bid = res["bids"][0][0]
        top_ask = res["asks"][0][0]
        return [top_bid, top_ask]

    async def fetch_current_price(self, symbol: str) -> float:
        latest_trade = await self.fetch_trades(symbol, limit=1)
        return latest_trade[0]['price']

    async def fetch_balance(
        self, params: Optional[Dict] = {},
    ) -> Dict[str, Any]:
        return await self.api.fetch_balance(params=params)

    async def fetch_ticker(
        self, symbol: str, 
        params: Optional[Dict] = {},
    ) -> Dict[str, Any]:
        return await self.api.fetch_ticker(symbol, params=params)

    async def fetch_trades(
        self, symbol: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
        params: Optional[Dict] = {},
    ) -> List[Dict[str, Any]]:
        if since:
            since = int(since.timestamp() * 1000)

        return await self.api.fetch_trades(
            symbol, since=since, limit=limit, params=params,
        )

    async def fetch_my_trades(
        self, symbol: Optional[str] = None, 
        since: Optional[datetime] = None,
        params: Optional[Dict] = {},
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if since:
            since = int(since.timestamp() * 1000)

        return await self.api.fetch_my_trades(
            symbol, since=since,
            limit=limit, params=params, 
        )

    async def fetch_funding_history(
        self, symbol: Optional[str] = None,
        since: Optional[datetime] = None,
        params: Optional[Dict] = {},
    ) -> List[Dict[str, Any]]:
        if since:
            since = int(since.timestamp() * 1000)

        return await self.api.fetch_funding_history(
            symbol, since=since, params=params,
        )

    async def fetch_orders(
        self, symbol: str,
        since: Optional[datetime] = None,
        params: Optional[Dict] = {},
    ) -> List[Dict[str, Any]]:
        if since:
            since = int(since.timestamp() * 1000)

        return await self.api.fetch_orders(
            symbol, since=since, params=params,
        )

    async def fetch_deposits(
        self, symbol: Optional[str] = None,
        since: Optional[datetime] = None,
        params: Optional[Dict] = {},
    ) -> List[Dict[str, Any]]:
        if since:
            since = int(since.timestamp() * 1000)

        return await self.api.fetch_deposits(
            symbol, since=since, params=params,
        )

    async def fetch_withdrawals(
        self, symbol: Optional[str] = None,
        since: Optional[datetime] = None,
        params: Optional[Dict] = {},
    ) -> List[Dict[str, Any]]:
        if since:
            since = int(since.timestamp() * 1000)

        return await self.api.fetch_withdrawals(
            symbol, since=since, params=params,
        )

    async def fetch_positions(
        self, params: Optional[Dict] = {},
    ) -> List[Dict[str, Any]]:
        positions = await self.api.fetch_positions(params=params)
        active_positions = [
            pos for pos in positions 
            if pos['maintenanceMargin'] > 0.0
        ]
        return active_positions

    async def fetch_funding_rate_history(
        self, symbol: Optional[str] = None,
        since: Optional[datetime] = None,
        params: Optional[Dict] = {},
    ) -> List[Dict[str, Any]]:
        if since:
            since = int(since.timestamp() * 1000)

        return await self.api.fetch_funding_rate_history(
            symbol, since=since, params=params,
        )