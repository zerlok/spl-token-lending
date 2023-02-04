import typing as t


def make_non_exhaustive_check_error(*args: t.NoReturn) -> Exception:  # pragma: no cover
    return RuntimeError("missed condition check", *args)
