import typing as t
from dataclasses import dataclass

from spl_token_lending.repository.data import LoanItem

T = t.TypeVar("T")


@dataclass(frozen=True)
class InitializedUserLoan:
    item: LoanItem


@dataclass(frozen=True)
class SubmittedUserLoan:
    item: LoanItem


@dataclass(frozen=True)
class FailedUserLoan:
    error: str


@dataclass(frozen=True)
class ItemsView(t.Generic[T]):
    @dataclass(frozen=True)
    class Info:
        offset: int
        limit: int
        total: int

    info: Info
    items: t.Sequence[T]


InitializedUserLoanResult = t.Union[InitializedUserLoan, FailedUserLoan]
SubmittedUserLoanResult = t.Union[SubmittedUserLoan, FailedUserLoan]
