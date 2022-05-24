import json
import os

from plutous.constants import DEFAULT_CONFIG, ENV_VAR_PREFIX
from plutous.utils import (
    flat_vars_to_nested_dict,
    deep_merge_dicts,
)


try:
    with open('plutous.json', 'r') as fopen:
        override_config = json.loads(fopen.read())
except FileNotFoundError:
    override_config = {}
    
    
config = deep_merge_dicts(override_config, DEFAULT_CONFIG)
enironment_vars = flat_vars_to_nested_dict(os.environ.copy(), ENV_VAR_PREFIX)
config = deep_merge_dicts(enironment_vars, config)