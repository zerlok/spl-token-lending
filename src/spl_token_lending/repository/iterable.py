import asyncio
import logging
import math
import typing as t

from solana.rpc.async_api import AsyncClient
from solders.signature import Signature
from solders.transaction_status import TransactionConfirmationStatus, TransactionStatus

_LOGGER = logging.getLogger(__name__)

DEFAULT_EXP_MAX_ATTEMPTS: t.Final[int] = 10
DEFAULT_EXP_INITIAL: t.Final[float] = 1.0
DEFAULT_EXP_ALPHA: t.Final[float] = 1.5


async def iter_with_exp_delay(
        max_attempts: int = DEFAULT_EXP_MAX_ATTEMPTS,
        initial: float = DEFAULT_EXP_INITIAL,
        alpha: float = DEFAULT_EXP_ALPHA,
) -> t.AsyncIterable[int]:
    for attempt in range(max_attempts):
        yield attempt

        if attempt + 1 < max_attempts:
            delay = initial * math.pow(alpha, attempt)
            await asyncio.sleep(delay)


async def wait_for_signature_status(
        client: AsyncClient,
        signature: Signature,
        expected: TransactionConfirmationStatus = TransactionConfirmationStatus.Finalized,
        max_attempts: int = DEFAULT_EXP_MAX_ATTEMPTS,
        initial: float = DEFAULT_EXP_INITIAL,
        alpha: float = DEFAULT_EXP_ALPHA,
) -> bool:
    async for _ in iter_with_exp_delay(max_attempts, initial, alpha):
        resp = await client.get_signature_statuses([signature])
        status = resp.value[0]

        _LOGGER.debug("signature status", extra={"signature": signature, "status": status})
        if isinstance(status, TransactionStatus) and status.confirmation_status == expected:
            return True

    return False
