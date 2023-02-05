import typing as t


def make_non_exhaustive_check_error(*args: t.NoReturn) -> Exception:  # pragma: no cover
    """Enables exhaustiveness check in MyPy, see: https://github.com/python/mypy/issues/5818"""
    return RuntimeError("missed condition check", *args)
