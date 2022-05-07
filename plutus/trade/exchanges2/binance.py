
from ccxt.async_support import binance, binanceusdm, binancecoinm
from ccxt.base.errors import NotSupported
from .utils import add_preprocess, paginate
from datetime import timedelta


@add_preprocess
class BinanceBase(binance):
    def describe(self):
        return self.deep_extend(super(BinanceBase, self).describe(), {
            'plutus_funcs': [
                'fetch_incomes',
                'fetch_commissions',
            ]
        })

    async def fetch_incomes(
        self, income_type=None, symbol=None, 
        since=None, limit=None, params={},
    ):
        request = {}
        if since is not None:
            request['startTime'] = since
        if limit is not None:
            request['limit'] = limit
        if income_type is not None:
            request['incomeType'] = income_type

        await self.load_markets()
        if symbol is not None:
            market = self.market(symbol)
            request['symbol'] = market['id']
        
        type = self.safe_string(self.options, 'defaultType', 'spot')
        if (type == 'future'):
            method = 'fapiPrivateGetIncome'
        elif (type == 'delivery'):
            method = 'dapiPrivateGetIncome'
        else:
            raise NotSupported(self.id + ' fetchIncomes() supports linear and inverse contracts only')
        response = getattr(self, method)(self.extend(request, params))
        return self.parse_incomes(response, market, since, limit)

    async def fetch_commissions(
        self, symbol= None, since=None, limit=None, params={},
    ): 
        return await self.fetch_incomes('COMMISSION', symbol, since, limit, params)

    async def fetch_funding_history(
        self, symbol=None, since=None, limit=None, params={},
    ):
        return await self.fetch_incomes('FUNDING_FEE', symbol, since, limit, params)


class Binance(BinanceBase):
    @paginate(
        max_limit=1000,
        max_interval=timedelta(days=1),
    )
    async def fetch_my_trades(
        self, symbol=None, since=None, 
        limit=None, params={}, **kwargs,
    ):
        return await super().fetch_my_trades(
            symbol, since, limit, params, **kwargs,
        )


class BinanceUsdm(BinanceBase, binanceusdm):
    @paginate(
        max_limit=1000,
        max_interval=timedelta(days=7),
    )
    async def fetch_my_trades(
        self, symbol=None, since=None, 
        limit=None, params={}, **kwargs,
    ):
        return await super().fetch_my_trades(
            symbol, since, limit, params, **kwargs
        )

    @paginate(max_limit=1000)
    async def fetch_incomes(
        self, income_type=None, symbol=None, 
        since=None, limit=None, **params
    ):
        return await super().fetch_incomes(
            income_type, symbol, since, limit, **params
        )


class BinanceCoinm(BinanceBase, binancecoinm):
    @paginate(max_limit=1000)
    async def fetch_my_trades(
        self, symbol=None, since=None, limit=None, **params
    ):
        return await super().fetch_my_trades(symbol, since, limit, params)

    @paginate(
        max_limit=1000,
        max_interval=timedelta(days=200),
    )
    async def fetch_incomes(
        self, income_type=None, symbol=None, 
        since=None, limit=None, **params
    ):
        return await super().fetch_incomes(
            income_type, symbol, since, limit, **params
        )