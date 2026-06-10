import functools
from collections import OrderedDict

import pandas as pd


def token(arg):
    if isinstance(arg, pd.DataFrame):
        if len(arg) == 0:
            return ("df", 0, tuple(arg.columns))
        digest = int(pd.util.hash_pandas_object(arg, index=True).sum())
        return ("df", arg.shape, tuple(arg.columns), digest)
    if isinstance(arg, pd.Series):
        if len(arg) == 0:
            return ("series", 0)
        return ("series", int(pd.util.hash_pandas_object(arg, index=True).sum()))
    if isinstance(arg, dict):
        return tuple(sorted((k, token(v)) for k, v in arg.items()))
    if isinstance(arg, (list, tuple)):
        return tuple(token(v) for v in arg)
    if isinstance(arg, set):
        return ("set", tuple(sorted(token(v) for v in arg)))
    try:
        hash(arg)
        return arg
    except TypeError:
        # unhashable stuff like the data singleton, just use id
        return ("id", id(arg))


def memoize_figure(maxsize=256):
    def decorator(fn):
        cache: OrderedDict = OrderedDict()

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (token(args),
                   tuple((k, token(v)) for k, v in sorted(kwargs.items())))
            if key in cache:
                cache.move_to_end(key)
                return cache[key]
            result = fn(*args, **kwargs)
            cache[key] = result
            cache.move_to_end(key)
            if len(cache) > maxsize:
                cache.popitem(last=False)
            return result

        wrapper.cache_clear = cache.clear
        return wrapper

    return decorator
