import pandas as pd


class HeikinAshi:
    def apply(self, bars):
        bars = bars.copy()
        bars['ha_close'] = (
            bars['open'] + bars['high']
            + bars['low'] + bars['close']
        ) / 4

        # ha open
        bars.at[bars.index[0], 'ha_open'] = (bars.at[bars.index[0], 'open'] + bars.at[bars.index[0], 'close']) / 2
        for i in bars.index[1:]:
            bars.at[i, 'ha_open'] = (bars.at[i - 1, 'ha_open'] + bars.at[i - 1, 'ha_close']) / 2

        bars['ha_high'] = bars.loc[:, ['high', 'ha_open', 'ha_close']].max(axis=1)
        bars['ha_low'] = bars.loc[:, ['low', 'ha_open', 'ha_close']].min(axis=1)

        return pd.DataFrame(
            index=bars.index,
            data={
                'ha_open': bars['ha_open'],
                'ha_high': bars['ha_high'],
                'ha_low': bars['ha_low'],
                'ha_close': bars['ha_close'],
            }
        )