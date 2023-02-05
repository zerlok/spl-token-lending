"""Module provides serializers for Keypair, Pubkey and Signature classes, so it can be easily read/written from/to
json/text/file etc."""

import typing as t

from pydantic.fields import ModelField
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature


class KeyPairObject(Keypair):
    @classmethod
    def __get_validators__(cls) -> t.Iterable[t.Callable[[object], Keypair]]:
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema: t.MutableMapping[str, object], field: t.Optional[ModelField]) -> None:
        field_schema.update(type="string", example=str(Keypair.from_bytes([0] * 64)))

    @classmethod
    def validate(cls, value: object) -> Keypair:
        if isinstance(value, Keypair):
            return value

        if not isinstance(value, str):
            raise ValueError("value must be an encoded string", value)

        return Keypair.from_base58_string(value)


class PublicKeyObject(Pubkey):
    @classmethod
    def __get_validators__(cls) -> t.Iterable[t.Callable[[object], Pubkey]]:
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema: t.MutableMapping[str, object], field: t.Optional[ModelField]) -> None:
        field_schema.update(type="string", example=str(Pubkey([1] * 32)))

    @classmethod
    def validate(cls, value: object) -> Pubkey:
        if isinstance(value, Pubkey):
            return value

        if not isinstance(value, str):
            raise ValueError("value must be an encoded string", value)

        return Pubkey.from_string(value)


class SignatureObject(Signature):
    @classmethod
    def __get_validators__(cls) -> t.Iterable[t.Callable[[object], Signature]]:
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema: t.MutableMapping[str, object], field: t.Optional[ModelField]) -> None:
        field_schema.update(type="string", example=str(Signature(bytes([1] * 64))))

    @classmethod
    def validate(cls, value: object) -> Signature:
        if isinstance(value, Signature):
            return value

        if not isinstance(value, str):
            raise ValueError("value must be an encoded string", value)

        return Signature.from_string(value)
