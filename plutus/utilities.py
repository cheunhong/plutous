from decimal import Decimal
import pandas as pd


def condecimal(amount):
    if isinstance(amount, Decimal):
        return amount
    if pd.isna(amount):
        amount = 0.0
    return Decimal(str(amount))

    
def deep_merge_dicts(
    source: dict, destination: dict, 
    allow_null_overrides: bool = True
) -> dict:
    """
    Values from Source override destination, destination is returned (and modified!!)
    Sample:
    >>> a = { 'first' : { 'rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            deep_merge_dicts(value, node, allow_null_overrides)
        elif value is not None or allow_null_overrides:
            destination[key] = value

    return destination