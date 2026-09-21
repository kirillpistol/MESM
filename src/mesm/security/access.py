from __future__ import annotations

CLASS_LEVEL = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "RESTRICTED": 2,
    "BANK_CONFIDENTIAL": 3,
    "HIGHLY_RESTRICTED": 4,
}

ROLE_MAX = {
    "BUSINESS_USER": 1,
    "MODEL_ANALYST": 1,
    "DATA_ENGINEER": 1,
    "AUDITOR": 3,
    "SECURITY_ADMIN": -1,  # управление политиками не дает автоматический доступ к данным
}

def can_read(role: str, data_class: str) -> bool:
    if role == "SECURITY_ADMIN":
        return False
    return ROLE_MAX.get(role, -1) >= CLASS_LEVEL.get(data_class, 999)
