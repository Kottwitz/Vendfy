from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialEncryptionError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = settings.security.credential_encryption_key
    if key is None:
        raise CredentialEncryptionError(
            "SECURITY__CREDENTIAL_ENCRYPTION_KEY must be configured."
        )
    try:
        return Fernet(key.get_secret_value().encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise CredentialEncryptionError(
            "SECURITY__CREDENTIAL_ENCRYPTION_KEY is invalid."
        ) from exc


def encrypt_credential(value: str) -> str:
    if not value:
        raise ValueError("Credential cannot be empty.")
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_credential(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError) as exc:
        raise CredentialEncryptionError(
            "Stored integration credential could not be decrypted."
        ) from exc
