from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class SecuritySettings(BaseModel):
    jwt_secret_key: SecretStr | None = Field(default=None, min_length=32)
    credential_encryption_key: SecretStr | None = Field(default=None, min_length=44)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)
