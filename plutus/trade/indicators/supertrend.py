import pandas as pd


class SuperTrend:
    def __init__(self, atr_period, atr_multiplier):
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier