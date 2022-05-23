from typing import Dict, Any
from decimal import Decimal
import pandas as pd
import logging


logger = logging.getLogger(__name__)


def condecimal(amount):
    if isinstance(amount, Decimal):
        return amount
    if pd.isna(amount):
        amount = 0.0
    return Decimal(str(amount))


def get_var_typed(val):
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            if val.lower() in ('t', 'true'):
                return True
            elif val.lower() in ('f', 'false'):
                return False
    # keep as string
    return val


def flat_vars_to_nested_dict(
    env_dict: Dict[str, Any], prefix: str
) -> Dict[str, Any]:
    """
    Environment variables must be prefixed with PLUTOUS.
    PLUTOUS__{section}__{key}
    :param env_dict: Dictionary to validate - usually os.environ
    :param prefix: Prefix to consider (usually PLUTOUS__)
    :return: Nested dict based on available and relevant variables.
    """
    relevant_vars: Dict[str, Any] = {}

    for env_var, val in sorted(env_dict.items()):
        if env_var.startswith(prefix):
            logger.info(f"Loading variable '{env_var}'")
            key = env_var.replace(prefix, '')
            for k in reversed(key.split('__')):
                val = {
                    k.lower(): get_var_typed(val)
                    if type(val) != dict else val
                }
            relevant_vars = deep_merge_dicts(val, relevant_vars)
    return relevant_vars


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