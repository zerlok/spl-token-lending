import logging
import sys
import typing as t

from pythonjsonlogger import jsonlogger


def setup_logging(
        logging_level: t.Union[int, str],
        enable_json: bool,
) -> None:
    stdout_handler = logging.StreamHandler(sys.stdout)

    if enable_json:
        stdout_handler.setFormatter(jsonlogger.JsonFormatter(
            fmt=_make_logging_format(
                "levelname",
                "name",
                "funcName",
                "lineno",
                "message",
            ),
            timestamp=True,
        ))

    clean_logging_level = (
        logging.getLevelName(logging_level.strip().upper())
        if isinstance(logging_level, str) else logging_level
    )

    logging.basicConfig(
        format=_make_logging_format(
            "asctime",
            "levelname",
            "name",
            "message",
            sep=" :: ",
        ),
        level=clean_logging_level,
        handlers=[stdout_handler],
    )


def _make_logging_format(*fields: str, sep: str = ":") -> str:
    return sep.join(f"%({f})s" for f in fields)
