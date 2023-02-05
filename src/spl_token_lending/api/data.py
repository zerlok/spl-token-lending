import typing as t
import uuid

from pydantic import BaseModel, Extra, Field, root_validator, validator
from pydantic.generics import GenericModel

from spl_token_lending.repository.data import Amount, LoanItem
from spl_token_lending.serializable import PublicKeyObject, SignatureObject
from spl_token_lending.strict_typing import make_non_exhaustive_check_error

T = t.TypeVar("T")


class BaseObject(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.forbid


class ItemsViewObject(GenericModel, t.Generic[T]):
    class InfoObject(BaseObject):
        offset: int
        limit: int
        total: int

    info: InfoObject
    items: t.Sequence[T]


LoanStatus = t.Literal["PENDING", "ACTIVE", "CLOSED"]


def decode_loan_item_status(value: LoanStatus) -> LoanItem.Status:
    if value == "PENDING":
        return LoanItem.Status.PENDING
    elif value == "ACTIVE":
        return LoanItem.Status.ACTIVE
    elif value == "CLOSED":
        return LoanItem.Status.CLOSED
    else:
        raise make_non_exhaustive_check_error(value)


class LoanRequestObject(BaseObject):
    wallet: PublicKeyObject
    amount: Amount = Field(exclusiveMinimum=0)


class LoanSubmitObject(BaseObject):
    signature: SignatureObject


class LoanObject(BaseObject):
    id_: uuid.UUID = Field(alias="id")
    status: LoanStatus
    # FIXME: can't use `Pubkey` or `PublicKeyObject` types when `LoanObject` is returned by handler, the following
    #  exception occur: TypeError("'solders.pubkey.Pubkey' object is not iterable")
    wallet: str
    amount: Amount

    @root_validator(pre=True)
    def validate_id(cls, value: t.Mapping[str, object]) -> t.Mapping[str, object]:
        if "id_" not in value:
            return value

        clean_values = dict(value)
        id_ = clean_values.pop("id_")
        clean_values["id"] = id_

        return clean_values

    @validator("status", pre=True)
    def validate_status(cls, value: t.Union[LoanStatus, LoanItem.Status]) -> LoanStatus:
        if not isinstance(value, LoanItem.Status):
            return value
        elif value is LoanItem.Status.PENDING:
            return "PENDING"
        elif value is LoanItem.Status.ACTIVE:
            return "ACTIVE"
        elif value is LoanItem.Status.CLOSED:
            return "CLOSED"
        else:
            raise make_non_exhaustive_check_error(value)

    @validator("wallet", pre=True)
    def validate_wallet(cls, value: object) -> str:
        return str(PublicKeyObject.validate(value))
