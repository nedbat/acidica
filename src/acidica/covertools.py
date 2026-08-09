import functools
import inspect
from collections.abc import Callable
from typing import ParamSpec, TypeVar

# coverage: exclude file

P = ParamSpec("P")
R = TypeVar("R")

try:
    import coverage
except:  # pragma: no cover

    def coverage_per_caller(func: Callable[P, R]) -> Callable[P, R]:
        return func
else:

    def coverage_per_caller(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            cov = coverage.Coverage.current()
            if cov is not None:
                assert cov._data is not None
                me = inspect.currentframe()
                assert me is not None
                caller = me.f_back
                assert caller is not None
                func_name = getattr(func, "__name__")
                new_context = f"per_caller:{func_name}:{caller.f_code.co_filename}:{caller.f_lineno}"
                prev_context = cov.switch_context(new_context)
                assert prev_context is not None
            try:
                ret = func(*args, **kwargs)
            finally:
                if cov is not None:
                    cov.switch_context(prev_context)
            return ret

        return _wrapper
