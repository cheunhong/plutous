import pandas as pd


class HighLow:
    def __init__(self, lookback=4, high='high', low='low'):
        self.lookback = lookback
        self.high = high
        self.low = low

    def apply(self, bars):
        bars = bars.copy()
        bars['highest'] = bars[self.high].rolling(window=self.lookback).max()
        bars['lowest'] = bars[self.low].rolling(window=self.lookback).min()

        return pd.DataFrame(
            index=bars.index,
            data={
                'highest': bars['highest'],
                'lowest': bars['lowest'],
            }
        )