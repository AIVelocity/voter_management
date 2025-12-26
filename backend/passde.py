# decrypt_password_tool.py
# -----------------------------------
# Standalone Django-aware decrypt tool
# -----------------------------------

import os
import django
from cryptography.fernet import Fernet

# 🔹 STEP 1: Configure Django settings
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "backend.settings"   # ⚠️ CHANGE if your settings module is different
)

django.setup()

# 🔹 STEP 2: Import Django settings
from django.conf import settings


# 🔹 STEP 3: Setup Fernet using Django setting
fernet = Fernet(settings.PASSWORD_ENCRYPTION_KEY.encode())


def decrypt_password(encrypted_password: str) -> str:
    """
    Decrypts a Fernet-encrypted password
    """
    if not encrypted_password:
        return None
    return fernet.decrypt(encrypted_password.encode()).decode()


# 🔹 STEP 4: TEST / USE
if __name__ == "__main__":

    encrypted = (
        "gAAAAABpRkzNVtAtg1ge06wefWVhHVAbzFIlupUhVFb_c6_17gjEPSnHly1BYvzjflrBhwdYuEmJIaz0Vom02jQiJicXxoo1vQ=="
    )

    try:
        plain = decrypt_password(encrypted)
        print("✅ Decrypted password:", plain)
    except Exception as e:
        print("❌ Failed to decrypt:", str(e))
