import enum
import typing as t
import uuid
from dataclasses import dataclass

from solders.pubkey import Pubkey

LoanId = t.NewType("LoanId", uuid.UUID)
Amount = t.NewType("Amount", int)


@dataclass(frozen=True)
class PaginationOptions:
    offset: int = 0
    limit: int = 1_000


@dataclass(frozen=True)
class LoanItem:
    class Status(enum.Enum):
        PENDING = enum.auto()
        ACTIVE = enum.auto()
        CLOSED = enum.auto()

    id_: LoanId
    status: Status
    wallet: Pubkey
    amount: Amount


@dataclass(frozen=True)
class LoanFilterOptions:
    id_equals: t.Optional[LoanId] = None
    status_equals: t.Optional[LoanItem.Status] = None
    wallet_equals: t.Optional[Pubkey] = None
