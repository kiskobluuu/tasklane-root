import keyring

SERVICE = "BetweenPaySalesOS"

def set_secret(name: str, value: str) -> None:
    if value:
        keyring.set_password(SERVICE, name, value)

def get_secret(name: str) -> str | None:
    return keyring.get_password(SERVICE, name)

def delete_secret(name: str) -> None:
    try:
        keyring.delete_password(SERVICE, name)
    except keyring.errors.PasswordDeleteError:
        pass
