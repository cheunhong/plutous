import ccxt.async_support as ccxt


class CoinMarketCap(ccxt.Exchange):
    def describe(self):
        return self.deep_extend(super(CoinMarketCap, self).describe(), {
            'id': 'coinmarketcap',
            'name': 'CoinMarketCap',
            'countries': ['US'],
            'urls': {
                'api': {
                    'v1': 'https://pro-api.coinmarketcap.com/v1',
                    'v2': 'https://pro-api.coinmarketcap.com/v2',
                }
            },
            'api': {
                # the API structure below will need 3-layer apidefs
                'v1': {
                    'get': {
                        'cryptocurrency/map': 1,
                        'cryptocurrency/info': 1,
                        'cryptocurrency/listings/latest': 1,
                        'cryptocurrency/listings/historical': 1,
                        'cryptocurrency/quotes/latest': 1,
                        'cryptocurrency/quotes/historical': 1,
                        'cryptocurrency/market-pairs/latest': 1,
                        'cryptocurrency/ohlcv/latest': 1,
                        'cryptocurrency/ohlcv/historical': 1,
                        'cryptocurrency/price-performance-stats/latest': 1,
                        'cryptocurrency/categories': 1,
                        'cryptocurrency/category': 1,
                        'cryptocurrency/airdrops': 1,
                        'cryptocurrency/airdrop': 1,
                        'cryptocurrency/trending/latest': 1,
                        'cryptocurrency/trending/most-visited': 1,
                        'cryptocurrency/trending/gainers-losers': 1,
                        'fiat/map': 1,
                        'exchange/map': 1,
                        'exchange/info': 1,
                        'exchange/listings/latest': 1,
                        'exchange/quotes/latest': 1,
                        'exchange/quotes/historical': 1,
                        'exchange/market-pairs/latest': 1,
                        'global-metrics/quotes/latest': 1,
                        'global-metrics/quotes/historical': 1,
                        'blockchain/statistics/latest': 1,
                        'key/info': 1,
                        
                    }
                },
                'v2': {
                    'get': {
                        'tools/price-conversion': 1,
                    }
                }
            }
        })
    
    def sign(self, path, api='v1', method='GET', params={}, headers=None, body=None):
        # self.check_required_credentials()
        url = self.urls['api'][api]
        url += '/' + path
        if params:
            url += '?' + self.urlencode(params)
        headers = {
          'Accepts': 'application/json',
          'X-CMC_PRO_API_KEY': self.apiKey,
        }
        return {'url': url, 'method': method, 'body': body, 'headers': headers}