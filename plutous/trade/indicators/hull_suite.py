from vectorbt.utils.figure import make_figure
import vectorbt as vbt
import numpy as np


def hull_suite(
    price, 
    mode='hma', 
    length=55, 
    length_mult=1.0, 
):
    WMA = vbt.IndicatorFactory.from_talib('WMA')
    EMA = vbt.IndicatorFactory.from_talib('EMA')

    def hma(_src, _length):
        a = WMA.run(_src, _length / 2).real.values
        b = WMA.run(_src, _length).real.values
        return WMA.run(
            2 * a - b, 
            round(np.sqrt(_length))
        ).real
        
    def ehma(_src, _length):
        a = EMA.run(_src, _length / 2).real.values
        b = EMA.run(_src, _length).real.values
        return EMA.run(
            2 * a - b, 
            round(np.sqrt(_length))
        ).real
        
    def thma(_src, _length):
        a = WMA.run(_src, _length / 3).real.values
        b = WMA.run(_src, _length / 2).real.values
        c = WMA.run(_src, _length).real.values
        return WMA.run(
            a * 3 - b - c,
            _length
        ).real
    
    MODE = {
        'hma': hma,
        'ehma': ehma,
        'thma': thma,
    }
    
    _hull = MODE[mode](price, int(length * length_mult))
    mhull = _hull
    shull = _hull.shift(2)
    
    return (mhull, shull)


HullSuite = vbt.IndicatorFactory(
    input_names=['price'],
    output_names=['mhull', 'shull'],
).from_apply_func(
    hull_suite, 
    kwargs_to_args=['mode','length', 'length_mult'], 
    mode='hma', length=55, length_mult=1.0,
)


class _HullSuite(HullSuite):
    def plot(self, fig=None, **layout_kwargs):
        if fig is None:
            fig = make_figure()
        fig.update_layout(**layout_kwargs)

        fig = self.mhull.vbt.plot(trace_kwargs=dict(name='MHull'), fig=fig)
        fig = self.shull.vbt.plot(trace_kwargs=dict(name='SHull'), fig=fig)

        return fig


setattr(HullSuite, '__doc__', _HullSuite.__doc__)
setattr(HullSuite, 'plot', _HullSuite.plot)