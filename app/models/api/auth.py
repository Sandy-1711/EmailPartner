from __future__ import annotations

from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    display_name: str | None = None


class SignupResponse(BaseModel):
    user_id: str


class ConnectGmailRequest(BaseModel):
    user_id: str


class ConnectGmailResponse(BaseModel):
    auth_url: str


class OAuthCallbackResponse(BaseModel):
    gmail_account_id: str
    gmail_address: EmailStr


class DeleteAccountRequest(BaseModel):
    user_id: str


class GoogleSignInStartResponse(BaseModel):
    auth_url: str


class GoogleSignInCallbackResponse(BaseModel):
    user_id: str
    email: EmailStr
    display_name: str | None = None
    gmail_address: EmailStr | None = None


class MeResponse(BaseModel):
    user_id: str
    email: EmailStr
    display_name: str | None = None
    picture_url: str | None = None
    gmail_connected: bool
