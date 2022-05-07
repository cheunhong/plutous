from typing import Dict, Any
from .utils import deep_merge_dicts
from .constants import (
    POSITION_CASH_EQUIVALENTS,
    POSITION_BASE_CURRENCY,
    ENV_VAR_PREFIX,
    TIMEZONE,
)
import logging
import json
import os


logger = logging.getLogger(__name__)


DEFAULT_CONFIG = {
    'timezone': TIMEZONE,
    'db': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'database': 'plutus',
    },
    'position': {
        'base_currency': POSITION_BASE_CURRENCY,
        'cash_equivalents': POSITION_CASH_EQUIVALENTS,
    },
}

try:
    with open('plutus.json', 'r') as fopen:
        override_config = json.loads(fopen.read())
except FileNotFoundError:
    override_config = {}
    
config = deep_merge_dicts(override_config, DEFAULT_CONFIG)


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
    Environment variables must be prefixed with PLUTUS.
    PLUTUS__{section}__{key}
    :param env_dict: Dictionary to validate - usually os.environ
    :param prefix: Prefix to consider (usually PLUTUS__)
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


enironment_vars = flat_vars_to_nested_dict(
    os.environ.copy(), ENV_VAR_PREFIX,
)
config = deep_merge_dicts(enironment_vars, config)