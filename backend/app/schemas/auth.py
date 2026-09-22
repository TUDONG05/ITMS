from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_email = value.casefold().strip()
        if "@" not in normalized_email:
            raise ValueError("Email không hợp lệ.")
        return normalized_email


class NewPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=256)


class ChangePasswordRequest(NewPasswordRequest):
    current_password: str = Field(min_length=1, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_email = value.casefold().strip()
        if "@" not in normalized_email:
            raise ValueError("Email không hợp lệ.")
        return normalized_email


class ResetPasswordRequest(NewPasswordRequest):
    email: str = Field(min_length=3, max_length=254)
    otp: str = Field(pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_email = value.casefold().strip()
        if "@" not in normalized_email:
            raise ValueError("Email không hợp lệ.")
        return normalized_email


class AuthenticatedUser(BaseModel):
    id: str
    email: str
    full_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int
    user: AuthenticatedUser


class MessageResponse(BaseModel):
    message: str
