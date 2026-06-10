"""Memoisation for the pure figure builders.

Every builder in ``app/figures`` is a pure function of its arguments: the same
(data, filtered frames, selection, axis choices) always yields the same figure.
Repeated brushing tends to revisit identical states (toggle a substance off then
on, clear then re-pick a country), so caching the builders returns those figures
without re-running the pandas aggregation + Plotly assembly.

``functools.lru_cache`` can't be used directly because the arguments aren't
hashable (the ``AppData`` singleton, DataFrames, the selection dict). ``_token``
turns each argument into a stable, hashable surrogate:

  * DataFrame / Series -> a content hash (``hash_pandas_object``) plus shape and
    columns, so a differently-filtered frame is a cache miss but an identical one
    is a hit;
  * dict / list / tuple / set -> recursively tokenised (selection dicts, the
    active-substance list, the year range);
  * the ``AppData`` singleton (and anything else unhashable) -> ``id()``: it is
    built once at import and lives for the whole process, so identity is a valid,
    cheap key.

Figures are treated as read-only after construction (the callback hands them
straight to Dash, which serialises them), so returning a shared cached object is
safe. Call ``<builder>.cache_clear()`` to drop a builder's cache.
"""
import functools
from collections import OrderedDict

import pandas as pd


def _token(arg):
    """Return a stable, hashable surrogate for one argument (see module doc)."""
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
        return tuple(sorted((k, _token(v)) for k, v in arg.items()))
    if isinstance(arg, (list, tuple)):
        return tuple(_token(v) for v in arg)
    if isinstance(arg, set):
        return ("set", tuple(sorted(_token(v) for v in arg)))
    try:
        hash(arg)
        return arg
    except TypeError:
        # AppData singleton, GeoDataFrame, etc. — constant for the process.
        return ("id", id(arg))


def memoize_figure(maxsize=256):
    """Decorator: cache a pure figure builder, keyed on tokenised arguments.

    LRU-bounded at ``maxsize`` distinct argument combinations. The decorated
    function gains a ``cache_clear()`` method.
    """
    def decorator(fn):
        cache: OrderedDict = OrderedDict()

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (_token(args),
                   tuple((k, _token(v)) for k, v in sorted(kwargs.items())))
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
