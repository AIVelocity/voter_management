from cryptography.fernet import Fernet
from django.conf import settings

fernet = Fernet(settings.PASSWORD_ENCRYPTION_KEY.encode())


def encrypt_password(raw_password: str) -> str:
    if raw_password is None:
        return None
    return fernet.encrypt(raw_password.encode()).decode()


def decrypt_password(encrypted_password: str) -> str:
    if encrypted_password is None:
        return None
    return fernet.decrypt(encrypted_password.encode()).decode()
