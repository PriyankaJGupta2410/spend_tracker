"""Pydantic models for the auth module (register/login/me)."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Username = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
]


class UserCreate(BaseModel):
    username: Username
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username")
    @classmethod
    def lowercase_username(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def fits_bcrypt_limit(cls, value: str) -> str:
        # bcrypt only uses the first 72 bytes, so reject anything longer instead of truncating.
        if len(value.encode()) > 72:
            raise ValueError("password must be at most 72 bytes")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
