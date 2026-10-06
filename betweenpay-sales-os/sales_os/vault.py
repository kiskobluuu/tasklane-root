from __future__ import annotations

SERVICE = "BetweenPaySalesOS"


def _keyring():
    import keyring
    return keyring


def set_secret(name: str, value: str) -> None:
    value = (value or "").strip()
    if value:
        _keyring().set_password(SERVICE, name, value)


def get_secret(name: str) -> str | None:
    try:
        return _keyring().get_password(SERVICE, name)
    except Exception:
        return None


def has_secret(name: str) -> bool:
    return bool(get_secret(name))


def delete_secret(name: str) -> None:
    try:
        kr = _keyring()
        kr.delete_password(SERVICE, name)
    except Exception:
        pass
