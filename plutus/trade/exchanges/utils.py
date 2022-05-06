from typing import Callable, Optional, Awaitable, List, Dict, Any
from datetime import datetime, timedelta, timezone
import functools
import asyncio
import ccxt


Coroutine = Callable[[Any], Awaitable[List[Dict[str, Any]]]]


def preprocess(kwargs):
    """
    Update ``since`` in kwargs so that it accepts ``millisecond`` and ``datetime``
    """
    since = kwargs.get('since')
    if since is not None:
        if isinstance(since, datetime):
            kwargs['since'] = int(since.timestamp() * 1000)


def add_preprocess(cls):
    """
    Decorator for a ``ccxt.Exchange`` class to add ``preprocess`` to 
    all existing ``fetch_*`` function with ``since`` in argument.
    """
    def decorate(func: Coroutine) -> Coroutine:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> List[Dict[str, Any]]:
            kwargs.update(zip(func.__code__.co_varnames, args))
            preprocess(kwargs)
            return await func(**kwargs)
        return wrapper

    for attr in dir(cls):
        if 'fetch_' in attr:
            func: Callable = getattr(cls, attr)
            if 'since' in func.__code__.co_varnames:
                setattr(cls, attr, decorate(func))
    return cls


def paginate(
    id_arg: Optional[str] = 'fromId',
    start_time_arg: Optional[str] = 'startTime',
    end_time_arg: Optional[str] = 'endTime',
    max_limit: Optional[int] = float('inf'),
    max_interval: Optional[timedelta] = None,
) -> Callable:
    """
    Decorator for adding pagination to a ``ccxt.Exchange`` class's method
    based on specified settings.
    
    Parameters
    ----------
    id_arg : str, optional
        Parameter name to filter 
    """
    def decorator(func: Coroutine) -> Coroutine:
        async def paginate_over_limit(**kwargs) -> List[Dict[str, Any]]:
            limit = kwargs.get('limit') or float('inf')
            limit_arg = min(limit, max_limit)
            kwargs['limit'] = limit_arg if limit_arg != float('inf') else None

            records = await func(**kwargs)
            all_records = records
            limit -= max_limit

            while (records == max_limit) & (limit > 0):
                kwargs['limit'] = min(limit, max_limit)
                if id_arg in kwargs:
                    kwargs[id_arg] = int(records[-1]['id']) + 1
                elif start_time_arg in kwargs:
                    kwargs['since'] = int(records[-1]['timestamp']) + 1
                records = await func(**kwargs)
                all_records.extend(records)
                limit -= max_limit
            return all_records

        async def paginate_over_interval(**kwargs) -> List[Dict[str, Any]]:
            since = kwargs.get('since') or kwargs.get(start_time_arg)
            now = int(datetime.now(timezone.utc).timestamp() * 1000)
            end = kwargs.get(end_time_arg, now)
            if 'timeframe' in kwargs:
                diff = (
                    ccxt.Exchange.parse_timeframe(kwargs['timeframe']) 
                    * 1000 * max_limit
                )
                kwargs['limit'] = max_limit
            else:
                diff = (
                    int(max_interval.total_seconds() * 1000)
                    if max_interval is not None
                    else (now - since + 1)
                )
                
            coroutines = []
            for since in range(since, end, diff):
                params = kwargs.copy()
                params['since'] = since
                params[end_time_arg] = min(since + diff - 1, end)
                coroutines.append(paginate_over_limit(**params))

            records = []
            all_records = await asyncio.gather(*coroutines)
            for record in all_records:
                records.extend(record)

            return records

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> List[Dict[str, Any]]:
            kwargs.update(zip(func.__code__.co_varnames, args))
            preprocess(kwargs)
            if id_arg in kwargs:
                return await paginate_over_limit(**kwargs)
            if ('since' in kwargs) or (start_time_arg in kwargs):
                return await paginate_over_interval(**kwargs)
            return await func(**kwargs)
        return wrapper
    return decorator