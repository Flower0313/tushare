from datetime import datetime

from pydantic import BaseModel, Field, SecretStr, field_validator


class TushareTokenUpdate(BaseModel):
    token: SecretStr = Field(min_length=20, max_length=256)

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: SecretStr) -> SecretStr:
        token = value.get_secret_value().strip()
        if not token.isalnum():
            raise ValueError("Tushare Token 只能包含字母和数字")
        return SecretStr(token)


class TushareTokenStatus(BaseModel):
    configured: bool
    source: str
    token: str
    updated_at: datetime | None = None
