from datetime import date
from uuid import UUID

from ninja import Schema


class RegisterIn(Schema):
    email: str
    password: str
    birth_date: date
    home_ags: str
    residence_ags: str
    invite_code: str | None = None
    accept_terms: bool = False
    pow: str | None = None


class TokenIn(Schema):
    token: str


class EmailPowIn(Schema):
    email: str
    pow: str | None = None


class LoginIn(Schema):
    email: str
    password: str
    pow: str | None = None


class ResetConfirmIn(Schema):
    uid: str
    token: str
    password: str


class PasswordChangeIn(Schema):
    current_password: str
    new_password: str


class PasswordIn(Schema):
    password: str


class PlaceChangeIn(Schema):
    field: str
    new_ags: str


class TextIn(Schema):
    text: str


class TokenTextIn(Schema):
    token: str
    text: str


class NearestIn(Schema):
    lat: float
    lon: float


class RequestIn(Schema):
    to_user_id: UUID
    body: str


class BodyIn(Schema):
    body: str


class BlockIn(Schema):
    user_id: UUID


class ReportIn(Schema):
    target_type: str
    target_id: UUID
    conversation_id: UUID | None = None
    reason: str
    note: str = ""
