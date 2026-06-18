from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterDeviceRequest(BaseModel):
    token: str = Field(min_length=1)
    platform: str = "android"
