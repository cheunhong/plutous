import pandas as pd


class EMVWAP:
    def __init__(self, anchor='day', avg_length=0):
        self.anchor = anchor
        self.avg_length = avg_length